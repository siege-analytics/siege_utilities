# siege_utilities — Failure Mode Catalog

Classification of every public function's failure handling. Per **ELE-2418** (audit sub-issue 3/6). Rubric: `coding/python-exceptions/SKILL.md` + `_data-trust-rules.md`.

## Categories

- **(a) Handled correctly** — specific `except` clauses, log-and-raise, or raise a domain exception with `from e`. Typed returns; raises documented in docstring.
- **(b) Handled silently** — catches (broad or narrow) then returns a sentinel (`None`, `{}`, `[]`, `False`, `""`, `0`) without logging OR without a way for the caller to distinguish "no data" from "error hidden."
- **(c) Not handled** — no try/except around known failure modes; code will raise an opaque library error (`KeyError`, `ValueError`, `AttributeError`) without domain context.

## Library-wide density (branches, not blocks)

Count of typed + broad `except` clauses and "trivial sentinel return" lines per module. Higher numbers are not automatically bad; they're where to look first for category (b) and (c) cases.

| Module | `except X:` count | Sentinel returns | Rough (b) density |
|---|---:|---:|---|
| `reporting/` | 139 | 88 | **Very high** — likely many (b) cases |
| `geo/` | 131 | 139 | **Very high** |
| `config/` | 87 | 134 | **High** |
| `files/` | 46 | 56 | High |
| `analytics/` | 46 | 47 | High |
| `distributed/` | 28 | 21 | Medium |
| `git/` | 22 | 3 | Medium (raises dominate) |
| `hygiene/` | 16 | 9 | Medium |
| `testing/` | 13 | 12 | Medium |
| `data/` | 11 | 22 | Medium |
| `admin/` | 6 | 2 | Low |
| `databricks/` | 3 | 1 | Low |
| `survey/` | 0 | 10 | Low — PR #391 already fixed the excepts; sentinels remain |
| `core/` | 1 | 2 | Very low |

**Starting order for the per-module deep dive**: `reporting/` → `geo/` → `config/` → `files/` → `analytics/`. Remaining modules get the same treatment under follow-up PRs.

## Cross-cutting patterns

These patterns appear in multiple modules and should be fixed wholesale rather than one file at a time. Each will surface as an issue under ELE-2420.

### CC1. `except Exception: return <sentinel>`

The "silent swallow" pattern. Caller gets back `None` / `{}` / `[]` / `False` without knowing whether it means "no data" or "the function crashed and I hid it." Fixes per `python-exceptions`: narrow the catch, log, raise a domain exception or return a typed `Result` object.

**Confirmed sites** (non-exhaustive, high-value first):
- `geo/boundary_providers.py:118` — CensusTIGERProvider swallows and returns None
- `geo/census_geocoder.py:280,393,397` — geocoding failures hidden
- `geo/geocoding.py:315` — module-level wrapper swallows
- `reporting/chart_types.py:332,339,352,355` — chart construction silently returns None
- `reporting/chart_types.py:416` — returns `{}` on error
- `reporting/client_branding.py:217,221,238,259` — branding lookup swallows
- `reporting/__init__.py:138,149,161` — top-level convenience returns False on anything

### CC2. `int(df[weight_var].sum())` / precision loss at return boundaries

Already fixed in `survey/crosstab._base_respondents` (float return) under #391. Likely analogous cases elsewhere — any `int(...)` wrapping a possibly-fractional sum is suspect.

**To audit:** `data/` DataFrame ops, `analytics/google_analytics.py` aggregations.

### CC3. Bare `logger.warning(...)` then `return None`

Half-log, half-silence. Logging at warn level + returning None is only correct when "no result" is a legitimate outcome AND the caller can distinguish it from success. Usually the log-level should be `error` and the function should raise.

**Confirmed sites** (sampled):
- `geo/boundary_providers.py:113` — `logger.warning(...); return None` — if the boundary fetch actually failed, caller should know via exception, not absent data
- `reporting/*` — widespread

### CC4. ImportError cascade — `try: import heavy_dep / except: def stub_fn...`

Legitimate pattern for optional dependencies BUT the stub function often does nothing (no raise, no warn) so callers using the module without the dep silently get no-ops.

**Sites (pattern from the code I already know):**
- `data/redistricting_data_hub.py:51-57` — logging functions stubbed to `pass` when `siege_utilities.core.logging` isn't importable. OK for logging specifically (no-op is fine), but the pattern shouldn't be copied for functions whose output is load-bearing.

### CC5. `validate_credentials() -> bool` without raising on failure

Pattern: `validate_credentials()` returns `False` + logs a warning. Callers then conditionally skip work. This is category (b) — the function call "succeeded" with zero matches when really the user forgot to set env vars.

**Site:** `data/redistricting_data_hub.py:187-192`. Fix: either raise `RDHAuthError` or return an explicit `CredentialStatus` enum with values `{OK, NOT_SET, INVALID}`.

## Per-module: `geo/`

Priority 1 (spatial is core to the library's domain).

### `geo/boundary_providers.py`

| Function | Failure mode | Category | Skill-rubric fix |
|---|---|---|---|
| `CensusTIGERProvider.get_boundary` | Downstream `fetch_geographic_boundaries` returns `result.success=False` | (b) — logs warning + returns None | Raise `BoundaryFetchError` |
| `GADMProvider.get_boundary` | `geopandas` missing | (a) — raises ImportError with install hint | ✓ keep |
| `GADMProvider.get_boundary` | Unknown level / missing country | (a) — raises ValueError | ✓ keep |
| `GADMProvider.is_available` | `geopandas` missing | (a) — returns False, doc'd | ✓ keep |
| `RDHProvider.get_boundary` | `load_shapefile` raises OSError/ValueError | (a) after #386 — wraps in `BoundaryFetchError` | ✓ fixed on #386 |
| `RDHProvider.get_boundary` | Credentials are empty string | (b) — logs warning, returns empty list | See CC5 |
| `resolve_boundary_provider` | Unknown country code | (c) — returns `GADMProvider(country_code=<unknown>)` which then 404s at fetch time | Raise early with list of known codes |

### `geo/census_geocoder.py`

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `geocode_address` (line ~280) | Address not found | (b) — returns `[]` | Return `Optional[GeocodeResult]` explicitly; distinguish "not found" from "lookup failed" |
| `batch_geocode` (line ~393) | HTTP timeout mid-batch | (b) — returns `None` | Retry + raise on final failure |
| `batch_geocode` (line ~397) | Parse error on response | (b) — returns `None` | Log full response text; raise |

### `geo/geocoding.py`

| Function | Failure mode | Category | Fix |
|---|---|---|---|
| `geocode_addresses` (line ~315) | Any error in underlying API | (b) — returns None | Catch specific (`requests.*`, `json.*`), raise `GeocodingError` |

### `geo/spatial_data.py` (touched by #386)

| Function | Failure mode | Category |
|---|---|---|
| `_is_vtd_pl_boundary(bt, year)` | Cross-vintage pair | (a) — returns False (fixed on #386) ✓ |
| `_construct_vtd_pl_url(2010, fips)` | Year 2010 state-level URL doesn't exist | (a) — raises BoundaryDiscoveryError (fixed on #386) ✓ |
| `CensusDataSource.fetch_geographic_boundaries` | Any stage of the pipeline | (a) — returns BoundaryFetchResult with success/error_stage/context | ✓ keep — good model |

## Per-module: `reporting/`

Priority 2 (highest raw density).

### `reporting/chart_types.py`

| Site | Pattern |
|---|---|
| L332, 339, 352, 355 | `return None` in chart constructors — callers lose the chart silently |
| L385, 392, 400 | `return False` on construction failure |
| L416 | `return {}` — a chart spec dict on error |

All category (b). Need per-function rewrite replacing sentinels with `ChartConstructionError`.

### `reporting/client_branding.py`

| Site | Pattern |
|---|---|
| L217, 221 | Branding lookup returns None on not-found |
| L238, 259 | Branding returns False |

Category (b). Fix: distinguish "no branding configured" (legitimate None) from "branding file corrupted" (should raise).

### `reporting/__init__.py`

| Site | Pattern |
|---|---|
| L138, 149, 161 | Top-level convenience returns `False` on any error |

These are the public convenience functions most likely to be called from notebooks — worst place for silent failure.

### `reporting/analytics/polling_analyzer.py` (touched by #389)

All (a) after #389 — typed catches raise `PollingAnalysisError`. ✓

### `reporting/engines/*_engine.py`

Deferred to ELE-2420 (shared-core rewrite) — need to read these 5+ files together to avoid duplicating the same fix across copies.

## Per-module: `config/`

Priority 3.

### `config/credential_manager.py`

Expected heavy failure-mode surface (external API calls, 1Password CLI, file I/O). Deferred to dedicated ELE-2418-sub PR. Known smells:
- L380, L744: hardcoded `"password"` / `"1password"` literals — confirm these are intentional field-name strings, not secrets
- Broad exception counts (79 `except X`) suggest widespread silent-swallow

### `config/databases.py`

- L235: `password = config['password']` — KeyError propagates (category (a) — correct)
- Audit all `config['<key>']` for whether missing keys should raise with context or be optional

## Per-module: `files/`

Priority 4.

### `files/paths.py`, `files/remote.py`, `files/hashing.py`

46 `except X:` clauses across the package. Pattern to audit:
- Download failures (`remote.py`) — should retry (which it does per docstring) but on final failure, the silent-None pattern (CC1) is wrong — should raise `DownloadError`
- Hash mismatches — should be `IntegrityError`, not silent return
- Path manipulation — most are (a); audit for edge cases like Windows path separators, UNC paths, symlink loops

## Per-module: `analytics/`

Priority 5.

### `analytics/google_analytics.py`, `analytics/google_slides.py`, `analytics/snowflake_connector.py`, `analytics/datadotworld_connector.py`, `analytics/facebook_business.py`

All wrap external APIs → broad except common + sentinel returns common. Each gets its own rewrite PR under ELE-2420, with the consistent pattern:

```python
# BEFORE
try:
    return external_api_call(...)
except Exception as e:
    log_error(f"call failed: {e}")
    return {}

# AFTER
try:
    return external_api_call(...)
except (RequestException, ValueError) as e:
    log_error(f"GA list_properties failed for account={account_id}: {e}")
    raise AnalyticsAPIError(f"GA list_properties failed for account={account_id}") from e
```

## Edge cases called out in ELE-2418 intake

Validated where each currently stands post-recent PRs:

| Edge case | Module | Status |
|---|---|---|
| Empty DataFrame → `pd.crosstab` | `reporting/analytics/polling_analyzer.py::create_cross_tabulation_matrix` | (a) after #389 — raises `PollingAnalysisError` ✓ |
| Mixed dtype cross-tabs in heatmap | same file | (a) after #389 — `_choose_heatmap_fmt` + cast ✓ |
| Cross-vintage FIPS / GEOID20 vs 10 | `geo/` | **Partial** — `_is_vtd_pl_boundary` done (#386); broader cross-vintage join safety is TBD under ELE-2418-geo-deep |
| Zero-baseline change detection | `reporting/analytics/polling_analyzer.py::create_change_detection_data` | (a) after #389 — `growth_from_zero` direction ✓ |
| `geo_column ≠ row_var` in chain_to_argument | `survey/render.py` | (a) after #391 — raises `RenderError` ✓ |
| Unknown `alpha` in significance test | `survey/significance.py` | (a) after #391 — raises `SignificanceError` ✓ |
| Missing metric column in `_build_mean_scale` | `survey/crosstab.py` | (a) after #391 — raises `ValueError` ✓ |
| `geopandas` absent | `geo/boundary_providers.py::GADMProvider.is_available` | (a) ✓ |
| `reportlab` absent at module load | `reporting/analytics/polling_analyzer.py` | **(c)** — module import fails if reportlab missing. Test imports work via `pytest.importorskip('reportlab')` added #389. Runtime fix: wrap the `chart_generator` import in a lazy-load or move ChartGenerator out of polling_analyzer's import chain. Under ELE-2420 |

## Output

Next PRs will:
1. Land this catalog (this PR).
2. Per-module rewrites under ELE-2420 that convert category-(b) sites to (a).
3. Each such rewrite references the relevant row(s) of this table so a future diff-reader can see which category (b) was fixed.

## Method notes for the next reviewer

- Run `rg "except Exception" siege_utilities/<module>/` to find broad catches
- Run `rg -nE "return (None|False|\\{\\}|\\[\\]|'')\\s*$" siege_utilities/<module>/` to find sentinel returns
- Pair with: `rg "log_warning|log_error" siege_utilities/<module>/` to identify pattern CC3 (half-log, half-silence)

## Attribution

Per `skills/_output-rules.md`: no AI attribution in this document or any commit / PR body produced under this audit.
