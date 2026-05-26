# Self-Review: SU#561 — remove stale deprecation shims

## Assumptions

Working as: software engineer, housekeeping focus
Goal source: https://github.com/siege-analytics/siege_utilities/issues/561
Goal source verification: ticket exists with 4 specific stale artefacts

- `data/dataframe_engine.py` shim announced removal at v3.17.0; current is v3.18.1-dev — past deadline
- `hygiene/pypi_release.py` deprecated since v2.0.0 with removal in v3.0.0; replacement `scripts/release_manager.py` exists and is executable
- `LIBRARY_VERSION` was never consumed at runtime (only re-exported); hardcoded "2.0.0" was stale since at least v3.x
- `data/__init__.py` `__version__ = "1.0.0"` served no purpose — the canonical version is in `pyproject.toml` and `siege_utilities.__version__`

## Peer review

Shelf: writing-code:1, writing-code:3

### Shelf checks

1. **data/dataframe_engine.py**: deleted — deadline passed. Canonical import path is `siege_utilities.engines.dataframe_engine`; the `data/__init__.py` re-exports still work via direct imports from `engines`
2. **data/__init__.py**: removed `__version__` and `__description__` metadata lines
3. **config/constants.py**: `LIBRARY_VERSION` now uses `importlib.metadata.version()` with `PackageNotFoundError` fallback to `"0.0.0"`
4. **hygiene/pypi_release.py**: deleted (467 lines of deprecated code)
5. **hygiene/__init__.py**: stripped deprecated re-exports; only `generate_docstrings` remains
6. **No new imports introduced** beyond `importlib.metadata` (stdlib)

## Lead review

- **[Backwards compatibility]** `data.dataframe_engine` was past its announced deadline; the `data.__init__` re-exports from `engines.dataframe_engine` are still present for callers using `from siege_utilities.data import Engine`
- **[hygiene removal]** Every function in pypi_release.py already emitted a DeprecationWarning pointing at `scripts/release_manager.py`; no runtime callers found outside `hygiene/__init__.py`
- **[LIBRARY_VERSION]** Consumers reading `config.LIBRARY_VERSION` now get the real installed version instead of a stale "2.0.0"
