"""Tests for NCES download infrastructure."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestNCESDownloader:
    """Tests for NCESDownloader class."""

    def test_init_default_cache(self):
        """NCESDownloader creates temp dir when no cache_dir given."""
        from siege_utilities.geo.nces_download import NCESDownloader

        downloader = NCESDownloader()
        assert downloader.cache_dir.exists()
        assert downloader.timeout == 120

    def test_init_custom_cache(self, tmp_path):
        """NCESDownloader uses provided cache_dir."""
        from siege_utilities.geo.nces_download import NCESDownloader

        cache = tmp_path / "nces_cache"
        downloader = NCESDownloader(cache_dir=str(cache))
        assert downloader.cache_dir == cache
        assert cache.exists()

    def test_validate_year_valid(self):
        """Valid NCES years pass validation."""
        from siege_utilities.geo.nces_download import NCESDownloader

        downloader = NCESDownloader()
        # Should not raise
        downloader._validate_year(2023)
        downloader._validate_year(2020)

    def test_validate_year_invalid(self):
        """Invalid NCES years raise ValueError."""
        from siege_utilities.geo.nces_download import NCESDownloader

        downloader = NCESDownloader()
        with pytest.raises(ValueError, match="not available"):
            downloader._validate_year(1999)

    def test_build_url(self):
        """URL construction uses correct endpoints and patterns."""
        from siege_utilities.geo.nces_download import NCESDownloader

        downloader = NCESDownloader()
        url = downloader._build_url("locale_boundaries", 2023)
        assert "EDGE_LOCALE_BOUNDARIES" in url
        assert "2023" in url

    def test_build_url_school_locations(self):
        """School location URLs are constructed correctly."""
        from siege_utilities.geo.nces_download import NCESDownloader

        downloader = NCESDownloader()
        url = downloader._build_url("school_locations", 2022)
        assert "EDGE_GEOCODE_PUBLICSCH" in url
        assert "2022" in url

    @patch("siege_utilities.geo.nces_download.NCESDownloader._download_and_extract")
    def test_download_locale_boundaries_cached(self, mock_extract, tmp_path):
        """download_locale_boundaries uses GeoDataFrame from shapefile."""
        import geopandas as gpd
        from shapely.geometry import box

        from siege_utilities.geo.nces_download import NCESDownloader

        # Create mock shapefile directory with a small GeoDataFrame
        extract_dir = tmp_path / "locale_boundaries_2023"
        extract_dir.mkdir()

        # Build a minimal GeoDataFrame with locale codes
        codes = [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43]
        geometries = [box(i, i, i + 1, i + 1) for i in range(12)]
        gdf = gpd.GeoDataFrame(
            {"LOCALE": codes, "NAME": [f"Zone_{c}" for c in codes]},
            geometry=geometries,
            crs="EPSG:4326",
        )
        shp_path = extract_dir / "locale_boundaries.shp"
        gdf.to_file(shp_path)

        mock_extract.return_value = extract_dir

        downloader = NCESDownloader(cache_dir=str(tmp_path))
        result = downloader.download_locale_boundaries(2023)

        assert len(result) == 12
        assert "locale_code" in result.columns
        assert "locale_category" in result.columns
        assert "locale_subcategory" in result.columns
        assert set(result["locale_code"]) == set(codes)

    @patch("siege_utilities.geo.nces_download.NCESDownloader._download_and_extract")
    def test_download_school_locations_from_shapefile(self, mock_extract, tmp_path):
        """download_school_locations reads shapefile with school points."""
        import geopandas as gpd
        from shapely.geometry import Point

        from siege_utilities.geo.nces_download import NCESDownloader

        extract_dir = tmp_path / "school_locations_2023"
        extract_dir.mkdir()

        gdf = gpd.GeoDataFrame(
            {
                "NCESSCH": ["010000100100", "010000100200"],
                "SCH_NAME": ["School A", "School B"],
                "LEAID": ["0100001", "0100002"],
                "ST": ["AL", "AL"],
                "LOCALE": ["11", "42"],
            },
            geometry=[Point(-86.3, 32.4), Point(-87.1, 33.5)],
            crs="EPSG:4326",
        )
        shp_path = extract_dir / "schools.shp"
        gdf.to_file(shp_path)

        mock_extract.return_value = extract_dir

        downloader = NCESDownloader(cache_dir=str(tmp_path))
        result = downloader.download_school_locations(2023)

        assert len(result) == 2
        assert "ncessch" in result.columns
        assert "school_name" in result.columns

    @patch("siege_utilities.geo.nces_download.NCESDownloader._download_and_extract")
    def test_download_school_locations_state_filter(self, mock_extract, tmp_path):
        """download_school_locations filters by state abbreviation."""
        import geopandas as gpd
        from shapely.geometry import Point

        from siege_utilities.geo.nces_download import NCESDownloader

        extract_dir = tmp_path / "school_locations_2023"
        extract_dir.mkdir()

        gdf = gpd.GeoDataFrame(
            {
                "NCESSCH": ["010000100100", "060000100200"],
                "SCH_NAME": ["School AL", "School CA"],
                "LEAID": ["0100001", "0600002"],
                "ST": ["AL", "CA"],
                "LOCALE": ["11", "21"],
            },
            geometry=[Point(-86.3, 32.4), Point(-118.2, 34.0)],
            crs="EPSG:4326",
        )
        shp_path = extract_dir / "schools.shp"
        gdf.to_file(shp_path)

        mock_extract.return_value = extract_dir

        downloader = NCESDownloader(cache_dir=str(tmp_path))
        result = downloader.download_school_locations(2023, state_abbr="CA")

        assert len(result) == 1
        assert result.iloc[0]["state_abbr"] == "CA"

    @patch("siege_utilities.geo.nces_download.NCESDownloader._download_and_extract")
    def test_download_district_data(self, mock_extract, tmp_path):
        """download_district_data reads CSV with district records."""
        import pandas as pd

        from siege_utilities.geo.nces_download import NCESDownloader

        extract_dir = tmp_path / "district_boundaries_2023"
        extract_dir.mkdir()

        df = pd.DataFrame(
            {
                "LEAID": ["0100001", "0100002"],
                "LEA_NAME": ["District A", "District B"],
                "ST": ["AL", "AL"],
                "LOCALE": ["11", "42"],
                "SURVYEAR": ["2022-23", "2022-23"],
            }
        )
        csv_path = extract_dir / "districts.csv"
        df.to_csv(csv_path, index=False)

        mock_extract.return_value = extract_dir

        downloader = NCESDownloader(cache_dir=str(tmp_path))
        result = downloader.download_district_data(2023)

        assert len(result) == 2
        assert "lea_id" in result.columns
        assert "locale_code" in result.columns
        assert result.iloc[0]["locale_code"] == 11


class TestNCESDownloadError:
    """Tests for error handling."""

    def test_nces_download_error(self):
        from siege_utilities.geo.nces_download import NCESDownloadError

        err = NCESDownloadError("test message")
        assert str(err) == "test message"


class TestFromNCESBoundaries:
    """Tests for NCESLocaleClassifier.from_nces_boundaries()."""

    def test_from_nces_boundaries_constructs_classifier(self):
        """from_nces_boundaries creates a working classifier."""
        import geopandas as gpd
        from shapely.geometry import box

        from siege_utilities.geo.locale import NCESLocaleClassifier

        # Build mock boundaries with all 12 locale codes
        codes = [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43]
        geometries = [box(i * 10, i * 10, i * 10 + 10, i * 10 + 10) for i in range(12)]
        subcats = [
            "city_large", "city_midsize", "city_small",
            "suburb_large", "suburb_midsize", "suburb_small",
            "town_fringe", "town_distant", "town_remote",
            "rural_fringe", "rural_distant", "rural_remote",
        ]
        cats = [
            "city", "city", "city",
            "suburban", "suburban", "suburban",
            "town", "town", "town",
            "rural", "rural", "rural",
        ]
        boundaries = gpd.GeoDataFrame(
            {
                "locale_code": codes,
                "locale_category": cats,
                "locale_subcategory": subcats,
                "name": [s.replace("_", " ").title() for s in subcats],
            },
            geometry=geometries,
            crs="EPSG:4326",
        )

        with patch(
            "siege_utilities.geo.nces_download.NCESDownloader"
        ) as MockDownloader:
            mock_instance = MagicMock()
            mock_instance.download_locale_boundaries.return_value = boundaries
            MockDownloader.return_value = mock_instance

            classifier = NCESLocaleClassifier.from_nces_boundaries(year=2023)
            assert classifier is not None
