"""Tests for siege_utilities.geo.census.catalog_cache."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.census.catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusFamily,
    CensusSubject,
    CensusTable,
    CensusVariable,
    FamilyType,
)
from siege_utilities.geo.census.catalog_cache import (
    CatalogCache,
    CatalogLoader,
    _catalog_from_dict,
    _catalog_to_dict,
)


def _make_catalog():
    """Build a small catalog for round-trip tests."""
    cat = CensusCatalog()

    v1 = CensusVariable(
        code="B19001_001E",
        label="Estimate!!Total:",
        concept="HOUSEHOLD INCOME",
        table_id="B19001",
    )
    v2 = CensusVariable(
        code="B19001_002E",
        label="Estimate!!Total:!!Less than $10,000",
        concept="HOUSEHOLD INCOME",
        table_id="B19001",
    )
    t1 = CensusTable(
        table_id="B19001",
        label="HOUSEHOLD INCOME",
        concept="HOUSEHOLD INCOME",
        variables=[v1, v2],
        geography_levels=["state", "county", "tract"],
    )
    t2 = CensusTable(
        table_id="B19001A",
        label="HOUSEHOLD INCOME (WHITE ALONE)",
        concept="HOUSEHOLD INCOME (WHITE ALONE)",
    )
    t3 = CensusTable(
        table_id="B01001",
        label="SEX BY AGE",
        concept="SEX BY AGE",
    )

    cat.add_tables([t1, t2, t3])

    fam = CensusFamily(
        family_id="race:B19001",
        family_type=FamilyType.RACE_ITERATION,
        root_table_id="B19001",
        tables=[t1, t2],
        description="Race iterations of B19001",
    )
    cat.add_family(fam)

    sub = CensusSubject(
        subject_id="income",
        label="Income",
        tables=[t1, t3],
    )
    cat.add_subject(sub)

    ds = CensusCatalogDataset(
        dataset_id="acs5_2022",
        survey_type="acs_5yr",
        year=2022,
        subjects=[sub],
        tables={"B19001": t1, "B01001": t3},
    )
    cat.add_dataset(ds)

    return cat


class TestSerializationRoundTrip:
    def test_round_trip_preserves_tables(self):
        cat = _make_catalog()
        data = _catalog_to_dict(cat)
        restored = _catalog_from_dict(data)
        assert set(restored.tables.keys()) == set(cat.tables.keys())

    def test_round_trip_preserves_variables(self):
        cat = _make_catalog()
        data = _catalog_to_dict(cat)
        restored = _catalog_from_dict(data)
        t = restored.get_table("B19001")
        assert len(t.variables) == 2
        assert t.variables[0].code == "B19001_001E"

    def test_round_trip_preserves_families(self):
        cat = _make_catalog()
        data = _catalog_to_dict(cat)
        restored = _catalog_from_dict(data)
        fam = restored.get_family("race:B19001")
        assert fam is not None
        assert fam.family_type == FamilyType.RACE_ITERATION
        assert "B19001" in fam.table_ids
        assert "B19001A" in fam.table_ids

    def test_round_trip_preserves_subjects(self):
        cat = _make_catalog()
        data = _catalog_to_dict(cat)
        restored = _catalog_from_dict(data)
        sub = restored.get_subject("income")
        assert sub is not None
        assert len(sub.tables) == 2

    def test_round_trip_preserves_datasets(self):
        cat = _make_catalog()
        data = _catalog_to_dict(cat)
        restored = _catalog_from_dict(data)
        ds = restored.get_dataset("acs5_2022")
        assert ds is not None
        assert ds.year == 2022
        assert ds.survey_type == "acs_5yr"
        assert "B19001" in ds.tables

    def test_round_trip_preserves_geography(self):
        cat = _make_catalog()
        data = _catalog_to_dict(cat)
        restored = _catalog_from_dict(data)
        t = restored.get_table("B19001")
        assert "tract" in t.geography_levels

    def test_dict_is_json_serializable(self):
        cat = _make_catalog()
        data = _catalog_to_dict(cat)
        text = json.dumps(data)
        assert isinstance(text, str)


class TestCatalogCache:
    def test_put_and_get(self, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path, ttl_days=30)
        cat = _make_catalog()
        cache.put("acs5", 2022, cat)

        restored = cache.get("acs5", 2022)
        assert restored is not None
        assert set(restored.tables.keys()) == set(cat.tables.keys())

    def test_get_returns_none_on_miss(self, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        assert cache.get("acs5", 2022) is None

    def test_expired_entry_returns_none(self, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path, ttl_days=0)
        cat = _make_catalog()
        cache.put("acs5", 2022, cat)

        path = cache._cache_path("acs5", 2022)
        old_time = time.time() - 86400
        import os
        os.utime(path, (old_time, old_time))

        assert cache.get("acs5", 2022) is None

    def test_clear_specific(self, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        cat = _make_catalog()
        cache.put("acs5", 2022, cat)
        cache.put("acs5", 2021, cat)
        assert cache.clear("acs5", 2022) == 1
        assert cache.get("acs5", 2022) is None
        assert cache.get("acs5", 2021) is not None

    def test_clear_all(self, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        cat = _make_catalog()
        cache.put("acs5", 2022, cat)
        cache.put("acs5", 2021, cat)
        assert cache.clear() == 2
        assert cache.get("acs5", 2022) is None

    def test_clear_empty_dir(self, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path / "nonexistent")
        assert cache.clear() == 0

    def test_corrupt_file_returns_none(self, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        path = cache._cache_path("acs5", 2022)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json", encoding="utf-8")
        assert cache.get("acs5", 2022) is None


class TestCatalogLoader:
    @patch("siege_utilities.geo.census.catalog_populator.CensusCatalogPopulator")
    def test_returns_cached_catalog(self, mock_pop_cls, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        cat = _make_catalog()
        cache.put("acs5", 2022, cat)

        loader = CatalogLoader(cache=cache)
        result = loader.load("acs5", 2022)

        assert set(result.tables.keys()) == set(cat.tables.keys())
        mock_pop_cls.assert_not_called()

    @patch("siege_utilities.geo.census.catalog_populator.CensusCatalogPopulator")
    def test_fetches_on_cache_miss(self, mock_pop_cls, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        cat = _make_catalog()
        mock_pop_cls.return_value.populate.return_value = cat

        loader = CatalogLoader(cache=cache)
        result = loader.load("acs5", 2022)

        mock_pop_cls.return_value.populate.assert_called_once_with(
            "acs5", 2022, survey_type=""
        )
        assert set(result.tables.keys()) == set(cat.tables.keys())
        # Should have been cached
        assert cache.get("acs5", 2022) is not None

    @patch("siege_utilities.geo.census.catalog_populator.CensusCatalogPopulator")
    def test_force_refresh_skips_cache(self, mock_pop_cls, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        cat = _make_catalog()
        cache.put("acs5", 2022, cat)
        mock_pop_cls.return_value.populate.return_value = cat

        loader = CatalogLoader(cache=cache)
        loader.load("acs5", 2022, force_refresh=True)

        mock_pop_cls.return_value.populate.assert_called_once()

    @patch("siege_utilities.geo.census.catalog_populator.CensusCatalogPopulator")
    def test_passes_base_url(self, mock_pop_cls, tmp_path):
        cache = CatalogCache(cache_dir=tmp_path)
        cat = _make_catalog()
        mock_pop_cls.return_value.populate.return_value = cat

        loader = CatalogLoader(cache=cache, base_url="https://custom.api")
        loader.load("acs5", 2022)

        mock_pop_cls.assert_called_once_with(base_url="https://custom.api")
