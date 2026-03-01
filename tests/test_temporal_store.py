"""Tests for TemporalDataStore save/load/query."""

import tempfile
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

pyarrow = pytest.importorskip("pyarrow", reason="pyarrow required for Parquet tests")

from siege_utilities.geo.temporal.store import TemporalDataStore, get_temporal_store


@pytest.fixture
def tmp_store(tmp_path):
    """Create a TemporalDataStore in a temp directory."""
    return TemporalDataStore(root_dir=tmp_path)


@pytest.fixture
def sample_boundaries():
    """Small GeoDataFrame of state boundaries."""
    return gpd.GeoDataFrame(
        {
            "geoid": ["06", "48"],
            "name": ["California", "Texas"],
            "state_fips": ["06", "48"],
            "vintage_year": [2020, 2020],
        },
        geometry=[box(-124, 32, -114, 42), box(-106, 25, -93, 36)],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_demographics():
    """Simple demographics DataFrame."""
    return pd.DataFrame({
        "boundary_id": ["06037101100", "06037101200"],
        "year": [2022, 2022],
        "dataset": ["acs5", "acs5"],
        "values": [
            {"B01001_001E": 4521, "B19013_001E": 75000},
            {"B01001_001E": 3200, "B19013_001E": 62000},
        ],
    })


class TestBoundaries:
    def test_save_and_load(self, tmp_store, sample_boundaries):
        path = tmp_store.save_boundaries(sample_boundaries, "state", 2020)
        assert path.exists()

        loaded = tmp_store.load_boundaries("state", 2020)
        assert len(loaded) == 2
        assert set(loaded["geoid"]) == {"06", "48"}

    def test_load_with_state_filter(self, tmp_store, sample_boundaries):
        tmp_store.save_boundaries(sample_boundaries, "state", 2020)
        loaded = tmp_store.load_boundaries("state", 2020, state_fips="06")
        assert len(loaded) == 1
        assert loaded.iloc[0]["geoid"] == "06"

    def test_load_missing_raises(self, tmp_store):
        with pytest.raises(FileNotFoundError):
            tmp_store.load_boundaries("state", 1999)

    def test_list_available_vintages(self, tmp_store, sample_boundaries):
        tmp_store.save_boundaries(sample_boundaries, "state", 2010)
        tmp_store.save_boundaries(sample_boundaries, "state", 2020)
        vintages = tmp_store.list_available_vintages("state")
        assert vintages == [2010, 2020]

    def test_list_vintages_empty(self, tmp_store):
        assert tmp_store.list_available_vintages("nonexistent") == []

    def test_query_boundaries_at_date(self, tmp_store, sample_boundaries):
        tmp_store.save_boundaries(sample_boundaries, "state", 2010)
        tmp_store.save_boundaries(sample_boundaries, "state", 2020)

        result = tmp_store.query_boundaries_at_date(
            "state", date(2022, 6, 1)
        )
        assert len(result) == 2  # Should pick 2020 vintage

    def test_query_boundaries_before_earliest(self, tmp_store, sample_boundaries):
        tmp_store.save_boundaries(sample_boundaries, "state", 2020)
        # Date before any vintage — falls back to earliest
        result = tmp_store.query_boundaries_at_date(
            "state", date(2005, 1, 1)
        )
        assert len(result) == 2

    def test_query_no_vintages_raises(self, tmp_store):
        with pytest.raises(FileNotFoundError):
            tmp_store.query_boundaries_at_date("state", date(2022, 1, 1))

    def test_gpkg_format(self, tmp_path, sample_boundaries):
        store = TemporalDataStore(root_dir=tmp_path, format="gpkg")
        store.save_boundaries(sample_boundaries, "state", 2020)
        loaded = store.load_boundaries("state", 2020)
        assert len(loaded) == 2
        assert store.list_available_vintages("state") == [2020]


class TestDemographics:
    def test_save_and_load(self, tmp_store, sample_demographics):
        tmp_store.save_demographics(
            sample_demographics, "tract", dataset="acs5", year=2022
        )
        loaded = tmp_store.load_demographics("tract", year=2022, dataset="acs5")
        assert len(loaded) == 2

    def test_load_all_years(self, tmp_store, sample_demographics):
        tmp_store.save_demographics(
            sample_demographics, "tract", dataset="acs5", year=2021
        )
        tmp_store.save_demographics(
            sample_demographics, "tract", dataset="acs5", year=2022
        )
        loaded = tmp_store.load_demographics("tract", dataset="acs5")
        assert len(loaded) == 4  # 2 rows x 2 years

    def test_year_from_dataframe(self, tmp_store, sample_demographics):
        tmp_store.save_demographics(sample_demographics, "tract", dataset="acs5")
        loaded = tmp_store.load_demographics("tract", year=2022, dataset="acs5")
        assert len(loaded) == 2

    def test_load_missing_raises(self, tmp_store):
        with pytest.raises(FileNotFoundError):
            tmp_store.load_demographics("tract", year=9999)


class TestTimeSeries:
    def test_save_and_load(self, tmp_store):
        ts_df = pd.DataFrame({
            "boundary_id": ["T001", "T002"],
            "variable_code": ["B01001_001E", "B01001_001E"],
            "years": [[2015, 2020], [2015, 2020]],
            "values": [[4000, 4500], [3000, 3200]],
        })
        tmp_store.save_timeseries(
            ts_df, "tract", variable_code="B01001_001E", dataset="acs5"
        )
        loaded = tmp_store.load_timeseries("tract", "B01001_001E", dataset="acs5")
        assert len(loaded) == 2

    def test_variable_code_from_df(self, tmp_store):
        ts_df = pd.DataFrame({
            "boundary_id": ["T001"],
            "variable_code": ["B19013_001E"],
            "years": [[2015, 2020]],
            "values": [[50000, 60000]],
        })
        tmp_store.save_timeseries(ts_df, "tract", dataset="acs5")
        loaded = tmp_store.load_timeseries("tract", "B19013_001E", dataset="acs5")
        assert len(loaded) == 1

    def test_load_missing_raises(self, tmp_store):
        with pytest.raises(FileNotFoundError):
            tmp_store.load_timeseries("tract", "NONEXISTENT", dataset="acs5")


class TestConvenience:
    def test_get_temporal_store_singleton(self, tmp_path):
        import siege_utilities.geo.temporal.store as store_mod
        store_mod._SINGLETON = None  # Reset

        s1 = get_temporal_store(root_dir=tmp_path)
        s2 = get_temporal_store()
        assert s1 is s2
        store_mod._SINGLETON = None  # Clean up

    def test_unsupported_format_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported format"):
            TemporalDataStore(root_dir=tmp_path, format="csv")
