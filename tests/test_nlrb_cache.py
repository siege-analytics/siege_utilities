"""Tests for NLRB data caching (SU#621)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from siege_utilities.geo.providers.nlrb_cache import (
    NLRBCache,
    NLRBLoader,
    _date_to_str,
    _dict_to_result,
    _result_to_dict,
    _str_to_date,
)
from siege_utilities.geo.providers.nlrb_clients import (
    ElectionRecord,
    NLRBCaseRecord,
    NLRBFetchResult,
    ULPRecord,
)


# ---------------------------------------------------------------------------
# Serialization helper tests
# ---------------------------------------------------------------------------


class TestDateHelpers:
    def test_date_to_str(self):
        assert _date_to_str(date(2024, 1, 15)) == "2024-01-15"

    def test_date_to_str_none(self):
        assert _date_to_str(None) is None

    def test_str_to_date(self):
        assert _str_to_date("2024-01-15") == date(2024, 1, 15)

    def test_str_to_date_none(self):
        assert _str_to_date(None) is None

    def test_str_to_date_invalid(self):
        assert _str_to_date("not-a-date") is None


class TestSerialization:
    def _make_result(self):
        return NLRBFetchResult(
            source="test",
            cases=[
                NLRBCaseRecord(
                    case_number="05-RC-100001",
                    case_type="RC",
                    case_name="Test Corp",
                    status="Open",
                    date_filed=date(2024, 1, 15),
                    region=5,
                    city="Chicago",
                    state="IL",
                    naics_code="622110",
                    employee_count=150,
                    source="labordata",
                ),
            ],
            elections=[
                ElectionRecord(
                    case_number="05-RC-100001",
                    tally_date=date(2024, 3, 1),
                    eligible_voters=200,
                    votes_for=120,
                    votes_against=75,
                    union_name="SEIU",
                    source="labordata",
                ),
            ],
            ulp_charges=[
                ULPRecord(
                    case_number="01-CA-200001",
                    allegation="8(a)(1) interference",
                    section_of_act="8(a)(1)",
                    date_filed=date(2024, 5, 1),
                    source="labordata",
                ),
            ],
        )

    def test_roundtrip(self):
        original = self._make_result()
        data = _result_to_dict(original)
        restored = _dict_to_result(data)

        assert len(restored.cases) == 1
        assert restored.cases[0].case_number == "05-RC-100001"
        assert restored.cases[0].date_filed == date(2024, 1, 15)
        assert restored.cases[0].employee_count == 150

        assert len(restored.elections) == 1
        assert restored.elections[0].votes_for == 120

        assert len(restored.ulp_charges) == 1
        assert restored.ulp_charges[0].section_of_act == "8(a)(1)"

    def test_dict_has_fetched_at(self):
        result = self._make_result()
        data = _result_to_dict(result)
        assert "fetched_at" in data

    def test_dict_is_json_serializable(self):
        result = self._make_result()
        data = _result_to_dict(result)
        json_str = json.dumps(data)
        assert len(json_str) > 0

    def test_empty_result_roundtrip(self):
        original = NLRBFetchResult(source="empty")
        data = _result_to_dict(original)
        restored = _dict_to_result(data)
        assert restored.total_records == 0


# ---------------------------------------------------------------------------
# NLRBCache tests
# ---------------------------------------------------------------------------


class TestNLRBCache:
    def test_get_missing_returns_none(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        assert cache.get("nonexistent") is None

    def test_put_and_get(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        result = NLRBFetchResult(
            source="test",
            cases=[NLRBCaseRecord(case_number="1", case_type="RC")],
        )
        cache.put("test_key", result)
        restored = cache.get("test_key")

        assert restored is not None
        assert len(restored.cases) == 1
        assert restored.cases[0].case_number == "1"

    def test_creates_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "nested" / "cache"
        cache = NLRBCache(cache_dir=cache_dir, ttl_days=30)
        result = NLRBFetchResult(source="test")
        cache.put("key", result)
        assert cache_dir.exists()

    def test_expired_returns_none(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=1)
        result = NLRBFetchResult(source="test")

        cache.put("key", result)

        # Backdate the fetched_at timestamp
        path = tmp_path / "key.json"
        data = json.loads(path.read_text())
        data["fetched_at"] = (datetime.now() - timedelta(days=5)).isoformat()
        path.write_text(json.dumps(data))

        assert cache.get("key") is None

    def test_invalidate_existing(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        cache.put("key", NLRBFetchResult(source="test"))
        assert cache.invalidate("key")
        assert cache.get("key") is None

    def test_invalidate_missing(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        assert not cache.invalidate("nonexistent")

    def test_invalidate_all(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        cache.put("a", NLRBFetchResult(source="test"))
        cache.put("b", NLRBFetchResult(source="test"))
        count = cache.invalidate_all()
        assert count == 2
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_invalidate_all_empty(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path / "empty", ttl_days=30)
        assert cache.invalidate_all() == 0

    def test_corrupted_json_returns_none(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        path = tmp_path / "bad.json"
        path.write_text("not valid json {{{")
        assert cache.get("bad") is None


# ---------------------------------------------------------------------------
# NLRBLoader tests
# ---------------------------------------------------------------------------


class TestNLRBLoader:
    def test_cache_hit(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        cache.put("unified", NLRBFetchResult(
            source="cached",
            cases=[NLRBCaseRecord(case_number="cached-1", case_type="RC")],
        ))

        client = MagicMock()
        loader = NLRBLoader(cache=cache, client=client)
        result = loader.load("unified")

        assert len(result.cases) == 1
        assert result.cases[0].case_number == "cached-1"
        client.fetch_all.assert_not_called()

    def test_cache_miss_fetches(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        client = MagicMock()
        client.fetch_all.return_value = NLRBFetchResult(
            source="fetched",
            cases=[NLRBCaseRecord(case_number="fresh-1", case_type="RC")],
        )

        loader = NLRBLoader(cache=cache, client=client)
        result = loader.load("unified")

        assert result.cases[0].case_number == "fresh-1"
        client.fetch_all.assert_called_once()
        assert cache.get("unified") is not None

    def test_force_refresh_skips_cache(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        cache.put("unified", NLRBFetchResult(
            source="stale",
            cases=[NLRBCaseRecord(case_number="stale-1", case_type="RC")],
        ))

        client = MagicMock()
        client.fetch_all.return_value = NLRBFetchResult(
            source="fresh",
            cases=[NLRBCaseRecord(case_number="fresh-1", case_type="RC")],
        )

        loader = NLRBLoader(cache=cache, client=client)
        result = loader.load("unified", force_refresh=True)

        assert result.cases[0].case_number == "fresh-1"
        client.fetch_all.assert_called_once()

    def test_failed_fetch_not_cached(self, tmp_path):
        cache = NLRBCache(cache_dir=tmp_path, ttl_days=30)
        client = MagicMock()
        client.fetch_all.return_value = NLRBFetchResult(
            source="failed",
            errors=["network error"],
        )

        loader = NLRBLoader(cache=cache, client=client)
        result = loader.load("unified")

        assert not result.success
        assert cache.get("unified") is None
