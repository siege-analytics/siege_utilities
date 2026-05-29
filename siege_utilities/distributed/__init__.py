"""
Distributed functions package — lazy-loaded.

Contains Spark utilities, HDFS configuration, and HDFS operations.
All submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import sys

# Explicit map of public names to their source modules.
_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- spark_utils: custom siege_utilities functions ---
_register([
    'sanitise_dataframe_column_names', 'tabulate_null_vs_not_null',
    'get_row_count', 'repartition_and_cache', 'register_temp_table',
    'move_column_to_front_of_dataframe', 'write_df_to_parquet', 'read_parquet_to_df',
    'flatten_json_column_and_join_back_to_df',
    'validate_geocode_data', 'mark_valid_geocode_data', 'clean_and_reorder_bbox',
    'ensure_literal', 'reproject_geom_columns',
    'prepare_dataframe_for_export', 'prepare_summary_dataframe',
    'export_pyspark_df_to_excel', 'pivot_summary_table_for_bools',
    'pivot_summary_with_metrics', 'export_prepared_df_as_csv_to_path_using_delimiter',
    'print_debug_table', 'compute_walkability', 'validate_geometry',
    'backup_full_dataframe', 'atomic_write_with_staging', 'create_unique_staging_directory',
    'walkability_config', 'py_round', 'PYSPARK_AVAILABLE',
], '.spark_utils')

# --- hdfs_config ---
_register([
    'HDFSConfig', 'create_hdfs_config', 'create_local_config',
    'create_cluster_config', 'create_geocoding_config',
    'create_yarn_config', 'create_census_analysis_config',
], '.hdfs_config')

# --- hdfs_operations ---
_register([
    'AbstractHDFSOperations', 'setup_distributed_environment', 'create_hdfs_operations',
], '.hdfs_operations')

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))
