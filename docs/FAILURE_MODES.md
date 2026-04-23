# siege_utilities — Failure Mode Catalog

**Goal:** classify every public-function failure path. Silent swallows become visible; category-(b) sites get a target fix.

**Scope:** ELE-2418 (audit sub-issue 3/6). Rubric: `coding/python-exceptions/SKILL.md` + `_data-trust-rules.md`. Snapshot: 2026-04-22.

## Categories

| Code | Meaning |
|---|---|
| (a) | Handled correctly — specific `except`, typed raise with `from e`, docstring mentions raises |
| (b) | Silent swallow — broad catch + sentinel return (`None`/`False`/`{}`/`[]`) with no way to distinguish success from hidden error |
| (c) | Not handled — raises opaque `KeyError` / `ValueError` / `AttributeError` without domain context |

## Library-wide density

| Module | `except X:` | Sentinel returns | (b) density |
|---|---:|---:|---|
| `reporting/` | 139 | 88 | Very high |
| `geo/` | 131 | 139 | Very high |
| `config/` | 87 | 134 | High |
| `files/` | 46 | 56 | High |
| `analytics/` | 46 | 47 | High |
| `distributed/` | 28 | 21 | Medium |
| `git/` | 22 | 3 | Medium (raises dominate) |
| `hygiene/` | 16 | 9 | Medium |
| `testing/` | 13 | 12 | Medium |
| `data/` | 11 | 22 | Medium |
| `admin/` | 6 | 2 | Low |
| `databricks/` | 3 | 1 | Low |
| `survey/` | 0 | 10 | Low (excepts fixed #391) |
| `core/` | 1 | 2 | Very low |

Starting order for per-module sweep: `reporting/` → `geo/` → `config/` → `files/` → `analytics/`.

## Cross-cutting patterns

Each pattern is tracked by ELE-2420 sub-issues.

| ID | Pattern | Fix |
|---|---|---|
| **CC1** | `except Exception: return <sentinel>` — silent swallow | Narrow catch, log, raise domain exception with `from e` |
| **CC2** | `int(df[col].sum())` — precision loss at return boundaries | Return float; cast only at display |
| **CC3** | `logger.warning(...); return None` — half-log/half-silence | Raise on real failure; return None only when absence is legitimate and caller can distinguish |
| **CC4** | `try: import X / except: def stub(): pass` — silent stub when dep missing | OK for logging; anti-pattern for load-bearing functions |
| **CC5** | `validate_credentials() -> bool` — returns False on missing creds | Raise typed error or return explicit `CredentialStatus` enum |

### CC1 — confirmed silent-swallow sites

| File | Lines | Status |
|---|---|---|
| `geo/boundary_providers.py` | L118 | CensusTIGERProvider — **fixed** #385 |
| `geo/census_geocoder.py` | L249, L303 | — **fixed** #401 (ELE-2420) |
| `geo/spatial_data.py` | L1395, L1412, L1433, L1484, L1536 | — **fixed** #405 (ELE-2420) |
| `geo/geocoding.py` | L315 | False positive — legitimate not-found return |
| `reporting/chart_types.py` | create_chart + validate | — **fixed** #399 (ELE-2420) |
| `reporting/client_branding.py` | L217, L221, L238, L259 + 2 more | — **fixed** #400 (ELE-2420) |
| `reporting/__init__.py` | L138, L149, L161 | — **fixed** #397 (ELE-2420) |
| `reporting/powerpoint_generator.py` | 2 sites | Pending ELE-2420 |
| `reporting/report_generator.py` | 1 site | Pending ELE-2420 |
| `reporting/engines/base_engine.py` | 1 site | Pending ELE-2420 |
| `analytics/snowflake_connector.py` | 7 sites | Pending ELE-2420 |
| `analytics/datadotworld_connector.py` | 11 sites | Pending ELE-2420 |
| `files/operations.py` | 12 sites | Pending ELE-2420 (high blast radius) |
| `files/remote.py` | 4 sites | Pending ELE-2420 |
| `geo/spatial_transformations.py` | 17 sites | Pending ELE-2420 (DRY refactor opportunity) |
| `geo/census/api.py` | L353, L373 | False positive — legitimate cache-miss |

## Per-module deep dive

### `geo/boundary_providers.py`

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `CensusTIGERProvider.get_boundary` | Downstream fetch fails | (a) #385 | Raises `BoundaryFetchError` |
| `GADMProvider.get_boundary` | geopandas missing | (a) | Raises ImportError with hint |
| `GADMProvider.get_boundary` | Unknown level / country | (a) | Raises ValueError |
| `GADMProvider.is_available` | geopandas missing | (a) | Returns False, documented |
| `RDHProvider.get_boundary` | Shapefile load error | (a) #386 | Wraps in `BoundaryFetchError` |
| `RDHProvider.get_boundary` | Empty credentials | (b) — CC5 | Return `CredentialStatus` or raise `RDHAuthError` |
| `resolve_boundary_provider` | Unknown country code | (c) | Raise early with list of known codes |

### `geo/census_geocoder.py`

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `geocode_single` | HTTP/API failure | (a) #401 | Raises `CensusGeocodeError` |
| `geocode_batch` | HTTP timeout | (a) #401 | Raises `CensusGeocodeError` with batch size in message |
| `geocode_batch` | Parse error | (a) #401 | Raises `CensusGeocodeError` |

### `geo/spatial_data.py`

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `GovernmentDataSource._get_dataset_metadata` | HTTP/parse failure | (a) #405 | Raises `SpatialDataError` |
| `GovernmentDataSource._find_best_format` | Metadata parse failure | (a) #405 | Raises `SpatialDataError` |
| `GovernmentDataSource._download_and_process_dataset` | File processing failure | (a) #405 | Raises `SpatialDataError` |
| `OpenStreetMapDataSource.download_osm_data` | Overpass API failure | (a) #405 | Raises `SpatialDataError` |
| `CensusDataSource.fetch_geographic_boundaries` | Any stage failure | (a) | Returns `BoundaryFetchResult` with error context |

### `reporting/chart_types.py`

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `create_chart` | Unknown chart type | (a) #399 | Raises `UnknownChartTypeError` |
| `create_chart` | Missing required params | (a) #399 | Raises `ChartParameterError` |
| `create_chart` | No `create_function` registered | (a) #399 | Raises `ChartCreationError` |
| `create_chart` | `create_function` raised | (a) #399 | Raises `ChartCreationError` with cause chain |
| `validate_chart_parameters` | Unknown chart type | (a) #399 | Raises `UnknownChartTypeError` |
| `validate_chart_parameters` | `validate_function` raised | (a) #399 | Raises `ChartParameterError` |

### `reporting/client_branding.py`

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `get_client_branding` | I/O or YAML parse failure | (a) #400 | Raises `ClientBrandingError` |
| `update_client_branding` | Client not found | (a) #400 | Raises `ClientBrandingNotFoundError` |
| `update_client_branding` | Save failure | (a) #400 | Raises `ClientBrandingError` |
| `delete_client_branding` | I/O failure | (a) #400 | Raises `ClientBrandingError` |
| `export_branding_config` | Not found / I/O failure | (a) #400 | Raises typed errors |
| `import_branding_config` | YAML parse failure | (a) #400 | Raises `ClientBrandingError` |
| `get_branding_summary` | I/O failure | (a) #400 | Raises `ClientBrandingError` |

### `reporting/__init__.py` (top-level convenience API)

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `export_branding_config` | Any failure | (a) #397 | Raises `ReportingConfigError` |
| `import_branding_config` | Any failure | (a) #397 | Raises `ReportingConfigError` |
| `export_chart_type_config` | Any failure | (a) #397 | Raises `ReportingConfigError` |

### `reporting/engines/*_engine.py`

Deferred — needs shared-core rewrite to avoid duplicating fixes. ELE-2420 follow-up.

### `config/credential_manager.py`

79 `except X:` clauses; many likely (b). Deferred to dedicated rewrite under ELE-2420. Initial audit:
- `L380`, `L744`: hardcoded `"password"` / `"1password"` — confirm these are field-name strings, not secrets
- Broad exception counts suggest widespread silent-swallow needing narrow catches

### `files/operations.py`

12 silent-swallow sites, high blast radius (every file op in the library touches this). Needs careful per-function audit — some `False` returns are legitimate ("file doesn't exist"), others mask real I/O errors. Pending ELE-2420.

### `files/remote.py`, `files/paths.py`, `files/hashing.py`

- Download failures → should retry (does) but final failure should raise `DownloadError`, not return None (CC1)
- Hash mismatches → should raise `IntegrityError`, not silent return
- Path manipulation → most (a); audit Windows / UNC / symlink loop edge cases

### `analytics/*_connector.py`

All wrap external APIs. Common pattern: broad except + `return {}`. Each gets its own rewrite PR with:

```python
# Before:   try/except Exception: return {}
# After:    try/except (RequestException, ValueError): raise AnalyticsAPIError from e
```

## Edge cases validated post-recent PRs

| Edge case | Where | Status |
|---|---|---|
| Empty DataFrame → `pd.crosstab` | `polling_analyzer::create_cross_tabulation_matrix` | (a) #389 |
| Mixed dtype heatmap | same | (a) #389 |
| Cross-vintage FIPS join safety | `geo/` | Partial — `_is_vtd_pl_boundary` done #386; broader join safety TBD |
| Zero-baseline change detection | `polling_analyzer::create_change_detection_data` | (a) #389 |
| `geo_column ≠ row_var` in chain_to_argument | `survey/render.py` | (a) #391 |
| Unknown `alpha` in significance test | `survey/significance.py` | (a) #391 |
| Missing metric column in `_build_mean_scale` | `survey/crosstab.py` | (a) #391 |
| `geopandas` absent | `boundary_providers::GADMProvider` | (a) |
| `reportlab` absent at module load | `reporting/analytics/polling_analyzer.py` | (c) — deprecated entirely under ELE-2439/0006 |

## Method notes

```bash
# Find broad catches
rg "except Exception" siege_utilities/<module>/

# Find sentinel returns
rg -nE "return (None|False|\\{\\}|\\[\\]|'')\\s*$" siege_utilities/<module>/

# Find CC3 (half-log / half-silence)
rg "log_warning|log_error" siege_utilities/<module>/
```

See also: [INTENT.md](INTENT.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [adr/](adr/)
