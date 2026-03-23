"""Tests for siege_utilities.config.directories module."""

from pathlib import Path
from siege_utilities.config.directories import (
    create_directory_structure,
    get_directory_info,
    ensure_directories_exist,
    clean_empty_directories,
    save_directory_config,
    load_directory_config,
    list_directory_configs,
)


class TestCreateDirectoryStructure:
    """Tests for create_directory_structure."""

    def test_simple_structure(self, tmp_path):
        structure = {"data": {}, "logs": {}}
        result = create_directory_structure(str(tmp_path / "project"), structure)
        assert "data" in result
        assert "logs" in result
        assert Path(result["data"]).exists()
        assert Path(result["logs"]).exists()

    def test_nested_structure(self, tmp_path):
        structure = {
            "data": {"raw": {}, "processed": {}},
            "output": {}
        }
        result = create_directory_structure(str(tmp_path / "project"), structure)
        assert "data" in result
        assert "data/raw" in result
        assert "data/processed" in result
        assert "output" in result

    def test_gitkeep_created(self, tmp_path):
        structure = {"mydir": {}}
        result = create_directory_structure(str(tmp_path / "project"), structure)
        gitkeep = Path(result["mydir"]) / ".gitkeep"
        assert gitkeep.exists()


class TestGetDirectoryInfo:
    """Tests for get_directory_info."""

    def test_existing_directory(self, tmp_path):
        # Create some files
        (tmp_path / "file1.txt").write_text("hello")
        (tmp_path / "file2.txt").write_text("world")
        (tmp_path / "subdir").mkdir()

        info = get_directory_info(str(tmp_path))
        assert info["exists"] is True
        assert info["file_count"] == 2
        assert info["directory_count"] == 1
        assert info["total_size_bytes"] > 0

    def test_nonexistent_directory(self, tmp_path):
        info = get_directory_info(str(tmp_path / "nonexistent"))
        assert info == {}

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        info = get_directory_info(str(empty_dir))
        assert info["exists"] is True
        assert info["file_count"] == 0


class TestEnsureDirectoriesExist:
    """Tests for ensure_directories_exist."""

    def test_creates_missing_dirs(self, tmp_path):
        paths = {
            "data": str(tmp_path / "data"),
            "logs": str(tmp_path / "logs"),
        }
        result = ensure_directories_exist(paths)
        assert result is True
        assert Path(paths["data"]).exists()
        assert Path(paths["logs"]).exists()

    def test_creates_gitkeep(self, tmp_path):
        paths = {"mydir": str(tmp_path / "mydir")}
        ensure_directories_exist(paths)
        assert (tmp_path / "mydir" / ".gitkeep").exists()


class TestCleanEmptyDirectories:
    """Tests for clean_empty_directories."""

    def test_removes_empty_dirs(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        removed = clean_empty_directories(str(tmp_path))
        assert removed == 1
        assert not empty_dir.exists()

    def test_keeps_dirs_with_gitkeep(self, tmp_path):
        dir_with_gitkeep = tmp_path / "kept"
        dir_with_gitkeep.mkdir()
        (dir_with_gitkeep / ".gitkeep").touch()
        removed = clean_empty_directories(str(tmp_path), keep_gitkeep=True)
        assert removed == 0
        assert dir_with_gitkeep.exists()

    def test_nonexistent_base_returns_zero(self, tmp_path):
        removed = clean_empty_directories(str(tmp_path / "nonexistent"))
        assert removed == 0

    def test_keeps_non_empty_dirs(self, tmp_path):
        non_empty = tmp_path / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")
        removed = clean_empty_directories(str(tmp_path))
        assert removed == 0
        assert non_empty.exists()


class TestSaveAndLoadDirectoryConfig:
    """Tests for save_directory_config and load_directory_config."""

    def test_roundtrip(self, tmp_path):
        paths = {"data": "/some/path", "logs": "/other/path"}
        config_dir = str(tmp_path / "config")
        save_directory_config(paths, "test_config", config_dir)
        loaded = load_directory_config("test_config", config_dir)
        assert loaded is not None
        assert loaded["name"] == "test_config"
        assert loaded["paths"] == paths

    def test_load_nonexistent_returns_none(self, tmp_path):
        result = load_directory_config("nonexistent", str(tmp_path))
        assert result is None


class TestListDirectoryConfigs:
    """Tests for list_directory_configs."""

    def test_empty_dir(self, tmp_path):
        result = list_directory_configs(str(tmp_path))
        assert result == []

    def test_nonexistent_dir(self, tmp_path):
        result = list_directory_configs(str(tmp_path / "nonexistent"))
        assert result == []

    def test_lists_configs(self, tmp_path):
        config_dir = str(tmp_path / "config")
        paths = {"data": "/path"}
        save_directory_config(paths, "cfg1", config_dir)
        save_directory_config(paths, "cfg2", config_dir)
        result = list_directory_configs(config_dir)
        assert len(result) == 2
        names = [c["name"] for c in result]
        assert "cfg1" in names
        assert "cfg2" in names
