"""#1539 / #1550: every bulk site prepares rows and reports only rows inserted.

Complements the reviewer drop-ins (test_1539_bulk_prepare_and_counts.py,
test_1550_demographics_group_merge.py) by covering each remaining
``bulk_create`` site and the model-level ``prepare_for_bulk()`` contract.

The ORM is replaced by ``_Table``, an in-memory stand-in for ``Model.objects``
with a unique key. ``taken`` holds keys a concurrent writer already inserted:
they are invisible to the loader's existence check but make
``ON CONFLICT DO NOTHING`` drop the row, exactly the case where the old
``created += len(batch)`` overcounted. ``transaction.atomic`` is patched out.
GDAL/GEOS are required to import GeoDjango; no database is used.
"""

import contextlib
import io
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from django.core.exceptions import ImproperlyConfigured
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon

try:
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.gis.geos import GEOSGeometry
    from django.db import IntegrityError

    from siege_utilities.geo.django import models as gm
    from siege_utilities.geo.django.managers.boundary_manager import BoundaryManager
    from siege_utilities.geo.django.services._bulk import bulk_insert_counted
    from siege_utilities.geo.django.services.crosswalk_service import (
        CrosswalkPopulationService,
    )
    from siege_utilities.geo.django.services.demographic_service import (
        DemographicPopulationService,
    )
    from siege_utilities.geo.django.services.nces_service import NCESPopulationService
    from siege_utilities.geo.django.services.rollup_service import DemographicRollupService
    from siege_utilities.geo.django.services.timeseries_service import TimeseriesService
    from siege_utilities.geo.django.services.timezone_service import (
        TimezonePopulationService,
    )
except (ImportError, ImproperlyConfigured, OSError, RuntimeError):
    pytest.skip("GeoDjango (GDAL/GEOS) required", allow_module_level=True)

pytestmark = pytest.mark.requires_gdal

SQUARE = Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])
COUNTY_CT = ContentType(id=1, app_label="siege_geo", model="county")
TRACT_CT = ContentType(id=2, app_label="siege_geo", model="tract")


class _Table:
    """``Model.objects`` stand-in. Filters are ignored; ``count()`` is the row total."""

    def __init__(self, key, taken=(), rows=()):
        self.key, self.taken, self.rows, self.inserted = key, set(taken), list(rows), []

    def _qs(self):
        qs = MagicMock()
        qs.first.return_value = None
        qs.exists.return_value = False
        qs.count.side_effect = lambda: len(self.inserted)
        qs.iterator.side_effect = lambda *a, **kw: iter(self.rows)
        qs.__iter__.side_effect = lambda: iter(self.rows)
        qs.values_list.side_effect = lambda *a, **kw: list(self.taken)
        qs.order_by.return_value = qs
        qs.filter.return_value = qs
        return qs

    def filter(self, *a, **kw):
        return self._qs()

    def all(self):
        return self._qs()

    def bulk_create(self, objs, ignore_conflicts=False, **kw):
        objs = list(objs)
        for obj in objs:
            key = self.key(obj)
            if key in self.taken:
                if not ignore_conflicts:
                    raise IntegrityError(f"duplicate key {key}")
                continue
            self.taken.add(key)
            self.inserted.append(obj)
        return objs  # Django returns every input object under ignore_conflicts


@contextlib.contextmanager
def _no_db():
    with patch("django.db.transaction.Atomic.__enter__", lambda self: None), patch(
        "django.db.transaction.Atomic.__exit__", lambda self, *a: False
    ):
        yield


def _check_constraints(obj):
    """Mirror the PositiveIntegerField CHECK (>= 0) PostGIS enforces on insert."""
    for name in ("total_population", "median_household_income"):
        value = getattr(obj, name)
        if value is not None and value < 0:
            raise IntegrityError(f'new row violates check constraint "{name}_check"')


# ---------------------------------------------------------------------------
# prepare_for_bulk(): model contract
# ---------------------------------------------------------------------------


def test_census_boundary_prepare_for_bulk_derives_identity_and_returns_self():
    county = gm.County(geoid="06037", name="Los Angeles", vintage_year=2020)
    assert county.prepare_for_bulk() is county
    assert (county.feature_id, county.boundary_id, county.source) == (
        "06037", "06037", "TIGER/Line",
    )
    kept = gm.County(geoid="06037", vintage_year=2020, source="custom").prepare_for_bulk()
    assert kept.source == "custom"


def test_nces_locale_and_school_prepare_for_bulk():
    locale = gm.NCESLocaleBoundary(locale_code=11, nces_year=2023, vintage_year=2023)
    locale.prepare_for_bulk()
    assert (locale.feature_id, locale.boundary_id, locale.source) == (
        "nces_locale_11_2023", "nces_locale_11_2023", "NCES EDGE",
    )
    school = gm.SchoolLocation(ncessch="060000100001", vintage_year=2023).prepare_for_bulk()
    assert (school.feature_id, school.source) == ("060000100001", "NCES EDGE")


def test_other_temporal_models_prepare_for_bulk():
    tz = gm.TimezoneGeometry(timezone_id="America/Chicago", vintage_year=2024).prepare_for_bulk()
    assert (tz.feature_id, tz.boundary_id, tz.source, tz.name) == (
        "America/Chicago", "America/Chicago", "timezone-boundary-builder", "America/Chicago",
    )
    region = gm.NLRBRegion(region_number=7, vintage_year=2024).prepare_for_bulk()
    assert (region.feature_id, region.boundary_id, region.source) == ("NLRB-07", "NLRB-07", "NLRB")
    country = gm.GADMCountry(gid="USA", vintage_year=2024).prepare_for_bulk()
    assert (country.feature_id, country.boundary_id, country.source) == ("USA", "USA", "GADM")


def test_save_still_applies_the_derivations():
    saved = []
    with patch("django.db.models.Model.save_base", lambda self, *a, **kw: saved.append(self)):
        county = gm.County(geoid="06001", vintage_year=2020)
        county.save()
        snapshot = gm.DemographicSnapshot(
            content_type=COUNTY_CT, object_id="06001", year=2022, dataset="acs5",
            values={"B01001_001E": 1500, "B19013_001E": -666666666},
        )
        snapshot.save()
    assert saved == [county, snapshot]
    assert (county.feature_id, county.boundary_id, county.source) == ("06001", "06001", "TIGER/Line")
    assert (snapshot.total_population, snapshot.median_household_income) == (1500, None)


@pytest.mark.parametrize(
    "raw, expected",
    [
        (85000, 85000),
        ("85000", 85000),
        (85000.4, 85000),
        (0, 0),
        (-666666666, None),
        ("-666666666", None),
        (-999999999, None),
        (-888888888, None),
        ("N/A", None),
        (None, None),
        (float("nan"), None),
        (2**31, None),
    ],
)
def test_snapshot_sentinels_never_reach_typed_columns(raw, expected):
    snapshot = gm.DemographicSnapshot(
        values={"B01001_001E": raw, "B19013_001E": raw}
    ).prepare_for_bulk()
    assert snapshot.total_population == expected
    assert snapshot.median_household_income == expected
    assert snapshot.values["B19013_001E"] is raw  # the raw value stays in values


@pytest.mark.parametrize("raw, expected", [(38.4, 38.4), ("41.0", 41.0), (-666666666, None), (1000, None)])
def test_snapshot_median_age_guard(raw, expected):
    assert gm.DemographicSnapshot(values={"B01002_001E": raw}).prepare_for_bulk().median_age == expected


def test_snapshot_prepare_leaves_columns_without_a_source_variable_alone():
    # populate_pl_demographics sets total_population from P1_001N explicitly
    snapshot = gm.DemographicSnapshot(values={"P1_001N": 812.0}, total_population=812)
    assert snapshot.prepare_for_bulk().total_population == 812


def test_schemas_to_orm_returns_prepared_instances():
    from siege_utilities.geo.schemas.converters import schemas_to_orm

    schema = MagicMock(model_dump=MagicMock(return_value={"geoid": "06", "name": "CA", "vintage_year": 2020}))
    [state] = schemas_to_orm([schema], gm.State)
    assert (state.feature_id, state.boundary_id, state.source) == ("06", "06", "TIGER/Line")


# ---------------------------------------------------------------------------
# #1539 x #1550 interaction: sentinels on the bulk path
# ---------------------------------------------------------------------------


def test_bulk_insert_of_sentinel_snapshot_maps_to_null_not_integrity_error():
    """prepare_for_bulk() must not copy -666666666 into a CHECK (>= 0) column."""
    df = pd.DataFrame({
        "GEOID": ["06037", "06059"],
        "NAME": ["Los Angeles County", "Orange County"],
        "B01001_001E": ["1000", "-666666666"],
        "B19013_001E": ["-666666666", "91000"],
    })
    table = _Table(key=lambda o: o.object_id)
    real_bulk_create = table.bulk_create

    def enforcing_bulk_create(objs, **kw):
        objs = list(objs)
        for obj in objs:
            _check_constraints(obj)
        return real_bulk_create(objs, **kw)

    table.bulk_create = enforcing_bulk_create
    svc = DemographicPopulationService(api_key="dummy")
    svc._client = MagicMock(fetch_data=MagicMock(return_value=df))
    with _no_db(), patch.object(gm.DemographicSnapshot, "objects", table), patch.object(
        DemographicPopulationService, "_get_content_type", return_value=COUNTY_CT
    ):
        result = svc.populate("county", 2022, "06", variable_group="income")
    assert result.errors == [] and result.records_created == 2
    by_geoid = {s.object_id: s for s in table.inserted}
    assert (by_geoid["06037"].total_population, by_geoid["06037"].median_household_income) == (1000, None)
    assert (by_geoid["06059"].total_population, by_geoid["06059"].median_household_income) == (None, 91000)
    assert by_geoid["06037"].values["B19013_001E"] == -666666666  # raw kept in values
    assert all("NAME" not in s.values for s in table.inserted)


def test_update_without_flag_does_not_overwrite_existing_variables():
    existing = gm.DemographicSnapshot(
        content_type=TRACT_CT, object_id="06001400100", year=2022, dataset="acs5",
        values={"B01001_001E": 3000}, moe_values={},
    )
    table = _Table(key=lambda o: o.object_id)
    table.filter = lambda *a, **kw: MagicMock(first=MagicMock(return_value=existing))
    svc = DemographicPopulationService(api_key="dummy")
    df = pd.DataFrame({"GEOID": ["06001400100"], "B01001_001E": ["9999"]})
    svc._client = MagicMock(fetch_data=MagicMock(return_value=df))
    with _no_db(), patch.object(gm.DemographicSnapshot, "objects", table), patch.object(
        DemographicPopulationService, "_get_content_type", return_value=TRACT_CT
    ), patch.object(gm.DemographicSnapshot, "save_base", lambda self, *a, **kw: None):
        plain = svc.populate("tract", 2022, "06", variable_group="total_population")
        assert existing.values["B01001_001E"] == 3000
        assert (plain.records_updated, plain.records_skipped) == (0, 1)
        forced = svc.populate(
            "tract", 2022, "06", variable_group="total_population", update_existing=True
        )
    assert existing.values["B01001_001E"] == 9999
    assert existing.total_population == 9999
    assert (forced.records_updated, forced.records_skipped) == (1, 0)


def test_update_integrity_error_is_reported_without_aborting_the_group():
    existing = gm.DemographicSnapshot(
        content_type=TRACT_CT, object_id="06001400100", year=2022, dataset="acs5",
        values={"B01001_001E": 3000}, moe_values={},
    )
    table = _Table(key=lambda o: o.object_id)
    table.filter = lambda *a, **kw: MagicMock(first=MagicMock(return_value=existing))
    svc = DemographicPopulationService(api_key="dummy")
    df = pd.DataFrame({"GEOID": ["06001400100"], "B19013_001E": ["85000"]})
    svc._client = MagicMock(fetch_data=MagicMock(return_value=df))

    def reject(self, *a, **kw):
        raise IntegrityError("simulated CHECK violation")

    with _no_db(), patch.object(gm.DemographicSnapshot, "objects", table), patch.object(
        DemographicPopulationService, "_get_content_type", return_value=TRACT_CT
    ), patch.object(gm.DemographicSnapshot, "save_base", reject):
        result = svc.populate("tract", 2022, "06", variable_group="income")
    assert result.records_updated == 0
    assert result.errors == ["GEOID 06001400100: simulated CHECK violation"]


# ---------------------------------------------------------------------------
# Honest created counts at every ignore_conflicts site
# ---------------------------------------------------------------------------


def test_bulk_insert_counted_reports_rows_inserted_not_offered():
    table = _Table(key=lambda o: o, taken={"b"})
    assert bulk_insert_counted(table, ["a", "b", "c"], scope={}) == 2
    assert bulk_insert_counted(table, [], scope={}) == 0


def test_nces_locale_boundaries_prepared_and_counted():
    gdf = gpd.GeoDataFrame(
        {"locale_code": [11, 12, 21], "locale_category": ["City", "City", "Suburb"]},
        geometry=[SQUARE] * 3, crs="EPSG:4269",
    )
    table = _Table(key=lambda o: (o.locale_code, o.nces_year), taken={(21, 2023)})
    svc = NCESPopulationService()
    downloader = MagicMock(download_locale_boundaries=MagicMock(return_value=gdf))
    with _no_db(), patch.object(gm.NCESLocaleBoundary, "objects", table), patch.object(
        svc, "_get_downloader", return_value=downloader
    ):
        result = svc.populate_locale_boundaries(year=2023)
    assert result.records_created == 2
    assert [(o.feature_id, o.boundary_id) for o in table.inserted] == [
        ("nces_locale_11_2023", "nces_locale_11_2023"),
        ("nces_locale_12_2023", "nces_locale_12_2023"),
    ]


def test_nces_school_locations_prepared_and_counted():
    gdf = gpd.GeoDataFrame(
        {"ncessch": ["060000100001", "060000100002", "060000100001"],
         "school_name": ["A", "B", "A again"]},
        geometry=[ShapelyPoint(-118.2, 34.0)] * 3, crs="EPSG:4326",
    )
    table = _Table(key=lambda o: o.ncessch)
    states = _Table(key=lambda o: o.state_fips)
    svc = NCESPopulationService()
    downloader = MagicMock(download_school_locations=MagicMock(return_value=gdf))
    with _no_db(), patch.object(gm.SchoolLocation, "objects", table), patch.object(
        gm.State, "objects", states
    ), patch.object(svc, "_get_downloader", return_value=downloader):
        result = svc.populate_school_locations(year=2023)
    assert result.records_created == 2, "duplicate ncessch dropped by ON CONFLICT"
    assert [o.feature_id for o in table.inserted] == ["060000100001", "060000100002"]


def test_timezone_rows_counted(tmp_path):
    features = [
        {"type": "Feature", "properties": {"tzid": tzid},
         "geometry": json.loads(GEOSGeometry(SQUARE.wkt).json)}
        for tzid in ("America/Chicago", "America/Denver")
    ]
    path = Path(tmp_path) / "tz.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    table = _Table(key=lambda o: (o.timezone_id, o.vintage_year), taken={("America/Denver", 2024)})
    with _no_db(), patch.object(gm.TimezoneGeometry, "objects", table):
        result = TimezonePopulationService().populate_from_geojson(path, vintage_year=2024)
    assert result.records_created == 1
    [tz] = table.inserted
    assert (tz.feature_id, tz.boundary_id, tz.source) == (
        "America/Chicago", "America/Chicago", "timezone-boundary-builder",
    )


def test_crosswalk_rows_counted():
    df = pd.DataFrame({
        "source_geoid": ["06001400100", "06001400200"],
        "target_geoid": ["06001400100", "06001400201"],
        "weight": [1.0, 1.0],
    })
    table = _Table(
        key=lambda o: (o.source_boundary_id, o.target_boundary_id),
        taken={("06001400200", "06001400201")},
    )
    svc = CrosswalkPopulationService()
    with _no_db(), patch.object(gm.TemporalCrosswalk, "objects", table), patch.object(
        gm.CrosswalkDataset, "objects", MagicMock()
    ) as datasets, patch.object(svc, "_load_crosswalk_data", return_value=df):
        result = svc.populate("tract", 2010, 2020)
    assert result.records_created == 1
    assert datasets.update_or_create.call_args.kwargs["defaults"]["record_count"] == 1


def test_rollup_snapshots_prepared_and_counted():
    sources = [
        gm.DemographicSnapshot(content_type=TRACT_CT, object_id=geoid, year=2022,
                               dataset="acs5", values={"B01001_001E": pop})
        for geoid, pop in (("06037000100", 100), ("06037000200", 200), ("06059000100", 50))
    ]
    # Source rows are read through iterator(); only target keys can conflict.
    table = _Table(key=lambda o: o.object_id, taken={"06059"}, rows=sources)
    svc = DemographicRollupService()
    get_ct = MagicMock(side_effect=[TRACT_CT, COUNTY_CT])
    with _no_db(), patch.object(gm.DemographicSnapshot, "objects", table), patch.object(
        svc, "_resolve_model", return_value=MagicMock()
    ), patch.object(ContentType.objects, "get_for_model", get_ct):
        [result] = svc.rollup("tract", "county", 2022, ["B01001_001E"])
    assert result.records_created == 1, "06059 was inserted concurrently"
    [county] = table.inserted
    assert (county.object_id, county.total_population) == ("06037", 300)


def test_timeseries_rows_counted():
    snaps = [
        gm.DemographicSnapshot(object_id="06037", year=year, dataset="acs5",
                               values={"B01001_001E": pop}, moe_values={})
        for year, pop in ((2019, 100), (2020, 110))
    ]
    snapshots = _Table(key=lambda o: o.object_id, rows=snaps)
    series = _Table(key=lambda o: o.object_id, taken={"06059"})
    model = MagicMock()
    model.objects.all.return_value.values_list.return_value.distinct.return_value = ["06037", "06059"]
    del model.state_fips
    svc = TimeseriesService()
    with _no_db(), patch.object(gm.DemographicSnapshot, "objects", snapshots), patch.object(
        gm.DemographicTimeSeries, "objects", series
    ), patch.object(svc, "_resolve_model", return_value=model), patch.object(
        ContentType.objects, "get_for_model", return_value=COUNTY_CT
    ):
        [result] = svc.populate_timeseries(["B01001_001E"], [2019, 2020], "county")
    assert result.records_created == 1
    assert [s.object_id for s in series.inserted] == ["06037"]


def test_populate_pl_demographics_counts_inserted_rows():
    from django.core.management import call_command

    df = pd.DataFrame({"GEOID": ["06037", "06059"], "P1_001N": ["1000", "2000"]})
    table = _Table(key=lambda o: o.object_id, taken={"06059"})
    out = io.StringIO()
    downloader = MagicMock(get_data=MagicMock(return_value=df))
    with _no_db(), patch.object(gm.DemographicSnapshot, "objects", table), patch(
        "siege_utilities.geo.census_files.pl_downloader.PLFileDownloader",
        return_value=downloader,
    ), patch.object(ContentType.objects, "get_for_model", return_value=COUNTY_CT):
        call_command("populate_pl_demographics", "--state", "06", "--geography", "county",
                     stdout=out)
    assert "Created=1," in out.getvalue()
    [snap] = table.inserted
    assert snap.total_population == 1000


def test_boundary_manager_returns_only_inserted_objects():
    gdf = gpd.GeoDataFrame(
        {"GEOID": ["06037", "06059", "06037"], "NAME": ["LA", "Orange", "LA dup"]},
        geometry=[SQUARE] * 3, crs="EPSG:4326",
    )
    table = _Table(key=lambda o: o.geoid, taken={"06059"})
    manager = BoundaryManager()
    manager.model = gm.County
    with patch.object(manager, "filter", table.filter), patch.object(
        manager, "bulk_create", table.bulk_create
    ):
        created = manager.bulk_create_from_geodataframe(gdf, 2020)
    assert [(o.geoid, o.name) for o in created] == [("06037", "LA")]
    assert (created[0].feature_id, created[0].source) == ("06037", "TIGER/Line")


def test_no_loader_counts_ignore_conflicts_batches_directly():
    """Structural guard: ignore_conflicts=True only inside the counting helpers."""
    root = Path(__file__).resolve().parents[1] / "siege_utilities" / "geo" / "django"
    allowed = {root / "services" / "_bulk.py", root / "managers" / "boundary_manager.py"}
    offenders = [
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if path not in allowed and re.search(r"ignore_conflicts\s*=\s*True", path.read_text())
    ]
    assert offenders == []


def test_backfill_derived_fields_rejects_invalid_batch_size():
    from django.core.management import call_command
    from django.core.management.base import CommandError

    from siege_utilities.geo.django.management.commands.backfill_derived_fields import Command

    with pytest.raises(CommandError, match="--batch-size must be at least 1"):
        call_command(Command(), "--batch-size", "0", stdout=io.StringIO())
