"""Tests for BatchGeocoder interface and GeocodingResult schema (SU#622)."""

from __future__ import annotations


import pytest

from siege_utilities.geo.providers.batch_geocoder import (
    AddressInput,
    BatchGeocoder,
    BatchGeocodingResult,
    GeocodingResult,
    MatchQuality,
    normalize_addresses,
)


# ---------------------------------------------------------------------------
# GeocodingResult tests
# ---------------------------------------------------------------------------


class TestGeocodingResult:
    def test_default_is_no_match(self):
        r = GeocodingResult()
        assert not r.matched
        assert r.match_quality == MatchQuality.NO_MATCH.value

    def test_exact_match(self):
        r = GeocodingResult(
            input_address="123 Main St",
            matched_address="123 MAIN ST",
            lat=41.8781,
            lon=-87.6298,
            match_quality=MatchQuality.EXACT.value,
            block_geoid="170310101001001",
            tract_geoid="17031010100",
            county_geoid="17031",
            state_geoid="17",
            backend="census",
        )
        assert r.matched
        assert r.has_block
        assert r.has_tract
        assert r.backend == "census"

    def test_has_block_requires_15_digits(self):
        r = GeocodingResult(block_geoid="1703101")
        assert not r.has_block

    def test_has_tract_requires_11_digits(self):
        r = GeocodingResult(tract_geoid="1703101")
        assert not r.has_tract

    def test_to_dict(self):
        r = GeocodingResult(
            input_address="test",
            match_quality=MatchQuality.EXACT.value,
        )
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["matched"] is True
        assert d["input_address"] == "test"


class TestMatchQuality:
    def test_values(self):
        assert MatchQuality.EXACT.value == "exact"
        assert MatchQuality.NO_MATCH.value == "no_match"

    def test_all_levels(self):
        levels = [e.value for e in MatchQuality]
        assert "exact" in levels
        assert "interpolated" in levels
        assert "approximate" in levels
        assert "centroid" in levels
        assert "no_match" in levels


# ---------------------------------------------------------------------------
# BatchGeocodingResult tests
# ---------------------------------------------------------------------------


class TestBatchGeocodingResult:
    def test_empty(self):
        b = BatchGeocodingResult()
        assert b.total == 0
        assert b.matched_count == 0
        assert b.match_rate == 0.0

    def test_counts(self):
        b = BatchGeocodingResult(results=[
            GeocodingResult(match_quality=MatchQuality.EXACT.value),
            GeocodingResult(match_quality=MatchQuality.EXACT.value),
            GeocodingResult(match_quality=MatchQuality.NO_MATCH.value),
        ])
        assert b.total == 3
        assert b.matched_count == 2
        assert abs(b.match_rate - 2 / 3) < 0.01

    def test_with_errors(self):
        b = BatchGeocodingResult(errors=["some error"])
        assert len(b.errors) == 1


# ---------------------------------------------------------------------------
# AddressInput tests
# ---------------------------------------------------------------------------


class TestAddressInput:
    def test_one_line(self):
        a = AddressInput(
            street="123 Main St",
            city="Chicago",
            state="IL",
            zipcode="60601",
        )
        assert a.one_line == "123 Main St, Chicago, IL, 60601"

    def test_one_line_partial(self):
        a = AddressInput(street="123 Main St", state="IL")
        assert a.one_line == "123 Main St, IL"

    def test_empty(self):
        a = AddressInput()
        assert a.one_line == ""


# ---------------------------------------------------------------------------
# normalize_addresses tests
# ---------------------------------------------------------------------------


class TestNormalizeAddresses:
    def test_from_dicts(self):
        addrs = [
            {"street": "123 Main St", "city": "Chicago", "state": "IL", "zipcode": "60601"},
            {"street": "456 Oak Ave", "city": "Boston", "state": "MA", "zip": "02101"},
        ]
        result = normalize_addresses(addrs)
        assert len(result) == 2
        assert result[0].street == "123 Main St"
        assert result[1].zipcode == "02101"

    def test_from_strings(self):
        addrs = ["123 Main St, Chicago, IL", "456 Oak Ave, Boston, MA"]
        result = normalize_addresses(addrs)
        assert len(result) == 2
        assert result[0].street == "123 Main St, Chicago, IL"
        assert result[0].input_id == "0"

    def test_from_address_inputs(self):
        addrs = [AddressInput(street="123 Main St")]
        result = normalize_addresses(addrs)
        assert len(result) == 1
        assert result[0].street == "123 Main St"

    def test_empty_list(self):
        assert normalize_addresses([]) == []

    def test_dict_with_address_key(self):
        addrs = [{"address": "123 Main St"}]
        result = normalize_addresses(addrs)
        assert result[0].street == "123 Main St"

    def test_dict_with_id_key(self):
        addrs = [{"street": "123 Main St", "id": "ABC"}]
        result = normalize_addresses(addrs)
        assert result[0].input_id == "ABC"

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            normalize_addresses([42, 43])


# ---------------------------------------------------------------------------
# BatchGeocoder ABC tests
# ---------------------------------------------------------------------------


class _TestGeocoder(BatchGeocoder):
    """Concrete implementation for testing the ABC."""

    @property
    def backend_name(self) -> str:
        return "test"

    def geocode(self, addresses, **kwargs):
        normalized = normalize_addresses(addresses)
        results = [
            GeocodingResult(
                input_address=a.one_line,
                input_id=a.input_id,
                match_quality=MatchQuality.EXACT.value,
                lat=0.0,
                lon=0.0,
                backend=self.backend_name,
            )
            for a in normalized
        ]
        return BatchGeocodingResult(results=results, backend=self.backend_name)


class TestBatchGeocoderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BatchGeocoder()

    def test_concrete_implementation(self):
        g = _TestGeocoder()
        assert g.backend_name == "test"
        assert g.is_available()

    def test_geocode_strings(self):
        g = _TestGeocoder()
        result = g.geocode(["123 Main St", "456 Oak Ave"])
        assert result.total == 2
        assert result.matched_count == 2
        assert result.backend == "test"

    def test_geocode_dicts(self):
        g = _TestGeocoder()
        result = g.geocode([
            {"street": "123 Main St", "city": "Chicago", "state": "IL"},
        ])
        assert result.total == 1

    def test_geocode_preserves_id(self):
        g = _TestGeocoder()
        result = g.geocode([{"street": "test", "id": "MY-ID"}])
        assert result.results[0].input_id == "MY-ID"
