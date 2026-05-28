"""Tests for RDH dataset catalog and discovery (SU#633)."""

from __future__ import annotations

import json
import time

import pytest

from siege_utilities.geo.rdh_catalog import (
    CatalogEntry,
    CoverageCell,
    DictRDHCatalogProvider,
    RDHCatalog,
    SearchResult,
    _infer_chamber,
    _score_entry,
)


def _entry(state="TX", year="2020", dtype="pl94171", fmt="csv", **kw):
    defaults = dict(
        title=f"{state} {dtype} {year}",
        url=f"https://example.com/{state}_{dtype}_{year}.{fmt}",
        state=state,
        year=year,
        dataset_type=dtype,
        format=fmt,
    )
    defaults.update(kw)
    return CatalogEntry(**defaults)


class TestCatalogEntry:
    def test_defaults(self):
        e = CatalogEntry()
        assert e.title == ""
        assert e.state == ""

    def test_matches_exact(self):
        e = _entry(state="TX", year="2020", dtype="pl94171")
        assert e.matches(state="TX")
        assert e.matches(year="2020")
        assert e.matches(dataset_type="pl94171")
        assert e.matches(state="TX", year="2020")

    def test_matches_case_insensitive(self):
        e = _entry(state="TX", dtype="PL94171")
        assert e.matches(state="tx")
        assert e.matches(dataset_type="pl94171")

    def test_matches_no_match(self):
        e = _entry(state="TX")
        assert not e.matches(state="CA")
        assert not e.matches(year="2022")

    def test_matches_no_filters(self):
        e = _entry()
        assert e.matches()

    def test_matches_format(self):
        e = _entry(fmt="csv")
        assert e.matches(format="csv")
        assert not e.matches(format="shp")

    def test_matches_chamber(self):
        e = _entry(chamber="congress")
        assert e.matches(chamber="congress")
        assert not e.matches(chamber="state_senate")

    def test_to_dict_roundtrip(self):
        e = _entry(state="VA", official=True)
        d = e.to_dict()
        e2 = CatalogEntry.from_dict(d)
        assert e2.state == "VA"
        assert e2.official is True
        assert e2.url == e.url

    def test_from_dict_missing_keys(self):
        e = CatalogEntry.from_dict({"title": "Test"})
        assert e.title == "Test"
        assert e.state == ""
        assert e.official is False


class TestDictProvider:
    def test_empty(self):
        p = DictRDHCatalogProvider()
        assert p.fetch_all_datasets() == []

    def test_add_and_fetch(self):
        p = DictRDHCatalogProvider()
        p.add(_entry())
        assert len(p.fetch_all_datasets()) == 1

    def test_init_with_entries(self):
        entries = [_entry(), _entry(state="CA")]
        p = DictRDHCatalogProvider(entries)
        assert len(p.fetch_all_datasets()) == 2

    def test_returns_copy(self):
        p = DictRDHCatalogProvider([_entry()])
        a = p.fetch_all_datasets()
        b = p.fetch_all_datasets()
        assert a is not b


class TestInferChamber:
    def test_congress(self):
        assert _infer_chamber("TX Congressional Districts 2022") == "congress"

    def test_state_senate(self):
        assert _infer_chamber("VA State Senate Districts") == "state_senate"

    def test_state_house(self):
        assert _infer_chamber("OH State House Map") == "state_house"

    def test_sldu(self):
        assert _infer_chamber("2020 SLDU Boundaries") == "state_senate"

    def test_sldl(self):
        assert _infer_chamber("2020 SLDL Boundaries") == "state_house"

    def test_no_match(self):
        assert _infer_chamber("PL 94-171 Block Data") == ""


class TestScoreEntry:
    def test_state_match(self):
        e = _entry(state="TX")
        assert _score_entry(e, state="TX") == 10.0
        assert _score_entry(e, state="CA") == 0.0

    def test_year_match(self):
        e = _entry(year="2020")
        assert _score_entry(e, year="2020") == 5.0

    def test_official_bonus(self):
        e = _entry(official=True)
        assert _score_entry(e, state=e.state) > _score_entry(
            _entry(official=False), state=e.state
        )

    def test_query_exact(self):
        e = _entry(title="Texas PL 94-171")
        score = _score_entry(e, query="Texas PL")
        assert score >= 3.0

    def test_query_partial(self):
        e = _entry(title="Texas PL 94-171")
        score = _score_entry(e, query="Texas something")
        assert 0 < score < 3.0

    def test_combined(self):
        e = _entry(state="TX", year="2020", dtype="pl94171")
        score = _score_entry(e, state="TX", year="2020", dataset_type="pl94171")
        assert score == 20.0  # 10 + 5 + 5


class TestRDHCatalogLoad:
    def test_load_from_provider(self):
        p = DictRDHCatalogProvider([_entry(), _entry(state="CA")])
        cat = RDHCatalog(provider=p)
        count = cat.load()
        assert count == 2
        assert cat.is_loaded
        assert cat.entry_count == 2

    def test_load_no_provider(self):
        cat = RDHCatalog()
        count = cat.load()
        assert count == 0
        assert not cat.is_loaded

    def test_entries_returns_copy(self):
        p = DictRDHCatalogProvider([_entry()])
        cat = RDHCatalog(provider=p)
        cat.load()
        a = cat.entries
        b = cat.entries
        assert a is not b


class TestRDHCatalogSearch:
    def _loaded_catalog(self, entries):
        p = DictRDHCatalogProvider(entries)
        cat = RDHCatalog(provider=p)
        cat.load()
        return cat

    def test_search_by_state(self):
        cat = self._loaded_catalog([
            _entry(state="TX"),
            _entry(state="CA"),
            _entry(state="TX", year="2022"),
        ])
        results = cat.search(state="TX")
        assert len(results) == 2
        assert all(r.entry.state == "TX" for r in results)

    def test_search_by_type(self):
        cat = self._loaded_catalog([
            _entry(dtype="pl94171"),
            _entry(dtype="cvap"),
            _entry(dtype="pl94171", state="CA"),
        ])
        results = cat.search(dataset_type="pl94171")
        assert len(results) == 2

    def test_search_format_filter(self):
        cat = self._loaded_catalog([
            _entry(fmt="csv"),
            _entry(fmt="shp"),
        ])
        results = cat.search(state="TX", format="csv")
        assert len(results) == 1
        assert results[0].entry.format == "csv"

    def test_search_ranked(self):
        cat = self._loaded_catalog([
            _entry(state="TX", official=False),
            _entry(state="TX", official=True),
        ])
        results = cat.search(state="TX")
        assert results[0].score > results[1].score
        assert results[0].entry.official

    def test_search_limit(self):
        entries = [_entry(state="TX", year=str(2000 + i)) for i in range(20)]
        cat = self._loaded_catalog(entries)
        results = cat.search(state="TX", limit=5)
        assert len(results) == 5

    def test_search_empty(self):
        cat = self._loaded_catalog([_entry(state="TX")])
        results = cat.search(state="CA")
        assert len(results) == 0

    def test_search_query(self):
        cat = self._loaded_catalog([
            _entry(title="Texas Congressional Districts 2022"),
            _entry(title="Ohio Block Data 2020"),
        ])
        results = cat.search(query="Texas Congressional")
        assert len(results) >= 1
        assert "Texas" in results[0].entry.title

    def test_search_no_filters_returns_empty(self):
        cat = self._loaded_catalog([_entry()])
        results = cat.search()
        assert len(results) == 0


class TestCoverageMatrix:
    def _loaded_catalog(self, entries):
        p = DictRDHCatalogProvider(entries)
        cat = RDHCatalog(provider=p)
        cat.load()
        return cat

    def test_basic(self):
        cat = self._loaded_catalog([
            _entry(state="TX", year="2020", dtype="pl94171", fmt="csv"),
            _entry(state="TX", year="2020", dtype="pl94171", fmt="shp"),
            _entry(state="CA", year="2020", dtype="cvap", fmt="csv"),
        ])
        matrix = cat.coverage_matrix()
        assert len(matrix) == 2

        tx_cell = next(c for c in matrix if c.state == "TX")
        assert tx_cell.count == 2
        assert "csv" in tx_cell.formats
        assert "shp" in tx_cell.formats

    def test_filter_by_type(self):
        cat = self._loaded_catalog([
            _entry(dtype="pl94171"),
            _entry(dtype="cvap"),
        ])
        matrix = cat.coverage_matrix(dataset_type="pl94171")
        assert len(matrix) == 1
        assert matrix[0].dataset_type == "pl94171"

    def test_empty(self):
        cat = self._loaded_catalog([])
        assert cat.coverage_matrix() == []

    def test_sorted(self):
        cat = self._loaded_catalog([
            _entry(state="TX", year="2022"),
            _entry(state="CA", year="2020"),
        ])
        matrix = cat.coverage_matrix()
        states = [c.state for c in matrix]
        assert states == sorted(states)


class TestCatalogHelpers:
    def _loaded_catalog(self, entries):
        p = DictRDHCatalogProvider(entries)
        cat = RDHCatalog(provider=p)
        cat.load()
        return cat

    def test_states(self):
        cat = self._loaded_catalog([_entry(state="TX"), _entry(state="CA")])
        assert cat.states() == ["CA", "TX"]

    def test_years(self):
        cat = self._loaded_catalog([_entry(year="2020"), _entry(year="2022")])
        assert cat.years() == ["2020", "2022"]

    def test_dataset_types(self):
        cat = self._loaded_catalog([_entry(dtype="pl94171"), _entry(dtype="cvap")])
        assert cat.dataset_types() == ["cvap", "pl94171"]

    def test_for_state(self):
        cat = self._loaded_catalog([
            _entry(state="TX"),
            _entry(state="CA"),
            _entry(state="TX", year="2022"),
        ])
        assert len(cat.for_state("TX")) == 2
        assert len(cat.for_state("ca")) == 1


class TestCatalogCache:
    def test_save_and_load(self, tmp_path):
        p = DictRDHCatalogProvider([
            _entry(state="TX"),
            _entry(state="CA", official=True),
        ])
        cat = RDHCatalog(provider=p, cache_dir=tmp_path)
        cat.load()

        cat2 = RDHCatalog(cache_dir=tmp_path)
        count = cat2.load()
        assert count == 2
        assert cat2.is_loaded
        assert cat2.entry_count == 2

    def test_cache_expired(self, tmp_path):
        p = DictRDHCatalogProvider([_entry()])
        cat = RDHCatalog(provider=p, cache_dir=tmp_path, cache_ttl=1)
        cat.load()

        cache_file = tmp_path / "rdh_catalog.json"
        data = json.loads(cache_file.read_text())
        data["cached_at"] = time.time() - 100
        cache_file.write_text(json.dumps(data))

        cat2 = RDHCatalog(provider=p, cache_dir=tmp_path, cache_ttl=1)
        count = cat2.load()
        assert count == 1

    def test_cache_corrupt(self, tmp_path):
        cache_file = tmp_path / "rdh_catalog.json"
        cache_file.write_text("not valid json")

        p = DictRDHCatalogProvider([_entry()])
        cat = RDHCatalog(provider=p, cache_dir=tmp_path)
        count = cat.load()
        assert count == 1

    def test_no_cache_dir(self):
        p = DictRDHCatalogProvider([_entry()])
        cat = RDHCatalog(provider=p)
        cat.load()
        assert cat.entry_count == 1

    def test_force_bypasses_cache(self, tmp_path):
        p1 = DictRDHCatalogProvider([_entry()])
        cat1 = RDHCatalog(provider=p1, cache_dir=tmp_path)
        cat1.load()

        p2 = DictRDHCatalogProvider([_entry(), _entry(state="CA")])
        cat2 = RDHCatalog(provider=p2, cache_dir=tmp_path)
        count = cat2.load(force=True)
        assert count == 2
