# Changelog

All notable changes to siege_utilities will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.17.0] - 2026-05-14

Minor release rolling up a 12-PR rule-cohort fix-exercise session against
claude-configs-public v2.2.0 through v2.6.0. New scanner `writing-code:15`
(unbounded blocking I/O) wired into CI. Four BREAKING changes to specific
public surfaces, each cited against the rule that drove the change.

### Added

- **writing-code:15 unbounded-I/O ratchet** (`scripts/check_unbounded_io.py`, #492):
  AST scanner that flags any `subprocess.run` / `subprocess.check_output` /
  `subprocess.check_call` / `requests.{get,post,...}` / `urllib.request.urlopen`
  / `socket.create_connection` / `sqlite3.connect` call that lacks an
  explicit `timeout=` kwarg. Every unbounded blocking call is a DoS
  primitive against the caller's process. Wired into CI as a new job
  (`unbounded-io-check`) that runs against the full repo on every PR.
  Per claude-configs-public v2.6.0 writing-code:15 ratification.
- **Sprint C gazetteers** (#470, closes #454): `CensusGazetteer` + `WikidataGazetteer`
  under `siege_utilities/geo/gazetteers/`. Two-step lookup against the
  Census Geocoder + TIGERWeb for US administrative places; SPARQL +
  Overpass for non-administrative places via Wikidata + OSM. Includes
  OSM way-segment stitching for split-outer multipolygon relations.
- **15 `_add_*_slide` methods return `Slide`** (#487, #492, closes #485):
  `PowerPointGenerator` private methods now return the python-pptx
  `Slide` object instead of `None`. Class docstring documents the
  convention. Per writing-code:11 floor (a) inspectable return value.
- **`_ENGINE_MAP` module-load-time exhaustiveness assertion** (#492):
  `engines/dataframe_engine.py` validates the engine-name map covers
  every Engine enum member at import time. New engine added without
  map entry now fails-fast at import, not lazily at lookup.

### Security

- **`databricks.lakebase` + `databricks.unity_catalog` input validation** (#482):
  SQL identifier validation in `build_foreign_table_sql`; shell injection
  prevention in `build_lakebase_psql_command` via `validate_sql_identifier`
  + `shlex.quote`. `build_pgpass_entry` correctly escapes `:` and `\` in
  passwords (previously emitted malformed pgpass lines on special chars).
- **`credential_manager` silent-swallow drain** (#484): five `except: pass`
  patterns narrowed; backend dispatch distinguishes "credential not found"
  from "credential lookup errored" via `op` exit code as trust boundary.

### Changed

- **Bounded blocking I/O across the library and scripts** (#492, writing-code:15): 55
  unbounded `subprocess.run` / `check_output` / `urlopen` /
  `sqlite3.connect` call sites now declare explicit timeouts. Per-call
  defaults reflect the operation (`git`/`hdfs`/`twine check` = 30-60s;
  `pip install` = 300s; `setup.py` build / `twine upload` / test
  runner = 600s; HTTP downloads = 60s; SQLite lock-wait = 10s; `op`
  CLI = 60s for biometric prompts). Sites that previously could hang
  the caller's process indefinitely now surface failure instead.
- **`DataFrameEngine.multi_assign` produces layer-prefixed columns** (#492, closes #473):
  Previously chained `assign_boundaries` without renaming — second join
  silently overwrote the first layer's `geoid`/`name`/etc. when TIGER
  layers shared column names. Now every polygon-side column is prefixed
  `{layer_name}_*`. Documented behavior now matches code.
- **Em-dash and other AI-typographic punctuation removed** (#478, #492):
  Per writing-prose:1, across `engines/dataframe_engine.py`,
  `geo/spatial_data.py`, `analytics/vista_social.py`, `core/sql_safety.py`,
  and all 8 `survey/*.py` files (~70+ ASCII conversions).
- **Cross-module return-type annotations corrected** (#492): five sites on
  `discover_boundary_types`, `get_available_boundary_types`,
  `get_available_state_fips`, `get_state_abbreviations` were annotated
  `List[str]` but always returned `Dict[str, str]` at runtime. Type
  stubs now match reality.
- **History-reference sweep** (#476, writing-code:2): PR/issue/commit
  references purged from code comments and docstrings across
  `engines/dataframe_engine.py` and `geo/spatial_data.py`. Per
  writing-code:2: code documentation must not reference git history.
- **`assign_boundaries` and `multi_assign` docstrings reflect actual behavior** (#472, #474):
  Two docstring-vs-code mismatches in `DataFrameEngine`.
  `assign_boundaries` was documented `predicate='contains'` but used
  `'within'`; `multi_assign` claimed layer-prefixed columns that #492
  delivered.
- **`_ensure_sedona` emits observable signal on every path** (#487):
  Three states (already-registered, sedona-disabled, fresh-registration)
  each log at DEBUG. Per writing-code:11 floor (b) audit-trail.
- **`spatial_data.py` failure-mode contract sweep** (#478, #489): consistent
  failure-mode contract across `GovernmentDataSource._get_dataset_metadata`,
  `OpenStreetMapDataSource.download_osm_data`, and related
  metadata-fetch surfaces. Per writing-code:13.
- **`databricks.get_dbutils` content-distinguishable dispatch** (#491):
  Two-path import (`pyspark.dbutils` vs IPython namespace) now uses
  module-presence checks rather than `try/except` for branching. Per
  writing-code:14 (no exception-as-dispatch when content is
  distinguishable).
- **`init_logger` deprecation note** (#492): `init_logger` is a
  get-or-create alias for `get_logger` despite its name suggesting
  first-time setup. Docstring marker `.. deprecated::` directs callers
  to `configure_shared_logging` + `get_logger`.

### Fixed

- **`flatten_json_column_and_join_back_to_df` corrupt-record paths** (#492):
  Both fallback branches wrap `validate_json` as a Spark UDF before
  passing to `.otherwise()`. Plain Python call had been evaluated once
  at plan-build time with a `Column` object, producing constant
  `lit(None)` per row instead of per-row validation.
- **`testing.environment.check_java_version` subprocess timeout** (#492):
  Was unbounded; a hung JDK process would cascade through
  `setup_spark_environment` → `quick_environment_setup` indefinitely.
  Now `timeout=10`.
- **`vista_social` history-reference scrub** (#492): docstring references
  to `issue #306` / `PR #433` / `Phase-3 sweep` purged per writing-code:2.
- **`scan_unbounded_io.py` self-greppable regression** (#492): scanner
  source includes a comment hash for itself; a revert that drops the
  UDF wrapping turns the regression test red.

### BREAKING

**From the v2.3.0 fix exercise (PR #487):**

- **`siege_utilities.databricks.ensure_secret_scope`** now returns the scope name (`str`) instead of `True`. Callers asserting on the bool return need to update; callers ignoring the return value are unaffected.
- **`siege_utilities.databricks.put_secret`** now returns the scope-qualified key (`str`, e.g. `"my-scope/my-key"`) instead of `True`. Callers asserting on the bool return need to update; callers ignoring the return value are unaffected.
- **`siege_utilities.databricks.runtime_secret_exists`** no longer catches `Exception` and silently returns `False` on lookup errors. The function now propagates the underlying exception (scope-missing, auth-denied, etc.) so the caller can distinguish "key not present in scope" from "lookup failed entirely." Callers relying on the silent-False on lookup errors need to wrap in their own exception handler or pre-check scope existence.

All three are public-API changes per `__all__` in `siege_utilities.databricks` and the top-level `siege_utilities` namespace. The new contracts are stricter (more informative returns; no silent error swallowing) but break callers depending on the previous shapes. Drift is intentional: the previous contracts violated [`writing-code:7`](https://github.com/siege-analytics/claude-configs-public/blob/main/skills/_writing-code-rules.md) (silent error swallowing) and [`writing-code:11`](https://github.com/siege-analytics/claude-configs-public/blob/main/skills/_writing-code-rules.md) (no silent processes) from claude-configs-public v2.3.0.

**From the v2.3.1 fix exercise (PR #489):**

- **`siege_utilities.reporting.PowerPointGenerator.generate_powerpoint_presentation`** now returns `Path` (the saved file location) instead of `bool`. Raises on any python-pptx or filesystem error. Consistent with sibling `create_*_presentation` methods per [claude-configs-public v2.3.1 writing-code:13](https://github.com/siege-analytics/claude-configs-public) (sibling methods within a class follow the same failure-mode contract). Callers using the bool return need to switch to try/except + Path; callers ignoring the return value are unaffected. The bundled example in `siege_utilities/reporting/examples/comprehensive_mapping_example.py` was updated as part of the change.
- **`siege_utilities.geo.spatial_data.GovernmentDataSource._get_dataset_metadata`** now raises `SpatialDataError` on HTTP non-2xx instead of returning `None`. Per writing-code:13 (consistent failure-mode contract), the mixed contract (return None for HTTP non-2xx, raise for transport/parse errors) collapsed to a single raise-everything-non-success contract. The private method's contract change is invisible to external consumers; the public `download_dataset` caller's contract is unchanged.

**From bugfix/logging-silent-nullhandler-fallback (PR #480):**

- **`LoggerManager._create_rotating_file_handler` now raises `OSError`** (or subclass: `PermissionError`, `FileNotFoundError`, etc.) on failure instead of silently substituting `logging.NullHandler()`. Previous behavior masked permission-denied / disk-full / invalid-path failures: the caller asked for file logging, the directory was unwritable, the call succeeded silently, and no logs were ever written. Callers configuring file logging must now handle `OSError` from `configure_shared_logging` / `init_logger` / `get_logger`. Per writing-code:11: file-handler creation failures are now observable rather than swallowed.

Drift is intentional and traceable: each BREAKING entry cites the rule that drove it. Per claude-configs-public v2.3.1 writing-releases:1 composition discipline, BREAKING-changelog entries land as separate commits on the fix-exercise PRs, composing writing-code:13 / writing-code:11 with writing-releases:1 without losing per-rule attribution.

## [3.16.0] - 2026-05-13

Minor release rolling up the post-v3.15.1 backlog and a six-round
hostile code review of that work.

### Added

- **Sprint B connector test coverage** (#459, #463): mock-test suites for
  `snowflake_connector`, `facebook_business`, `datadotworld_connector`,
  `vista_social`, and `google_workspace`, plus a live-API smoke
  addition to the existing `google_analytics` suite. All live-API
  tests are gated behind `@pytest.mark.requires_api_key` and skip
  when `~/.siege-test-credentials.yaml` is absent. Documentation at
  `docs/testing/sprint-b-credentials.md`.
- **Sprint E Phase 1 invariants doc** (#462): `docs/engines/INVARIANTS.md`
  defines what cross-engine `DataFrameEngine` behaviour is mandatory
  vs. allowed to differ across PandasEngine, DuckDBEngine, SparkEngine,
  and PostGISEngine. Hypothesis-based skeleton property test that
  actually crosses an engine boundary (pandas vs. raw DuckDB SQL).

### Changed

- **NCES populator vectorisation** (#461): the three
  `NCESPopulationService` methods (`populate_locale_boundaries`,
  `populate_school_locations`, `enrich_school_districts`) pre-fetch
  existing rows into a dict keyed by the unique-together tuple,
  collapsing N+1 SELECT patterns to a single SELECT plus batched
  `bulk_update`. `objects_to_update` lists now flush every
  `batch_size` rows mid-loop so memory growth is bounded. `bulk_update`
  bypasses Django's `auto_now=True`, so `updated_at` is set explicitly
  via `timezone.now()` and included in the update field list.
  `enrich_school_districts` now accepts a `batch_size` keyword argument
  matching the other two methods.
- **PostGIS upload via `executemany`** (#461): replaces per-row
  `cursor.execute` with batched `executemany` and pandas-level
  geometry extraction.
- **PostGIS `execute_spatial_query` uses `gpd.read_postgis`** (#465):
  the previous manual-fetch path returned a non-geo frame with raw
  WKB bytes in the geometry column. `gpd.read_postgis` decodes
  geometry and picks up SRID from the geometry column metadata.
  SELECT and non-SELECT branches each have their own
  try/except/rollback so a failed read does not leave the connection
  in an aborted-transaction state.
- **DuckDB upload via explicit `register`/`unregister`** (#465):
  `DuckDBConnector.upload_spatial_data` and
  `_convert_to_duckdb` no longer rely on duckdb's replacement scan
  finding `df` in the caller frame. The unregister call is wrapped
  so it cannot mask the original exception.
- **`DataFrameEngine.groupby_agg` agg-name validation** (#465):
  all four engines now route through the shared
  `_validate_agg_names` helper at the top of `groupby_agg`. Unknown
  agg names raise `ValueError` consistently; empty `agg_dict` raises
  with the same shape; `avg` is normalised to `mean` so the
  documented synonym works everywhere.
- **`spatial_transformations._convert_to_postgis` vectorised**
  (#461): the SQL-file generator builds the line set with
  `Series.apply` and string concatenation instead of an `iterrows`
  loop. Output is byte-identical to the old path.

### Fixed

- **Bulk_update timestamp regression** (#464, #465): the in-loop
  flush path is exercised by Django-backed tests under
  `requires_api_key`-style gating (`pytest.mark.django_db` plus
  GDAL skipif) seeding `batch_size + N` rows so both the in-loop
  and the post-loop bulk_update branches are hit.
- **Perf test fraud** (#465): `tests/perf/test_iterrows_regressions.py`
  now imports and drives `SpatialDataTransformer._convert_to_postgis`
  rather than re-inlining the algorithm. A revert of the production
  vectorisation now turns the test red.
- **Cross-engine property test fraud** (#465): the skeleton compared
  `PandasEngine` to `DuckDBEngine`, but `DuckDBEngine.groupby_agg`
  passes pandas DataFrames straight through to pandas. The test could
  not detect a divergence. Rewritten to compare PandasEngine's output
  to raw DuckDB SQL via `duckdb.connect`, parametrised across
  `sum`/`mean`/`min`/`max`/`count`. Added fixed-case tests pinning
  the documented `sum`-of-all-NaN-is-0.0 and `count`-excludes-NaN
  invariants.
- **`api_credentials` fixture polarity** (#465): malformed YAML now
  raises via `pytest.fail` instead of skipping silently.

### Sprint summary

- Sprint A (#452): reliability fixes -- shipped in v3.15.1.
- Sprint B (#453): connector test coverage -- complete.
- Sprint C (#454): Census + Wikidata gazetteers -- deferred per the
  ticket's own reactive-only guidance; remains open as a placeholder.
- Sprint D (#455): iterrows vectorisation -- complete; perf benchmarks
  reframed as correctness checks.
- Sprint E (#456): cross-engine invariants -- Phase 1 (design doc +
  skeleton) complete; Phase 2 and Phase 3 to be filed.

## [3.15.1] - 2026-05-12

Patch release: Sprint A reliability fixes (#452, shipped via #457). Nine
small correctness improvements flagged in the 2026-05-08 hostile review
but deferred from v3.15.0. Each fix carries a regression test in
`tests/test_sprint_a_reliability.py`.

### Fixed

- **`survey/crosstab.build_chain`** rejects empty / schema-incompatible
  input with `CrosstabInputError` instead of returning a silent blank
  `Chain` indistinguishable from "no significant results."
- **`engines/dataframe_engine.SparkEngine.groupby_agg`** validates
  aggregation function names against a known set; unknown names raise
  `ValueError` up-front instead of cryptic `AttributeError` from
  `getattr(F, func)` deep in the Spark call stack.
- **`survey/weights.apply_rim_weights`** pre-validates target columns
  and categories before handing off to weightipy, which otherwise fails
  to converge with an opaque message after a long run. NaN target keys
  are skipped (NaN != NaN was tripping false positives).
- **`analytics/google_analytics`** validates GA date parameters as
  `YYYY-MM-DD` or recognized relative keyword (`today`, `yesterday`,
  `NdaysAgo`) before the API call. Docstrings now state that GA dates
  are interpreted in the property's configured timezone.
- **`reporting/report_generator`** escapes `<` and `&` in user text
  before passing to ReportLab `Paragraph` at every call site
  (mini-HTML parser would otherwise crash on `Q&A` / `<3`-style
  content). Applies to titles, text sections, bullets, image / map
  descriptions, and the default-section fallback.
- **`reporting/powerpoint_generator`** appends a `uuid4` fragment to
  the timestamp filename so two reports generated in the same second
  no longer overwrite each other (cron batch hazard).
- **`reporting/report_generator.generate_pdf_report`** pre-checks
  output-directory writability and builds the PDF into a sibling
  `.part` temp before `os.replace` into the final path. Partial PDFs
  no longer appear on disk on failure; the temp is cleaned up on
  rename error.
- **`config/credential_manager._redact`** carves out 40-char Git
  SHA-1s from the "long hex run" redaction rule so commit IDs pass
  through in error messages, while still redacting other long hex
  tokens and base64/JWT-style secrets.

### Notes

- IDML `add_text_frame` `style_name` parameter was already addressed in
  v3.15.0 (a525ba2); verified and tested in this release.
- `scripts/check_no_stub_docstrings.py` / `scripts/check_lazy_imports.py`
  remain clean.

## [3.15.0] - 2026-05-11

A combined feature + hardening release. Five new substantive surfaces
(grid utilities, gazetteers, hex cartograms, NL→geometry resolver) plus
the full landing of the 2026-05-08 hostile code review (15 Blockers,
≈11 Major-tier findings, 20+ CodeRabbit follow-ups, stub-docstring
cleanup).

### Added — new public surfaces

- **H3 + S2 grid utilities** with grid-agnostic dispatcher (`#438`):
  `siege_utilities.geo.grids.index_points` / `index_polygon` /
  `infer_grid`. Pass `resolution=` for H3, `level=` for S2, or
  `grid=` explicit. Wired through the multi-engine
  `DataFrameEngine.index_points` / `index_polygon` (`#439`).
- **Hex cartograms** (`#440`) — `siege_utilities.reporting.hex_cartogram`
  with `hex_tile_layout`, `hex_tile_map`, three algorithms
  (`Algorithm.GREEDY` / `HUNGARIAN` / `ANNEALING`) and three sizing
  modes (`Sizing.EQUAL` / `VALUE_PROPORTIONAL` / `VALUE_SQRT`).
  Connected-component splitting handles non-contiguous admin sets
  (CONUS + AK + HI).
- **Gazetteer protocol** (`#441` + `#442`) —
  `siege_utilities.geo.gazetteers`: a typed `Gazetteer` Protocol with
  `lookup` / `search`, two backends:
  - `WklsGazetteer` (Overture Maps admin boundaries via embedded
    sedonadb, no API key, no rate limit).
  - `NominatimGazetteer` (geopy wrapper requesting
    `geometry='geojson'`).
  Plus `resolve_gazetteer(prefer='wkls' | 'nominatim')` factory and
  typed error hierarchy (`GazetteerError` / `NotFoundError` /
  `AmbiguousError` / `BackendError`).
- **`etter_to_geometry` resolver** (`#447`) —
  `siege_utilities.geo.providers.etter_to_geometry`. Turns an Etter
  `EtterFilter` plus a `Gazetteer` into a shapely geometry. Three
  relation-semantics modes:
  - `RelationSemantics.BOUNDED` (default) — finite directional buffer
    suitable for indexed-lookup workloads.
  - `RelationSemantics.HALFPLANE` — unbounded halfplane clipped to
    world bbox.
  - `RelationSemantics.CONTAINS_CENTROID` — returns a
    `PointPredicate` callable instead of a polygon.
- **End-to-end NL→geometry showcase notebook** (`#448`) —
  `notebooks/spatial/07_natural_language_to_geometry.ipynb` chains
  Gazetteer → Etter → resolver → grid dispatcher in one demo.

### Security & correctness

- **SQL injection sweep** (`#443` B1) — parameterized or
  allow-list-validated identifier interpolation at 8 sites across
  DuckDB, Snowflake, PostGIS, and Spark/Sedona.
- **Zip-slip protection** (`#443` B2) — `unzip_file_to_directory`
  now validates AND extracts per member; previous validate-then-
  `extractall` ignored the check.
- **`run_command(unsafe=True)` no longer implies `shell=True`**
  (`#443` B4) — the two are now orthogonal; argv-level execution
  preserved for safety even when bypassing the allow-list.
- **SSL `verify=False` fallback is now opt-in** (`#444`) — controlled
  by `SIEGE_INSECURE_SSL=1`. Previously the spatial-data downloader
  silently disabled verification on every SSL error, which is exactly
  the case a MITM proxy creates.
- **Env-path traversal guard** (`#444`) — `SIEGE_OUTPUT`,
  `SIEGE_DATA`, `SIEGE_CACHE` etc. refuse paths outside `$HOME` by
  default; `SIEGE_ALLOW_UNSAFE_PATHS=1` to override.
- **`_slugify_client_name`** (`#444`) — branding directory names are
  now allow-list normalised. Previously `replace(' ', '_')` left
  `../` and OS path separators free to escape `config_dir`.
- **Platform-aware Liberation font lookup** (`#444`) — was hardcoded
  to `/usr/share/fonts/truetype/liberation` (Linux-only).
- **`print()` log fallbacks removed** (`#444`) — `geo/geocoding.py`
  and `providers/census_geocoder.py` previously bypassed user
  logging config when the package-level helpers couldn't be
  imported. Stdlib `logging.getLogger` is a hard requirement now.
- **PostGIS uploads pass SRID** (`#443` review-followup) —
  `PostGISConnector.upload_spatial_data` now calls
  `ST_GeomFromText(wkt, srid)`. Previously the 1-arg form returned
  SRID=0 and failed against `_create_spatial_table`'s
  `GEOMETRY(<type>, <srid>)` constraint.
- **DuckDBConnector / PostGISConnector init repair** (`#443` B5) —
  both classes used `self.user_config` before initialising it and
  crashed on construction. Now actually usable.
- **DuckDB connection lifecycle** (`#443` B6) —
  `SpatialDataTransformer._convert_to_duckdb` wraps `duckdb.connect`
  in a context manager.
- **NaN-drop fix in `apportion`** (`#443` B8) — zero-area source
  polygons are detected and logged BEFORE `gpd.overlay`; previously
  they silently disappeared from the weighted aggregation.
- **`to_geodataframe` IndexError fix** (`#443` B10) — predicate
  evaluated on the dropna result, not on `len(df)`.
- **Survey significance SE underflow** (`#443` B9) — guard
  tightened from `se == 0` to `not finite or se <= 1e-12` so
  underflowed-but-nonzero SEs don't produce inf/NaN z-scores.

### Changed — architecture

- **`BoundaryRetrievalError` now inherits from `SiegeGeoError`**
  (`#445`) — `except SiegeError` now catches the entire geo
  exception family. Previously this stood alone outside the
  documented hierarchy.
- **Spark temp views get uuid-suffixed names** (`#445`) — 8 sites
  (`spatial_join`, `buffer`, `distance`, `assign_boundaries`,
  `nearest`). Concurrent calls no longer clobber each other's
  catalog state.
- **`apportion` NaN-drop detection moved to pre-overlay** (`#445`).
- **matplotlib figure cleanup in `try/finally`** (`#445`) — leaks
  on `savefig()` exceptions are gone.
- **Cache LRU + atomic write** (`#445`) —
  `siege_utilities.cache.ensure_sample_dataset` enforces a per-call
  size budget (default 5 GiB; configurable via
  `SIEGE_UTILITIES_CACHE_MAX_BYTES`) and atomic-renames via
  `tempfile.mkstemp` instead of a predictable `.part` filename.

### Tooling

- **`scripts/check_no_stub_docstrings.py`** — CI gate that fails
  any new placeholder docstring (`"Description needed"`,
  `"Auto-discovered and available"`). Initial backlog of 18
  placeholders rewritten in `#449`; baseline drained to `{}`.
- **`scripts/check_lazy_imports.py`** — CI gate that verifies every
  `_LAZY_IMPORTS` registry entry resolves to a real attribute.
  Tolerates optional-dep failures; fails on registry drift.
- **`siege_utilities.core.sql_safety`** extended:
  `validate_sql_identifier_in(name, allowed)`,
  `escape_sql_string_literal(value)`, and `allow_dotted=True`.
- **`[credentials]` extra populated** (`#444`) — now pulls
  `keyring>=24.0.0` so `pip install siege-utilities[credentials]`
  isn't a no-op.

### Notable behaviour changes (for library consumers)

- `SIEGE_INSECURE_SSL=1` is required to restore the legacy
  verify=False fallback in `siege_utilities/geo/spatial_data.py`.
- `SIEGE_ALLOW_UNSAFE_PATHS=1` is required for any `SIEGE_*` env-var
  path outside `$HOME` (CI / Docker setups pointing at `/data` or
  `/var/cache/X` need this).
- `siege_utilities.cache.ensure_sample_dataset` evicts LRU when the
  cache exceeds 5 GiB; tune via `SIEGE_UTILITIES_CACHE_MAX_BYTES`.
- Connector identifiers (`table_name`, `schema`, column names) are
  now validated against `[A-Za-z_][A-Za-z0-9_]*`. Identifiers
  containing spaces / dashes raise `ValueError` rather than landing
  in SQL.
- Nominatim timestamps are timezone-aware (`datetime.now(timezone.utc)`).
  Code comparing returned timestamps to naive `datetime.now()` will
  raise `TypeError` — call `isoformat()` or use tz-aware comparisons.
- `BoundaryRetrievalError` now inherits from `SiegeGeoError`. Code
  catching `except BoundaryRetrievalError` still works; broader
  `except SiegeError` now catches it where it didn't before. Net
  additive.

### Added — ELE-2415 library audit

- **Typed exception hierarchies** across silent-swallow sites in `reporting/` and `geo/`:
  - `siege_utilities.reporting.ReportingConfigError` (new) — raised by top-level
    `export_branding_config` / `import_branding_config` / `export_chart_type_config`
    instead of returning `False` on failure.
  - `siege_utilities.reporting.chart_types.UnknownChartTypeError` /
    `ChartParameterError` / `ChartCreationError` — raised by
    `ChartTypeRegistry.create_chart()` and `validate_chart_parameters()`
    instead of returning `None` / `False`.
  - `siege_utilities.reporting.client_branding.ClientBrandingError` /
    `ClientBrandingNotFoundError` — raised by `ClientBrandingManager`
    methods for unexpected I/O and missing-client paths.
  - `siege_utilities.geo.census_geocoder.CensusGeocodeError` — raised by
    `geocode_single()` / `geocode_batch()` on API/network failure. Previously,
    failures returned `CensusGeocodeResult(matched=False)`, indistinguishable
    from genuine no-match results.
  - `siege_utilities.geo.spatial_data.SpatialDataError` — raised by
    `GovernmentDataSource` and `OpenStreetMapDataSource` download helpers on
    HTTP/parse failures instead of returning `None`.

  All new exceptions use `raise ... from e` chaining. See
  `docs/FAILURE_MODES.md` (pattern CC1) for the full catalog.

- **Survey waves subsystem** (ELE-2440 / D7 part 2):
  - `siege_utilities.survey.Wave` — one fielding: `id`, `date`, optional
    respondent-level `df`, optional per-wave `stack` and `weight_scheme`.
  - `siege_utilities.survey.WaveSet` — ordered set of Waves with
    `compare_chain(row_var, break_vars=…)` returning a LONGITUDINAL Chain
    aligned across waves (columns = wave ids in date order, trailing Δ
    column when ≥2 waves).
  - `siege_utilities.survey.waves.compare_waves` — primitive the WaveSet
    method delegates to; raises `WavesError` on empty WaveSet or missing
    per-wave DataFrame.
  - `siege_utilities.reporting.wave_charts` — `trend_chart` and `heatmap`
    rendering helpers consuming a LONGITUDINAL Chain.

  Completes the PollingAnalyzer migration path: longitudinal polling
  analysis is now a WaveSet composition on top of the survey primitives
  rather than a separate analyzer class.

- **Client ↔ Survey registry** (`siege_utilities.survey.registry`):
  - `WaveSet.client_id` — optional string keying into the branding /
    profile system or an external CRM.
  - `ClientSurveyRegistry` — in-memory map of ``client_id → {name →
    WaveSet}`` with `register` / `register_for` / `surveys_for` /
    `get_survey` / `require_survey` / `unregister` / `client_of`.
    Supports `"acme" in reg` and `("acme", "Tracker") in reg`
    membership checks; `len(reg)` counts all surveys across clients.
  - `ClientSurveyError` (subclass of `KeyError`) raised on missing
    lookups, duplicate survey names within a client, or registration
    without a client_id.

  Survey names are scoped per-client: ``("Acme", "Tracker Q2")`` and
  ``("Beacon", "Tracker Q2")`` coexist fine. Branding / display info
  stays in `reporting/client_branding`; the registry only answers
  "which surveys belong to this client".

### Documentation

- **`docs/INTENT.md`** — per-module purpose and 9 divergence candidates.
- **`docs/FAILURE_MODES.md`** — 5 cross-cutting anti-pattern categories (CC1–CC5)
  with per-module site inventory.
- **`docs/TEST_UPGRADES.md`** — coverage scorecard and 5 test-upgrade patterns
  (PU1–PU5); zero-coverage modules identified.
- **`docs/ARCHITECTURE.md`** — three-layer model (core → domain → consumers),
  imports-go-DOWN invariant.
- **`docs/adr/0001–0007`** — Architecture Decision Records covering Chain
  pipeline ownership, chart/map generator injection, BoundaryProvider
  registration, dataclass-vs-Pydantic, lazy-import convention, analytics
  location split, and model type location.
- **`docs/NOTEBOOKS.md`** — inventory of 27 notebooks, consolidation plan
  to 12 canonical + 7 focused specializations.

### Test coverage

New dedicated test modules for previously-untested code:
- `tests/test_admin_profile_manager.py` (16 tests)
- `tests/test_hygiene_generate_docstrings.py` (22 tests)
- `tests/test_files_paths.py` (28 tests)
- `tests/test_reporting_config_exports.py` (10 tests)
- `tests/test_chart_types_errors.py` (10 tests)
- `tests/test_client_branding_errors.py` (14 tests)
- `tests/test_census_geocoder_errors.py` (6 tests)
- `tests/test_spatial_data_errors.py` (7 tests)

### Changed

- `pytest-randomly`, `hypothesis`, `nbmake` added to `dev` extras.

### Migration notes

Callers that relied on the old silent-swallow behavior (checking for
`None` / `False` return) must migrate to `try/except` around the new
exception types. The exception types are subclasses of standard Python
exceptions (`LookupError`, `ValueError`, `RuntimeError`) so broad
existing handlers will still catch them.

## [3.13.0] - 2026-03-30

### Added
- **First-class geospatial in every DataFrame engine** — 5 spatial abstract methods (`read_spatial`, `spatial_join`, `buffer`, `distance`, `to_geodataframe`) + 2 concrete sugar methods (`point_in_polygon`, `dissolve`) in DataFrameEngine ABC. All 4 engines (Pandas, DuckDB, Spark, PostGIS) implement spatial operations using native capabilities.
- **SparkEngine Sedona integration** — `enable_sedona=True` parameter registers Apache Sedona UDFs for distributed spatial operations.
- **DuckDB spatial extension** — lazily activated via `_ensure_spatial()` for `ST_Read`, `ST_Buffer`, `ST_Distance`, etc.
- **Temporal political models (Phase A)** — `CongressionalTerm`, `Seat`, `StateElectionCalendar` Django models + Pydantic schemas + `populate_congressional_terms` management command.
- **Temporal event models (Phase B)** — `Race`, `RaceEvent`, `SpatioTemporalEvent`, `ReturnSnapshot` for election event tracking and progressive result reporting.
- **PlanDistrictAssignment (Phase C)** — GenericFK bridge mapping Seats to boundary polygons within redistricting plans.
- **Django migration 0005** — creates tables for all temporal, redistricting, and event models.
- **SpatiaLite geocoding cache** — `SpatiaLiteCache` for portable file-based caching of geocoding results, boundary lookups, and crosswalk mappings with bounding-box queries.
- **S3 boundary staging** — `stage_boundaries_s3` management command exports TIGER boundaries to MinIO in Parquet and GeoJSON formats.
- **Census API refactoring** — monolithic `census_api_client.py` split into `census/` subpackage (variable_registry, dataset_selector, api modules).
- **Papermill notebook test runner** — `test_notebooks.py` runs all 27 notebooks headlessly with dependency grouping (pure-python, geo, django, analytics, spark, credentials).
- **6 new notebooks** — NB22 (Temporal Political Models), NB23 (Redistricting Analysis), NB24 (DuckDB & Engine Abstraction), NB25 (SpatiaLite Cache & Geocoding), NB26 (International Boundaries / GADM), NB27 (Advanced Census MOE & NAICS/SOC).
- **SiegeSpatialError** exception class under `SiegeGeoError`.
- **boto3 optional dependency** in `[s3]` extras group.
- **papermill + nbformat** in `[notebooks]` and `dev` extras.
- **29 Django ORM tests** against PostGIS verifying CRUD, FK relationships, constraints, GenericFK, M2M, and model methods.
- **19 spatial engine tests** verifying Pandas and DuckDB spatial operations and cross-engine consistency.

### Fixed
- **PlanDistrictAssignment FK bug** — string reference `"temporal_political.Seat"` used wrong app label; fixed to direct `Seat` import.
- **NB10 generate_sample_ga_data()** — updated call signature and data key references for changed API.

### Changed
- **Notebook NB02/NB03** — added cross-reference notes clarifying scope overlap.
- **Notebook NB04** — added navigation note pointing to focused notebooks for specific subsystems.
- **Notebooks NB16/19/20** — moved to `integration` marker (require Spark/external downloads).

## [3.12.1] - 2026-03-22

### Fixed
- **Missing data exports** (su#328) — `data/__init__.py` missing 7 exports from `redistricting_data_hub`.
- **Name collisions** (su#329) — top-level `__init__.py` had two name collisions (`get_dataset_info`, `diagnose_environment`).
- **extras_require sync** (su#330) — `setup.py` extras out of sync with `pyproject.toml`.
- **Bare except clauses** (su#331) — replaced 19 bare `except:` with `except Exception:` across 7 files.
- **CONTRIBUTING.md test count** (su#332) — updated from 1884 to 3058.
- **CI contract allowlist** — updated for changed top-level API signatures.
- **geo-no-gdal CI lane** — updated ignore list for Django/Google-dependent test files.
- **F401/F841 lint violations** — cleaned up unused imports and variables across source and test files.

## [3.11.0] - 2026-03-22

### Added
- **Enterprise onboarding notebooks** — NB21 for branded PPT/PDF generation using `ChartGenerator` and `ClientBrandingManager`.
- **Commit-to-issue linkage script** — `scripts/link_commits_to_issues.py` for retroactive GitHub issue traceability.

## [3.10.0] - 2026-03-11

### Added
- **Vector chart export** — `ChartGenerator.save_figure_as_vector()` for SVG/EPS/PDF output.
  All 7 GA report chart functions gained `vector_export_path` parameter; `generate_ga_report_pdf()`
  gained `vector_export_dir` for batch SVG export (designer handoff for InDesign/Illustrator).
- **Period-over-period comparison** (su#304) — `create_period_comparison_chart()` overlays
  current vs prior period daily sessions with fill_between shading and change annotation.
  Prior daily data added to both `generate_sample_ga_data()` and `fetch_real_ga4_data()`.
- **Report cosmetic enhancements** (su#305) — GA term definitions footnote system after KPI
  and traffic tables, cover page logo support (`client_logo_path`/`company_logo_path`),
  dynamic section numbering across all report sections.
- **Raster chart export** — `generate_ga_report_pdf()` gained `raster_export_dir` parameter
  to save high-resolution PNG copies (300 DPI) of all 8 charts for presentations and web use.
- **Design kit export** — `export_design_kit()` produces a complete InDesign handoff package:
  SVG vector charts, PNG raster charts, CSV data tables, report narrative markdown, and
  metadata YAML with KPIs and file inventory.
- **SVG logo support** — Cover page logo auto-converts SVG to PNG via `cairosvg` for
  ReportLab compatibility (graceful fallback if cairosvg not installed).

### Fixed
- **GA4 API response parsing** (su#302, PR #299) — `dimension_headers`/`metric_headers`
  now read from the Response object (not Row objects). Metric columns coerced to numeric
  via `pd.to_numeric()` to fix `nlargest`/aggregation on string-typed values.

### Tests
- **GA4 connector tests** (PR #301) — 7 unit tests covering response parsing, numeric
  coercion, empty responses, dimensions-only, metrics-only, and unauthenticated state.

## [3.9.1] - 2026-03-10

### Fixed
- **Credential hygiene** — `.gitignore` blocks `*credentials*.json`, `*service_account*.json`,
  `*token*.json`, `*client_secret*.json`, `*.pem` from accidental commits.
- **Hardcoded credentials removed** — `database_connections.yaml` now uses `CHANGE_ME` placeholders.
- **Name collision fix** — `load_client_profile`/`save_client_profile`/`list_client_profiles`
  rename shims in `__init__.py` to avoid shadowing.
- **`get_download_directory()` signature** — fixed call in `files/__init__.py` and
  `reporting/__init__.py` to pass `username` arg, added `client_code` path handling.
- **`release_manager.py`** — now tracks `docs/source/conf_fast.py` version.
- **Geocoding log noise** — demoted `log_warning` to `log_debug` in `use_nominatim_geocoder`.
- **`get_available_survey_years`** — added alias in `geo/timeseries` for clarity
  (`get_available_years` still works).

## [3.9.0] - 2026-03-10

### Added
- **1Password integration for Google Workspace** — `GoogleWorkspaceClient.from_1password()`
  auto-detects OAuth client secret vs service account key from 1Password Document items.
  `get_google_oauth_document_from_1password()` in credential_manager.
- **URL helpers** — `GoogleWorkspaceClient.spreadsheet_url()`, `document_url()`,
  `presentation_url()`, `file_url()` static methods. Create functions now log live URLs.
- **folder_id support** — `create_spreadsheet()`, `create_document()`, `create_presentation()`
  accept `folder_id` to place files in a specific Drive folder at creation time.
- **Auth script** — `scripts/google_workspace_auth.py` with `--mode`, `--item`, `--vault`,
  `--account` CLI options. Supports both OAuth (browser) and service account (headless) modes.

### Fixed
- **Registry register() self-default bug** — re-registering an account with `is_default=True`
  no longer clears its own default flag.
- **from_service_account() null crash** — raises `ValueError` instead of `AttributeError`
  when 1Password returns no data.
- **credential_manager error logging** — `op` stderr now surfaced in error messages.

## [3.8.4] - 2026-03-09

### Added
- **Google Workspace write APIs** (su#289) — `GoogleWorkspaceClient` base client with
  OAuth2 and service account auth. Module-level functions for Sheets (`create_spreadsheet`,
  `write_dataframe`, `read_dataframe`), Slides (`create_presentation`, `add_blank_slide`,
  `create_textbox`), and Docs (`create_document`, `insert_paragraph`, `insert_table`,
  `replace_text`). Drive utilities (`copy_file`, `share_file`, `move_to_folder`).
- **Multi-Google-account management** (su#290) — `GoogleAccount` model, `GoogleAccountRegistry`
  with JSON persistence and default selection, `Person.google_accounts` integration,
  `GoogleWorkspaceClient.from_account()` / `from_registry()` factory methods,
  `migrate_single_account()` utility.
- **Tiered geo extras** (su#275) — `[geo-lite]` tier (shapely, pyproj, geopy — no GDAL),
  import guards on 5 modules, `geo_capabilities()` runtime detection function.
  `[geo]` and `[geodjango]` tiers preserved. Managed environments docs (Databricks, Colab, SageMaker).
- **IsochroneResult Django model** + `IsochroneComputeService` + migration 0004 (su#287).
- **Isochrone quality rewrite** (su#268) — Domain exceptions (`IsochroneError`,
  `IsochroneNetworkError`, `IsochroneProviderError`), TypedDict result types, retry logic,
  method dispatch, configurable CRS via `get_default_crs()`/`set_default_crs()`.
- **CRS parameter** on 19 spatial-returning functions across `spatial_data`, `spatial_transformations`,
  `temporal/query`, `interpolation/areal`, `schemas/converters`, `nces_download`, `boundary_manager`.
- **Python version support policy** doc and CI for Python 3.13 (su#274).
- **Convergence diagram** chart type in reporting module.
- **Notebook NB18** — Google Workspace demo using elect.info onboarding content.
- **Sphinx docs** — `google_workspace.rst`, updated `geo.rst` with tiered extras and isochrones.

### Changed
- **License model update (effective March 6, 2026)** — moved from MIT to a dual-license model:
  - AGPL-3.0-only for open-source use
  - Commercial license path for proprietary/commercial use by separate agreement
  - Attribution required in both license paths
- **Raised dependency floors** — pandas>=2.0, numpy>=1.24, scipy>=1.11, shapely>=2.0.0,
  geopandas uncapped (removed <1.0 cap). Python floor: 3.11.
- **Version sync** via `importlib.metadata` — single source of truth in pyproject.toml.

## [3.2.0] - 2026-03-01

### Changed
- **Lazy imports** — `import siege_utilities` is now lazy-loaded via PEP 562 `__getattr__`. Import time reduced from ~29s to ~0.02s. All public API names remain accessible via `from siege_utilities import X` (su#183)
- **Optional dependencies** — Core install (`pip install siege-utilities`) now pulls only 4 packages: pyyaml, requests, tqdm, pydantic. All heavy packages (geopandas, matplotlib, pyspark, etc.) moved to optional extras. Use `pip install siege-utilities[all]` for previous behavior (su#181, su#182)
- All subsystem `__init__.py` files converted from eager imports to lazy `__getattr__` registries: distributed, core, geo, reporting, analytics, testing
- `release_manager.py` tracks 5 version locations (removed hardcoded `get_package_info` version, now uses `__version__` dynamically)

### Added
- **New dependency extras**: `data`, `config-extras`, `web`, `database` (joins existing `geo`, `reporting`, `analytics`, `distributed`, `geodjango`, etc.)
- **CI lanes**: `test-core` (core-only install), `test-geo-no-gdal` (geo without GDAL system libs) (su#184)
- **Pytest markers**: `core`, `geo`, `requires_gdal`, `requires_spark`, `integration`
- **`check_ci_status()`** in `release_manager.py` — queries GitHub Actions before release
- **`tests/test_backward_compat.py`** — 202-test regression gate verifying all critical names remain importable

### Migration guide
- `pip install siege-utilities` — only 4 core packages installed
- `pip install siege-utilities[all]` — full install, identical to v3.1.0
- `pip install siege-utilities[geo]` — geo functions only
- `from siege_utilities import X` — works exactly as before (lazy loaded)

## [3.1.0] - 2026-03-01

### Added
- **NCES urbanicity download** — `NcesDownloadService`, Django models (`NcesSchool`, `NcesDistrict`, `NcesLocale`), and `populate_nces` management command (PR#173, su#136-138)
- **Areal interpolation** — `ArealInterpolationService` wrapping PySAL Tobler for area-weighted and dasymetric interpolation between geographic boundaries (PR#174, su#140)
- **Crosswalk time series analytics** — `CrosswalkTimeSeriesService` for temporal analysis across geographic boundary changes, with rollup and trend detection (PR#175, su#139)

### Fixed
- `county_fips` threading issue in geography services (su#176)
- Geography alias normalization for Census boundary lookups (su#177)
- GEOID preservation during geographic enrichment joins (su#178)
- `strict_years` validation rejecting valid year ranges in time series queries (su#180)
- Stale/missing source references in Census dataset documentation (su#163)

### Changed
- `run_tests.py` rewritten to match actual 41 test files in test suite

### Removed
- `hdfs_legacy.py` — broken duplicate stubs of HDFS utilities
- Stale `__init__.py.backup` artifact

## [3.0.1] - 2026-02-27

### Added
- **Census Django gaps** (su#116) — `nearest()` query, Tract urbanicity lookup, GEOID validators, GEOID slugs, Django cache layer, timeseries + rollup services
- **Urbanicity classification** (su#131) — `UrbanicityClassificationService` and `populate_urbanicity` management command
- Migration 0002: `urbanicity_code` field + GEOID check constraints
- Census dataset relationships documentation (`docs/data-relationships/`)
- Spatio-temporal events design doc for election cycles and races

### Fixed
- `CensusDataSelector` primary dataset bonus never applied (su#164, PR#169)
- `CheckConstraint` API: `check=` → `condition=` for Django 5.2 compatibility
- Pydantic v2 config system lazy-loaded for Databricks v1 compatibility (su#160, PR#170)

## [3.0.0] - 2026-02-25

### Added
- **Unified Geographic Model** (Epic 14) — complete rearchitecture of spatial data layer:
  - `TemporalGeographicFeature` → `TemporalBoundary` → `CensusTIGERBoundary` hierarchy replacing `CensusBoundary`
  - `TemporalLinearFeature` + `TemporalPointFeature` abstract bases for roads/addresses
  - 25+ new models: political districts, GADM administrative boundaries, education boundaries, federal boundaries, intersections, crosswalks
  - 50+ geometry columns across 34 tables in initial migration (`0001_initial.py`)
  - Full Pydantic schema layer (`geo/schemas/`) with GDF↔Schema↔ORM converters
- Updated managers, serializers, and services for v3 field renames
- CBSA, UrbanArea, and intersection models
- Template architecture problem design doc
- Sphinx `conf.py` files added to release manager version tracking

### Changed
- Version bump 2.2.0 → 3.0.0 (breaking: model renames and field changes)
- CI updated to install GDAL/GEOS/PROJ for GeoDjango test jobs

## [2.0.0] - 2026-02-23

### Added
- **Person/Actor architecture** — unified domain model for people across political, business, and nonprofit contexts, with Hydra config integration, JSON/CSV/Parquet export, and deprecation shims for legacy code
- **Geographic reconciliation** — canonical `CANONICAL_GEOGRAPHIC_LEVELS` (20 entries), `resolve_geographic_level()` alias resolver, `GeographyLevel` enum with `_missing_()`, 75 tests
- **Census API client** — `CensusDataIntelligence` with retry/fallback, boundary type catalog, and state FIPS lookup
- **GeoDjango integration** — spatial data utilities for choropleth and bivariate choropleth map generation
- **OAuth2 1Password credential wiring** — `get_google_oauth_from_1password()` for GA4 reporting, with service-account-first fallback to OAuth2
- **GA4 multi-client reporter** — real Google Analytics 4 data fetching via `fetch_real_ga4_data()` with cached OAuth2 tokens
- **Choropleth library** — heatmap dispatcher, bivariate choropleth serialization, Folium attribution fixes
- **Credential manager** — 1Password integration for secure credential retrieval across notebooks
- **Release manager** — consolidated `scripts/release_manager.py` with PyPI upload, twine validation, dry-run, git tagging, and changelog extraction
- **Boundary type catalog** — comprehensive reference for Census geographic boundary types
- **Census data intelligence** — smart data retrieval with automatic variable resolution
- **17 Jupyter notebooks** — NB01 through NB17 covering data science workflows, spatial analysis, GA4 reporting, and more
- **724 tests** — comprehensive test suite covering unit, E2E, and pipeline/environment tests

### Changed
- Python version floor raised to **3.11** (from 3.9)
- Structured logging across 32 modules via `siege_utilities.core.logging`
- Dynamic package discovery in `setup.py` and `pyproject.toml`
- CI/CD pipeline: UV-based installs, Java 17 for Spark, branch pattern expansion, twine validation in build job
- Branch naming convention updated: developer-prefixed (`dheerajchand/<feature>`), release branches accept `v` prefix and `-rc.N` suffixes

### Fixed
- Census API retry fallback for intermittent 500 errors
- Bivariate choropleth serialization for GeoJSON export
- Folium map attribution rendering in notebook environments
- Heatmap dispatcher type resolution for custom color schemes
- NB10 SecurityError with pickle deserialization
- NB16 JAVA_HOME detection for PySpark sessions

### Deprecated
- `siege_utilities.hygiene.pypi_release` — all public functions emit `DeprecationWarning`, use `scripts/release_manager.py` instead

### Removed
- 20 unvalidated test files from early restoration (preserved in git history)
- Stale merge artifacts from initial branch setup

## [1.1.0] - 2024-12-15

### Added
- Hygiene module with docstring generation and PyPI release utilities
- Git workflow utilities for branch validation and commit conventions
- Core logging module with structured output

### Changed
- Package structure reorganized into core/, git/, hygiene/ submodules

## [1.0.0] - 2024-08-01

### Added
- Initial release of siege_utilities
- Spatial data processing functions
- Multi-client reporting framework
- Basic choropleth generation
- Package configuration with setup.py and pyproject.toml
