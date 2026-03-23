"""Tests for siege_utilities.config.projects module."""

from pathlib import Path
from siege_utilities.config.projects import (
    create_project_config,
    save_project_config,
    load_project_config,
    get_project_path,
    list_projects,
    update_project_config,
    setup_project_directories,
)


class TestCreateProjectConfig:
    """Tests for create_project_config."""

    def test_basic_creation(self, tmp_path):
        config = create_project_config("Test Project", "TP001", base_directory=str(tmp_path))
        assert config["project_name"] == "Test Project"
        assert config["project_code"] == "TP001"
        assert "directories" in config
        assert "settings" in config

    def test_directories_populated(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        dirs = config["directories"]
        assert "base" in dirs
        assert "input" in dirs
        assert "output" in dirs
        assert "data" in dirs
        assert "reports" in dirs
        assert "logs" in dirs
        assert "config" in dirs

    def test_default_settings(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        settings = config["settings"]
        assert settings["data_format"] == "parquet"
        assert settings["log_level"] == "INFO"
        assert settings["backup_enabled"] is True

    def test_custom_description(self, tmp_path):
        config = create_project_config(
            "Test", "T001",
            base_directory=str(tmp_path),
            description="My description"
        )
        assert config["description"] == "My description"

    def test_custom_settings(self, tmp_path):
        config = create_project_config(
            "Test", "T001",
            base_directory=str(tmp_path),
            data_format="csv",
            log_level="DEBUG",
            custom_key="custom_value"
        )
        assert config["settings"]["data_format"] == "csv"
        assert config["settings"]["log_level"] == "DEBUG"
        assert config["settings"]["custom_key"] == "custom_value"


class TestSaveAndLoadProjectConfig:
    """Tests for save_project_config and load_project_config."""

    def test_save_creates_file(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        config_dir = str(tmp_path / "config")
        result = save_project_config(config, config_dir)
        assert Path(result).exists()

    def test_roundtrip(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        config_dir = str(tmp_path / "config")
        save_project_config(config, config_dir)
        loaded = load_project_config("T001", config_dir)
        assert loaded is not None
        assert loaded["project_name"] == "Test"
        assert loaded["project_code"] == "T001"

    def test_load_nonexistent_returns_none(self, tmp_path):
        config_dir = str(tmp_path / "config")
        result = load_project_config("NONEXIST", config_dir)
        assert result is None


class TestGetProjectPath:
    """Tests for get_project_path."""

    def test_known_path_type(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        result = get_project_path(config, "output")
        assert result is not None
        assert "output" in result

    def test_unknown_path_type(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        result = get_project_path(config, "nonexistent")
        assert result is None


class TestListProjects:
    """Tests for list_projects."""

    def test_empty_directory(self, tmp_path):
        result = list_projects(str(tmp_path))
        assert result == []

    def test_nonexistent_directory(self, tmp_path):
        result = list_projects(str(tmp_path / "nonexistent"))
        assert result == []

    def test_lists_saved_projects(self, tmp_path):
        config_dir = str(tmp_path / "config")
        config1 = create_project_config("Project A", "PA001", base_directory=str(tmp_path))
        config2 = create_project_config("Project B", "PB001", base_directory=str(tmp_path))
        save_project_config(config1, config_dir)
        save_project_config(config2, config_dir)
        result = list_projects(config_dir)
        assert len(result) == 2
        codes = [p["code"] for p in result]
        assert "PA001" in codes
        assert "PB001" in codes


class TestUpdateProjectConfig:
    """Tests for update_project_config."""

    def test_update_description(self, tmp_path):
        config_dir = str(tmp_path / "config")
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        save_project_config(config, config_dir)
        result = update_project_config("T001", {"description": "Updated"}, config_dir)
        assert result is True
        loaded = load_project_config("T001", config_dir)
        assert loaded["description"] == "Updated"

    def test_update_nonexistent_returns_false(self, tmp_path):
        config_dir = str(tmp_path / "config")
        result = update_project_config("NONEXIST", {"description": "test"}, config_dir)
        assert result is False


class TestSetupProjectDirectories:
    """Tests for setup_project_directories."""

    def test_creates_directories(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        result = setup_project_directories(config)
        assert result is True
        for dir_path in config["directories"].values():
            assert Path(dir_path).exists()

    def test_creates_gitkeep_files(self, tmp_path):
        config = create_project_config("Test", "T001", base_directory=str(tmp_path))
        setup_project_directories(config)
        for dir_path in config["directories"].values():
            gitkeep = Path(dir_path) / ".gitkeep"
            assert gitkeep.exists()
