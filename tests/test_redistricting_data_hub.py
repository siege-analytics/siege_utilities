"""Tests for siege_utilities.data.redistricting_data_hub module."""

from __future__ import annotations

import json
import math
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from siege_utilities.data.redistricting_data_hub import (
    RDHClient,
    RDHDataset,
    RDHDataFormat,
    RDHDatasetType,
    RDH_BASE_URL,
    US_STATES,
    polsby_popper,
    reock,
    convex_hull_ratio,
    schwartzberg,
    compute_compactness,
    compare_plans,
    demographic_profile,
    CompactnessScores,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    """Create an RDHClient with test credentials."""
    return RDHClient(
        username="test@example.com",
        password="secret",
        cache_dir=tmp_path / "rdh_cache",
    )


@pytest.fixture
def sample_api_response():
    """Sample API response listing datasets."""
    return [
        {
            "title": "VA_2020_PL94171_block_csv",
            "url": "https://redistrictingdatahub.org/files/VA_2020_PL94171_block.csv",
            "state": "VA",
            "format": "csv",
            "year": "2020",
            "geography": "block",
            "type": "pl94171",
            "official": True,
            "file_size": "45MB",
        },
        {
            "title": "VA_enacted_congress_2022_shp",
            "url": "https://redistrictingdatahub.org/files/VA_congress_2022.zip",
            "state": "VA",
            "format": "shp",
            "year": "2022",
            "geography": "congressional",
            "type": "legislative",
            "official": True,
        },
        {
            "title": "VA_CVAP_2021_tract_csv",
            "url": "https://redistrictingdatahub.org/files/VA_CVAP_2021.csv",
            "state": "VA",
            "format": "csv",
            "year": "2021",
            "geography": "tract",
            "type": "cvap",
            "official": False,
        },
        {
            "title": "VA_precinct_election_2020_shp",
            "url": "https://redistrictingdatahub.org/files/VA_precinct_2020.zip",
            "state": "VA",
            "format": "shp",
            "year": "2020",
            "geography": "precinct",
            "type": "election",
            "official": False,
        },
    ]


@pytest.fixture
def circle_geometry():
    """A circle-like geometry for compactness testing."""
    from shapely.geometry import Point
    return Point(0, 0).buffer(1, resolution=64)


@pytest.fixture
def square_geometry():
    """A square geometry for compactness testing."""
    from shapely.geometry import box
    return box(0, 0, 1, 1)


@pytest.fixture
def elongated_geometry():
    """A long thin rectangle (low compactness)."""
    from shapely.geometry import box
    return box(0, 0, 10, 0.1)


# ---------------------------------------------------------------------------
# RDHDataset
# ---------------------------------------------------------------------------

class TestRDHDataset:

    def test_filename_from_url(self):
        ds = RDHDataset(title="test", url="https://example.com/path/data.csv")
        assert ds.filename == "data.csv"

    def test_filename_empty_url(self):
        ds = RDHDataset(title="test", url="")
        assert ds.filename == ""

    def test_is_shapefile(self):
        ds = RDHDataset(title="t", url="u", format="shp")
        assert ds.is_shapefile is True
        ds2 = RDHDataset(title="t", url="u", format="shapefile")
        assert ds2.is_shapefile is True
        ds3 = RDHDataset(title="t", url="u", format="csv")
        assert ds3.is_shapefile is False

    def test_is_csv(self):
        ds = RDHDataset(title="t", url="u", format="csv")
        assert ds.is_csv is True
        ds2 = RDHDataset(title="t", url="u", format="shp")
        assert ds2.is_csv is False


class TestRDHDataFormat:

    def test_enum_values(self):
        assert RDHDataFormat.CSV.value == "csv"
        assert RDHDataFormat.SHAPEFILE.value == "shp"


class TestRDHDatasetType:

    def test_enum_values(self):
        assert RDHDatasetType.PL94171.value == "pl94171"
        assert RDHDatasetType.CVAP.value == "cvap"
        assert RDHDatasetType.ACS5.value == "acs5"


# ---------------------------------------------------------------------------
# RDHClient initialization
# ---------------------------------------------------------------------------

class TestRDHClientInit:

    def test_init_with_explicit_credentials(self, tmp_path):
        c = RDHClient(username="u", password="p", cache_dir=tmp_path)
        assert c.username == "u"
        assert c.password == "p"
        assert c.cache_dir == tmp_path

    def test_init_from_env_vars(self, tmp_path):
        with patch.dict(os.environ, {"RDH_USERNAME": "env_user", "RDH_PASSWORD": "env_pass"}):
            c = RDHClient(cache_dir=tmp_path)
            assert c.username == "env_user"
            assert c.password == "env_pass"

    def test_init_default_cache_dir(self):
        c = RDHClient(username="u", password="p")
        assert c.cache_dir == Path.home() / ".cache" / "siege_utilities" / "rdh"

    def test_init_custom_base_url(self, tmp_path):
        c = RDHClient(username="u", password="p", base_url="http://test.local/api", cache_dir=tmp_path)
        assert c.base_url == "http://test.local/api"

    def test_init_missing_requests(self, tmp_path):
        with patch.dict("sys.modules", {"requests": None}):
            with patch("siege_utilities.data.redistricting_data_hub.HAS_REQUESTS", False):
                with pytest.raises(ImportError, match="requests"):
                    RDHClient(username="u", password="p", cache_dir=tmp_path)


class TestValidateCredentials:

    def test_valid(self, client):
        assert client.validate_credentials() is True

    def test_missing_username(self, tmp_path):
        c = RDHClient(username="", password="p", cache_dir=tmp_path)
        assert c.validate_credentials() is False

    def test_missing_password(self, tmp_path):
        c = RDHClient(username="u", password="", cache_dir=tmp_path)
        assert c.validate_credentials() is False


# ---------------------------------------------------------------------------
# Listing datasets
# ---------------------------------------------------------------------------

class TestListDatasets:

    def test_list_returns_datasets(self, client, sample_api_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.list_datasets(states=["VA"])

        assert len(results) == 4
        assert all(isinstance(r, RDHDataset) for r in results)
        assert results[0].title == "VA_2020_PL94171_block_csv"

    def test_list_with_format_filter(self, client, sample_api_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.list_datasets(states=["VA"], format=RDHDataFormat.CSV)

        # All returned (server-side filter), client doesn't re-filter by format
        assert len(results) >= 1

    def test_list_state_batching(self, client, sample_api_response):
        """Lists of >4 states should be batched into multiple requests."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response[:1]
        mock_resp.raise_for_status = MagicMock()

        states = ["VA", "MD", "DC", "NC", "PA", "NY"]
        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            results = client.list_datasets(states=states)

        # Should make 2 batches: 4 + 2
        assert mock_get.call_count == 2

    def test_list_no_credentials(self, tmp_path):
        c = RDHClient(username="", password="", cache_dir=tmp_path)
        results = c.list_datasets(states=["VA"])
        assert results == []

    def test_list_api_error(self, client):
        import requests
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.RequestException("timeout")

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.list_datasets(states=["VA"])

        assert results == []

    def test_list_with_dataset_type_filter(self, client, sample_api_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.list_datasets(states=["VA"], dataset_type="cvap")

        assert len(results) == 1
        assert "CVAP" in results[0].title

    def test_list_official_only(self, client, sample_api_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.list_datasets(states=["VA"], official=True)

        assert all(ds.official for ds in results)

    def test_parse_dict_response(self, client, sample_api_response):
        """API may return {data: [...]} instead of bare list."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": sample_api_response}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.list_datasets(states=["VA"])

        assert len(results) == 4


class TestParseDatasetEntry:

    def test_parse_standard_entry(self, client):
        entry = {
            "title": "VA_2020_data",
            "url": "https://example.com/VA_2020.csv",
            "state": "VA",
            "format": "csv",
            "year": "2020",
        }
        ds = client._parse_dataset_entry(entry)
        assert ds is not None
        assert ds.title == "VA_2020_data"
        assert ds.state == "VA"
        assert ds.format == "csv"

    def test_parse_no_url(self, client):
        entry = {"title": "no url"}
        ds = client._parse_dataset_entry(entry)
        assert ds is None

    def test_parse_non_dict(self, client):
        ds = client._parse_dataset_entry("not a dict")
        assert ds is None

    def test_infer_format_from_url(self, client):
        entry = {"title": "test", "url": "https://x.com/data.csv"}
        ds = client._parse_dataset_entry(entry)
        assert ds.format == "csv"

    def test_infer_state_from_title(self, client):
        entry = {"title": "VA_2020_data", "url": "https://x.com/data.csv"}
        ds = client._parse_dataset_entry(entry)
        assert ds.state == "VA"

    def test_alternative_url_keys(self, client):
        entry = {"title": "test", "download_url": "https://x.com/data.csv"}
        ds = client._parse_dataset_entry(entry)
        assert ds is not None
        assert ds.url == "https://x.com/data.csv"


# ---------------------------------------------------------------------------
# Downloading
# ---------------------------------------------------------------------------

class TestDownloadDataset:

    def test_download_creates_file(self, client, tmp_path):
        content = b"col1,col2\na,b\n"
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [content]
        mock_resp.raise_for_status = MagicMock()

        ds = RDHDataset(title="test", url="https://example.com/test.csv")

        with patch.object(client._session, "get", return_value=mock_resp):
            path = client.download_dataset(ds, output_dir=tmp_path)

        assert path.exists()
        assert path.read_bytes() == content

    def test_download_uses_cache(self, client, tmp_path):
        cached = tmp_path / "cached.csv"
        cached.write_text("cached data")

        ds = RDHDataset(title="test", url="https://example.com/cached.csv")

        path = client.download_dataset(ds, output_dir=tmp_path, use_cache=True)
        assert path == cached

    def test_download_string_url(self, client, tmp_path):
        content = b"data"
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [content]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            path = client.download_dataset(
                "https://example.com/file.csv", output_dir=tmp_path
            )

        assert path.name == "file.csv"

    def test_download_zip_extraction(self, client, tmp_path):
        # Create a real ZIP in memory
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("data.shp", "fake shapefile")
            zf.writestr("data.dbf", "fake dbf")
        zip_bytes = buf.getvalue()

        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [zip_bytes]
        mock_resp.raise_for_status = MagicMock()

        ds = RDHDataset(title="test", url="https://example.com/data.zip")

        with patch.object(client._session, "get", return_value=mock_resp):
            path = client.download_dataset(ds, output_dir=tmp_path)

        # Should return extracted directory
        assert path.is_dir()
        assert (path / "data.shp").exists()

    def test_download_error_raises(self, client, tmp_path):
        import requests
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.RequestException("404")

        ds = RDHDataset(title="test", url="https://example.com/missing.csv")

        with patch.object(client._session, "get", return_value=mock_resp):
            with pytest.raises(requests.RequestException):
                client.download_dataset(ds, output_dir=tmp_path)


# ---------------------------------------------------------------------------
# Loading data
# ---------------------------------------------------------------------------

class TestLoadCSV:

    def test_load_csv_from_path(self, client, tmp_path):
        import pandas as pd
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n")

        df = client.load_csv(csv_file)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["a", "b"]

    def test_load_csv_from_directory(self, client, tmp_path):
        csv_file = tmp_path / "subdir" / "data.csv"
        csv_file.parent.mkdir()
        csv_file.write_text("x,y\n1,2\n")

        import pandas as pd
        # Create an RDHDataset that returns the directory
        with patch.object(client, "download_dataset", return_value=csv_file.parent):
            ds = RDHDataset(title="test", url="https://example.com/data.zip")
            df = client.load_csv(ds)

        assert len(df) == 1

    def test_load_csv_no_csv_in_dir(self, client, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="No CSV"):
            client.load_csv(empty_dir)


class TestLoadShapefile:

    def test_load_shapefile_missing_geopandas(self, client, tmp_path):
        with patch("siege_utilities.data.redistricting_data_hub.HAS_GEOPANDAS", False):
            with pytest.raises(ImportError, match="geopandas"):
                client.load_shapefile(tmp_path / "test.shp")


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:

    def test_get_enacted_plans(self, client, sample_api_response):
        # Add an enacted congress dataset
        sample_api_response[1]["title"] = "VA_enacted_congressional_2022"
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            plans = client.get_enacted_plans("VA", chamber="congress")

        assert len(plans) >= 1
        assert any("enacted" in p.title.lower() or "congressional" in p.title.lower() for p in plans)

    def test_get_precinct_data(self, client, sample_api_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.get_precinct_data("VA")

        assert len(results) == 1
        assert "precinct" in results[0].title.lower()

    def test_get_cvap_data(self, client, sample_api_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.get_cvap_data("VA")

        assert len(results) == 1
        assert "CVAP" in results[0].title

    def test_get_pl94171_data(self, client, sample_api_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_api_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            results = client.get_pl94171_data("VA")

        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Compactness scoring
# ---------------------------------------------------------------------------

class TestPolsbyPopper:

    def test_circle_near_one(self, circle_geometry):
        score = polsby_popper(circle_geometry)
        assert 0.95 < score <= 1.0

    def test_square(self, square_geometry):
        score = polsby_popper(square_geometry)
        expected = (4 * math.pi * 1.0) / (4.0 ** 2)  # pi/4 ≈ 0.785
        assert abs(score - expected) < 0.01

    def test_elongated_low(self, elongated_geometry):
        score = polsby_popper(elongated_geometry)
        assert score < 0.2

    def test_empty_geometry(self):
        from shapely.geometry import Point
        empty = Point().buffer(0)
        assert polsby_popper(empty) == 0.0

    def test_none(self):
        assert polsby_popper(None) == 0.0


class TestReock:

    def test_circle_near_one(self, circle_geometry):
        score = reock(circle_geometry)
        # Circle should score high
        assert score > 0.5

    def test_square_moderate(self, square_geometry):
        score = reock(square_geometry)
        assert 0.3 < score < 1.0

    def test_none(self):
        assert reock(None) == 0.0

    def test_empty(self):
        from shapely.geometry import Point
        assert reock(Point().buffer(0)) == 0.0


class TestConvexHullRatio:

    def test_convex_shape_is_one(self, square_geometry):
        score = convex_hull_ratio(square_geometry)
        assert abs(score - 1.0) < 0.01

    def test_circle_is_one(self, circle_geometry):
        score = convex_hull_ratio(circle_geometry)
        assert abs(score - 1.0) < 0.01

    def test_concave_below_one(self):
        from shapely.geometry import Polygon
        # L-shape
        l_shape = Polygon([(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)])
        score = convex_hull_ratio(l_shape)
        assert score < 1.0
        assert score > 0.5

    def test_none(self):
        assert convex_hull_ratio(None) == 0.0


class TestSchwartzberg:

    def test_circle_near_one(self, circle_geometry):
        score = schwartzberg(circle_geometry)
        assert 0.95 < score <= 1.0

    def test_square_moderate(self, square_geometry):
        score = schwartzberg(square_geometry)
        assert 0.5 < score < 1.0

    def test_elongated_low(self, elongated_geometry):
        score = schwartzberg(elongated_geometry)
        assert score < 0.5

    def test_none(self):
        assert schwartzberg(None) == 0.0


class TestComputeCompactness:

    def test_compute_from_geodataframe(self):
        import pandas as pd
        import geopandas as gpd
        from shapely.geometry import Point, box

        gdf = gpd.GeoDataFrame(
            {"GEOID": ["D1", "D2", "D3"]},
            geometry=[
                Point(0, 0).buffer(1, resolution=64),
                box(0, 0, 1, 1),
                box(0, 0, 10, 0.1),
            ],
        )

        result = compute_compactness(gdf)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "polsby_popper" in result.columns
        assert "reock" in result.columns
        assert "convex_hull_ratio" in result.columns
        assert "schwartzberg" in result.columns

        # Circle should have highest PP score
        assert result.iloc[0]["polsby_popper"] > result.iloc[2]["polsby_popper"]


# ---------------------------------------------------------------------------
# Plan comparison
# ---------------------------------------------------------------------------

class TestComparePlans:

    def test_compare_two_plans(self):
        import geopandas as gpd
        from shapely.geometry import box

        plan_a = gpd.GeoDataFrame(
            {
                "GEOID": ["D1", "D2", "D3"],
                "TOTPOP": [100000, 105000, 95000],
            },
            geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)],
        )
        plan_b = gpd.GeoDataFrame(
            {
                "GEOID": ["D1", "D2", "D3"],
                "TOTPOP": [98000, 102000, 100000],
            },
            geometry=[box(0, 0, 1.1, 1), box(1.1, 0, 2.1, 1), box(2.1, 0, 3, 1)],
        )

        result = compare_plans(plan_a, plan_b)

        assert "plan_a" in result
        assert "plan_b" in result
        assert result["plan_a"]["num_districts"] == 3
        assert result["plan_b"]["num_districts"] == 3
        assert result["district_count_match"] is True
        assert "compactness_delta" in result
        assert isinstance(result["population_difference"], int)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:

    def test_us_states_count(self):
        assert len(US_STATES) == 52  # 50 + DC + PR

    def test_base_url(self):
        assert "redistrictingdatahub.org" in RDH_BASE_URL

    def test_compactness_scores_dataclass(self):
        cs = CompactnessScores(district_id="D1", polsby_popper=0.8)
        assert cs.district_id == "D1"
        assert cs.polsby_popper == 0.8
        assert cs.reock == 0.0
