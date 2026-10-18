"""Reviewer pre-check for #1613. Mocked ORM + autospec'd get_crosswalk; GDAL/GEOS required.

The three pre-check tests are verbatim; the tests after them cover the MERGED
relationship and the remaining Done-when items.
"""
import contextlib
import inspect
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.geos import GEOSGeometry  # noqa: F401
    from siege_utilities.geo.django.models import crosswalks as xw_models
    from siege_utilities.geo.django.services.crosswalk_service import CrosswalkPopulationService
except (ImportError, ImproperlyConfigured, OSError, RuntimeError):
    pytest.skip("GeoDjango (GDAL/GEOS) required", allow_module_level=True)

pytestmark = pytest.mark.requires_gdal

# Shape the real CrosswalkClient returns. Tract A splits 0.6 / 0.4; B->C has zero overlap.
CLIENT_DF = pd.DataFrame({
    "source_geoid": ["06001000100", "06001000100", "06001000200"],
    "target_geoid": ["06001000101", "06001000102", "06001000300"],
    "area_weight": [0.6, 0.4, 0.0],
})


class _Mgr:
    def __init__(self):
        self.inserted = []

    def filter(self, *a, **kw):
        qs = MagicMock()
        qs.first.return_value = None
        qs.exists.return_value = False
        qs.count.side_effect = lambda: len(self.inserted)
        return qs

    def bulk_create(self, objs, **kw):
        self.inserted.extend(objs)
        return list(objs)

    def update_or_create(self, *a, **kw):
        return MagicMock(), True


@contextlib.contextmanager
def _env():
    mgr = _Mgr()
    with patch("django.db.transaction.Atomic.__enter__", lambda self: None), patch(
        "django.db.transaction.Atomic.__exit__", lambda self, *a: False
    ), patch.object(xw_models.TemporalCrosswalk, "objects", mgr), patch.object(
        xw_models.CrosswalkDataset, "objects", _Mgr()
    ), patch(
        "siege_utilities.geo.crosswalk.get_crosswalk", autospec=True, return_value=CLIENT_DF.copy(),
    ) as get_xw:
        yield mgr, get_xw


def _level(get_xw):
    assert get_xw.call_args is not None, "get_crosswalk was never called successfully"
    from siege_utilities.geo.crosswalk.crosswalk_client import get_crosswalk
    bound = inspect.signature(get_crosswalk).bind(*get_xw.call_args.args, **get_xw.call_args.kwargs)
    bound.apply_defaults()
    return bound.arguments["geography_level"]


def _weights(mgr):
    return {(o.source_boundary_id, o.target_boundary_id): o.weight for o in mgr.inserted}


def test_populate_calls_client_with_real_signature_and_stores_area_weight():
    with _env() as (mgr, get_xw):
        result = CrosswalkPopulationService().populate("tract", 2010, 2020, state_fips="06")
    assert result.errors == []
    assert _level(get_xw) == "tract"
    assert _weights(mgr) == {
        ("06001000100", "06001000101"): pytest.approx(0.6),
        ("06001000100", "06001000102"): pytest.approx(0.4),
        ("06001000200", "06001000300"): 0.0,
    }


def test_block_group_crosswalk_uses_canonical_level_name():
    with _env() as (mgr, get_xw):
        CrosswalkPopulationService().populate_block_group_crosswalk(2010, 2020, state_fips="06")
    assert _level(get_xw) == "block_group"


def test_missing_weight_raises_or_errors_instead_of_defaulting_to_one():
    df = CLIENT_DF.drop(columns=["area_weight"])
    svc = CrosswalkPopulationService()
    with _env() as (mgr, _), patch.object(svc, "_load_crosswalk_data", return_value=df):
        try:
            result = svc.populate("tract", 2010, 2020, state_fips="06")
        except (KeyError, ValueError):
            return
    assert result.errors and not any(o.weight == 1.0 for o in mgr.inserted)


# --- Remaining #1613 Done-when items -----------------------------------------

def _relationships(mgr):
    return {(o.source_boundary_id, o.target_boundary_id): o.relationship for o in mgr.inserted}


def test_two_sources_at_full_weight_into_one_target_are_merged():
    df = pd.DataFrame({
        "source_geoid": ["06001000100", "06001000200", "06001000300", "06001000400", "06001000400"],
        "target_geoid": ["06001000900", "06001000900", "06001000300", "06001000401", "06001000402"],
        "area_weight": [1.0, 1.0, 1.0, 0.7, 0.3],
    })
    svc = CrosswalkPopulationService()
    with _env() as (mgr, _), patch.object(svc, "_load_crosswalk_data", return_value=df):
        result = svc.populate("tract", 2010, 2020, state_fips="06")
    assert result.errors == []
    assert _relationships(mgr) == {
        ("06001000100", "06001000900"): "MERGED",
        ("06001000200", "06001000900"): "MERGED",
        ("06001000300", "06001000300"): "IDENTICAL",
        ("06001000400", "06001000401"): "SPLIT",
        ("06001000400", "06001000402"): "SPLIT",
    }


def test_nan_weight_is_an_error_not_a_full_allocation():
    df = CLIENT_DF.copy()
    df.loc[1, "area_weight"] = float("nan")
    svc = CrosswalkPopulationService()
    with _env() as (mgr, _), patch.object(svc, "_load_crosswalk_data", return_value=df):
        result = svc.populate("tract", 2010, 2020, state_fips="06")
    assert len(result.errors) == 1 and "06001000102" in result.errors[0]
    assert _weights(mgr) == {("06001000100", "06001000101"): pytest.approx(0.6),
                             ("06001000200", "06001000300"): 0.0}


def test_blockgroup_alias_is_stored_under_canonical_level():
    with _env() as (mgr, get_xw):
        result = CrosswalkPopulationService().populate("blockgroup", 2010, 2020, state_fips="06")
    assert _level(get_xw) == "block_group"
    assert result.geography_type == "block_group"
    assert {(o.source_type, o.target_type) for o in mgr.inserted} == {("block_group", "block_group")}
