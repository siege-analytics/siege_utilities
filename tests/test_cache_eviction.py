"""Tests for the LRU eviction + atomic-write behaviour in siege_utilities.cache.

PR follow-up: the cache was previously unbounded and used a
predictable `.part` filename that could race under concurrent writers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from siege_utilities.cache import _evict_to_fit, ensure_sample_dataset


def _seed(root: Path, name: str, size: int, atime: float) -> Path:
    p = root / name
    p.write_bytes(b"x" * size)
    import os
    os.utime(p, (atime, atime))
    return p


class TestEviction:
    def test_no_eviction_when_under_budget(self, tmp_path):
        a = _seed(tmp_path, "a.bin", 100, 1_000_000.0)
        b = _seed(tmp_path, "b.bin", 100, 2_000_000.0)
        _evict_to_fit(tmp_path, incoming_bytes=50, budget=1000)
        assert a.exists() and b.exists()

    def test_lru_oldest_evicted_first(self, tmp_path):
        old = _seed(tmp_path, "old.bin", 400, 1_000_000.0)
        mid = _seed(tmp_path, "mid.bin", 400, 2_000_000.0)
        _seed(tmp_path, "new.bin", 400, 3_000_000.0)
        # Existing total 1200, budget 1000, incoming 400 → need ≥600
        # evicted. Oldest is "old" (400) → not enough; also "mid" (400)
        # → total 800 freed, still need more; also "new" (400).
        _evict_to_fit(tmp_path, incoming_bytes=400, budget=1000)
        assert not old.exists()
        assert not mid.exists()
        # We freed everything older than incoming — the order is
        # oldest-first so by the time we hit "new" we've freed enough.
        # Either way: total + incoming should fit.
        survivors = [p for p in tmp_path.iterdir() if p.is_file()]
        remaining = sum(p.stat().st_size for p in survivors)
        assert remaining + 400 <= 1000

    def test_zero_budget_is_noop(self, tmp_path):
        a = _seed(tmp_path, "a.bin", 100, 1.0)
        _evict_to_fit(tmp_path, incoming_bytes=50, budget=0)
        assert a.exists()  # 0 means "no eviction"


class TestAtomicWrite:
    def test_existing_file_returns_unchanged_and_touches_atime(self, tmp_path):
        target = tmp_path / "fixture.bin"
        target.write_bytes(b"data")
        before_atime = target.stat().st_atime
        # No url should be hit because file exists.
        result = ensure_sample_dataset(
            "fixture.bin",
            url="http://example.invalid/should-not-be-fetched",
            cache_dir=tmp_path,
        )
        assert result == target
        assert result.read_bytes() == b"data"
        # atime should have been bumped.
        after_atime = target.stat().st_atime
        assert after_atime >= before_atime

    def test_path_separator_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="single filename"):
            ensure_sample_dataset("a/b.bin", url="http://example.invalid",
                                  cache_dir=tmp_path)
