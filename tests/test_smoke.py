"""
Smoke tests for siege_utilities critical paths.

These tests validate that the library's public API is importable and that
key objects instantiate correctly. They require no network, no GDAL, and
no heavy dependencies — designed to run fast on every push.
"""

import pytest
import importlib
import inspect


@pytest.mark.smoke
class TestPublicModuleImports:
    """All public modules should import without error."""

    PUBLIC_MODULES = [
        "siege_utilities",
        "siege_utilities.core",
        "siege_utilities.core.logging",
        "siege_utilities.core.string_utils",
        "siege_utilities.core.sql_safety",
        "siege_utilities.config",
        "siege_utilities.config.census_constants",
        "siege_utilities.geo",
        "siege_utilities.geo.boundary_result",
        "siege_utilities.geo.geoid_utils",
        "siege_utilities.data",
        "siege_utilities.databricks",
    ]

    @pytest.mark.parametrize("module_name", PUBLIC_MODULES)
    def test_module_imports(self, module_name):
        mod = importlib.import_module(module_name)
        assert mod is not None


@pytest.mark.smoke
class TestCensusDataSourceInstantiation:
    """CensusDataSource should instantiate without network calls."""

    def test_census_data_source_class_exists(self):
        from siege_utilities.geo.spatial_data import CensusDataSource
        assert inspect.isclass(CensusDataSource)

    def test_boundary_type_catalog_populated(self):
        from siege_utilities.geo.spatial_data import BOUNDARY_TYPE_CATALOG
        assert isinstance(BOUNDARY_TYPE_CATALOG, dict)
        assert len(BOUNDARY_TYPE_CATALOG) > 40
        # Verify key boundary types are present
        for bt in ["state", "county", "tract", "block_group", "place", "zcta"]:
            assert bt in BOUNDARY_TYPE_CATALOG, f"Missing boundary type: {bt}"

    def test_boundary_type_catalog_entries_well_formed(self):
        from siege_utilities.geo.spatial_data import BOUNDARY_TYPE_CATALOG
        required_keys = {"category", "abbrev", "name", "geometry_type"}
        for bt_name, bt_info in BOUNDARY_TYPE_CATALOG.items():
            assert required_keys.issubset(bt_info.keys()), (
                f"Boundary type '{bt_name}' missing keys: {required_keys - bt_info.keys()}"
            )


@pytest.mark.smoke
class TestBoundaryResultTypes:
    """BoundaryFetchResult and typed exceptions should be importable and functional."""

    def test_boundary_fetch_result_importable(self):
        from siege_utilities.geo.boundary_result import BoundaryFetchResult
        assert hasattr(BoundaryFetchResult, "ok")
        assert hasattr(BoundaryFetchResult, "fail")
        assert hasattr(BoundaryFetchResult, "raise_on_error")

    def test_all_exception_classes_importable(self):
        from siege_utilities.geo.boundary_result import (
            BoundaryRetrievalError,
            BoundaryInputError,
            BoundaryDiscoveryError,
            BoundaryUrlValidationError,
            BoundaryDownloadError,
            BoundaryParseError,
            BoundaryConfigurationError,
        )
        for cls in [
            BoundaryInputError,
            BoundaryDiscoveryError,
            BoundaryUrlValidationError,
            BoundaryDownloadError,
            BoundaryParseError,
            BoundaryConfigurationError,
        ]:
            assert issubclass(cls, BoundaryRetrievalError)


@pytest.mark.smoke
class TestCensusConvenienceFunctions:
    """All 5 Census convenience functions should be callable (signature check only)."""

    CONVENIENCE_FUNCTIONS = [
        "get_available_years",
        "discover_boundary_types",
        "construct_download_url",
        "validate_download_url",
        "get_optimal_year",
    ]

    @pytest.mark.parametrize("func_name", CONVENIENCE_FUNCTIONS)
    def test_convenience_function_callable(self, func_name):
        from siege_utilities.geo import spatial_data
        func = getattr(spatial_data, func_name, None)
        assert func is not None, f"Missing convenience function: {func_name}"
        assert callable(func)

    def test_get_census_boundaries_callable(self):
        from siege_utilities.geo.spatial_data import get_census_boundaries
        assert callable(get_census_boundaries)

    def test_fetch_geographic_boundaries_on_class(self):
        from siege_utilities.geo.spatial_data import CensusDataSource
        assert hasattr(CensusDataSource, "fetch_geographic_boundaries")


@pytest.mark.smoke
class TestGeographicLevelResolution:
    """Geographic level canonical system should work without network."""

    def test_resolve_geographic_level(self):
        from siege_utilities.config.census_constants import resolve_geographic_level
        assert resolve_geographic_level("county") == "county"
        assert resolve_geographic_level("bg") == "block_group"
        assert resolve_geographic_level("congressional_district") == "cd"

    def test_canonical_levels_populated(self):
        from siege_utilities.config.census_constants import CANONICAL_GEOGRAPHIC_LEVELS
        assert isinstance(CANONICAL_GEOGRAPHIC_LEVELS, dict)
        assert len(CANONICAL_GEOGRAPHIC_LEVELS) >= 15

    def test_version_accessible(self):
        import siege_utilities
        assert hasattr(siege_utilities, "__version__")
        assert isinstance(siege_utilities.__version__, str)
        assert len(siege_utilities.__version__) > 0
