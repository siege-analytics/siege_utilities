"""Tests for siege_utilities.geo.geocoding — pure computation and cache logic."""

import json
import sqlite3
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
geocoding = pytest.importorskip("siege_utilities.geo.geocoding")

COUNTRY_CODES = geocoding.COUNTRY_CODES
DEFAULT_COUNTRY_CODE = geocoding.DEFAULT_COUNTRY_CODE
NominatimGeoClassifier = geocoding.NominatimGeoClassifier
SpatiaLiteCache = geocoding.SpatiaLiteCache
concatenate_addresses = geocoding.concatenate_addresses
get_country_code = geocoding.get_country_code
get_country_name = geocoding.get_country_name
list_countries = geocoding.list_countries
mark_valid_geocode_data_pandas = geocoding.mark_valid_geocode_data_pandas
validate_geocode_data_pandas = geocoding.validate_geocode_data_pandas


class TestCountryCodeLookup:
    def test_get_country_name_valid(self):
        assert get_country_name("us") == "United States"
        assert get_country_name("gb") == "United Kingdom"

    def test_get_country_name_case_insensitive(self):
        assert get_country_name("US") == "United States"

    def test_get_country_name_unknown(self):
        result = get_country_name("zz")
        assert result is None or result == "Unknown"

    def test_get_country_code_valid(self):
        assert get_country_code("United States") == "us"
        assert get_country_code("United Kingdom") == "gb"

    def test_get_country_code_unknown(self):
        result = get_country_code("Narnia")
        assert result is None

    def test_list_countries(self):
        result = list_countries()
        assert isinstance(result, dict)
        assert len(result) > 100
        assert "us" in result

    def test_default_country_code(self):
        assert DEFAULT_COUNTRY_CODE == "us"

    def test_country_codes_completeness(self):
        assert "us" in COUNTRY_CODES
        assert "gb" in COUNTRY_CODES
        assert "au" in COUNTRY_CODES
        assert "jp" in COUNTRY_CODES


class TestConcatenateAddresses:
    def test_full_address(self):
        result = concatenate_addresses(
            street="123 Main St",
            city="Austin",
            state_province_area="TX",
            postal_code="78701",
            country="US",
        )
        assert "123 Main St" in result
        assert "Austin" in result
        assert "TX" in result
        assert "78701" in result

    def test_partial_address(self):
        result = concatenate_addresses(city="Austin", state_province_area="TX")
        assert "Austin" in result
        assert "TX" in result

    def test_empty_address(self):
        result = concatenate_addresses()
        assert result is not None


class TestNominatimGeoClassifier:
    def test_default_instance(self):
        clf = NominatimGeoClassifier()
        assert clf is not None

    def test_serialization_roundtrip(self):
        clf = NominatimGeoClassifier()
        json_str = clf.to_json()
        assert json_str is not None
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_deserialization(self):
        clf = NominatimGeoClassifier()
        json_str = clf.to_json()
        clf2 = NominatimGeoClassifier()
        clf2.from_json(json_str)


class TestSpatiaLiteCache:
    def test_init_creates_db(self, tmp_path):
        db_path = tmp_path / "cache.db"
        cache = SpatiaLiteCache(db_path=str(db_path))
        assert db_path.exists()
        cache.close()

    def test_put_get_geocode(self, tmp_path):
        cache = SpatiaLiteCache(db_path=str(tmp_path / "cache.db"))
        cache.put_geocode("123 Main St", 30.2672, -97.7431)
        result = cache.get_geocode("123 Main St")
        assert result is not None
        assert abs(result["latitude"] - 30.2672) < 0.001
        assert abs(result["longitude"] - (-97.7431)) < 0.001
        cache.close()

    def test_get_missing_geocode(self, tmp_path):
        cache = SpatiaLiteCache(db_path=str(tmp_path / "cache.db"))
        result = cache.get_geocode("nonexistent address")
        assert result is None
        cache.close()

    def test_stats(self, tmp_path):
        cache = SpatiaLiteCache(db_path=str(tmp_path / "cache.db"))
        cache.put_geocode("addr1", 30.0, -97.0)
        cache.put_geocode("addr2", 31.0, -98.0)
        stats = cache.stats()
        assert isinstance(stats, dict)
        assert stats.get("geocodes", 0) == 2
        cache.close()

    def test_clear(self, tmp_path):
        cache = SpatiaLiteCache(db_path=str(tmp_path / "cache.db"))
        cache.put_geocode("addr", 30.0, -97.0)
        cache.clear()
        assert cache.get_geocode("addr") is None
        cache.close()

    def test_context_manager(self, tmp_path):
        with SpatiaLiteCache(db_path=str(tmp_path / "cache.db")) as cache:
            cache.put_geocode("test", 30.0, -97.0)
            assert cache.get_geocode("test") is not None

    def test_boundary_cache(self, tmp_path):
        cache = SpatiaLiteCache(db_path=str(tmp_path / "cache.db"))
        cache.put_boundary("48453", 2020, point_wkt="POINT(-97.7 30.3)")
        result = cache.get_boundary("48453", 2020)
        assert result is not None
        cache.close()

    def test_crosswalk_cache(self, tmp_path):
        cache = SpatiaLiteCache(db_path=str(tmp_path / "cache.db"))
        cache.put_crosswalk("48453001100", "48453", weight=0.85)
        result = cache.get_crosswalk("48453001100")
        assert result is not None
        assert len(result) > 0
        cache.close()


class TestValidateGeocodeData:
    def test_filters_invalid_coords(self):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({
            "lat": [30.0, None, 200.0, 31.0],
            "lon": [-97.0, -98.0, -97.0, None],
        })
        result = validate_geocode_data_pandas(df, "lat", "lon")
        assert len(result) == 1
        assert result.iloc[0]["lat"] == 30.0

    def test_marks_validity(self):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({
            "lat": [30.0, None, 31.0],
            "lon": [-97.0, -98.0, None],
        })
        result = mark_valid_geocode_data_pandas(df, "lat", "lon")
        assert "is_valid" in result.columns
        assert result.iloc[0]["is_valid"] is True
        assert result.iloc[1]["is_valid"] is False
