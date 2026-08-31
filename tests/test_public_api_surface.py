"""Public API surface regression tests (#1176).

Ensures the top-level `siege_utilities.__all__` is well-formed and every
declared name actually resolves. Complements the audit script by catching
accidental removal, name typos, and cross-module registration collisions
introduced by future promotion batches.

Cross-refs: SU-4b (error-path coverage extended to declarative metadata),
hostile-review-1176-batch1.md F2.
"""

from __future__ import annotations

import sys
import warnings

import pytest

import siege_utilities


class TestAllDeclaration:
    def test_all_is_defined(self):
        assert hasattr(siege_utilities, "__all__"), \
            "siege_utilities must declare __all__ explicitly (per #1176)"
        assert isinstance(siege_utilities.__all__, list), \
            "__all__ must be a list, not a tuple/set (Python convention for star-import)"

    def test_all_has_no_duplicates(self):
        names = siege_utilities.__all__
        duplicates = [n for n in set(names) if names.count(n) > 1]
        assert not duplicates, f"__all__ contains duplicates: {duplicates}"

    def test_every_declared_name_resolves(self):
        """Every name in __all__ must be a real, importable attribute.

        This catches: (a) name typos in the __all__ list, (b) symbols
        removed from _LAZY_IMPORTS without a matching __all__ update,
        (c) cross-module registration collisions.
        """
        unresolved = []
        for name in siege_utilities.__all__:
            try:
                getattr(siege_utilities, name)
            except AttributeError as exc:
                unresolved.append((name, str(exc)))
        assert not unresolved, (
            f"__all__ declares {len(unresolved)} unresolvable names: {unresolved}"
        )

    def test_star_import_backward_compat_preserved(self):
        """The 39 symbols previously exposed via `.distributed.__all__`
        fallback must remain in `__all__` so `from siege_utilities import *`
        does not silently BREAK for existing consumers (per #1176 batch 1).
        """
        preserved_distributed = {
            "AbstractHDFSOperations", "HDFSConfig", "PYSPARK_AVAILABLE",
            "atomic_write_with_staging", "backup_full_dataframe",
            "clean_and_reorder_bbox", "compute_walkability",
            "create_census_analysis_config", "create_cluster_config",
            "create_geocoding_config", "create_hdfs_config",
            "create_hdfs_operations", "create_local_config",
            "create_unique_staging_directory", "create_yarn_config",
            "ensure_literal",
            "export_prepared_df_as_csv_to_path_using_delimiter",
            "export_pyspark_df_to_excel",
            "flatten_json_column_and_join_back_to_df",
            "get_row_count", "mark_valid_geocode_data",
            "move_column_to_front_of_dataframe",
            "pivot_summary_table_for_bools", "pivot_summary_with_metrics",
            "prepare_dataframe_for_export", "prepare_summary_dataframe",
            "print_debug_table", "py_round", "read_parquet_to_df",
            "register_temp_table", "repartition_and_cache",
            "reproject_geom_columns", "sanitise_dataframe_column_names",
            "setup_distributed_environment", "tabulate_null_vs_not_null",
            "validate_geocode_data", "validate_geometry",
            "walkability_config", "write_df_to_parquet",
        }
        missing = preserved_distributed - set(siege_utilities.__all__)
        assert not missing, (
            f"Star-import backward-compat broken; distributed symbols removed "
            f"from __all__ without a documented BREAKING CHANGE: {sorted(missing)}"
        )


class TestBatch1Promotions:
    """Verify #1176 batch 1 (geo.spatial_data, 27 canonicals) shipped correctly."""

    BATCH_1 = [
        "discover_boundary_types", "download_data", "download_dataset",
        "download_osm_data", "get_available_state_fips",
        "get_available_years", "get_census_boundaries", "get_census_data",
        "get_geographic_boundaries", "get_optimal_year",
        "get_state_abbreviations", "get_state_by_abbreviation",
        "normalize_fips_code", "normalize_state_abbreviation",
        "normalize_state_input", "normalize_state_name",
        "construct_download_url", "get_available_boundary_types",
        "get_comprehensive_state_info", "get_state_abbreviation",
        "get_state_by_name", "get_state_name", "get_unified_fips_data",
        "get_year_directory_contents", "refresh_discovery_cache",
        "validate_download_url", "validate_state_fips",
    ]

    @pytest.mark.parametrize("name", BATCH_1)
    def test_batch_1_symbol_in_all(self, name):
        assert name in siege_utilities.__all__, (
            f"{name!r} promoted per #1176 batch 1 but missing from __all__"
        )

    @pytest.mark.parametrize("name", BATCH_1)
    def test_batch_1_symbol_resolves_to_geo_spatial_data(self, name):
        obj = getattr(siege_utilities, name)
        # Every batch-1 symbol must resolve to geo.spatial_data (hostile
        # review F1: prevents future promotion batches from silently
        # rebinding to a colliding sibling def in a different module).
        assert obj.__module__ == "siege_utilities.geo.spatial_data", (
            f"{name!r} resolves to {obj.__module__!r}, expected "
            "'siege_utilities.geo.spatial_data' — cross-module collision"
        )


class TestBatch2Promotions:
    """Verify #1176 batch 2 (reporting, 26 canonicals) shipped correctly.

    Batch 2 spans multiple `.reporting.*` submodules (chart_generator,
    chart_types, analytics.polling_analyzer, plus top-level `.reporting`
    for classes re-exported from `reporting/__init__.py`). Assertion is
    weaker than batch 1: each symbol must resolve to SOME module under
    `siege_utilities.reporting.*`, not a single specific one.
    """

    BATCH_2 = [
        "AnalyticsReportGenerator", "BaseReportTemplate", "ChartGenerator",
        "ChartTypeRegistry", "ClientBrandingManager", "PollingAnalyzer",
        "PowerPointGenerator", "ReportGenerator",
        "create_bar_chart", "create_bivariate_choropleth",
        "create_choropleth_map", "create_dashboard",
        "create_dataframe_summary_charts", "create_flow_map",
        "create_heatmap", "create_line_chart", "create_marker_map",
        "create_pie_chart", "create_powerpoint_generator",
        "create_report_generator", "create_scatter_plot",
        "export_branding_config", "export_chart_type_config",
        "generate_chart_from_dataframe", "get_report_output_directory",
        "import_branding_config",
    ]

    @pytest.mark.parametrize("name", BATCH_2)
    def test_batch_2_symbol_in_all(self, name):
        assert name in siege_utilities.__all__, (
            f"{name!r} promoted per #1176 batch 2 but missing from __all__"
        )

    @pytest.mark.parametrize("name", BATCH_2)
    def test_batch_2_symbol_resolves_under_reporting(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        # Tightened per hostile-review F2: exact-match on `siege_utilities.reporting`
        # (for symbols defined in reporting/__init__.py) OR strict `.reporting.`
        # prefix (submodules). Rejects sibling packages like `reporting_v2`.
        is_reporting_root = module == "siege_utilities.reporting"
        is_reporting_submodule = module.startswith("siege_utilities.reporting.")
        assert is_reporting_root or is_reporting_submodule, (
            f"{name!r} resolves to {module!r}, expected exactly "
            "'siege_utilities.reporting' or a strict '.reporting.*' submodule"
        )


class TestBatch3Promotions:
    """Verify #1176 batch 3 (databricks, 18 canonicals) shipped correctly.

    Batch 3 spans multiple `.databricks` submodules (runtime, secrets,
    urls, sql, spark_interop, etc.) but all resolve under
    `siege_utilities.databricks.*`. Uses the same tightened prefix check
    as batch 2 (per hostile-review-1176-batch2.md F2).
    """

    BATCH_3 = [
        "build_databricks_run_url", "build_foreign_table_sql",
        "build_jdbc_url", "build_lakebase_psql_command",
        "build_pgpass_entry", "build_schema_and_table_sync_sql",
        "ensure_secret_scope", "geopandas_to_spark",
        "get_active_spark_session", "get_dbutils",
        "get_runtime_secret", "get_workspace_client",
        "pandas_to_spark", "parse_conninfo", "put_secret",
        "runtime_secret_exists", "spark_to_geopandas", "spark_to_pandas",
    ]

    @pytest.mark.parametrize("name", BATCH_3)
    def test_batch_3_symbol_in_all(self, name):
        assert name in siege_utilities.__all__, (
            f"{name!r} promoted per #1176 batch 3 but missing from __all__"
        )

    @pytest.mark.parametrize("name", BATCH_3)
    def test_batch_3_symbol_resolves_under_databricks(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        is_databricks_root = module == "siege_utilities.databricks"
        is_databricks_submodule = module.startswith("siege_utilities.databricks.")
        assert is_databricks_root or is_databricks_submodule, (
            f"{name!r} resolves to {module!r}, expected exactly "
            "'siege_utilities.databricks' or a strict '.databricks.*' submodule"
        )


class TestBatch4Promotions:
    """Verify #1176 batch 4 (config profile canonicals) shipped correctly.

    Batch 4 covers the stdlib-backed client and connection profile helpers.
    It intentionally excludes pydantic-backed enhanced config aliases and
    connection verification helpers that the audit did not classify as
    canonical in this batch.
    """

    CLIENT_SYMBOLS = [
        "associate_client_with_project", "create_client_profile",
        "get_client_project_associations", "list_client_profiles",
        "load_client_profile", "save_client_profile",
        "search_client_profiles", "update_client_profile",
        "validate_client_profile",
    ]

    CONNECTION_SYMBOLS = [
        "cleanup_old_connections", "create_connection_profile",
        "find_connection_by_name", "get_connection_status",
        "list_connection_profiles", "load_connection_profile",
        "save_connection_profile", "update_connection_profile",
    ]

    BATCH_4 = CLIENT_SYMBOLS + CONNECTION_SYMBOLS

    @pytest.mark.parametrize("name", BATCH_4)
    def test_batch_4_symbol_in_all(self, name):
        assert name in siege_utilities.__all__, (
            f"{name!r} promoted per #1176 batch 4 but missing from __all__"
        )

    @pytest.mark.parametrize("name", CLIENT_SYMBOLS)
    def test_batch_4_client_symbol_resolves_to_config_clients(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        assert module == "siege_utilities.config.clients", (
            f"{name!r} resolves to {module!r}, expected "
            "'siege_utilities.config.clients' — cross-module collision"
        )

    @pytest.mark.parametrize("name", CONNECTION_SYMBOLS)
    def test_batch_4_connection_symbol_resolves_to_config_connections(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        assert module == "siege_utilities.config.connections", (
            f"{name!r} resolves to {module!r}, expected "
            "'siege_utilities.config.connections' — cross-module collision"
        )


class TestBatch5Promotions:
    """Verify #1176 batch 5 (file utility canonicals) shipped correctly.

    Batch 5 covers small, stdlib-backed file helpers across hashing,
    operations, remote metadata/download helpers, and path creation.
    """

    HASHING_SYMBOLS = [
        "calculate_file_hash", "generate_sha256_hash_for_file",
        "get_file_hash", "get_quick_file_signature", "verify_file_integrity",
    ]

    OPERATIONS_SYMBOLS = [
        "copy_file", "file_exists", "move_file",
    ]

    REMOTE_SYMBOLS = [
        "download_file", "download_file_with_retry",
        "get_file_info", "is_downloadable",
    ]

    PATH_SYMBOLS = ["ensure_path_exists"]

    BATCH_5 = HASHING_SYMBOLS + OPERATIONS_SYMBOLS + REMOTE_SYMBOLS + PATH_SYMBOLS

    @pytest.mark.parametrize("name", BATCH_5)
    def test_batch_5_symbol_in_all(self, name):
        assert name in siege_utilities.__all__, (
            f"{name!r} promoted per #1176 batch 5 but missing from __all__"
        )

    @pytest.mark.parametrize("name", HASHING_SYMBOLS)
    def test_batch_5_hashing_symbol_resolves_to_files_hashing(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        assert module == "siege_utilities.files.hashing", (
            f"{name!r} resolves to {module!r}, expected "
            "'siege_utilities.files.hashing' — cross-module collision"
        )

    @pytest.mark.parametrize("name", OPERATIONS_SYMBOLS)
    def test_batch_5_operation_symbol_resolves_to_files_operations(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        assert module == "siege_utilities.files.operations", (
            f"{name!r} resolves to {module!r}, expected "
            "'siege_utilities.files.operations' — cross-module collision"
        )

    @pytest.mark.parametrize("name", REMOTE_SYMBOLS)
    def test_batch_5_remote_symbol_resolves_to_files_remote(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        assert module == "siege_utilities.files.remote", (
            f"{name!r} resolves to {module!r}, expected "
            "'siege_utilities.files.remote' — cross-module collision"
        )

    @pytest.mark.parametrize("name", PATH_SYMBOLS)
    def test_batch_5_path_symbol_resolves_to_files_paths(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        assert module == "siege_utilities.files.paths", (
            f"{name!r} resolves to {module!r}, expected "
            "'siege_utilities.files.paths' — cross-module collision"
        )

    def test_run_command_lazy_but_not_canonical_pending_collision_decision(self):
        """#1215 tracks files.operations vs testing.runner run_command ambiguity."""
        from siege_utilities import _LAZY_IMPORTS

        assert "run_command" not in siege_utilities.__all__
        assert _LAZY_IMPORTS["run_command"][0] == ".files.operations"


class TestBatch6Promotions:
    """Verify #1176 batch 6 / #1213 sample-data canonicals.

    Batch 6 retargets root lazy loading away from the deprecated
    `siege_utilities.data.sample_data` shim and promotes only the safe
    sample-data constants and synthetic/loading helpers.
    """

    FUNCTION_SYMBOLS = [
        "generate_synthetic_businesses", "generate_synthetic_housing",
        "generate_synthetic_population", "list_available_datasets",
        "load_sample_data",
    ]

    CONSTANT_SYMBOLS = ["CENSUS_SAMPLES", "SAMPLE_DATASETS", "SYNTHETIC_SAMPLES"]

    BATCH_6 = CONSTANT_SYMBOLS + FUNCTION_SYMBOLS

    @pytest.mark.parametrize("name", BATCH_6)
    def test_batch_6_symbol_in_all(self, name):
        assert name in siege_utilities.__all__, (
            f"{name!r} promoted per #1176 batch 6 / #1213 but missing from __all__"
        )

    @pytest.mark.parametrize("name", BATCH_6)
    def test_batch_6_lazy_metadata_targets_reference_sample_data(self, name):
        from siege_utilities import _LAZY_IMPORTS

        module, _source_name, deps = _LAZY_IMPORTS[name]
        assert module == ".reference.sample_data"
        assert deps == ["pandas"]

    @pytest.mark.parametrize("name", FUNCTION_SYMBOLS)
    def test_batch_6_function_resolves_to_reference_sample_data(self, name):
        obj = getattr(siege_utilities, name)
        module = getattr(obj, "__module__", "")
        assert module == "siege_utilities.reference.sample_data", (
            f"{name!r} resolves to {module!r}, expected "
            "'siege_utilities.reference.sample_data' — deprecated shim collision"
        )

    @pytest.mark.parametrize("name", BATCH_6)
    def test_batch_6_access_does_not_import_deprecated_data_sample_shim(self, name):
        sys.modules.pop("siege_utilities.data.sample_data", None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            getattr(siege_utilities, name)

        shim_warnings = [
            warning for warning in caught
            if isinstance(warning.message, DeprecationWarning)
            and "siege_utilities.data.sample_data has moved" in str(warning.message)
        ]
        assert not shim_warnings
        assert "siege_utilities.data.sample_data" not in sys.modules


class TestLazyDependencyMetadata:
    """Verify lazy dependency metadata tracks migrated implementations."""

    @pytest.mark.parametrize(
        "name",
        ["build_isochrone_request", "get_isochrone", "isochrone_to_geodataframe"],
    )
    def test_isochrones_lazy_metadata_requires_httpx(self, name):
        """#1190 migrated geo.isochrones from requests to httpx.

        If the lazy metadata still says requests, a missing-local-httpx
        environment leaks ModuleNotFoundError instead of the package's
        dependency wrapper.
        """
        from siege_utilities import _LAZY_IMPORTS

        module, _source_name, deps = _LAZY_IMPORTS[name]
        assert module == ".geo.isochrones"
        assert deps == ["httpx"]


class TestLazyRegistrationGuard:
    """Verify _register_lazy raises on duplicate registration (hostile
    review F1 mechanical guard)."""

    def test_duplicate_registration_raises(self):
        # Import the private guard directly; register a fresh name once,
        # then attempt a rebind to a different module.
        from siege_utilities import _LAZY_IMPORTS, _register_lazy

        sentinel = "__test_duplicate_registration_sentinel__"
        assert sentinel not in _LAZY_IMPORTS, "sentinel leaked from prior run"
        try:
            _register_lazy([sentinel], ".geo.spatial_data")
            with pytest.raises(RuntimeError, match="duplicate registration"):
                _register_lazy([sentinel], ".config.enhanced_config")
        finally:
            _LAZY_IMPORTS.pop(sentinel, None)

    def test_idempotent_registration_allowed(self):
        """Registering the same name for the same module is a no-op, not
        an error. Some subpackages may re-register from multiple call sites."""
        from siege_utilities import _LAZY_IMPORTS, _register_lazy

        sentinel = "__test_idempotent_registration_sentinel__"
        try:
            _register_lazy([sentinel], ".geo.spatial_data")
            # Second call to same module should not raise
            _register_lazy([sentinel], ".geo.spatial_data")
            assert _LAZY_IMPORTS[sentinel][0] == ".geo.spatial_data"
        finally:
            _LAZY_IMPORTS.pop(sentinel, None)
