"""Tests for SpatiaLite geocoding cache."""

import pytest

from siege_utilities.geo.geocoding import SpatiaLiteCache, _address_hash


@pytest.fixture
def cache(tmp_path):
    """Create a temporary cache for testing."""
    db_path = str(tmp_path / "test_cache.db")
    c = SpatiaLiteCache(db_path=db_path)
    yield c
    c.close()


class TestAddressHash:

    def test_deterministic(self):
        h1 = _address_hash("123 Main St, Springfield, IL 62701")
        h2 = _address_hash("123 Main St, Springfield, IL 62701")
        assert h1 == h2

    def test_case_insensitive(self):
        h1 = _address_hash("123 Main St")
        h2 = _address_hash("123 MAIN ST")
        assert h1 == h2

    def test_whitespace_normalized(self):
        h1 = _address_hash("123   Main   St")
        h2 = _address_hash("123 Main St")
        assert h1 == h2

    def test_different_addresses_differ(self):
        h1 = _address_hash("123 Main St")
        h2 = _address_hash("456 Oak Ave")
        assert h1 != h2


class TestGeocodeCache:

    def test_put_and_get(self, cache):
        addr = "123 Main St, Springfield, IL 62701"
        cache.put_geocode(addr, 39.7817, -89.6501, source="nominatim")

        result = cache.get_geocode(addr)
        assert result is not None
        assert result["latitude"] == 39.7817
        assert result["longitude"] == -89.6501
        assert result["source"] == "nominatim"
        assert "POINT" in result["point_wkt"]

    def test_get_missing(self, cache):
        result = cache.get_geocode("nonexistent address")
        assert result is None

    def test_update_existing(self, cache):
        addr = "123 Main St"
        cache.put_geocode(addr, 39.78, -89.65)
        cache.put_geocode(addr, 39.79, -89.66)

        result = cache.get_geocode(addr)
        assert result["latitude"] == 39.79
        assert result["longitude"] == -89.66

    def test_raw_response_stored(self, cache):
        addr = "456 Oak Ave"
        raw = '{"display_name": "456 Oak Ave"}'
        cache.put_geocode(addr, 40.0, -88.0, raw_response=raw)

        result = cache.get_geocode(addr)
        assert result["raw_response"] == raw

    def test_get_geocode_or_fetch_cache_hit_does_not_call_provider(self, cache, monkeypatch):
        import siege_utilities.geo.geocoding as geocoding

        address = "301 W 2nd St, Austin, TX 78701"
        cache.put_geocode(address, 30.265, -97.747, source="fixture")

        def fail_if_called(*args, **kwargs):
            raise AssertionError("provider should not be called on cache hit")

        monkeypatch.setattr(geocoding, "use_nominatim_geocoder", fail_if_called)

        result = cache.get_geocode_or_fetch("  301 w 2nd st,   austin, tx 78701  ")

        assert result is not None
        assert result["latitude"] == 30.265
        assert result["longitude"] == -97.747
        assert result["source"] == "fixture"

    def test_get_geocode_or_fetch_no_match_does_not_poison_cache(self, cache, monkeypatch):
        import siege_utilities.geo.geocoding as geocoding

        monkeypatch.setattr(geocoding, "use_nominatim_geocoder", lambda *a, **k: None)

        assert cache.get_geocode_or_fetch("unmatched fixture") is None
        assert cache.stats()["geocodes"] == 0
        assert cache.get_geocode("unmatched fixture") is None


class TestBboxQuery:

    def test_within_bbox(self, cache):
        cache.put_geocode("Point A", 40.0, -89.0)
        cache.put_geocode("Point B", 41.0, -88.0)
        cache.put_geocode("Point C", 50.0, -70.0)  # outside

        results = cache.get_geocodes_in_bbox(39.0, 42.0, -90.0, -87.0)
        addresses = {r["address"] for r in results}
        assert "Point A" in addresses
        assert "Point B" in addresses
        assert "Point C" not in addresses


class TestBoundaryCache:

    def test_put_and_get(self, cache):
        cache.put_boundary("06037", 2020, point_wkt="POINT(-118.2 34.0)")

        result = cache.get_boundary("06037", 2020)
        assert result is not None
        assert result["geoid"] == "06037"
        assert result["vintage_year"] == 2020

    def test_get_missing(self, cache):
        result = cache.get_boundary("99999", 2020)
        assert result is None

    def test_different_vintage_years(self, cache):
        cache.put_boundary("06037", 2010, point_wkt="POINT(-118.2 34.0)")
        cache.put_boundary("06037", 2020, point_wkt="POINT(-118.3 34.1)")

        r2010 = cache.get_boundary("06037", 2010)
        r2020 = cache.get_boundary("06037", 2020)
        assert r2010["point_wkt"] != r2020["point_wkt"]


class TestCrosswalkCache:

    def test_put_and_get(self, cache):
        cache.put_crosswalk("06037100100", "06037200100", weight=0.75)
        cache.put_crosswalk("06037100100", "06037200200", weight=0.25)

        results = cache.get_crosswalk("06037100100")
        assert len(results) == 2
        weights = {r["target_geoid"]: r["weight"] for r in results}
        assert weights["06037200100"] == 0.75
        assert weights["06037200200"] == 0.25

    def test_get_missing(self, cache):
        results = cache.get_crosswalk("99999999999")
        assert results == []


class TestCacheUtility:

    def test_stats(self, cache):
        cache.put_geocode("addr1", 40.0, -89.0)
        cache.put_geocode("addr2", 41.0, -88.0)
        cache.put_boundary("06037", 2020)

        stats = cache.stats()
        assert stats["geocodes"] == 2
        assert stats["boundaries"] == 1
        assert stats["crosswalks"] == 0

    def test_clear_all(self, cache):
        cache.put_geocode("addr1", 40.0, -89.0)
        cache.put_boundary("06037", 2020)
        cache.put_crosswalk("src", "tgt")

        cache.clear()
        stats = cache.stats()
        assert stats["geocodes"] == 0
        assert stats["boundaries"] == 0
        assert stats["crosswalks"] == 0

    def test_clear_single_table(self, cache):
        cache.put_geocode("addr1", 40.0, -89.0)
        cache.put_boundary("06037", 2020)

        cache.clear("geocode_cache")
        stats = cache.stats()
        assert stats["geocodes"] == 0
        assert stats["boundaries"] == 1

    def test_context_manager(self, tmp_path):
        db_path = str(tmp_path / "ctx_cache.db")
        with SpatiaLiteCache(db_path=db_path) as cache:
            cache.put_geocode("test", 40.0, -89.0)
            assert cache.stats()["geocodes"] == 1


class TestGeocodeCacheValidation:

    @pytest.mark.parametrize(
        "latitude,longitude",
        [
            (91, 0),
            (-91, 0),
            (0, 181),
            (0, -181),
            ("bad", 0),
            (0, "bad"),
            (float("nan"), 0),
        ],
    )
    def test_put_geocode_rejects_invalid_wgs84_coordinates(self, cache, latitude, longitude):
        with pytest.raises(ValueError):
            cache.put_geocode("bad", latitude, longitude)
        assert cache.stats()["geocodes"] == 0

    def test_get_geocode_or_fetch_rejects_invalid_provider_payload_without_poisoning_cache(self, cache, monkeypatch):
        import siege_utilities.geo.geocoding as geocoding
        from siege_utilities.geo.geocoding import GeocodingError

        monkeypatch.setattr(
            geocoding,
            "use_nominatim_geocoder",
            lambda *a, **k: '{"nominatim_lat": 999, "nominatim_lng": 0}',
        )

        with pytest.raises(GeocodingError):
            cache.get_geocode_or_fetch("bad provider point")

        assert cache.stats()["geocodes"] == 0
        assert cache.get_geocode("bad provider point") is None


@pytest.mark.parametrize("payload", ["[]", '"string"', "123"])
def test_get_geocode_or_fetch_wraps_non_object_json_without_poisoning(cache, monkeypatch, payload):
    import siege_utilities.geo.geocoding as geocoding
    from siege_utilities.geo.geocoding import GeocodingError

    monkeypatch.setattr(geocoding, "use_nominatim_geocoder", lambda *a, **k: payload)

    with pytest.raises(GeocodingError, match="must be an object"):
        cache.get_geocode_or_fetch("bad json shape")

    assert cache.stats()["geocodes"] == 0
    assert cache.get_geocode("bad json shape") is None
