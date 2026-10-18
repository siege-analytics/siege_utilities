"""Live PostGIS regressions for calendar-year CAGR, MOE alignment and reads (#1622)."""

import os
from statistics import mean, pstdev

import pytest

if os.environ.get("SIEGE_TEST_POSTGIS") != "1":
    pytest.skip(
        "Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* for live PostGIS tests.",
        allow_module_level=True,
    )

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import connection
from django.test.utils import CaptureQueriesContext

from siege_utilities.geo.django.models import County, ZCTA
from siege_utilities.geo.django.models.demographics import (
    DemographicSnapshot,
    DemographicTimeSeries,
)
from siege_utilities.geo.django.services.timeseries_service import TimeseriesService

pytestmark = [pytest.mark.postgis, pytest.mark.django_db]

VARIABLE = "B01001_001E"
OTHER_VARIABLE = "B01002_001E"


@pytest.fixture
def make_county():
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)

    def create(geoid="06037", vintage=2020):
        return County.objects.create(
            geoid=geoid, state_fips=geoid[:2], county_fips=geoid[2:],
            vintage_year=vintage, geometry=geometry,
        )

    return create


def add_snapshots(boundary, years, values, moes, dataset="acs5"):
    content_type = ContentType.objects.get_for_model(boundary)
    for year, value, moe in zip(years, values, moes):
        DemographicSnapshot.objects.create(
            content_type=content_type, object_id=boundary.geoid,
            dataset=dataset, year=year, values={VARIABLE: value},
            moe_values={} if moe is None else {VARIABLE: moe},
        )


def populate(boundary, years, dataset="acs5", update=False):
    if update:
        DemographicTimeSeries.objects.create(
            content_type=ContentType.objects.get_for_model(boundary),
            object_id=boundary.geoid, variable_code=VARIABLE, dataset=dataset,
            start_year=min(years), end_year=max(years), years=years,
            values=[1] * len(years), moe_values=[], cagr=0.5,
        )
    [result] = TimeseriesService(dataset=dataset).populate_timeseries(
        [VARIABLE], years, "county", update_existing=update,
    )
    assert result.success
    assert (result.records_created, result.records_updated, result.records_skipped) == (
        int(not update), int(update), 0,
    )
    return DemographicTimeSeries.objects.get(object_id=boundary.geoid)


@pytest.mark.parametrize("update", [False, True], ids=["create", "update"])
@pytest.mark.parametrize(
    "years,dataset,expected",
    [
        ([2000, 2010, 2020], "dec", 0.009576582776887),
        ([2012, 2017, 2022], "acs5", 0.019244876491457),
        ([2018, 2019, 2020], "acs5", 0.10),
    ],
    ids=["decennial", "sparse-acs", "annual"],
)
def test_cagr_uses_calendar_year_span(make_county, years, dataset, expected, update):
    county = make_county()
    add_snapshots(county, years, [1000, 1100, 1210], [50, 45, 40], dataset)
    series = populate(county, list(reversed(years)), dataset, update)
    assert series.years == years
    assert series.values == [1000, 1100, 1210]
    assert series.cagr == pytest.approx(expected)
    if dataset == "dec":
        assert series.cagr != pytest.approx(0.10)


@pytest.mark.parametrize("update", [False, True], ids=["create", "update"])
@pytest.mark.parametrize("moes", [[50, None, 40], [None, None, None]])
def test_moes_keep_missing_positions(make_county, update, moes):
    county = make_county()
    years = [2018, 2019, 2020]
    add_snapshots(county, years, [1000, 1100, 1210], moes)
    series = populate(county, years, update=update)
    assert series.moe_values == moes
    assert series.moe_values[1] is None
    assert len(series.years) == len(series.values) == len(series.moe_values) == 3


@pytest.mark.parametrize("requested_years", [[], [2020], [2020, 2020]])
def test_fewer_than_two_observations_are_skipped(make_county, requested_years):
    county = make_county()
    add_snapshots(county, [2020], [1000], [50])
    [result] = TimeseriesService().populate_timeseries(
        [VARIABLE], requested_years, "county",
    )
    assert result.success
    assert (result.records_created, result.records_updated, result.records_skipped) == (0, 0, 1)
    assert not DemographicTimeSeries.objects.exists()
    with pytest.raises(ValueError, match="periods > 0"):
        TimeseriesService._cagr(1000, 1000, 0)


@pytest.mark.parametrize("county_count", [1, 8])
@pytest.mark.parametrize("mode", ["create", "skip", "update"])
def test_batched_reads_match_per_geoid_values(make_county, county_count, mode):
    """Read counts stay fixed as GEOIDs grow, including existence checks."""
    years = [2018, 2019, 2020]
    variables = [VARIABLE, OTHER_VARIABLE]
    content_type = ContentType.objects.get_for_model(County)
    expected = {}
    for index in range(county_count):
        county = make_county(f"06{index + 1:03d}")
        # Multiple boundary vintages still represent just one timeseries.
        make_county(county.geoid, vintage=2010)
        for offset, year in enumerate(years):
            DemographicSnapshot.objects.create(
                content_type=content_type, object_id=county.geoid, dataset="acs5", year=year,
                values={VARIABLE: 1000 * (index + 1) + 100 * offset,
                        OTHER_VARIABLE: None if offset == 0 else 30 + offset},
                moe_values={VARIABLE: 50 - offset} if offset != 1 else {},
            )
        # Independent per-GEOID read, outside the captured service queries.
        for variable in variables:
            snapshots = list(DemographicSnapshot.objects.filter(
                content_type=content_type, object_id=county.geoid, dataset="acs5",
                year__in=years,
            ).order_by("year"))
            snapshots = [s for s in snapshots if s.values.get(variable) is not None]
            expected[county.geoid, variable] = (
                [s.year for s in snapshots], [s.values[variable] for s in snapshots],
                [s.moe_values.get(variable) for s in snapshots],
            )

    service = TimeseriesService()
    if mode != "create":
        service.populate_timeseries(variables, years, "county")
    if mode == "update":
        DemographicTimeSeries.objects.update(values=[-1], moe_values=[], cagr=0.5)

    with CaptureQueriesContext(connection) as queries:
        results = service.populate_timeseries(
            variables, years, "county", update_existing=mode == "update",
        )

    # iterator() may use DECLARE CURSOR; count the table reads in either form.
    snapshot_reads = [q for q in queries if f'FROM "{DemographicSnapshot._meta.db_table}"' in q["sql"]]
    existing_reads = [q for q in queries if (
        f'FROM "{DemographicTimeSeries._meta.db_table}"' in q["sql"]
        and "COUNT(" not in q["sql"]
    )]
    assert len(snapshot_reads) == len(variables)
    assert len(existing_reads) == len(variables)

    for result in results:
        assert result.success
        assert result.records_created == (county_count if mode == "create" else 0)
        assert result.records_updated == (county_count if mode == "update" else 0)
        assert result.records_skipped == (county_count if mode == "skip" else 0)
    stored = list(DemographicTimeSeries.objects.all())
    assert len(stored) == county_count * len(variables)
    for series in stored:
        expected_years, values, moes = expected[series.object_id, series.variable_code]
        assert series.years == expected_years
        assert series.values == values
        assert series.moe_values == moes
        assert (series.start_year, series.end_year) == (expected_years[0], expected_years[-1])
        assert series.mean_value == pytest.approx(mean(values))
        assert series.std_dev == pytest.approx(pstdev(values))
        assert series.cagr == pytest.approx(
            (values[-1] / values[0]) ** (1 / (expected_years[-1] - expected_years[0])) - 1
        )
        assert series.trend_direction == service._trend_direction(values)


def test_batched_reads_preserve_scope_and_existing_intervals(make_county):
    county = make_county()
    outside_state = make_county("13001")
    empty_county = make_county("06059")
    years = [2018, 2019, 2020]
    add_snapshots(county, years, [1000, None, 1210], [50, 45, 40])
    add_snapshots(county, years, [9000, 9000, 9000], [1, 1, 1], dataset="acs1")
    add_snapshots(county, [2021], [9000], [1])
    add_snapshots(outside_state, years, [9000, 9000, 9000], [1, 1, 1])
    zcta = ZCTA.objects.create(
        geoid=county.geoid, zcta5=county.geoid, vintage_year=2020, geometry=county.geometry,
    )
    add_snapshots(zcta, years, [8000, 8000, 8000], [1, 1, 1])
    other_interval = DemographicTimeSeries.objects.create(
        content_type=ContentType.objects.get_for_model(County), object_id=county.geoid,
        variable_code=VARIABLE, dataset="acs5", start_year=2018, end_year=2019,
        years=[2018, 2019], values=[1000, 1100], moe_values=[50, 45],
    )
    [result] = TimeseriesService().populate_timeseries(
        [VARIABLE], years, "county", state_fips="06", update_existing=True,
    )
    assert (result.records_created, result.records_updated, result.records_skipped) == (1, 0, 1)
    series = DemographicTimeSeries.objects.get(object_id=county.geoid, end_year=2020)
    assert series.years == [2018, 2020]
    assert series.values == [1000, 1210]
    assert series.moe_values == [50, 40]
    assert series.cagr == pytest.approx(0.10)
    other_interval.refresh_from_db()
    assert other_interval.values == [1000, 1100]
    assert not DemographicTimeSeries.objects.filter(object_id=empty_county.geoid).exists()
    assert not DemographicTimeSeries.objects.filter(object_id=outside_state.geoid).exists()


@pytest.mark.parametrize("start_value", [0, -666666666])
def test_nonpositive_start_keeps_existing_cagr_behavior(make_county, start_value):
    county = make_county()
    years = [2010, 2020]
    add_snapshots(county, years, [start_value, 1000], [None, None])
    series = populate(county, years)
    assert series.values == [start_value, 1000]
    assert series.mean_value == pytest.approx(mean([start_value, 1000]))
    assert series.cagr is None
