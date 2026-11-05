"""Reviewer pre-check for #1604. In-memory ORM stand-in; GDAL/GEOS required.

The three pre-check tests are verbatim except for ``_env``: it also stands in
the boundary tables (``_Boundaries``, empty by default), because coverage now
counts expected children from them (#1604 Done-when). The tests after the
pre-check block cover the remaining Done-when items.
"""
import contextlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.gis.geos import GEOSGeometry  # noqa: F401
    from siege_utilities.geo.django import models as gm
    from siege_utilities.geo.django.models.crosswalks import TemporalCrosswalk
    from siege_utilities.geo.django.services.crosswalk_service import CrosswalkPopulationService
    from siege_utilities.geo.django.services.rollup_service import DemographicRollupService
except (ImportError, ImproperlyConfigured, OSError, RuntimeError):
    pytest.skip("GeoDjango (GDAL/GEOS) required", allow_module_level=True)

pytestmark = pytest.mark.requires_gdal

CTS = {m: ContentType(id=i, app_label="siege_geo", model=m.__name__.lower())
       for i, m in enumerate([gm.Tract, gm.County, gm.BlockGroup, gm.State], start=1)}
TRACT_CT, COUNTY_CT = CTS[gm.Tract], CTS[gm.County]


def _match(obj, key, want):
    field, _, op = key.partition("__")
    have = getattr(obj, field)
    return {"": lambda: have == want, "startswith": lambda: str(have).startswith(want),
            "in": lambda: have in want}[op]()


class _QS(list):
    def filter(self, **kw):
        return _QS(o for o in self if all(_match(o, k, v) for k, v in kw.items()))

    def first(self):
        return self[0] if self else None

    def exists(self):
        return bool(self)

    def count(self):
        return len(self)

    def iterator(self, *a, **kw):
        return iter(list(self))

    def order_by(self, *a):
        return self


class _Table:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def all(self):
        return _QS(self.rows)

    def filter(self, **kw):
        return self.all().filter(**kw)

    def bulk_create(self, objs, **kw):
        self.rows.extend(o for o in objs if o not in self.rows)
        return list(objs)

    def bulk_update(self, objs, fields, **kw):
        return len(objs)


def _snap(ct, geoid, year, value, pop=None, var="B19013_001E"):
    return gm.DemographicSnapshot(content_type=ct, object_id=geoid, year=year,
                                  dataset="acs5", values={var: value}, total_population=pop)


class _Boundaries:
    """Boundary-manager stand-in: geoid/vintage_year rows, the lookups coverage uses."""

    def __init__(self, rows=()):
        self.rows = list(rows)

    def filter(self, **kw):
        def keep(row):
            for key, want in kw.items():
                field, _, op = key.partition("__")
                have = getattr(row, field)
                if not {"": lambda: have == want, "lte": lambda: have <= want,
                        "startswith": lambda: str(have).startswith(want)}[op]():
                    return False
            return True
        return _Boundaries(r for r in self.rows if keep(r))

    def aggregate(self, **kw):
        ((alias, agg),) = kw.items()
        values = [getattr(r, agg.source_expressions[0].name) for r in self.rows]
        return {alias: max(values) if values else None}

    def values_list(self, field, flat=False):
        return [getattr(r, field) for r in self.rows]


@contextlib.contextmanager
def _env(snaps, crosswalks=(), boundaries=()):
    table = _Table(snaps)

    def save_base(self, *a, **kw):
        if self not in table.rows:
            table.rows.append(self)

    with patch.object(gm.DemographicSnapshot, "objects", table), patch.object(
        gm.DemographicSnapshot, "save_base", save_base
    ), patch.object(TemporalCrosswalk, "objects", _Table(crosswalks)), patch.object(
        ContentType.objects, "get_for_model", side_effect=lambda m, **kw: CTS[m]
    ), contextlib.ExitStack() as stack:
        for model in CTS:
            rows = [b for b in boundaries if b[0] is model]
            stack.enter_context(patch.object(model, "objects", _Boundaries(
                SimpleNamespace(geoid=g, vintage_year=v) for _, g, v in rows)))
        yield table


def _county(table, geoid="06001", year=2022):
    return table.filter(content_type=COUNTY_CT, object_id=geoid, year=year).first()


def test_default_rollup_does_not_overwrite_existing_county_value():
    snaps = [_snap(TRACT_CT, "06001400100", 2022, 50000), _snap(TRACT_CT, "06001400200", 2022, 70000),
             _snap(COUNTY_CT, "06001", 2022, 99999)]  # county value fetched from the API
    with _env(snaps) as table:
        DemographicRollupService().rollup("tract", "county", 2022, ["B19013_001E"], operation="avg")
    assert _county(table).values["B19013_001E"] == 99999


def test_crosswalk_weighted_avg_maps_to_target_level_and_applies_weight_once():
    # 2010 tract A (value 100, pop 1000) splits 0.5/0.5; tract B (300, 3000) maps 1.0.
    # Population-weighted mean for county 06001 = (100*1000 + 300*3000) / 4000 = 250.
    snaps = [_snap(TRACT_CT, "06001000100", 2020, 100, pop=1000),
             _snap(TRACT_CT, "06001000200", 2020, 300, pop=3000)]
    xw = [TemporalCrosswalk(source_boundary_id=s, target_boundary_id=t, source_type="tract",
                            target_type="tract", source_vintage_year=2010,
                            target_vintage_year=2020, weight=w, state_fips="06")
          for s, t, w in [("06001000100", "06001000300", 0.5), ("06001000100", "06001000400", 0.5),
                          ("06001000200", "06001000500", 1.0)]]
    with _env(snaps, xw) as table:
        DemographicRollupService().rollup("tract", "county", 2020, ["B19013_001E"],
                                          operation="weighted_avg", crosswalk_year=2010)
    county_rows = table.filter(content_type=COUNTY_CT)
    assert [s.object_id for s in county_rows] == ["06001"], "crosswalk targets not mapped to county"
    assert county_rows[0].values["B19013_001E"] == pytest.approx(250.0)


def test_block_group_crosswalks_written_by_loader_are_found_by_rollup():
    with patch.object(CrosswalkPopulationService, "populate") as loader:
        CrosswalkPopulationService().populate_block_group_crosswalk(2010, 2020)
    stored_type = loader.call_args.args[0]
    xw = [TemporalCrosswalk(source_boundary_id="060014001001", target_boundary_id="060014001001",
                            source_type=stored_type, target_type=stored_type,
                            source_vintage_year=2010, target_vintage_year=2020, weight=1.0,
                            state_fips="06")]
    with _env([], xw):
        mapping = DemographicRollupService()._build_crosswalk_map("block_group", 2010, 2020)
    assert mapping == {"060014001001": [("060014001001", 1.0)]}


# --- Remaining #1604 Done-when items -----------------------------------------

def _two_tract_snaps(county_value=None):
    snaps = [_snap(TRACT_CT, "06001400100", 2022, 50000), _snap(TRACT_CT, "06001400200", 2022, 70000)]
    if county_value is not None:
        snaps.append(_snap(COUNTY_CT, "06001", 2022, county_value))
    return snaps


def test_default_rollup_reports_existing_value_as_skipped_not_updated():
    with _env(_two_tract_snaps(county_value=99999)):
        (result,) = DemographicRollupService().rollup(
            "tract", "county", 2022, ["B19013_001E"], operation="avg")
    assert (result.records_created, result.records_updated, result.records_skipped) == (0, 0, 1)


def test_overwrite_true_replaces_value_and_counts_an_update():
    with _env(_two_tract_snaps(county_value=99999)) as table:
        (result,) = DemographicRollupService().rollup(
            "tract", "county", 2022, ["B19013_001E"], operation="avg", overwrite=True)
    assert _county(table).values["B19013_001E"] == pytest.approx(60000.0)
    assert (result.records_created, result.records_updated, result.records_skipped) == (0, 1, 0)


def test_existing_target_without_the_variable_gets_it_added_as_an_update():
    snaps = _two_tract_snaps() + [_snap(COUNTY_CT, "06001", 2022, 1234, var="B01001_001E")]
    with _env(snaps) as table:
        (result,) = DemographicRollupService().rollup(
            "tract", "county", 2022, ["B19013_001E"], operation="avg")
    assert _county(table).values == {"B01001_001E": 1234, "B19013_001E": pytest.approx(60000.0)}
    assert (result.records_created, result.records_updated, result.records_skipped) == (0, 1, 0)


def test_coverage_counts_expected_children_from_boundary_table():
    # Two 2020-vintage tracts in county 06001, only one has a snapshot. The 2010
    # vintage and the vintage after the data year must not be counted.
    boundaries = [(gm.Tract, "06001400100", 2020), (gm.Tract, "06001400200", 2020),
                  (gm.Tract, "06001999900", 2010), (gm.Tract, "06001888800", 2030)]
    snaps = [_snap(TRACT_CT, "06001400100", 2022, 50000)]
    with _env(snaps, boundaries=boundaries) as table:
        (result,) = DemographicRollupService().rollup(
            "tract", "county", 2022, ["B19013_001E"], operation="avg")
    assert result.coverage_ratio == 0.5
    assert _county(table).values["B19013_001E"] == 50000


def test_coverage_in_crosswalk_mode_counts_crosswalk_sources():
    snaps = [_snap(TRACT_CT, "06001000100", 2020, 100, pop=1000)]
    xw = [TemporalCrosswalk(source_boundary_id=s, target_boundary_id=t, source_type="tract",
                            target_type="tract", source_vintage_year=2010,
                            target_vintage_year=2020, weight=1.0, state_fips="06")
          for s, t in [("06001000100", "06001000300"), ("06001000200", "06001000500")]]
    with _env(snaps, xw):
        (result,) = DemographicRollupService().rollup(
            "tract", "county", 2020, ["B19013_001E"], operation="avg", crosswalk_year=2010)
    assert result.coverage_ratio == 0.5


def _split_crosswalk():
    return [TemporalCrosswalk(source_boundary_id=s, target_boundary_id=t, source_type="tract",
                              target_type="tract", source_vintage_year=2010,
                              target_vintage_year=2020, weight=w, state_fips="06")
            for s, t, w in [("06001000100", "06001000300", 0.5),
                            ("06001000100", "06001000400", 0.5),
                            ("06001000200", "06001000500", 1.0)]]


@pytest.mark.parametrize("operation, expected", [
    ("sum", 100 * 0.5 + 100 * 0.5 + 300 * 1.0),        # allocated shares: 400
    ("avg", (100 * 0.5 + 100 * 0.5 + 300) / 2.0),      # split tract counts once: 200
])
def test_crosswalk_sum_and_avg_apply_weight_once(operation, expected):
    snaps = [_snap(TRACT_CT, "06001000100", 2020, 100, pop=1000),
             _snap(TRACT_CT, "06001000200", 2020, 300, pop=3000)]
    with _env(snaps, _split_crosswalk()) as table:
        DemographicRollupService().rollup("tract", "county", 2020, ["B19013_001E"],
                                          operation=operation, crosswalk_year=2010)
    assert _county(table, year=2020).values["B19013_001E"] == pytest.approx(expected)


def test_crosswalk_map_ignores_rows_whose_target_is_another_level():
    xw = [TemporalCrosswalk(source_boundary_id="06001000100", target_boundary_id=t,
                            source_type="tract", target_type=tt, source_vintage_year=2010,
                            target_vintage_year=2020, weight=1.0, state_fips="06")
          for t, tt in [("06001000300", "tract"), ("06001", "county")]]
    with _env([], xw):
        mapping = DemographicRollupService()._build_crosswalk_map("tract", 2010, 2020)
    assert mapping == {"06001000100": [("06001000300", 1.0)]}


def test_blockgroup_alias_is_canonicalised_in_rollup():
    xw = [TemporalCrosswalk(source_boundary_id="060014001001", target_boundary_id="060014001001",
                            source_type="block_group", target_type="block_group",
                            source_vintage_year=2010, target_vintage_year=2020, weight=1.0,
                            state_fips="06")]
    with _env([], xw):
        mapping = DemographicRollupService()._build_crosswalk_map("blockgroup", 2010, 2020)
        (result,) = DemographicRollupService().rollup("blockgroup", "tract", 2020, ["X"])
    assert mapping == {"060014001001": [("060014001001", 1.0)]}
    assert result.source_level == "block_group" and result.errors == []
