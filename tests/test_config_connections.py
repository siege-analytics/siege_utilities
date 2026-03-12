"""Tests for siege_utilities.config.connections module."""

import pytest
from siege_utilities.config.connections import (
    create_connection_profile,
    save_connection_profile,
    load_connection_profile,
)


class TestCreateConnectionProfile:
    """Tests for create_connection_profile."""

    def test_basic_creation(self):
        profile = create_connection_profile(
            "Test Connection",
            "notebook",
            {"url": "http://localhost:8888"},
        )
        assert profile["name"] == "Test Connection"
        assert profile["connection_type"] == "notebook"
        assert "connection_id" in profile
        assert "metadata" in profile

    def test_empty_params_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            create_connection_profile("Test", "notebook", {})

    def test_notebook_specific_fields(self):
        profile = create_connection_profile(
            "Jupyter",
            "notebook",
            {"url": "http://localhost:8888"},
            kernel_type="python3",
        )
        assert "notebook_specific" in profile
        assert profile["notebook_specific"]["kernel_type"] == "python3"

    def test_spark_specific_fields(self):
        profile = create_connection_profile(
            "Spark",
            "spark",
            {"master": "local[*]"},
            app_name="TestApp",
        )
        assert "spark_specific" in profile
        assert profile["spark_specific"]["app_name"] == "TestApp"

    def test_database_specific_fields(self):
        profile = create_connection_profile(
            "Postgres",
            "database",
            {"host": "localhost", "port": 5432},
        )
        assert "database_specific" in profile
        assert profile["database_specific"]["connection_pool_size"] == 5

    def test_metadata_defaults(self):
        profile = create_connection_profile(
            "Test",
            "api",
            {"endpoint": "https://api.example.com"},
        )
        meta = profile["metadata"]
        assert meta["status"] == "active"
        assert meta["auto_connect"] is False
        assert meta["timeout"] == 30

    def test_custom_kwargs(self):
        profile = create_connection_profile(
            "Test",
            "api",
            {"endpoint": "https://api.example.com"},
            tags=["production"],
            notes="Test connection",
            auto_connect=True,
        )
        assert profile["tags"] == ["production"]
        assert profile["notes"] == "Test connection"
        assert profile["metadata"]["auto_connect"] is True

    def test_unique_connection_ids(self):
        p1 = create_connection_profile("A", "api", {"url": "a"})
        p2 = create_connection_profile("B", "api", {"url": "b"})
        assert p1["connection_id"] != p2["connection_id"]


class TestSaveAndLoadConnectionProfile:
    """Tests for save/load roundtrip."""

    def test_roundtrip(self, tmp_path):
        profile = create_connection_profile(
            "Test",
            "notebook",
            {"url": "http://localhost"},
        )
        config_dir = str(tmp_path / "config")
        save_connection_profile(profile, config_dir)
        loaded = load_connection_profile(profile["connection_id"], config_dir)
        assert loaded is not None
        assert loaded["name"] == "Test"
        assert loaded["connection_type"] == "notebook"

    def test_load_nonexistent(self, tmp_path):
        loaded = load_connection_profile("nonexistent-id", str(tmp_path))
        assert loaded is None
