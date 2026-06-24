"""Tests for GST-ported geocoding + spatial-data helpers (#515)."""

import math
from unittest.mock import patch

import pytest

from siege_utilities.geo.crs import distance_to_decimal_degrees
from siege_utilities.geo.geocoding import (
    GeocodingError,
    geocode_with_nominatim_public,
    geocode_addresses_with_nominatim,
)


class TestDistanceToDecimalDegrees:
    """distance_to_decimal_degrees converts meters to degrees."""

    def test_equator(self):
        result = distance_to_decimal_degrees(111_320, 0.0)
        assert abs(result - 1.0) < 0.01

    def test_45_degrees(self):
        result = distance_to_decimal_degrees(111_320, 45.0)
        expected = 1.0 / math.cos(math.radians(45))
        assert abs(result - expected) < 0.01

    def test_zero_distance(self):
        assert distance_to_decimal_degrees(0.0, 30.0) == 0.0

    def test_pole_returns_zero(self):
        assert distance_to_decimal_degrees(1000.0, 90.0) == 0.0

    def test_negative_latitude(self):
        pos = distance_to_decimal_degrees(1000.0, 30.0)
        neg = distance_to_decimal_degrees(1000.0, -30.0)
        assert abs(pos - neg) < 1e-10

    def test_invalid_latitude_high(self):
        with pytest.raises(ValueError, match="latitude"):
            distance_to_decimal_degrees(100.0, 91.0)

    def test_invalid_latitude_low(self):
        with pytest.raises(ValueError, match="latitude"):
            distance_to_decimal_degrees(100.0, -91.0)


class TestGeocodeWithNominatimPublic:
    """geocode_with_nominatim_public wraps get_coordinates."""

    @patch("siege_utilities.geo.geocoding.get_coordinates")
    def test_delegates_to_get_coordinates(self, mock_gc):
        mock_gc.return_value = (30.2672, -97.7431)
        result = geocode_with_nominatim_public("Austin, TX")
        assert result == (30.2672, -97.7431)
        mock_gc.assert_called_once_with(
            "Austin, TX", country_codes=None, server_url=None,
        )

    @patch("siege_utilities.geo.geocoding.get_coordinates")
    def test_returns_none_on_no_match(self, mock_gc):
        mock_gc.return_value = None
        assert geocode_with_nominatim_public("xyznotreal") is None

    @patch("siege_utilities.geo.geocoding.get_coordinates")
    def test_passes_country_codes(self, mock_gc):
        mock_gc.return_value = (51.5, -0.1)
        geocode_with_nominatim_public("London", country_codes="gb")
        mock_gc.assert_called_once_with(
            "London", country_codes="gb", server_url=None,
        )


class TestGeocodeAddressesWithNominatim:
    """geocode_addresses_with_nominatim batch-geocodes."""

    @patch("siege_utilities.geo.geocoding.get_coordinates")
    def test_batch_returns_all(self, mock_gc):
        mock_gc.side_effect = [(30.0, -97.0), (40.0, -74.0)]
        result = geocode_addresses_with_nominatim(["Austin", "NYC"])
        assert len(result) == 2
        assert result[0] == {"address": "Austin", "lat": 30.0, "lon": -97.0}
        assert result[1] == {"address": "NYC", "lat": 40.0, "lon": -74.0}

    @patch("siege_utilities.geo.geocoding.get_coordinates")
    def test_no_match_yields_none_coords(self, mock_gc):
        mock_gc.return_value = None
        result = geocode_addresses_with_nominatim(["nowhere"])
        assert result == [{"address": "nowhere", "lat": None, "lon": None}]

    @patch("siege_utilities.geo.geocoding.get_coordinates")
    def test_error_yields_none_coords(self, mock_gc):
        mock_gc.side_effect = GeocodingError("service down")
        result = geocode_addresses_with_nominatim(["broken"])
        assert result == [{"address": "broken", "lat": None, "lon": None}]

    @patch("siege_utilities.geo.geocoding.get_coordinates")
    def test_mixed_success_and_failure(self, mock_gc):
        mock_gc.side_effect = [
            (30.0, -97.0),
            GeocodingError("timeout"),
            None,
        ]
        result = geocode_addresses_with_nominatim(["ok", "fail", "none"])
        assert result[0]["lat"] == 30.0
        assert result[1]["lat"] is None
        assert result[2]["lat"] is None

    def test_empty_list(self):
        result = geocode_addresses_with_nominatim([])
        assert result == []


class TestFindVectorDatasetFile:
    """find_vector_dataset_file_in_directory discovers spatial files."""

    def test_finds_shapefile(self, tmp_path):
        (tmp_path / "data.shp").touch()
        (tmp_path / "data.dbf").touch()
        from siege_utilities.geo.vector_files import find_vector_dataset_file_in_directory
        result = find_vector_dataset_file_in_directory(tmp_path)
        assert result is not None
        assert result.suffix == ".shp"

    def test_finds_geojson(self, tmp_path):
        (tmp_path / "layer.geojson").touch()
        from siege_utilities.geo.vector_files import find_vector_dataset_file_in_directory
        result = find_vector_dataset_file_in_directory(tmp_path)
        assert result is not None
        assert result.suffix == ".geojson"

    def test_finds_gpkg(self, tmp_path):
        (tmp_path / "districts.gpkg").touch()
        from siege_utilities.geo.vector_files import find_vector_dataset_file_in_directory
        result = find_vector_dataset_file_in_directory(tmp_path)
        assert result is not None
        assert result.suffix == ".gpkg"

    def test_custom_extensions(self, tmp_path):
        (tmp_path / "data.csv").touch()
        (tmp_path / "data.parquet").touch()
        from siege_utilities.geo.vector_files import find_vector_dataset_file_in_directory
        result = find_vector_dataset_file_in_directory(
            tmp_path, extensions=[".parquet"]
        )
        assert result is not None
        assert result.suffix == ".parquet"

    def test_returns_none_empty_dir(self, tmp_path):
        from siege_utilities.geo.vector_files import find_vector_dataset_file_in_directory
        assert find_vector_dataset_file_in_directory(tmp_path) is None

    def test_returns_none_nonexistent_dir(self, tmp_path):
        from siege_utilities.geo.vector_files import find_vector_dataset_file_in_directory
        assert find_vector_dataset_file_in_directory(tmp_path / "nope") is None

    def test_recursive_search(self, tmp_path):
        sub = tmp_path / "nested" / "deep"
        sub.mkdir(parents=True)
        (sub / "boundary.shp").touch()
        from siege_utilities.geo.vector_files import find_vector_dataset_file_in_directory
        result = find_vector_dataset_file_in_directory(tmp_path)
        assert result is not None
        assert result.name == "boundary.shp"
