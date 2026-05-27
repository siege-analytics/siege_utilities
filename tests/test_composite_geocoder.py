"""Tests for composite batch geocoder (SU#626)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.providers.batch_geocoder import (
    AddressInput,
    BatchGeocoder,
    BatchGeocodingResult,
    GeocodingResult,
    MatchQuality,
)
from siege_utilities.geo.providers.composite_geocoder import (
    CompositeBatchGeocoder,
    _quality_rank,
)


# ---------------------------------------------------------------------------
# Stub backends for testing
# ---------------------------------------------------------------------------


class _StubGeocoder(BatchGeocoder):
    """Configurable stub backend for testing."""

    def __init__(self, name, results=None, available=True, raises=None):
        self._name = name
        self._results = results or {}
        self._available = available
        self._raises = raises
        self.called_with = None

    @property
    def backend_name(self):
        return self._name

    def is_available(self):
        return self._available

    def geocode(self, addresses, **kwargs):
        if self._raises:
            raise self._raises
        self.called_with = addresses
        result = BatchGeocodingResult(backend=self._name)
        for addr in addresses:
            key = addr.input_id if isinstance(addr, AddressInput) else str(addr)
            if key in self._results:
                result.results.append(self._results[key])
            else:
                result.results.append(GeocodingResult(
                    input_address=addr.one_line if isinstance(addr, AddressInput) else str(addr),
                    input_id=key,
                    match_quality=MatchQuality.NO_MATCH.value,
                    backend=self._name,
                ))
        return result


def _gr(input_id, quality, backend, lat=41.0, lon=-87.0, **kw):
    return GeocodingResult(
        input_address=f"addr-{input_id}",
        input_id=input_id,
        lat=lat,
        lon=lon,
        match_quality=quality,
        backend=backend,
        **kw,
    )


# ---------------------------------------------------------------------------
# Quality rank tests
# ---------------------------------------------------------------------------


class TestQualityRank:
    def test_ordering(self):
        assert _quality_rank(MatchQuality.EXACT.value) > _quality_rank(MatchQuality.INTERPOLATED.value)
        assert _quality_rank(MatchQuality.INTERPOLATED.value) > _quality_rank(MatchQuality.APPROXIMATE.value)
        assert _quality_rank(MatchQuality.APPROXIMATE.value) > _quality_rank(MatchQuality.CENTROID.value)
        assert _quality_rank(MatchQuality.CENTROID.value) > _quality_rank(MatchQuality.NO_MATCH.value)

    def test_unknown_quality(self):
        assert _quality_rank("unknown") == 0


# ---------------------------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------------------------


class TestCompositeConfig:
    def test_backend_name(self):
        g = CompositeBatchGeocoder(backends=[_StubGeocoder("a")])
        assert g.backend_name == "composite"

    def test_requires_at_least_one_backend(self):
        with pytest.raises(ValueError, match="At least one backend"):
            CompositeBatchGeocoder(backends=[])

    def test_empty_input(self):
        g = CompositeBatchGeocoder(backends=[_StubGeocoder("a")])
        result = g.geocode([])
        assert result.total == 0

    def test_all_unavailable_returns_error(self):
        g = CompositeBatchGeocoder(backends=[
            _StubGeocoder("a", available=False),
            _StubGeocoder("b", available=False),
        ])
        result = g.geocode(["123 Main St"])
        assert len(result.errors) == 1
        assert "No available" in result.errors[0]


# ---------------------------------------------------------------------------
# Fallback behavior tests
# ---------------------------------------------------------------------------


class TestCompositeFallback:
    def test_first_backend_succeeds(self):
        b1 = _StubGeocoder("census", results={
            "0": _gr("0", MatchQuality.EXACT.value, "census"),
        })
        b2 = _StubGeocoder("nominatim")
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["123 Main St"])

        assert result.total == 1
        assert result.results[0].backend == "census"
        assert result.results[0].match_quality == MatchQuality.EXACT.value
        assert b2.called_with is None

    def test_fallback_to_second_backend(self):
        b1 = _StubGeocoder("census", results={})
        b2 = _StubGeocoder("nominatim", results={
            "0": _gr("0", MatchQuality.APPROXIMATE.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["123 Main St"])

        assert result.total == 1
        assert result.results[0].backend == "nominatim"
        assert result.results[0].matched

    def test_keeps_best_result_across_backends(self):
        b1 = _StubGeocoder("census", results={
            "0": _gr("0", MatchQuality.CENTROID.value, "census"),
        })
        b2 = _StubGeocoder("nominatim", results={
            "0": _gr("0", MatchQuality.APPROXIMATE.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(
            backends=[b1, b2],
            min_quality=MatchQuality.INTERPOLATED.value,
        )
        result = g.geocode(["123 Main St"])

        assert result.results[0].backend == "nominatim"
        assert result.results[0].match_quality == MatchQuality.APPROXIMATE.value

    def test_mixed_results_partial_fallback(self):
        b1 = _StubGeocoder("census", results={
            "0": _gr("0", MatchQuality.EXACT.value, "census"),
        })
        b2 = _StubGeocoder("nominatim", results={
            "1": _gr("1", MatchQuality.APPROXIMATE.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["addr1", "addr2"])

        assert result.total == 2
        assert result.results[0].backend == "census"
        assert result.results[1].backend == "nominatim"

    def test_backend_exception_continues_to_next(self):
        b1 = _StubGeocoder("census", raises=RuntimeError("API down"))
        b2 = _StubGeocoder("nominatim", results={
            "0": _gr("0", MatchQuality.APPROXIMATE.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["123 Main St"])

        assert result.total == 1
        assert result.results[0].backend == "nominatim"

    def test_skip_unavailable_backends(self):
        b1 = _StubGeocoder("tamu", available=False)
        b2 = _StubGeocoder("nominatim", results={
            "0": _gr("0", MatchQuality.APPROXIMATE.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["123 Main St"])

        assert result.results[0].backend == "nominatim"
        assert b1.called_with is None

    def test_dont_skip_unavailable_when_disabled(self):
        b1 = _StubGeocoder("tamu", available=False, results={
            "0": _gr("0", MatchQuality.EXACT.value, "tamu"),
        })
        g = CompositeBatchGeocoder(backends=[b1], skip_unavailable=False)
        result = g.geocode(["123 Main St"])

        assert result.results[0].backend == "tamu"

    def test_all_backends_fail_returns_no_match(self):
        b1 = _StubGeocoder("census", results={})
        b2 = _StubGeocoder("nominatim", results={})
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["123 Main St"])

        assert result.total == 1
        assert not result.results[0].matched

    def test_quality_threshold_triggers_fallback(self):
        b1 = _StubGeocoder("census", results={
            "0": _gr("0", MatchQuality.CENTROID.value, "census"),
        })
        b2 = _StubGeocoder("nominatim", results={
            "0": _gr("0", MatchQuality.INTERPOLATED.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(
            backends=[b1, b2],
            min_quality=MatchQuality.APPROXIMATE.value,
        )
        result = g.geocode(["123 Main St"])

        assert result.results[0].backend == "nominatim"

    def test_exact_threshold_only_accepts_exact(self):
        b1 = _StubGeocoder("census", results={
            "0": _gr("0", MatchQuality.INTERPOLATED.value, "census"),
        })
        b2 = _StubGeocoder("nominatim", results={
            "0": _gr("0", MatchQuality.EXACT.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(
            backends=[b1, b2],
            min_quality=MatchQuality.EXACT.value,
        )
        result = g.geocode(["123 Main St"])

        assert result.results[0].backend == "nominatim"

    def test_three_backends_chain(self):
        b1 = _StubGeocoder("census", results={})
        b2 = _StubGeocoder("nominatim", results={
            "0": _gr("0", MatchQuality.CENTROID.value, "nominatim"),
        })
        b3 = _StubGeocoder("tamu", results={
            "0": _gr("0", MatchQuality.EXACT.value, "tamu"),
        })
        g = CompositeBatchGeocoder(backends=[b1, b2, b3])
        result = g.geocode(["123 Main St"])

        assert result.results[0].backend == "tamu"

    def test_preserves_input_ids(self):
        b1 = _StubGeocoder("census", results={
            "MY-ID": _gr("MY-ID", MatchQuality.EXACT.value, "census"),
        })
        g = CompositeBatchGeocoder(backends=[b1])
        result = g.geocode([
            {"street": "123 Main St", "city": "Chicago", "state": "IL", "id": "MY-ID"},
        ])

        assert result.results[0].input_id == "MY-ID"

    def test_stops_early_when_all_resolved(self):
        b1 = _StubGeocoder("census", results={
            "0": _gr("0", MatchQuality.EXACT.value, "census"),
            "1": _gr("1", MatchQuality.EXACT.value, "census"),
        })
        b2 = _StubGeocoder("nominatim")
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["a", "b"])

        assert result.matched_count == 2
        assert b2.called_with is None

    def test_multiple_addresses_different_backends(self):
        b1 = _StubGeocoder("census", results={
            "0": _gr("0", MatchQuality.EXACT.value, "census"),
            "2": _gr("2", MatchQuality.EXACT.value, "census"),
        })
        b2 = _StubGeocoder("nominatim", results={
            "1": _gr("1", MatchQuality.APPROXIMATE.value, "nominatim"),
        })
        g = CompositeBatchGeocoder(backends=[b1, b2])
        result = g.geocode(["a", "b", "c"])

        assert result.total == 3
        assert result.results[0].backend == "census"
        assert result.results[1].backend == "nominatim"
        assert result.results[2].backend == "census"
