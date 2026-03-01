"""Tests for pure-Python temporal services."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from siege_utilities.geo.temporal.services import (
    TemporalTimeseriesBuilder,
    TemporalDemographicService,
    TimeseriesBuildResult,
)


@pytest.fixture
def snapshots_df():
    """Multi-year snapshot data for a single tract."""
    rows = []
    for year, pop in [(2015, 4000), (2016, 4100), (2017, 4200),
                      (2018, 4300), (2019, 4400), (2020, 4600)]:
        rows.append({
            "boundary_id": "06037101100",
            "year": year,
            "values": {"B01001_001E": pop, "B19013_001E": 50000 + year * 10},
            "moe_values": {"B01001_001E": 100 + year - 2015},
        })
    return pd.DataFrame(rows)


@pytest.fixture
def multi_boundary_df():
    """Snapshot data for two tracts."""
    rows = []
    for bid, base in [("T001", 4000), ("T002", 3000)]:
        for year in [2015, 2016, 2017, 2018, 2019, 2020]:
            rows.append({
                "boundary_id": bid,
                "year": year,
                "values": {"B01001_001E": base + (year - 2015) * 100},
                "moe_values": {},
            })
    return pd.DataFrame(rows)


class TestTemporalTimeseriesBuilder:
    def test_build_single_variable(self, snapshots_df):
        builder = TemporalTimeseriesBuilder(dataset="acs5")
        results = builder.build(
            variables=["B01001_001E"],
            years=[2015, 2016, 2017, 2018, 2019, 2020],
            geography_type="tract",
            snapshots_df=snapshots_df,
        )
        assert len(results) == 1
        r = results[0]
        assert r.success
        assert r.records_created == 1
        ts = r.series[0]
        assert ts.start_year == 2015
        assert ts.end_year == 2020
        assert ts.trend_direction == "increasing"
        assert ts.mean_value is not None
        assert ts.cagr is not None

    def test_build_multiple_variables(self, snapshots_df):
        builder = TemporalTimeseriesBuilder(dataset="acs5")
        results = builder.build(
            variables=["B01001_001E", "B19013_001E"],
            years=[2015, 2016, 2017, 2018, 2019, 2020],
            geography_type="tract",
            snapshots_df=snapshots_df,
        )
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_build_multiple_boundaries(self, multi_boundary_df):
        builder = TemporalTimeseriesBuilder(dataset="acs5")
        results = builder.build(
            variables=["B01001_001E"],
            years=[2015, 2016, 2017, 2018, 2019, 2020],
            geography_type="tract",
            snapshots_df=multi_boundary_df,
        )
        assert results[0].records_created == 2

    def test_skip_insufficient_data(self):
        """Boundaries with <2 data points are skipped."""
        df = pd.DataFrame([{
            "boundary_id": "T001", "year": 2020,
            "values": {"B01001_001E": 4000}, "moe_values": {},
        }])
        builder = TemporalTimeseriesBuilder(dataset="acs5")
        results = builder.build(
            variables=["B01001_001E"],
            years=[2015, 2020],
            geography_type="tract",
            snapshots_df=df,
        )
        assert results[0].records_skipped == 1
        assert results[0].records_created == 0

    def test_moe_values_collected(self, snapshots_df):
        builder = TemporalTimeseriesBuilder(dataset="acs5")
        results = builder.build(
            variables=["B01001_001E"],
            years=[2015, 2016, 2017, 2018, 2019, 2020],
            geography_type="tract",
            snapshots_df=snapshots_df,
        )
        ts = results[0].series[0]
        assert len(ts.moe_values) > 0

    def test_no_store_no_df_raises(self):
        builder = TemporalTimeseriesBuilder(dataset="acs5")
        with pytest.raises(ValueError, match="Either snapshots_df or a store"):
            builder.build(
                variables=["B01001_001E"], years=[2020],
                geography_type="tract",
            )


class TestStatisticalMethods:
    """Verify statistical methods match Django TimeseriesService output."""

    def test_std_dev(self):
        values = [4000, 4100, 4200, 4300, 4400, 4600]
        mean = sum(values) / len(values)
        result = TemporalTimeseriesBuilder._std_dev(values, mean)
        assert isinstance(result, float)
        assert result > 0

    def test_std_dev_single_value(self):
        assert TemporalTimeseriesBuilder._std_dev([42], 42.0) == 0.0

    def test_cagr_positive(self):
        cagr = TemporalTimeseriesBuilder._cagr(4000, 4600, 5)
        assert cagr is not None
        assert cagr > 0

    def test_cagr_zero_start(self):
        assert TemporalTimeseriesBuilder._cagr(0, 100, 5) is None

    def test_cagr_zero_periods(self):
        assert TemporalTimeseriesBuilder._cagr(100, 200, 0) is None

    def test_trend_increasing(self):
        values = [100, 110, 120, 130, 140, 150]
        assert TemporalTimeseriesBuilder._trend_direction(values) == "increasing"

    def test_trend_decreasing(self):
        values = [150, 140, 130, 120, 110, 100]
        assert TemporalTimeseriesBuilder._trend_direction(values) == "decreasing"

    def test_trend_stable(self):
        values = [100, 101, 100, 99, 100, 101]
        assert TemporalTimeseriesBuilder._trend_direction(values) == "stable"

    def test_trend_single_value(self):
        assert TemporalTimeseriesBuilder._trend_direction([42]) == "stable"


class TestTemporalDemographicService:
    def test_build_snapshots(self):
        service = TemporalDemographicService()
        df = pd.DataFrame({
            "GEOID": ["06037101100", "06037101200"],
            "NAME": ["Tract 1", "Tract 2"],
            "B01001_001E": [4521, 3200],
            "B19013_001E": [75000, 62000],
            "B01001_001M": [150, 120],
            "B19013_001M": [5000, 4000],
        })
        snapshots = service.build_snapshots(df, "tract", 2022)
        assert len(snapshots) == 2
        assert snapshots[0].boundary_type == "tract"
        assert snapshots[0].boundary_id == "06037101100"
        assert snapshots[0].total_population == 4521
        assert snapshots[0].median_household_income == 75000

    def test_build_snapshots_moe(self):
        service = TemporalDemographicService()
        df = pd.DataFrame({
            "GEOID": ["06037101100"],
            "B01001_001E": [4521],
            "B01001_001M": [150],
        })
        snapshots = service.build_snapshots(df, "tract", 2022)
        assert snapshots[0].get_moe("B01001_001E") == 150

    def test_build_snapshots_custom_columns(self):
        service = TemporalDemographicService()
        df = pd.DataFrame({
            "GEOID": ["06"],
            "B01001_001E": [39000000],
            "EXTRA_COL": ["ignore"],
        })
        snapshots = service.build_snapshots(
            df, "state", 2022, variable_columns=["B01001_001E"]
        )
        assert len(snapshots) == 1
        assert "EXTRA_COL" not in snapshots[0].values
