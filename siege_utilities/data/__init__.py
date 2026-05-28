"""
Data module for siege_utilities.

After ELE-2437, ``data/`` narrowed to hold statistics primitives
(``data.statistics``) + the RDH provider shim. Other concerns moved:

- Engine abstractions → :mod:`siege_utilities.engines`
- Sample datasets + crosswalks → :mod:`siege_utilities.reference`

Top-level imports at this package are preserved (re-exports from the
new homes) for one deprecation window so existing callers still work.

All re-exports use PEP 562 lazy loading so that importing
``siege_utilities.data`` does not pull in heavy transitive dependencies
(geopandas via RDH, etc.) unless the caller actually uses them.
"""

# ---------------------------------------------------------------------------
# PEP 562 lazy imports
# ---------------------------------------------------------------------------

_LAZY_IMPORTS = {
    # Reference data (moved to siege_utilities.reference but re-exported here)
    "load_sample_data":              ("..reference.sample_data", "load_sample_data"),
    "list_available_datasets":       ("..reference.sample_data", "list_available_datasets"),
    "get_dataset_info":              ("..reference.sample_data", "get_dataset_info"),
    "get_census_boundaries":         ("..reference.sample_data", "get_census_boundaries"),
    "get_census_data":               ("..reference.sample_data", "get_census_data"),
    "join_boundaries_and_data":      ("..reference.sample_data", "join_boundaries_and_data"),
    "create_sample_dataset":         ("..reference.sample_data", "create_sample_dataset"),
    "generate_synthetic_population": ("..reference.sample_data", "generate_synthetic_population"),
    "generate_synthetic_businesses": ("..reference.sample_data", "generate_synthetic_businesses"),
    "generate_synthetic_housing":    ("..reference.sample_data", "generate_synthetic_housing"),
    "HOUSING_LOCALE_PRESETS":        ("..reference.sample_data", "HOUSING_LOCALE_PRESETS"),
    "SAMPLE_DATASETS":               ("..reference.sample_data", "SAMPLE_DATASETS"),
    "CENSUS_SAMPLES":                ("..reference.sample_data", "CENSUS_SAMPLES"),
    "SYNTHETIC_SAMPLES":             ("..reference.sample_data", "SYNTHETIC_SAMPLES"),

    # RDH provider (moved to geo/providers/ under ELE-2438)
    "RDHClient":                     ("..geo.providers.redistricting_data_hub", "RDHClient"),
    "RDHDataset":                    ("..geo.providers.redistricting_data_hub", "RDHDataset"),
    "RDHDataFormat":                 ("..geo.providers.redistricting_data_hub", "RDHDataFormat"),
    "RDHDatasetType":                ("..geo.providers.redistricting_data_hub", "RDHDatasetType"),
    "RDH_BASE_URL":                  ("..geo.providers.redistricting_data_hub", "RDH_BASE_URL"),
    "US_STATES":                     ("..geo.providers.redistricting_data_hub", "US_STATES"),
    "polsby_popper":                 ("..geo.providers.redistricting_data_hub", "polsby_popper"),
    "reock":                         ("..geo.providers.redistricting_data_hub", "reock"),
    "convex_hull_ratio":             ("..geo.providers.redistricting_data_hub", "convex_hull_ratio"),
    "schwartzberg":                  ("..geo.providers.redistricting_data_hub", "schwartzberg"),
    "compute_compactness":           ("..geo.providers.redistricting_data_hub", "compute_compactness"),
    "compare_plans":                 ("..geo.providers.redistricting_data_hub", "compare_plans"),
    "demographic_profile":           ("..geo.providers.redistricting_data_hub", "demographic_profile"),
    "fetch_enacted_plan":            ("..geo.providers.redistricting_data_hub", "fetch_enacted_plan"),
    "fetch_precinct_results":        ("..geo.providers.redistricting_data_hub", "fetch_precinct_results"),
    "fetch_cvap":                    ("..geo.providers.redistricting_data_hub", "fetch_cvap"),
    "fetch_pl94171":                 ("..geo.providers.redistricting_data_hub", "fetch_pl94171"),
    "fetch_demographic_summary":     ("..geo.providers.redistricting_data_hub", "fetch_demographic_summary"),
    "CompactnessScores":             ("..geo.providers.redistricting_data_hub", "CompactnessScores"),
    "RDH_SITE_URL":                  ("..geo.providers.redistricting_data_hub", "RDH_SITE_URL"),

    # Engine abstractions (moved to siege_utilities.engines but re-exported here)
    "Engine":                        ("..engines.dataframe_engine", "Engine"),
    "PANDAS":                        ("..engines.dataframe_engine", "PANDAS"),
    "DUCKDB":                        ("..engines.dataframe_engine", "DUCKDB"),
    "SPARK":                         ("..engines.dataframe_engine", "SPARK"),
    "POSTGIS":                       ("..engines.dataframe_engine", "POSTGIS"),
    "DataFrameEngine":               ("..engines.dataframe_engine", "DataFrameEngine"),
    "PandasEngine":                  ("..engines.dataframe_engine", "PandasEngine"),
    "DuckDBEngine":                  ("..engines.dataframe_engine", "DuckDBEngine"),
    "SparkEngine":                   ("..engines.dataframe_engine", "SparkEngine"),
    "PostGISEngine":                 ("..engines.dataframe_engine", "PostGISEngine"),
    "get_engine":                    ("..engines.dataframe_engine", "get_engine"),
}

__all__ = [
    # Core functions
    "load_sample_data",
    "list_available_datasets",
    "get_dataset_info",

    # Census samples
    "get_census_boundaries",
    "get_census_data",
    "join_boundaries_and_data",
    "create_sample_dataset",

    # Synthetic generation
    "generate_synthetic_population",
    "generate_synthetic_businesses",
    "generate_synthetic_housing",
    "HOUSING_LOCALE_PRESETS",

    # Dataset info
    "SAMPLE_DATASETS",
    "CENSUS_SAMPLES",
    "SYNTHETIC_SAMPLES",

    # Redistricting Data Hub
    "RDHClient",
    "RDHDataset",
    "RDHDataFormat",
    "RDHDatasetType",
    "RDH_BASE_URL",
    "US_STATES",
    "polsby_popper",
    "reock",
    "convex_hull_ratio",
    "schwartzberg",
    "compute_compactness",
    "compare_plans",
    "demographic_profile",
    "fetch_enacted_plan",
    "fetch_precinct_results",
    "fetch_cvap",
    "fetch_pl94171",
    "fetch_demographic_summary",
    "CompactnessScores",
    "RDH_SITE_URL",

    # Engine-agnostic DataFrame operations
    "Engine",
    "PANDAS",
    "DUCKDB",
    "SPARK",
    "POSTGIS",
    "DataFrameEngine",
    "PandasEngine",
    "DuckDBEngine",
    "SparkEngine",
    "PostGISEngine",
    "get_engine",
]


def __getattr__(name):  # noqa: E303
    """PEP 562 lazy loader — resolve re-exports on first access."""
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        from importlib import import_module
        mod = import_module(module_path, __name__)
        val = getattr(mod, attr)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Ensure dir() reports all lazy exports."""
    return __all__
