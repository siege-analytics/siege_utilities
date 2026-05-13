"""Regression test for the bulk_update timestamp fix.

Django's auto_now=True does not fire under bulk_update. The
NCESPopulationService methods now set ``updated_at`` explicitly and
include it in the bulk_update field list; this test verifies the
existing-row path actually advances ``updated_at``.

Requires PostGIS test DB; skips when GDAL is absent.
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest

try:
    from django.contrib.gis.geos import MultiPolygon, Polygon

    HAS_GDAL = True
except Exception:
    HAS_GDAL = False

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.requires_gdal,
    pytest.mark.skipif(not HAS_GDAL, reason="GDAL/PostGIS not available"),
]


def _make_polygon():
    return MultiPolygon(Polygon(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))))


def test_populate_locale_boundaries_advances_updated_at_on_update(db):
    """If a NCESLocaleBoundary already exists for (locale_code, year),
    re-running populate with update_existing=True must bump
    ``updated_at`` to reflect the rewrite. bulk_update bypasses
    auto_now=True, so the service has to set it explicitly. If anyone
    removes that explicit assignment, this test goes red."""
    import geopandas as gpd

    from siege_utilities.geo.django.models import NCESLocaleBoundary
    from siege_utilities.geo.django.services.nces_service import (
        NCESPopulationService,
    )

    year = 2099
    stale_time = datetime(2020, 1, 1, tzinfo=dt_timezone.utc)

    existing = NCESLocaleBoundary.objects.create(
        feature_id=f"nces_locale_11_{year}",
        locale_code=11,
        locale_category="city_old",
        locale_subcategory="city_large_old",
        nces_year=year,
        vintage_year=year,
        name="Old Name",
        geometry=_make_polygon(),
        source="NCES EDGE",
    )
    NCESLocaleBoundary.objects.filter(pk=existing.pk).update(
        updated_at=stale_time,
    )
    existing.refresh_from_db()
    assert existing.updated_at == stale_time

    gdf = gpd.GeoDataFrame(
        {
            "locale_code": [11],
            "locale_category": ["city"],
            "locale_subcategory": ["city_large"],
            "name": ["New Name"],
        },
        geometry=[_make_polygon()],
        crs="EPSG:4326",
    )

    service = NCESPopulationService()
    with patch.object(service, "_get_downloader") as mock_get:
        mock_get.return_value.download_locale_boundaries.return_value = gdf
        result = service.populate_locale_boundaries(
            year=year, update_existing=True,
        )

    assert result.records_updated == 1
    existing.refresh_from_db()
    assert existing.updated_at > stale_time, (
        "bulk_update did not advance updated_at; "
        "auto_now=True does not fire under bulk_update and the service "
        "must set the field explicitly."
    )
    assert existing.updated_at > datetime.now(dt_timezone.utc) - timedelta(
        minutes=5,
    )
    assert existing.name == "New Name"
