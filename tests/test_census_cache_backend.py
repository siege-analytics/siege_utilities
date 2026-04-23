"""
Unit tests for Census API cache backend selection.

Tests that the cache_backend parameter dispatches correctly between
parquet and Django cache backends.
"""

import inspect



class TestCacheBackendInit:
    """Tests for CensusAPIClient cache_backend parameter."""

    def test_cache_backend_parameter_exists(self):
        """Verify cache_backend is a parameter on __init__."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        sig = inspect.signature(CensusAPIClient.__init__)
        assert "cache_backend" in sig.parameters
        assert sig.parameters["cache_backend"].default == "parquet"

    def test_cache_ttl_parameter_exists(self):
        """Verify cache_ttl is a parameter on __init__."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        sig = inspect.signature(CensusAPIClient.__init__)
        assert "cache_ttl" in sig.parameters

    def test_django_cache_methods_exist(self):
        """Verify Django cache dispatch methods exist."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        assert hasattr(CensusAPIClient, "_django_cache_get")
        assert hasattr(CensusAPIClient, "_django_cache_set")

    def test_parquet_cache_methods_exist(self):
        """Verify parquet cache dispatch methods exist."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        assert hasattr(CensusAPIClient, "_parquet_cache_get")
        assert hasattr(CensusAPIClient, "_parquet_cache_set")

    def test_dispatch_methods_call_correct_backend(self):
        """Verify _get_from_cache dispatches based on backend."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        source = inspect.getsource(CensusAPIClient._get_from_cache)
        assert "django" in source
        assert "parquet" in source

    def test_dispatch_save_calls_correct_backend(self):
        """Verify _save_to_cache dispatches based on backend."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        source = inspect.getsource(CensusAPIClient._save_to_cache)
        assert "django" in source
        assert "parquet" in source
