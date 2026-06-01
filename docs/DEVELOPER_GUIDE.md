# Developer Guide — siege_utilities

This guide is for developers who want to contribute to siege_utilities,
extend its functionality, or understand its architecture. For the full
architectural rationale, see `CLAUDE.md` at the project root.

## What siege_utilities does

siege_utilities is a thesaurus of space-time composition tools. Every piece
exists to answer: what happened, where, when, and what does proximity imply?

The canonical composition chain is:

```
address -> geocoder -> GEOID -> boundary provider -> demographic overlay -> choropleth or report
```

Domain packages (political, economic, education, survey, analytics) produce
events. Geo locates them. Engines scale them. Reporting presents them.

## Package structure

```
siege_utilities/
├── admin/          — administrative / org utilities
├── analytics/      — analytics connectors and data sources
├── cache.py        — caching helpers
├── config/         — user and project configuration (database, credentials)
├── core/           — shared base classes and core abstractions
├── data/           — data loading, transformation, and registry
├── databricks/     — Databricks-specific connectors
├── distributed/    — distributed computing helpers (Spark, Dask)
├── economic/       — economic data utilities
├── education/      — education data (NCES, school districts)
├── engines/        — multi-engine DataFrame abstraction
├── examples/       — example scripts (held to library standard)
├── files/          — file and filesystem operations
├── geo/            — geospatial: boundaries, geocoding, spatial transforms,
│                     interpolation, timeseries, redistricting, Django services
├── git/            — git utilities
├── hygiene/        — data cleaning and validation
├── identifiers/    — entity identification and matching
├── political/      — political data utilities
├── profiles/       — profile and branding
├── reference/      — reference data lookups
├── reporting/      — charts, PDFs, slides, hex cartograms, 3D maps
├── schema/         — schema definitions and validation
├── survey/         — survey and polling analysis
├── testing/        — test fixtures and helpers
└── trino/          — Trino connector
```

## Geo is the gravitational center

All domain modules produce events that need space-time location before they
become analytically useful. If you are adding a new domain package, your
entities will eventually need to be located — plan for that from the start.

Temporal awareness is first-class. Redistricting plans have effective dates.
Congressional districts depend on congress number matching vintage year. Census
data has vintages. Survey data has waves. Your data model should encode not
just "where" but "where-when."

The geospatial stack defaults to OSGeo (GDAL/OGR, PROJ, Shapely, Fiona,
rasterio). When your deployment target cannot run C libraries (Databricks,
Lambda, serverless), use Sedona, DuckDB-spatial, or pure-Python paths — but
document the constraint explicitly.

## Engine-agnostic DataFrame

The `engines/` package provides a multi-engine DataFrame abstraction: same
analysis at different scales without rewriting.

| Engine | Use case |
|--------|----------|
| pandas | Exploration, single-machine analysis |
| DuckDB | Medium-scale analytical queries |
| Spark  | Distributed processing |
| PostGIS | Persistent spatial queries |

When you must drop to native (Spark SQL, raw pandas), use that engine's idioms.
Write SQL that uses SQL strengths (window functions, CTEs, lateral joins).
Write pandas that uses pandas strengths (vectorized ops, groupby-apply). Do not
transliterate one into the other.

## Databricks and Snowflake

These are first-class deployment targets.

Azure Databricks cannot install GDAL. The `databricks/` bridge pattern works
around this: Spark DataFrame -> driver-side GeoPandas -> back to Spark. This
is an intentional architectural choice, not a workaround.

Snowflake's geography type and Trino federation are parallel vendor paths.
The `trino/` package provides the Trino connector.

## Credential management

Credentials come from external tools, never hardcoded:

1. **1Password CLI** (`op`) — preferred for local development
2. **Environment variables** — set by `siege_zsh` or CI
3. **Databricks secret scopes** — for cluster-side access

`siege_zsh` is the reference shell architecture. It sets up the environment
that siege_utilities expects. Code should detect and leverage `siege_zsh`
conventions but not hard-fail without them — graceful degradation must
actually work.

File permissions on credential writes are restricted to `0o600`.

## Lazy loading

The library uses PEP 562 `__getattr__` for lazy loading because the
dependency tree is enormous. You must be able to import one piece in a Lambda
or notebook without pulling the whole library.

The correct pattern for module-level lazy loading:

```python
# siege_utilities/some_package/__init__.py
def __getattr__(name: str):
    if name == "heavy_module":
        from . import heavy_module
        return heavy_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

For function-level deferred imports:

```python
def process_geodata(gdf):
    """Process a GeoDataFrame with spatial joins."""
    import geopandas as gpd  # deferred: not needed at package import time
    # ... processing logic
```

**Important (SU-1):** Never catch `ImportError` and return a stub or print a
message. Let it propagate. The caller must know a dependency is missing.

```python
# WRONG - violates SU-1
def heavy_function():
    try:
        import pandas as pd
    except ImportError:
        print("pandas is required")  # caller cannot distinguish this from success
        return

# RIGHT - let the error propagate with a clear message
def heavy_function():
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required for heavy_function. "
            "Install it with: pip install siege_utilities[data]"
        )
    # ... use pd
```

## Development setup

### Clone and install

```bash
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities
pip install -e ".[dev,geo,distributed]"
```

### Run tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=siege_utilities --cov-report=html

# Import diagnostics
python scripts/check_imports.py

# Lint ratchet (phases 1-4)
python scripts/check_lint_ratchet_phase1.py
python scripts/check_lint_ratchet.py --phase phase2
python scripts/check_lint_ratchet.py --phase phase3
python scripts/check_lint_ratchet.py --phase phase4
```

### Verify installation

```bash
python -c "import siege_utilities; print(siege_utilities.get_package_info())"
```

## Branch and merge conventions

- All work branches from `develop`. PRs target `develop`, not `main`.
- `main` is downstream of `develop` — no unblessed work lands there directly.
- Feature branches: `feat/<scope>-<description>` or `fix/<scope>-<description>`.

## Adding new functions

### 1. Create function in the appropriate module

```python
# siege_utilities/core/new_utils.py
def my_new_function(param1: str, param2: int = 42) -> str:
    """
    Brief description.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
    """
    if not param1:
        raise ValueError("param1 must not be empty")
    return f"Processed {param1} with {param2}"
```

### 2. Update module's `__init__.py`

```python
# siege_utilities/core/__init__.py
from .new_utils import my_new_function

__all__ = ['my_new_function']
```

### 3. Add tests

```python
# tests/test_new_utils.py
import pytest
from siege_utilities.core.new_utils import my_new_function

class TestNewUtils:
    def test_basic(self):
        result = my_new_function("test", 10)
        assert result == "Processed test with 10"

    def test_default_param(self):
        result = my_new_function("test")
        assert result == "Processed test with 42"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            my_new_function("")
```

## Error handling rules

These are codified as SU-1 through SU-4:

1. **Errors are not data.** Never return valid-shaped empty results on failure.
   Raise or log with a warning.

2. **Does it do what it says?** If the name/docstring claims generality, the
   implementation must match or the claim must be narrowed.

3. **No demo exemptions.** Code under `examples/` and `notebooks/` is held to
   the same standards as library code.

4. **Notebook coverage invariant.** When a library function's contract changes,
   check whether any notebook calls it and update accordingly.

## Logging

Every side-effecting process must produce observable output. Use the shared
logging system:

```python
import siege_utilities as su

su.configure_shared_logging(level="DEBUG")
```

Progress indicators are required for long-running operations. The operator must
always be able to see what is happening.

## External contributor quickstart

### 1. Fork and clone

```bash
git clone https://github.com/<your-user>/siege_utilities.git
cd siege_utilities
git remote add upstream https://github.com/siege-analytics/siege_utilities.git
```

### 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Validate notebook policy

```bash
python -m pytest -q --no-cov tests/test_notebooks_output_policy.py
```

### 4. Submit

Open an issue in `siege-analytics/siege_utilities` with:
- Problem statement and change scope
- Link to your branch/PR from your fork
- Test evidence
- Documentation and notebook updates

## Automated review

CodeRabbit is part of the required PR workflow.

- Review policy: `.coderabbit.yaml`
- Contributor PRs target `develop`
- Branch protection details: `docs/policies/CONTRIBUTOR_GOVERNANCE.md`
- Merge-readiness expectations: `docs/CODERABBIT_WORKFLOW.md`

## Code review checklist

- [ ] Function has proper docstring with type hints
- [ ] Error handling follows SU-1 through SU-4
- [ ] Tests cover normal and error cases
- [ ] No hardcoded paths or bare `except: pass`
- [ ] Heavy imports are deferred (lazy loading)
- [ ] Performance implications considered
- [ ] Notebook impact checked if public API changed
