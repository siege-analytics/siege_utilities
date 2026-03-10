# Python Version Support Policy

## Supported Versions

| Version | Status | CI | Notes |
|---------|--------|-----|-------|
| 3.11 | **Fully supported** (floor) | Required pass | Minimum required version |
| 3.12 | **Fully supported** | Required pass | |
| 3.13 | **Supported** | Allow-failure | `continue-on-error` in CI while ecosystem stabilizes |
| 3.14 | **Experimental** | Not in CI | Awaiting C-extension wheel availability |

## Version Floor

The library requires `python_requires >= "3.11"`. This is set in both `pyproject.toml` and `setup.py`.

Python 3.11 is the floor because:
- It is the oldest version still receiving security updates
- It introduced `tomllib`, `ExceptionGroup`, and other stdlib improvements we rely on
- Our deployment targets (Databricks, enterprise Django) run 3.11+

## C-Extension Dependencies

Geospatial extras (`[geo]`, `[geodjango]`) depend on packages with compiled C/Rust extensions. Wheel availability on newer Python versions lags behind CPython releases.

### Key C-extension packages

| Package | Binding | 3.13 Wheels | 3.14 Wheels | Notes |
|---------|---------|-------------|-------------|-------|
| numpy | C | Yes | Partial | Core dep for pandas/scipy |
| pandas | C/Cython | Yes | Partial | |
| shapely | C (GEOS) | Yes (>=2.0) | No | Requires `>=2.0.0` for 3.13 |
| fiona | C (GDAL) | Limited | No | Needs system GDAL |
| pyproj | C (PROJ) | Yes | No | |
| geopandas | Pure Python | Yes | Yes | But depends on shapely/fiona |
| scipy | C/Fortran | Yes | No | |
| scikit-learn | C/Cython | Yes | No | |
| pydantic-core | Rust (pyo3) | Yes | Yes | pyo3 updated for 3.14 |
| duckdb | C++ | Yes | No | |
| lxml | C | Yes | No | |
| pillow | C | Yes | Partial | |
| psycopg2-binary | C | Yes | No | |

### Pure Python packages (no version concerns)

PySpark, Apache Sedona, and most of our analytics connectors are pure Python — they work on any Python version that satisfies their own `python_requires`.

## CI Strategy

### Current matrix

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
continue-on-error: ${{ matrix.python-version == '3.13' }}
```

### Promotion criteria

A Python version moves from allow-failure to required-pass when:

1. All core dependencies have published wheels for that version
2. All geospatial C-extension dependencies have wheels (or build cleanly from source)
3. The full test suite passes without modifications
4. At least one release cycle has passed without regressions

### Adding Python 3.14

Python 3.14 will be added to CI when:
- fiona publishes 3.14 wheels (GDAL bindings, historically lags 3-6 months)
- pandas publishes cp314 wheels (claimed in classifiers but not yet shipped)
- snowflake-connector-python publishes 3.14 wheels (if `[analytics]` extra needed)

Until then, 3.14 is listed in classifiers as experimental.

## Dropping Old Versions

We follow the [NumPy Enhancement Proposal 29 (NEP 29)](https://numpy.org/neps/nep-0029-deprecation_policy.html) guideline: support Python versions for 42 months after their initial release.

Before dropping a version:
1. Announce deprecation in the changelog one minor release before removal
2. Update `python_requires` in both `pyproject.toml` and `setup.py`
3. Remove the version from CI matrix
4. Update classifiers and README badge
