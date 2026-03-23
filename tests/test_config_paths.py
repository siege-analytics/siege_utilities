"""Tests for siege_utilities.config.paths module."""

from pathlib import Path


class TestConstants:
    """Tests for path constants."""

    def test_siege_utilities_home_is_path(self):
        from siege_utilities.config.paths import SIEGE_UTILITIES_HOME
        assert isinstance(SIEGE_UTILITIES_HOME, Path)

    def test_standard_subdirs(self):
        from siege_utilities.config.paths import STANDARD_SUBDIRS
        assert isinstance(STANDARD_SUBDIRS, dict)
        assert "config" in STANDARD_SUBDIRS
        assert "data" in STANDARD_SUBDIRS
        assert "logs" in STANDARD_SUBDIRS
        assert "output" in STANDARD_SUBDIRS

    def test_file_extensions(self):
        from siege_utilities.config.paths import FILE_EXTENSIONS
        assert "data" in FILE_EXTENSIONS
        assert "images" in FILE_EXTENSIONS
        assert "documents" in FILE_EXTENSIONS
        assert "config" in FILE_EXTENSIONS
        assert ".csv" in FILE_EXTENSIONS["data"]
        assert ".png" in FILE_EXTENSIONS["images"]


class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists."""

    def test_creates_directory(self, tmp_path):
        from siege_utilities.config.paths import ensure_directory_exists
        new_dir = tmp_path / "new_dir"
        result = ensure_directory_exists(new_dir)
        assert new_dir.exists()
        assert result == new_dir

    def test_existing_directory_ok(self, tmp_path):
        from siege_utilities.config.paths import ensure_directory_exists
        result = ensure_directory_exists(tmp_path)
        assert result == tmp_path

    def test_nested_directories(self, tmp_path):
        from siege_utilities.config.paths import ensure_directory_exists
        nested = tmp_path / "a" / "b" / "c"
        result = ensure_directory_exists(nested)
        assert nested.exists()
        assert result == nested


class TestGetProjectPath:
    """Tests for get_project_path."""

    def test_known_project(self):
        from siege_utilities.config.paths import get_project_path, SIEGE_UTILITIES_HOME
        result = get_project_path("siege_utilities")
        assert result == SIEGE_UTILITIES_HOME

    def test_unknown_project(self):
        from siege_utilities.config.paths import get_project_path
        result = get_project_path("nonexistent")
        assert result is None

    def test_case_insensitive(self):
        from siege_utilities.config.paths import get_project_path
        result = get_project_path("SIEGE_UTILITIES")
        assert result is not None


class TestGetCachePath:
    """Tests for get_cache_path."""

    def test_default_cache(self):
        from siege_utilities.config.paths import get_cache_path, SIEGE_CACHE_DIR
        result = get_cache_path()
        assert result == SIEGE_CACHE_DIR

    def test_spark_cache(self):
        from siege_utilities.config.paths import get_cache_path, SPARK_CACHE_DIR
        result = get_cache_path("spark")
        assert result == SPARK_CACHE_DIR

    def test_unknown_returns_default(self):
        from siege_utilities.config.paths import get_cache_path, SIEGE_CACHE_DIR
        result = get_cache_path("nonexistent")
        assert result == SIEGE_CACHE_DIR


class TestGetOutputPath:
    """Tests for get_output_path."""

    def test_default_output(self):
        from siege_utilities.config.paths import get_output_path, SIEGE_OUTPUT_DIR
        result = get_output_path()
        assert result == SIEGE_OUTPUT_DIR

    def test_reports_output(self):
        from siege_utilities.config.paths import get_output_path, REPORTS_OUTPUT_DIR
        result = get_output_path("reports")
        assert result == REPORTS_OUTPUT_DIR


class TestGetDataPath:
    """Tests for get_data_path."""

    def test_default_data(self):
        from siege_utilities.config.paths import get_data_path, DATA_DIR
        result = get_data_path()
        assert result == DATA_DIR

    def test_census_data(self):
        from siege_utilities.config.paths import get_data_path, CENSUS_DATA_DIR
        result = get_data_path("census")
        assert result == CENSUS_DATA_DIR


class TestGetFileType:
    """Tests for get_file_type."""

    def test_csv_is_data(self):
        from siege_utilities.config.paths import get_file_type
        assert get_file_type(Path("file.csv")) == "data"

    def test_png_is_images(self):
        from siege_utilities.config.paths import get_file_type
        assert get_file_type(Path("image.png")) == "images"

    def test_pdf_matches_first_category(self):
        from siege_utilities.config.paths import get_file_type
        # PDF appears in both images and documents; it matches whichever comes first
        result = get_file_type(Path("doc.pdf"))
        assert result in ("images", "documents")

    def test_yaml_is_config(self):
        from siege_utilities.config.paths import get_file_type
        assert get_file_type(Path("config.yaml")) == "config"

    def test_py_is_code(self):
        from siege_utilities.config.paths import get_file_type
        assert get_file_type(Path("script.py")) == "code"

    def test_unknown_extension(self):
        from siege_utilities.config.paths import get_file_type
        assert get_file_type(Path("file.xyz")) == "unknown"

    def test_case_insensitive(self):
        from siege_utilities.config.paths import get_file_type
        assert get_file_type(Path("file.CSV")) == "data"


class TestGetRelativeToHome:
    """Tests for get_relative_to_home."""

    def test_home_relative(self):
        from siege_utilities.config.paths import get_relative_to_home
        home = Path.home()
        result = get_relative_to_home(home / "projects" / "test")
        assert result == "~/projects/test"

    def test_non_home_path(self):
        from siege_utilities.config.paths import get_relative_to_home
        result = get_relative_to_home(Path("/tmp/test"))
        assert result == "/tmp/test"


class TestSetupStandardDirectories:
    """Tests for setup_standard_directories."""

    def test_creates_standard_dirs(self, tmp_path):
        from siege_utilities.config.paths import setup_standard_directories, STANDARD_SUBDIRS
        result = setup_standard_directories(tmp_path)
        assert isinstance(result, dict)
        for dirname in STANDARD_SUBDIRS:
            assert dirname in result
            assert (tmp_path / dirname).exists()
