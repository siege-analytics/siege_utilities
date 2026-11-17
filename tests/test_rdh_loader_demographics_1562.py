"""RDHLoaderService.load_demographics_for_plan: districts with no census unit (#1562)."""

import warnings
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

gpd = pytest.importorskip("geopandas")

from shapely.geometry import box  # noqa: E402

try:
    from django.core.exceptions import ImproperlyConfigured
except ImportError:  # Django absent; the service import below raises ImportError
    ImproperlyConfigured = ImportError
try:
    from siege_utilities.geo.django.services.rdh_loader import RDHLoaderService
    # The loader imports these GeoDjango models at call time; they need GDAL.
    import siege_utilities.geo.django.models.redistricting  # noqa: F401

    HAS_GDAL = True
except (ImportError, ImproperlyConfigured, OSError):
    # GeoDjango without system libgdal raises ImproperlyConfigured (OSError for
    # an unloadable GDAL_LIBRARY_PATH). Narrowed so unrelated errors still fail.
    HAS_GDAL = False

pytestmark = [
    pytest.mark.requires_gdal,
    pytest.mark.skipif(not HAS_GDAL, reason="GeoDjango/GDAL not available"),
]


def _plan(*geoids):
    districts = {geoid: MagicMock(geoid=geoid) for geoid in geoids}
    queryset = MagicMock()
    queryset.exists.return_value = True
    queryset.filter.side_effect = lambda geoid: MagicMock(
        first=MagicMock(return_value=districts.get(geoid))
    )
    plan = SimpleNamespace(state_fips="01", districts=MagicMock())
    plan.districts.exclude.return_value = queryset
    return plan, districts


def _plan_gdf(*geoids):
    return gpd.GeoDataFrame(
        {"geoid": list(geoids)},
        geometry=[box(10 * i, 0, 10 * (i + 1), 10) for i in range(len(geoids))],
        crs=5070,
    )


def _census(*cells):
    """Census units by (district slot, population); slot 9 lies outside every district."""
    return gpd.GeoDataFrame(
        {"TOTPOP": [population for _, population in cells]},
        geometry=[box(10 * slot + 1, 1, 10 * slot + 2, 2) for slot, _ in cells],
        crs=5070,
    )


def _load(plan, plan_gdf, census):
    service = RDHLoaderService(client=MagicMock())
    with patch(
        "siege_utilities.geo.schemas.converters.orm_to_gdf", return_value=plan_gdf
    ), patch(
        "siege_utilities.geo.django.models.redistricting.DistrictDemographics"
    ) as model, warnings.catch_warnings():
        # The loader must report demographic_profile's warnings, not leak them.
        warnings.simplefilter("error")
        # Bypass @transaction.atomic: the skip logic needs no database.
        result = RDHLoaderService.load_demographics_for_plan.__wrapped__(
            service, plan, 2020, census_gdf=census,
        )
    return result, model.objects.update_or_create


def _stored_districts(update_or_create):
    return [call.kwargs["district"].geoid for call in update_or_create.call_args_list]


def test_district_without_units_is_skipped_not_overwritten_with_zeros():
    plan, _ = _plan("D1", "D2")

    result, update_or_create = _load(plan, _plan_gdf("D1", "D2"), _census((0, 100)))

    assert _stored_districts(update_or_create) == ["D1"]
    assert update_or_create.call_args.kwargs["defaults"] == {"values": {"TOTPOP": 100}}
    assert result.success
    assert result.records_created == 1 and result.records_skipped == 1
    assert len(result.warnings) == 1 and "D2" in result.warnings[0]


def test_no_district_receiving_units_is_an_error():
    plan, _ = _plan("D1", "D2")

    result, update_or_create = _load(plan, _plan_gdf("D1", "D2"), _census((9, 100)))

    update_or_create.assert_not_called()
    assert not result.success
    assert "No district matched" in result.errors[0]
    assert result.records_created == 0 and result.records_skipped == 2
    # The excluded unit is reported as a warning in the result, not leaked.
    assert any("1 census unit(s)" in message for message in result.warnings)


def test_every_district_receiving_units_stores_all_without_warnings():
    plan, _ = _plan("D1", "D2")

    result, update_or_create = _load(
        plan, _plan_gdf("D1", "D2"), _census((0, 100), (1, 200)),
    )

    assert _stored_districts(update_or_create) == ["D1", "D2"]
    assert result.success and result.records_created == 2 and result.records_skipped == 0
    assert result.warnings == [] and result.errors == []
