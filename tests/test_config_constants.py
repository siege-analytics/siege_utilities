"""Tests for siege_utilities.config.constants module."""


class TestGetTimeout:
    """Tests for get_timeout helper function."""

    def test_default_timeout(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout() == 30
        assert get_timeout("default") == 30

    def test_download_timeout(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout("download") == 60

    def test_database_timeout(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout("database") == 30

    def test_census_timeout(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout("census") == 45

    def test_api_timeout(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout("api") == 30

    def test_extended_timeout(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout("extended") == 300

    def test_cache_timeout(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout("cache") == 3600

    def test_unknown_returns_default(self):
        from siege_utilities.config.constants import get_timeout
        assert get_timeout("nonexistent") == 30


class TestGetChartDimensions:
    """Tests for get_chart_dimensions helper function."""

    def test_default_dimensions(self):
        from siege_utilities.config.constants import get_chart_dimensions
        assert get_chart_dimensions() == (10.0, 8.0)
        assert get_chart_dimensions("default") == (10.0, 8.0)

    def test_wide_dimensions(self):
        from siege_utilities.config.constants import get_chart_dimensions
        assert get_chart_dimensions("wide") == (12.0, 10.0)

    def test_presentation_dimensions(self):
        from siege_utilities.config.constants import get_chart_dimensions
        assert get_chart_dimensions("presentation") == (14.0, 10.0)

    def test_unknown_returns_default(self):
        from siege_utilities.config.constants import get_chart_dimensions
        assert get_chart_dimensions("nonexistent") == (10.0, 8.0)


class TestGetFilePath:
    """Tests for get_file_path helper function."""

    def test_home_path(self):
        from siege_utilities.config.constants import get_file_path, SIEGE_UTILITIES_HOME
        assert get_file_path("home") == SIEGE_UTILITIES_HOME

    def test_cache_path(self):
        from siege_utilities.config.constants import get_file_path, SIEGE_CACHE_DIR
        assert get_file_path("cache") == SIEGE_CACHE_DIR

    def test_output_path(self):
        from siege_utilities.config.constants import get_file_path, SIEGE_OUTPUT_DIR
        assert get_file_path("output") == SIEGE_OUTPUT_DIR

    def test_unknown_returns_home(self):
        from siege_utilities.config.constants import get_file_path, SIEGE_UTILITIES_HOME
        assert get_file_path("nonexistent") == SIEGE_UTILITIES_HOME


class TestGetServiceTimeout:
    """Tests for get_service_timeout helper function."""

    def test_known_services(self):
        from siege_utilities.config.constants import get_service_timeout
        assert get_service_timeout("google_analytics") == 30
        assert get_service_timeout("census_api") == 45
        assert get_service_timeout("census_download") == 60
        assert get_service_timeout("snowflake_query") == 300
        assert get_service_timeout("health_check") == 10

    def test_unknown_service_returns_default(self):
        from siege_utilities.config.constants import get_service_timeout, DEFAULT_TIMEOUT
        assert get_service_timeout("nonexistent") == DEFAULT_TIMEOUT


class TestGetServiceRowLimit:
    """Tests for get_service_row_limit helper function."""

    def test_known_services(self):
        from siege_utilities.config.constants import get_service_row_limit
        assert get_service_row_limit("google_analytics") == 100000
        assert get_service_row_limit("census_api") == 50000
        assert get_service_row_limit("reporting") == 1000000

    def test_unknown_service_returns_default(self):
        from siege_utilities.config.constants import get_service_row_limit, DEFAULT_ROW_LIMIT
        assert get_service_row_limit("nonexistent") == DEFAULT_ROW_LIMIT


class TestConstantValues:
    """Tests that key constants have expected values."""

    def test_library_metadata(self):
        from siege_utilities.config.constants import LIBRARY_NAME, LIBRARY_AUTHOR
        assert LIBRARY_NAME == "siege_utilities"
        assert LIBRARY_AUTHOR == "Siege Analytics"

    def test_file_formats(self):
        from siege_utilities.config.constants import SUPPORTED_FILE_FORMATS, SUPPORTED_IMAGE_FORMATS
        assert "csv" in SUPPORTED_FILE_FORMATS
        assert "parquet" in SUPPORTED_FILE_FORMATS
        assert "png" in SUPPORTED_IMAGE_FORMATS

    def test_timeout_ordering(self):
        from siege_utilities.config.constants import DEFAULT_TIMEOUT, LONG_TIMEOUT, EXTENDED_TIMEOUT, CACHE_TIMEOUT
        assert DEFAULT_TIMEOUT < LONG_TIMEOUT < EXTENDED_TIMEOUT < CACHE_TIMEOUT

    def test_file_thresholds(self):
        from siege_utilities.config.constants import SMALL_FILE_THRESHOLD, LARGE_FILE_THRESHOLD
        assert SMALL_FILE_THRESHOLD < LARGE_FILE_THRESHOLD
        assert SMALL_FILE_THRESHOLD == 1024 * 1024
        assert LARGE_FILE_THRESHOLD == 100 * 1024 * 1024

    def test_chart_constants(self):
        from siege_utilities.config.constants import DEFAULT_DPI, DEFAULT_FONT_SIZE
        assert DEFAULT_DPI == 300
        assert DEFAULT_FONT_SIZE == 10

    def test_color_palette_not_empty(self):
        from siege_utilities.config.constants import DEFAULT_COLOR_PALETTE
        assert len(DEFAULT_COLOR_PALETTE) > 0
        assert all(c.startswith("#") for c in DEFAULT_COLOR_PALETTE)
