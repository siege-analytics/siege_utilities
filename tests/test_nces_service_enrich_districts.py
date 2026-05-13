"""Tests for NCESPopulationService.enrich_school_districts.

Drives the real production method against the Django ORM, with the
downstream NCES API mocked. Covers the vectorised lookup-dict build
and the bulk_update updated_at handling.

Requires GDAL/PostGIS; skips otherwise.
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


def test_enrich_districts_applies_lookup_and_advances_updated_at(db):
    """Seed an unenriched SchoolDistrictUnified row, run enrich with
    a mocked download_district_data, and verify both the lookup
    fields and updated_at advanced."""
    import pandas as pd

    from siege_utilities.geo.django.models import SchoolDistrictUnified
    from siege_utilities.geo.django.services.nces_service import (
        NCESPopulationService,
    )

    year = 2097
    stale_time = datetime(2020, 1, 1, tzinfo=dt_timezone.utc)

    district = SchoolDistrictUnified.objects.create(
        feature_id=f"unified_{year}_0612345",
        geoid="0612345",
        name="Test Unified",
        lea_id="0612345",
        vintage_year=year,
        geometry=_make_polygon(),
        source="NCES EDGE",
        locale_code="",
    )
    SchoolDistrictUnified.objects.filter(pk=district.pk).update(
        updated_at=stale_time,
    )

    df = pd.DataFrame({
        "lea_id": ["0612345"],
        "locale_code": [21],
        "locale_category": ["suburban"],
        "locale_subcategory": ["suburban_large"],
    })

    service = NCESPopulationService()
    with patch.object(service, "_get_downloader") as mock_get:
        mock_get.return_value.download_district_data.return_value = df
        result = service.enrich_school_districts(year=year)

    assert result.records_updated == 1
    district.refresh_from_db()
    assert district.locale_code == "21"
    assert district.locale_category == "suburban"
    assert district.locale_subcategory == "suburban_large"
    assert district.updated_at > stale_time
    assert district.updated_at > datetime.now(dt_timezone.utc) - timedelta(minutes=5)


def test_enrich_districts_skips_when_lea_id_not_in_lookup(db):
    """Districts without a matching lea_id in the download must be
    counted as skipped, not silently updated to nulls."""
    import pandas as pd

    from siege_utilities.geo.django.models import SchoolDistrictUnified
    from siege_utilities.geo.django.services.nces_service import (
        NCESPopulationService,
    )

    year = 2096

    SchoolDistrictUnified.objects.create(
        feature_id=f"unified_{year}_9999999",
        geoid="9999999",
        name="Untouched",
        lea_id="9999999",
        vintage_year=year,
        geometry=_make_polygon(),
        source="NCES EDGE",
        locale_code="",
    )

    df = pd.DataFrame({
        "lea_id": ["0000001"],
        "locale_code": [11],
        "locale_category": ["city"],
        "locale_subcategory": ["city_large"],
    })

    service = NCESPopulationService()
    with patch.object(service, "_get_downloader") as mock_get:
        mock_get.return_value.download_district_data.return_value = df
        result = service.enrich_school_districts(year=year)

    assert result.records_skipped == 1
    assert result.records_updated == 0


def test_enrich_districts_flushes_updates_mid_loop(db):
    """When the queryset of matched districts exceeds batch_size,
    the in-loop bulk_update must fire. Seed batch_size+2 rows and
    assert bulk_update is invoked at least twice."""
    import pandas as pd

    from siege_utilities.geo.django.models import SchoolDistrictUnified
    from siege_utilities.geo.django.services.nces_service import (
        NCESPopulationService,
    )

    year = 2095
    batch_size = 3
    n_rows = batch_size + 2
    lea_ids = [f"070000{i}" for i in range(n_rows)]

    for lea in lea_ids:
        SchoolDistrictUnified.objects.create(
            feature_id=f"unified_{year}_{lea}",
            geoid=lea,
            name=f"District {lea}",
            lea_id=lea,
            vintage_year=year,
            geometry=_make_polygon(),
            source="NCES EDGE",
            locale_code="",
        )

    df = pd.DataFrame({
        "lea_id": lea_ids,
        "locale_code": [11] * n_rows,
        "locale_category": ["city"] * n_rows,
        "locale_subcategory": ["city_large"] * n_rows,
    })

    service = NCESPopulationService()
    with patch.object(service, "_get_downloader") as mock_get, \
         patch.object(
             SchoolDistrictUnified.objects, "bulk_update",
             wraps=SchoolDistrictUnified.objects.bulk_update,
         ) as mock_bulk_update:
        mock_get.return_value.download_district_data.return_value = df
        result = service.enrich_school_districts(
            year=year, batch_size=batch_size,
        )

    assert result.records_updated == n_rows
    assert mock_bulk_update.call_count >= 2, (
        f"expected at least 2 bulk_update calls for {n_rows} rows at "
        f"batch_size={batch_size}, got {mock_bulk_update.call_count}"
    )
