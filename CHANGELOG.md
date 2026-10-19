# Changelog

All notable changes to siege_utilities will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `QCEWFiles.parse()` includes ranged NAICS sectors `31-33`, `44-45`, and
  `48-49` and excludes the `10` all-industry total that caused double-counting,
  along with supersector aggregates. **Behavior change:** `parse()` and
  `load()` now default to `own_code=5` (private) and `area_level="state"`
  (statewide, `agglvl_code=54` at the default `naics_depth=2`), instead of
  mixing ownerships and statewide/county rows. Callers can select another
  ownership and `county`, `national`, or `msa` area level; the aggregation
  code follows the requested NAICS depth. Suppressed rows (`disclosure_code`
  of `N`) carry a boolean `is_suppressed` flag, so their source employment
  and wage zeros can be excluded from calculations. When their source
  disclosure columns exist, boolean `is_lq_suppressed` and `is_oty_suppressed`
  flags separately identify `lq_disclosure_code` and `oty_disclosure_code`
  values of `N`; corresponding `lq_*`/`oty_*` zeros are sentinels, not measured
  zeros. The parser docstring now describes all preserved source columns
  plus these flags (#1507).

## [4.1.0] - 2026-10-18

### Changed

- New *file* names now get the same check as new directory names. The
  `siege_utilities.files` helpers that create a file refuse a name containing
  a C0, DEL or C1 control character, or a lone surrogate: they raise
  `PathSecurityError` and create nothing. The helpers are `touch_file`,
  `copy_file`, `move_file` (into an existing directory, the source's name is
  checked), `delete_existing_file_and_replace_it_with_an_empty_file`,
  `safe_file_write`, `safe_json_write`, `atomic_write_path`,
  `atomic_write_shapefile`, `download_file`, `save_spatial`, `save_tabular`,
  `secure_write_text`, and `unzip_file_to_directory` for member files, checked
  at the path `zipfile` actually writes (so `a/../f<ESC>.txt` is refused). The
  check is public as `reject_unsafe_new_file_path` (#1737).
  **Migration:** existing files with such names can still be read, moved and
  overwritten, except as a shapefile: `atomic_write_shapefile` and
  `save_spatial(..., fmt=SpatialFormat.SHAPEFILE)` refuse an unsafe target
  name even when it exists (its sidecars are published under that name), so
  rename such a shapefile first. Callers that build file names from external
  input should pass them through
  `siege_utilities.files.operations.sanitize_filename`. This check's message
  now reads "...in new name" rather than "...in new directory name";
  `validate_directory_path` (and so `ensure_path_exists`) keeps the old text.
  Writers outside `siege_utilities.files` are not yet covered (#1763).
- Docstring generation now defaults to a dry run. CLI callers must pass
  `--write` (or `--apply`), and Python callers must pass `dry_run=False` to
  `process_python_file` or `main` to modify files (#1589).
- **Release process:** PyPI releases go only through `publish-tag.yml`, on a
  `v*` tag push. It checks that the tag equals `v` + the pyproject version and
  that the tagged commit is on `main`, then runs the whole of `ci.yml` on the
  tag. Only after that passes does it build, check wheel contents and publish
  with `pypa/gh-action-pypi-publish` (using the existing `PYPI_API_TOKEN`
  secret; trusted publishing with attestations once configured, RELEASING.md). The token-based `release` job
  in `ci.yml` and its `release: published` trigger are removed.
  `scripts/release_manager.py --release` no longer uploads or needs
  `PYPI_API_TOKEN`. It pushes only the new tag, not `--tags`, and stops if
  tagging fails. `--build --pypi` defaults to TestPyPI and refuses
  `--repository pypi`. Manual uploads are prohibited; see `RELEASING.md`,
  which also records the `v3.19.0`, `v3.21.0` and `v4.0.0` dispositions.
  CHANGELOG entries for 3.18.0-3.23.0 have been added from the tags and git
  log (#1419).

- `validate_directory_path(..., must_exist=False)` now raises
  `PathSecurityError` when a path component that does not exist yet contains a
  C0 control character, DEL or a C1 control character. This covers callers that
  create directories through it, such as `ensure_path_exists`, and the
  zip-named subdirectory `unzip_file_to_directory` creates. Member directories
  inside an archive are checked too (#1716). Existing directories with such names still
  validate when they can be stat'ed, and file-path validation is unchanged.
  Path-validation messages and the debug log now show paths with `repr()`, so
  escape sequences are not written raw. Because the zip-named subdirectory is
  now validated, a zip whose stem is `..` (e.g. `...zip`) raises instead of
  extracting into the parent of `extract_to` (#1692).
- Google Slides report figures no longer persist in Drive.
  `create_report_from_arguments` / `create_argument_slide` now insert each
  chart or map through the new `temporary_public_figure` context manager: the
  PNG is uploaded into the report's `folder_id` (previously the Drive root),
  shared anyone-with-the-link only while Slides copies it, and deleted from
  Drive afterwards, including when the insert fails. Anyone relying on the
  leftover `fig_slide_*.png` files in Drive no longer gets them; keep your own
  copy of the figure if you need one. A failed delete is logged at ERROR with
  the file ID; it is raised only when the insert itself succeeded, so it never
  hides an insert error. New `publish_figures=True` keyword on both functions:
  pass `False` to create no anyone-with-the-link permission at all, in which
  case figures are left out of the slides with a WARNING. `create_argument_slide`
  also gains an optional `folder_id`. A Google API `HttpError` from the figure
  upload/insert is now reported as a failed slide like other figure errors.
  `upload_figure_to_drive` is unchanged and still leaves its file public; its
  docstring now says so. The file-ID log lines in `upload_figure_to_drive` and
  `GoogleWorkspaceClient.public_url` moved from INFO to DEBUG (#1450).
- The same check now covers every public helper that creates a directory or
  a file's parent: `ensure_directory_exists`, `touch_file`, `copy_file`,
  `move_file`, `delete_existing_file_and_replace_it_with_an_empty_file`,
  `safe_file_write`, `safe_json_write`, `atomic_write_path`,
  `atomic_write_shapefile`, `download_file`, `save_spatial`, `save_tabular`
  and the credential writer `secure_write_text`. Each raises
  `PathSecurityError` and creates nothing. Paths are checked as written, so in
  `a/<new>/../b` the `<new>` that `mkdir` would create on the way is checked
  too; where files land and how symlinks are treated are unchanged.
  `unzip_file_to_directory` refuses an archive, before extracting anything,
  if a member would create such a directory. New components containing a lone surrogate, which is
  how undecodable (non-UTF-8) bytes reach Python, are refused as well. The
  check is public as `reject_unsafe_new_directory_names` (#1716).

### Fixed

- RDH downloads write to a temporary file beside the cache destination and
  validate Content-Length when present before an atomic replacement. Failed
  downloads remove partial temporary files and preserve any existing cache
  entry, so an interrupted download cannot become a cache hit (#1415).
- Political schema migrations can now be applied: remove the trailing comma
  that prevented V0002 from parsing and blocked dependent V0003. Limit the
  composite foreign key's `ON DELETE SET NULL` to `(next_term_id)` so deleting
  a linked office term preserves its predecessor's required `seat_id`
  (PostgreSQL 15+). Widen congressional-terms uniqueness to
  `(congress_number, seat_id, office_term_id)` so a successor can serve the
  same seat in the same Congress (#1468).
- Docstring generation inserts lines without rewriting existing comments or
  formatting, handles async definitions, and extracts signature details without
  importing target files. File exclusions match path components and include
  Django migrations while retaining `distributed`, `redistricting`, and `builds`
  paths. Templates omit CI-rejected stub markers and skip generated doctest
  examples. Inline suites are left unchanged with a warning (#1589).
- RDH fetch and load no longer return the wrong data silently (#1571).
  `fetch_cvap` and `fetch_pl94171` match the requested geography against the
  level named in the dataset title, tokenised on spaces and underscores with
  "block group" tried before "block", or against the dataset's `geography`
  metadata when present. `geography="block"` no longer returns block groups,
  and `"block_group"` matches titles spelled "Block Group". A cached ZIP
  returns the extracted directory, as the first download does, instead of
  the archive. `load_csv` and `load_shapefile` sort the members of an
  extracted directory and raise when there is not exactly one CSV or `.shp`.
  A listing response of `RDH_MAX_RESULTS` entries logs a truncation warning.
  `RDHLoaderService.load_cvap_for_plan` and the CSV path of
  `load_demographics_for_plan` report numeric GEOID columns and unmatched
  districts instead of skipping them silently.
- `get_directory_info`, `load_directory_config`, `list_directory_configs`,
  `load_project_config` and `list_projects` create nothing, so they are back to
  their behaviour before #1692: a missing name containing a control character
  returns `{}`, `None`, `[]`, raises `FileNotFoundError` and returns `[]`
  respectively, instead of raising `PathSecurityError` (#1716).
- The test suite drops every inherited `SIEGE_*` variable except the
  `SIEGE_TEST_*` run controls, so a run never reads or rewrites the
  developer's own config through `SIEGE_USER_CONFIG_DIR`,
  `SIEGE_SETTINGS_FILE` or any `SIEGE_<SETTING>` override (#1717).
- `is_sensitive_path` again blocks `_`/`-` prefixed private-key names outside
  `.ssh` (`deploy_id_rsa`, `github-id_ecdsa`) and now covers `id_ed25519`;
  `paid_rsa` and `*.pub` stay allowed (#1702).
- Demographic population queries now keep equal GEOIDs in different boundary
  types and datasets separate. Boundary lookups use GEOIDs instead of integer
  PKs; plan assignments accept BigAutoField-sized boundary PKs. The migration
  keeps existing GEOID matches unchanged, including those with coincident
  boundary PKs. GEOID-shaped orphans also stay unchanged: a leading zero on a
  multi-character key or a length present in that content type's loaded GEOIDs
  prevents PK conversion, even when the boundary is not loaded. Only canonical
  positive integers without leading zeros or a GEOID length can convert from a
  matching boundary PK; other unmatched keys are unresolved.
  Any unresolved or duplicate rows abort the migration atomically with counts
  per model and reason. After reviewing those counts, operators can explicitly
  set `SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE=1` for the migration command to
  archive and remove those rows. Duplicates retain the newest `updated_at`, then
  highest PK. Recovery copies support reversal unless migrated rows were edited.
  Both migration directions allow 30 minutes per statement for large index and
  constraint builds, with a five-second lock timeout.
  Before running `migrate siege_geo`, back up `siege_geo_demographicsnapshot`
  and `siege_geo_demographictimeseries`, for example with
  `pg_dump -t siege_geo_demographicsnapshot -t siege_geo_demographictimeseries`.
  The opt-in `SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE=1` archives removed rows
  into `siege_geo_demographickeyarchive`; this archive table is dropped when
  the migration is reversed.
  (#1560)

- Failed legacy profile migrations no longer create defaults or report
  `migrated=True`; missing files are not migrations. Missing snapshot years
  fail the requested time-series interval and report every missing year.
  Unknown city/UA populations cannot silently classify as Small. State boundary
  requests cannot return an unfiltered national file. Invalid NLRB cache
  timestamps expire the entry. Add a blocking exception-contract AST guard
  with reviewed, fingerprinted exceptions and zero unlisted handlers (#1532).
- Bulk configuration migration records missing/corrupt user-profile errors and
  continues migrating valid clients. SWMaps files with neither optional attribute
  table retain empty attributes and the selected missing-value policy; incomplete
  schemas and broken queries against existing tables raise. The exception guard
  now covers all 14 reviewer shapes, including factories, tuples, strings, log-only handlers,
  empty-frame assignments and unannotated data functions. Package `log_*` helpers,
  including attribute calls, are recognized; 14 existing log-only handlers are
  fingerprinted for consumer tracing under #1708 (#1532).

- `populate_nlrb_regions` now creates registry-only rows by default without
  raising `IntegrityError`. Migration 0018 makes only `NLRBRegion.geometry`
  nullable; callers must allow NULL geometry, and population returns and logs
  the count of regions without geometry. County dissolves filter by the
  requested vintage and use a database-side `Union` aggregate, returning NULL
  if any requested state has no counties at that vintage. Explicit rebuilds
  clear incomplete geometry; metadata-only updates retain existing geometry.
  The command reports the without-geometry count and warns instead of printing
  a success message when any region lacks geometry. The provider and service
  now share one registry of the 26 regional offices listed by
  [nlrb.gov](https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices)
  (checked 2026-10-17), excluding subregional offices 11, 17, 24 and 26.
  State lists are corrected for Regions 20 (CA/HI), 21 (CA), 27 (CO/UT/WY),
  28 (Phoenix, AZ/NM/NV) and 32 (Oakland, CA/NV). The lists still approximate
  primary coverage with whole states; dissolved polygons overlap where regions
  share states and do not certify that every county is loaded. Exhaustive
  sub-state jurisdiction mapping is tracked in [#1713](https://github.com/siege-analytics/siege_utilities/issues/1713).
  Restore IA/KS/NE/OK coverage under Region 14 and AR under Region 15;
  remove WY from Region 19, leaving WY under Region 27 only. Coverage tests
  require all 50 states plus DC, PR and VI to resolve to a regional office.
  The command prints `stale_registry_rows=N` and the offending region numbers
  across all vintages without deleting any rows. See the BREAKING upgrade
  note below for existing databases. Historical subregional case prefixes
  roll up to verified parent offices through `NLRB_SUBREGIONS`.
  (#1585)

- Cache/output/config writers now publish complete files atomically so interrupted
  downloads, extractions and serialization cannot be served as valid cached data.
  `atomic_write_path` preserves umask-derived permissions and fsyncs before
  replacement, with best-effort directory fsync after replacement.
  `safe_file_write` and `safe_json_write` now use the atomic helper;
  `secure_write_text` atomically replaces credential/profile files with mode
  0600 throughout. Spark staged exports finish copying beside the destination
  before publication, preserving existing data on copy failures (#1509).

- Attach `BoundaryManager` to all boundary models so the documented
  `.objects.containing_point/nearest/for_state/for_year` API works. Distance
  filters on SRID-4326 geometry now cast to geography to honor meters, and
  GeoJSON output emits geometry objects instead of strings (#1570).

- NCES locale classification returns the published City/Suburb/Town/Rural
  codes instead of collapsing to -Small or recomputing distance subtypes.
  `from_census_year` now raises with the required population and principal-city
  sources instead of silently degrading; custom place population lookups use
  the full 7-digit GEOID to prevent cross-state PLACEFP collisions. (#1441)

- `CensusDataSource.fetch_geographic_boundaries` no longer reports success
  for a scope or vintage it did not serve. `context['served_year']` is always
  set, and the `census_year` column holds the served vintage (it was always
  null). `county_fips` now filters on `countyfp`. `aitsce`, `ttract` and
  `tbg` are filtered by state like the other national-only layers, and a
  state request against a national layer with no `statefp` column fails with
  `STATE_FILTER_UNAVAILABLE` and `context['state_filter_applied']=False`
  instead of returning the national file. The module-level
  `fetch_geographic_boundaries` forwards `county_fips` and
  `allow_nearest_year`; the module-level `get_geographic_boundaries` no longer
  passes `state_identifier` into the `county_fips` slot (#1482).
- TIGER URL construction: `anrc` always resolves to the Alaska file
  `tl_{year}_02_anrc.zip`; `concity` requires `state_fips`; `cd{n}` resolves
  to the `CD/` directory for the congress that vintage publishes
  (`YEAR_TO_CONGRESS[year]`, so `cd119` for 2024 works; other pairings stay
  "not available" instead of building a 404); `rails` is national
  (`tl_{year}_us_rails.zip`, flat `TIGER2010/RAILS/` in 2010); `submcd` uses
  the published `subbarrio` filename from 2013; the 403/429 fallback directory
  list names `COUSUB` and `ADDRFEAT` and drops the non-existent `COUNTYSUB`,
  `SDELM`, `SDSEC` and `SDUNI`. An opt-in `-m integration` test HEADs one
  built URL per catalog type for 2010, 2019 and 2023 (#1464).

### BREAKING

- `CensusDataSource.fetch_geographic_boundaries` (and the module-level
  wrapper) no longer substitutes the nearest published TIGER vintage. A
  request for an unpublished year now returns `success=False`,
  `error_code="VINTAGE_NOT_PUBLISHED"`, `error_stage="discovery"`, with
  `context['served_year']` naming the vintage that would have been used.
  The legacy `get_geographic_boundaries` therefore returns `None` for such a
  year. A year with no TIGER directory at all (for example 2006, 2007 or a
  future year) still fails earlier, with `error_code="INVALID_PARAMETERS"` at
  `error_stage="input_validation"`, as in 4.0.0. **Migration:** callers that
  can request a vintage Census has not published for that layer must handle
  both codes. Treat `VINTAGE_NOT_PUBLISHED` and `INVALID_PARAMETERS` as "not
  published" and skip or retry later, or pass `allow_nearest_year=True` and
  key the rows by `result.context['served_year']` (or the frame's
  `census_year` column), never by the requested year. Do not write one
  vintage's data under another vintage's year (#1482).
- A `state_fips` request for a national-only layer that has no state FIPS
  column (`cbsa`, `csa`, `metdiv`, `micro`, `necta`, `nectadiv`, `cnecta`,
  `aiannh` and similar) now fails with `STATE_FILTER_UNAVAILABLE`
  (`error_stage="configuration"`) instead of returning the whole national
  file. **Migration:** request these layers without `state_fips` and
  intersect spatially if a state subset is needed. This includes
  `populate_boundaries --type cbsa --state ...`. `county_fips` now filters
  and must be a 3-digit code with `state_fips`; a layer without a `countyfp`
  column fails with `COUNTY_FILTER_UNAVAILABLE` (#1482).
- `address_features`, `linear_water`, `area_water`, `roads` and `edges` are
  removed from `BOUNDARY_TYPE_CATALOG`, and `construct_download_url` raises
  `BoundaryConfigurationError` for them. Census publishes these only per
  county, so every URL the builder produced for them 404'd. **Migration:**
  download the per-county files directly
  (`tl_{year}_{state}{county}_linearwater.zip`, `areawater`, `roads`,
  `edges`, `addrfeat`) until county-level support lands. `anrc` with a
  `state_fips` other than `02`, and `concity` without `state_fips`, now raise
  `BoundaryConfigurationError`. `rails` with `state_fips` now fails with
  `STATE_FILTER_UNAVAILABLE` (the national file has no state column) instead
  of building a per-state URL that 404'd (#1464).
- `populate_demographics --variables all` stores every variable group. A
  group whose snapshot already exists is merged into it instead of being
  skipped, so income, education, housing and the other groups are no longer
  silently dropped after `total_population`. The Census API's `NAME` label is
  no longer stored in `DemographicSnapshot.values`. Census sentinels
  (`-666666666`, `-999999999` and other negatives), non-numeric values and
  out-of-range values become NULL in `total_population`,
  `median_household_income` and `median_age` instead of raising
  `IntegrityError` and rolling back the group load; the raw value stays in
  `values` (#1550).
- Bulk loaders now set the fields `save()` derives. Census boundaries get
  `feature_id`, `boundary_id` and `source`; NCES locale boundaries, school
  locations and timezones get `feature_id`/`source`; `DemographicSnapshot`
  rows get `total_population`, `median_household_income` and `median_age`.
  This repairs `classify_urbanicity`, `by_population()` and weighted rollups
  after `populate_demographics`. Each model exposes `prepare_for_bulk()`,
  which `save()` also calls, and `schemas_to_orm` returns prepared instances.
  Loaders that insert with `ignore_conflicts=True` now report the rows
  actually inserted. New `backfill_derived_fields` command repairs rows
  loaded before this fix (#1539).

### BREAKING

- `DemographicPopulationService.populate` (and `populate_demographics`,
  `populate_all_groups`) no longer skips an existing snapshot. Without
  `update_existing`/`--update` it merges in only the variables the snapshot
  lacks and counts it as `records_updated`; it counts `records_skipped` only
  when nothing new arrived. A group load that used to report `N skipped`
  now reports `N updated`. Variables a snapshot already holds are still
  overwritten only with `update_existing=True` (#1550).
- `DemographicSnapshot.total_population`, `median_household_income` and
  `median_age` are NULL when the source estimate is a negative Census
  sentinel or not numeric. Fractional estimates (for example rollup
  averages) are rounded to the nearest integer instead of truncated (#1550).
- `records_created` from the demographic, rollup, timeseries, crosswalk,
  NCES and timezone loaders and `populate_pl_demographics` counts only rows
  inserted: rows dropped by `ON CONFLICT DO NOTHING` (concurrent loads,
  repeated keys in a source file) are no longer included, so counts can drop.
  `BoundaryManager.bulk_create_from_geodataframe` returns only the objects
  actually inserted. Crosswalk `CrosswalkDataset.record_count` follows the
  corrected count (#1539).
- The derivations moved from the `save()` overrides into `prepare_for_bulk()`
  on `TemporalGeographicFeature` subclasses and `DemographicSnapshot`.
  `save()` behaves as before. Subclasses that overrode `save()` to change a
  derivation should override `prepare_for_bulk()` and end with
  `return super().prepare_for_bulk()` so bulk paths see the change too (#1539).
- **Upgrade:** rows loaded before this release keep empty `feature_id`,
  `boundary_id` and `source`, NULL summary columns and `values["NAME"]`.
  Nothing repairs them automatically. Run
  `python manage.py backfill_derived_fields --dry-run --strip-name` to see
  the counts, then the same command without `--dry-run` (#1539, #1550).
- `CrosswalkPopulationService.populate` (and `populate_crosswalks`) now loads
  crosswalks: it calls `get_crosswalk(geography_level=...)` instead of the
  nonexistent `geography_type=` keyword, which raised `TypeError` on every
  call. Weights are read from the client's `area_weight` column and stored
  as-is, so a 0.6/0.4 split stays 0.6/0.4 and a real 0.0 stays 0.0. A frame
  with no weight column returns an error result, and a row with a missing or
  NaN weight is reported in `errors`; neither is defaulted to 1.0. Two or more
  sources mapping to one target at full weight are classified `MERGED`. Level
  names are canonicalised through `resolve_geographic_level`, so block-group
  crosswalks are requested and stored as `block_group`; `populate_crosswalks
  --type` accepts `block_group` and keeps `blockgroup` as an alias (#1613).
- `DemographicRollupService.rollup` no longer overwrites a target snapshot
  that already holds the variable, and reports writes to existing snapshots
  in the new `RollupResult.records_updated` instead of `records_skipped`.
  Crosswalk mode maps crosswalk targets up to `target_level` (truncating the
  GEOID) instead of writing tract GEOIDs as county snapshots, uses only
  crosswalk rows whose `target_type` is the source level, and applies the
  crosswalk weight once: `sum` adds `value·w`, `avg` is `Σvalue·w / Σw`, and
  `weighted_avg` is `Σvalue·pop·w / Σpop·w`. Level names share the
  `block_group` vocabulary with the crosswalk loader, so block-group
  crosswalks are found. `coverage_ratio` counts expected children from the
  source-level boundary table (latest vintage <= `year`), or the crosswalk
  sources in crosswalk mode, so missing children lower it; when no boundaries
  are loaded it logs a warning and falls back to existing snapshots (#1604).

### BREAKING

- `DemographicRollupService.rollup` has a new `overwrite: bool = False`
  parameter, and by default it no longer replaces a value already present on
  the target snapshot (for example a county value fetched from the Census
  API). Callers that refreshed targets by re-running a rollup must pass
  `overwrite=True`; such writes are counted in `RollupResult.records_updated`.
  Crosswalk-mode `avg`/`weighted_avg` results change numerically (the weight
  was applied twice), and crosswalk-mode targets are now `target_level`
  GEOIDs; snapshots previously written with source-level GEOIDs under the
  target content type are wrong and should be deleted and recomputed (#1604).
- Block-group crosswalks are stored with `source_type`/`target_type`
  `"block_group"` instead of `"blockgroup"`. Rename existing rows, e.g.
  `TemporalCrosswalk.objects.filter(source_type="blockgroup").update(source_type="block_group", target_type="block_group")`.
  Any `TemporalCrosswalk` row written with weight 1.0 by an earlier version
  should be reloaded with `populate_crosswalks --update` (#1613).
- `[etter]` caps `pandas<3.0` like the other pandas-pulling extras; etter
  requires `geopandas>=1.1`, so an etter-only install could resolve pandas 3
  and hit #1365. The pyproject comments on the removed `streamlit`/`export`
  extras now say 3.24.0 (#1186), not v3.19, and the `all` comment lists the
  extras it leaves out (#1419).
- **Packaging:** the wheel ships only `siege_utilities`. 4.0.0 also installed
  a top-level `spikes` package at the site-packages root; package discovery is
  now `include = ["siege_utilities*"]`. The wheel now carries the files the
  library loads at runtime, which no published wheel had:
  `political/migrations/V*.sql` (so `political.schema_migrations_dir()`
  exists in an installed package) and `configs/**/*.yaml` (the default Hydra
  config dir, which `HydraConfigManager` raises on when absent). The CI
  `build` job runs `scripts/check_wheel_contents.py` on the built wheel and
  fails on any other top-level entry, a missing referenced data file, a member
  name containing whitespace (3.22.0 shipped two Finder `" 2.py"` copies) or
  bytecode. (#1420)

### BREAKING

- `groupby_agg` on PandasEngine, DuckDBEngine and PostGISEngine now keeps
  NULL-key groups (pandas `dropna=False`, matching SQL and SparkEngine);
  previously rows with a NULL group key were silently dropped, so totals
  could be short. The `sum` of a group with no non-null values is now NULL
  (NaN/NA), not 0.0; INVARIANTS.md is updated to match SQL/Spark. Callers
  that relied on 0.0 should `.fillna(0)` explicitly. `first`/`last` still
  differ between the pandas-backed engines and Spark (documented) (#1454).

- `DemographicSnapshot` and `DemographicTimeSeries` now use GEOID-native keys.
  The indexed `object_id` CharField is retained as the ORM/storage name and
  repurposed as GEOID-only; `geoid` is a read/write instance alias (also accepted
  by `create`). `content_type` is a plain FK. `content_object`, including
  `create(content_object=boundary)`, is deprecated for one release and will be
  removed in v4.2.0; it warns and now stores/resolves the boundary's GEOID, never
  its PK. Use `create(content_type=..., object_id=boundary.geoid)` and
  `get_boundary(vintage_year=...)`; omitted vintage selects the newest available
  boundary. Reverse access is `County.objects.filter(pk=...).snapshots()`.
  `by_population(..., dataset="acs5")` now scopes by content type and dataset and
  selects the newest data year when no year is specified. GFK-specific relation
  introspection/prefetch APIs no longer apply. (#1560)

- `ConfigurationMigrator.migrate_user_profile` and `migrate_client_profile`
  in both `config.enhanced_config` and `config.migration` now propagate file,
  YAML/JSON and validation errors; missing files raise `FileNotFoundError`.
  `migrate_all_configurations` records user failures in `user_profile.error`
  while continuing independent client migrations. `UserConfigManager.export_config`
  and `import_config` propagate file/YAML errors, including failed persistence
  of an imported profile (#1532).
- Direct `NCESLocaleClassifier` classification raises `ValueError` for missing
  or unparseable place/UA populations. `get_census_boundaries` raises
  `ValueError` for invalid state identifiers or missing state FIPS columns.
  `VariableRegistry.get_variable_metadata` raises `LookupError` for a 404,
  transport/HTTP errors for request failures, and `ValueError` for malformed
  JSON/metadata. The public `CensusAPIClient.get_variable_metadata` and
  `CensusAPI.get_variable_metadata` wrappers propagate these failures too.
  These calls no longer return defaults or unknown labels (#1532).
- `ChartGenerator.create_bar_chart`, `create_line_chart`, `create_pie_chart`,
  `create_proportional_text_bar_chart` and `create_heatmap_text_chart` raise
  `RuntimeError` on rendering errors instead of returning error placeholders.
  `read_features` and `extract_attributes_swmaps` raise `sqlite3.DatabaseError`
  for failed joins when either attribute table exists. Only when neither table
  exists do they yield empty attributes or honor the documented missing policy (#1532).
- `SpatialDataTransformer`, `PostGISConnector` and `DuckDBConnector` propagate
  user-configuration failures. `PostGISConnector` raises for missing connection
  settings/dependencies and uses `ConnectionError` for connection failures.
  `classify_series` raises `RuntimeError` when mapclassify fails rather than
  changing algorithms; CRS normalization (including `detect_crs`) raises for
  invalid CRS input or missing pyproj (#1532).
- `TimezonePopulationService` raises `ValueError` and stops population at the
  first unresolved timezone ID;
  `load_gadm_boundaries` raises `RuntimeError` when staged data cannot be read;
  `codify_area` raises on default-geocoder construction failure. NLRB
  `NLRBDatagovClient.fetch_cases`, `NLRBLabordataClient.fetch_cases` and
  `NLRBNxGenClient.fetch_case` raise `RuntimeError` on the listed HTTP/XML
  failures. `NLRBNxGenClient.fetch_case` also raises on result parsing failures,
  and `NLRBDataClient.fetch_all` aborts when any source fails.
  `setup_distributed_environment` raises `RuntimeError` on HDFS sync
  failure instead of returning a local path (#1532).

- The public `NLRB_REGIONS` registry removes keys 11, 17, 24 and 26 because
  these are subregional offices, not regional offices. Direct dictionary
  callers must use the parent regional keys. `assign_region` and
  `region_summary` now roll historical prefixes up through
  `NLRB_SUBREGIONS = {11: 10, 17: 14, 24: 12, 26: 15, 30: 18, 37: 20}`;
  summaries combine their counts under the parent office. Unverified prefixes
  33, 34 and 36 remain unmapped and report office `"Unknown"`.
  Upgrade existing NLRB tables by re-running `populate_nlrb_regions --update`
  (with `--year` for each stored vintage) to refresh regional metadata, then
  manually delete rows whose `region_number` is 11, 17, 24 or 26. The command
  only reports stale rows; it does not delete them. (#1585)

- `NCESLocaleClassifier.from_census_year` now raises instead of approximating
  missing population and principal-city inputs. Use `from_nces_boundaries` or
  supply authoritative data to the direct constructor, with place populations
  keyed by 7-digit GEOID. NCES point lookups outside published coverage now
  raise instead of assigning an inferred rural code. (#1441)
- Non-secret data files written by `atomic_write_path` now use `0666 & ~umask`
  (0644 with umask 022), including replacement of previously owner-only data
  exports. Consumers that relied on the old accidental 0600 mode should use
  umask 077. Credential/token/config exports using `secure_write_text` remain
  0600 and are not routed through this helper. `atomic_write_path` and
  `secure_write_text` replace final-component symlinks rather than following
  them; the referenced file is left unchanged (#1509).

- `BoundaryQuerySet.geojson()` and `BoundaryWithDemographicsSerializer.get_geometry`
  now return GeoJSON geometry objects (dicts) instead of JSON strings. A consumer
  that applied `json.loads()` to the geometry value must drop it; the value is
  already a `dict`. (#1570)
- Facebook, Instagram, X/Twitter, Google Analytics and connection profile helpers
  now default to `~/.siege_utilities/<service>/` instead of CWD-relative `config/`.
  Matching loaders/listers use the same new default. Pass `config_directory="config"`
  explicitly to retain the old location; existing profiles are not migrated.
  `create_temporary_service_account_file` must now be used as a context manager;
  its returned path is valid only inside the `with` block. (#1541)
- `select_vintage_for_cycle` now selects `CENSUS_2010` for the 2012-2020
  election cycles (years 2012 through 2021), correcting the decade-off
  block/tract GEOIDs. The `CURRENT` tier starts at 2022 and currently supplies
  2020 Census blocks; pre-2012 years retain the documented `CENSUS_2010`
  fallback because 2000 geography is not offered. Re-geocode affected cycle
  results before joining them to 2010-based block-assignment or district
  files. (#1498)

- Config passwords, tokens, client secrets and API keys now use Pydantic
  `SecretStr`, including the API keys on `User` and `postgresql_connection`
  on `EnhancedUserProfile` and `User`. Consumers must call
  `.get_secret_value()` when passing these values to clients or string APIs.
  `UserConfigManager.get_database_connection()` and explicit YAML persistence
  continue to return or store the real values. (#1552)

- `populate_boundaries`, `populate_demographics`, `populate_crosswalks`,
  `populate_timezones`, `populate_nlrb_regions`, `populate_nces`, and
  `classify_urbanicity` now exit non-zero when a load reports errors, after
  printing the existing details and summaries. Use `--allow-partial` to retain
  tolerant behavior when at least one record was created, updated, or classified;
  errors with nothing loaded still fail. Multi-result runs count successful
  records across all requested types, groups, or actions. (#1533)

- CredentialManager Keychain reads now skip every field other than `password`,
  including `secret`; writes of other fields raise `ValueError`. Use environment
  variables, service-scoped files, or 1Password for distinct `secret`, OAuth, and
  service-account fields.
  1Password retrieval raises on every nonzero exit, including exit 1, because
  absence cannot be distinguished safely from authentication or server failure.
  Supply the exact item title or ID for both reads and writes; failed reads no
  longer try title variants or fall through to other backends. Stores refuse
  legacy title variations with guidance to use the exact title or ID, rather
  than editing an item that retrieval cannot resolve. (#1513)
- Credential resolution now defaults to env -> 1Password -> service-scoped
  files -> Keychain -> prompt. Unscoped credential files are no longer searched.
  Move files to a service directory (for example `postgres/password.txt`) or
  use a service-prefixed filename such as `postgres_password.txt`; set
  `backend_priority` explicitly to change backend precedence. (#1402)
- 1Password updates refuse all Login items because CLI JSON cannot establish
  passkey absence and template edits can delete passkeys. Missing/unknown
  categories, SSH Key/Document items, attachments, and passkey/SSHKEY/OTP/TOTP/file
  fields are also refused with `SiegeConfigError`. Use the 1Password app for
  these edits. New items use API Credential so password rotation stays editable;
  existing Login items still require the app.
  Other edits preserve the full item JSON and verify the saved field before
  reporting success; failed persistence checks raise `SiegeConfigError`. (#1402)
- `populate_demographics --api-key` is rejected without echoing its value.
  Set `CENSUS_API_KEY` in the environment instead. (#1402)
- `scripts/release_manager.py --token` is rejected without echoing its value.
  Set `PYPI_API_TOKEN` in the environment for CLI uploads and releases. (#1402)
- `UserConfigManager` now creates configuration directories with mode 0700
  and atomically saves `user_config.yaml` with mode 0600, including when
  replacing an existing file. The temporary fallback moves from
  `$TMPDIR/siege_utilities/config` (or `/tmp/siege_utilities/config`) to
  `tempfile.gettempdir()/siege_utilities-<uid>`. Pre-existing fallback paths
  that are symlinks, are not directories, belong to another uid, or are
  group/other-writable are rejected with `ValueError` before loading or
  saving credentials, even if passed explicitly as `config_dir` (including
  aliases of the predictable temp path). Shared config directories lose
  group/other access; use a private `SIEGE_USER_CONFIG_DIR` if the fallback
  is unsafe. Old
  fallback files are not migrated or trusted automatically. Platforms without
  a POSIX uid use per-user Windows LocalAppData/AppData instead of shared temp;
  Windows file privacy depends on the user's inherited ACLs, not POSIX chmod.
  (#1452)
- `UserConfigManager.export_config()` no longer writes `postgresql_connection`
  or `duckdb_path` (in addition to the three API keys), and writes the export
  atomically at mode 0600 on POSIX. Exports are no longer a way to copy the
  database DSN between machines; set it again with `set_database_connection`.
  (#1452)
- `Person.from_yaml` and `import_entities` now reject imported string values
  containing `***REDACTED***` (including nested mapping/list values and
  scrubbed URLs), rather than restoring those placeholders as credentials.
  The redaction guard does not inspect mapping keys. `exclude_sensitive=True`
  exports write `***REDACTED***` for redacted fields; use an unredacted export
  for restoration. These input values were previously accepted. (#1460)
- `safe_join_paths` now confines a joined path to its resolved first component
  by default and rejects later absolute, rooted, or drive-qualified components
  (including Windows forms). Joins that previously escaped this boundary now
  raise `PathSecurityError`. Pass a trusted `base_directory` to override the
  containment boundary; it is not prepended to path components. (#1528)

- RDH (#1571). Callers of these functions need to be checked, including
  electinfo `spark_jobs/geo/spatial_fetch_rdh.py`:
  - `fetch_cvap` and `fetch_pl94171` raise `FileNotFoundError`, listing the
    available titles, when no dataset is at the requested geography. Before,
    they loaded `datasets[0]`, and with a single dataset they skipped the
    filter. Pass the level you want, or `geography=None` to take the first
    listed dataset unfiltered.
  - `RDHClient.load_csv` reads `GEOID*`, `*FP`, `*CE` and `*NS` columns as
    `str` unless you pass `dtype`. Code that compared or joined these columns
    as integers needs string keys, or `dtype={...}` to opt out.
  - `load_csv` and `load_shapefile` raise `ValueError` for a directory with
    more than one CSV or `.shp`. Load the member you want by path.
  - `download_dataset` returns the extracted directory on a cache hit for a
    ZIP, where it used to return the `.zip` path. `gpd.read_file` and
    `load_*` accept the directory.
  - `RDHLoaderService.load_cvap_for_plan` takes `geography` (default
    `"tract"`), which is passed to `fetch_cvap`. If no district matches,
    the result now has an error and `success` is False; before, it returned
    success with 0 updated. Unmatched districts are counted in
    `records_skipped`, and a partial match adds a warning. Pass the CVAP
    level whose GEOIDs equal your plan's district GEOIDs.

### Security

- Credential files are written with mode 0600 before writing their payload,
  including existing files, with no write-then-chmod race. Missing parent
  directories are created with mode 0700. Profile defaults use per-user paths;
  service-account key files are always deleted on context exit. Non-Spark
  boundary staging uses a private random temporary directory and returns/logs
  its actual local path, with no predictable `/tmp` path or false S3 report.
  A blocking AST guard rejects unsafe credential writes, write-then-chmod and
  unlisted fixed `/tmp/` literals. Also secured configuration/entity YAML
  exports and database configuration writes; the latter retain the legacy
  CWD-relative `config/` default, so shared-host callers should explicitly
  choose a private per-user directory. (#1541)

- Config secret fields no longer expose their values in model `repr`/`str`
  or those models' validation error messages, including nested validation
  failures on `Person` and `ClientProfile`. Legacy dataclass API keys and
  PostgreSQL connection strings are omitted from repr. A CI AST class guard
  rejects secret-, connection- and DSN-named plain string fields without
  `repr=False`, and treats string defaults as values, not annotations. (#1552)
- `stage_boundaries_s3` rejects removed `--access-key` and `--secret-key`
  options without echoing their values, for both spaced and equals forms.
  Parser errors also redact underscore spellings and values with whitespace.
  Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` or use a boto3 profile.
  CI checks every management command parser for non-None credential defaults,
  including access and private keys. The required test matrix scans the
  published package for credential literals. (#1578)
- Closed OData filter injection in Dynamics list filters with shared string
  literal escaping for scalar filters and batch alternate keys. Zoho criteria
  now escapes backslashes and parentheses while preserving quote escaping.
  Batch alternate-key literals are percent-encoded after OData escaping to
  prevent encoded quotes, fragments, spaces, and CR/LF from changing the inner
  request URI or headers. Structured Dynamics, Zoho COQL, and Salesforce SOQL
  builders reject invalid identifiers with `ValueError`; Salesforce and Zoho
  fields allow dotted relationship paths and custom-field suffixes.
  (#1418)
- Escape report data in Paragraph text, Folium popup HTML, and IDML XML.
  Closes stored XSS in saved Folium maps and fixes report/IDML crashes on
  `& < > "` while preserving intentional markup. (#1565)
- For the planned 4.1.0 release, SSL failures now raise instead of silently
  retrying with `verify=False`. The optional `download_file` parameter
  `allow_insecure_fallback=False` is allowlisted in the API contract gate as
  a backward-compatible addition. Verified downloads honor `REQUESTS_CA_BUNDLE`,
  then `CURL_CA_BUNDLE`, before platform defaults. TIGER, government dataset,
  and NCES downloads honor `SIEGE_INSECURE_SSL` as an explicit opt-in with
  ERROR logging; warning suppression is limited to individual unverified
  discovery requests. (#1456)
- Credential prompts hide all fields except `client_id`, `client_email`,
  `project_id`, and `username`. Backend availability probes time out after five
  seconds, log the timeout without command output, and mark the backend
  unavailable. CredentialManager no longer loads user configuration for the
  nonexistent `credential_paths` attribute; pass paths to the constructor. (#1513)
- Path validation permits data inside a cwd or base at or below `/root` while
  keeping root's `.aws`, `.netrc`, `.kube`, `.docker`, `.pgpass`,
  `.git-credentials`, and `.config/gcloud` locations blocked. Both file and
  shell validation explicitly block `/etc/shadow-`, `/etc/gshadow`,
  `/etc/gshadow-`, and `/etc/passwd-`. (#1528)
- HTTP diagnostics redact complete query secrets containing encoded delimiters
  or punctuation. Nested URLs are decoded up to a fixed limit before their
  secrets are removed, with excessive encoding redacted in full. The credential
  URL guard also checks positional requests.get params, Request construction,
  setdefault, and in-place dictionary merges. Userinfo matching avoids quadratic
  scans of long alphanumeric runs. The guard follows params forwarded through
  kwargs and positional Session.request calls. (#1400)
- PyPI uploads pass credentials through the child environment and capture
  diagnostics. `run_command` and `run_subprocess` log status only, omitting all
  arguments and output rather than guessing which values are secrets. Their
  exceptions retain failure types and timeout/errno information without raw
  command details or output; returned output remains available to callers. (#1402)
- `exclude_sensitive=True` now recursively redacts credentials across live
  models, subclass fields, nested dataclasses and plain objects, dictionaries
  and lists. YAML exports use safe mappings instead of Python-object tags.
  One shared `SECRET_FIELD_NAME` classifier covers both config field names and
  URL query/fragment keys, with a provider-signature alias floor. URL userinfo,
  nested percent-encoded redirect passwords and secret query values are
  scrubbed without discarding benign URL context; decoding is bounded and
  fails closed. JSON-encoded strings still need an explicit sensitive marker
  or structured dictionary fields to redact secrets by name. (#1460)
- File-path validation rejects actual `..` components, sensitive targets and
  symlink escapes under an explicit base, while allowing benign embedded dots,
  literal percent sequences, and non-sensitive names such as `paid_rsa`.
  `/dev/shm` and standard pseudo-devices remain usable; root-in-container
  workflows have a documented `/root` cwd/base carve-out, with other listed
  sensitive files still blocked. Without a trusted `base_directory`, the
  blocklist is a guardrail, not a sandbox; filesystem changes after validation
  remain outside this check. (#1528)

## [4.0.0] - 2026-10-11

Major release. The public surface changes incompatibly (the data.world
connector and its exports are removed, and several packaging extras changed),
so this supersedes the 3.24.0 in-repo version and bumps the major per Semantic
Versioning. 3.24.0 was never tagged or uploaded to PyPI, but a 3.24.0 wheel is
on Nexus (#1401).

### BREAKING

- **Removed the data.world connector** (`siege_utilities.analytics.datadotworld_connector`
  and its exports: `DataDotWorldConnector`, `get_datadotworld_connector`,
  `search_datadotworld_datasets`, `load_datadotworld_dataset`,
  `query_datadotworld_dataset`, `search_datasets`, `list_datasets`,
  `DATADOTWORLD_AVAILABLE`). The upstream open-source `datadotworld` product was
  discontinued, so the connector is removed rather than repaired. The
  `datadotworld` dependency is dropped from the `analytics` extra. Code importing
  these symbols must remove those imports. (C15/C16, #1358.)

### Added

- Dual-source Census retrieval framework with provenance. A `CensusDataSource`
  protocol abstracts a source; `ApiSource` wraps the Census API and exposes an
  exhausted-timeout cause so the fallback policy recognizes it;
  `DualSourceCensusClient` retries the primary on configured errors (rate limit,
  timeout) up to a budget, then tries the secondary once, recording per-request
  `Provenance` (source, location, attempts, degraded). If both sources fail the
  last error propagates rather than returning an empty frame. `AlternationPolicy`
  is pure, validated configuration. (#1375.)
- ACS table-based Summary File bulk source (`BulkFileSource`), the secondary for
  the dual-source client: streamed per-table caching, geography filtering, API
  variable names, numeric estimates and MOEs, sentinel normalization, and
  fallback provenance. Malformed records (width drift, embedded control bytes,
  duplicate or BOM-masked headers, quoted delimiters, non-finite tokens) raise
  rather than returning misaligned or NaN data. Geographic name enrichment is
  deferred; bulk `NAME` values are missing. (#1385.)
- First-class yearless Census timeseries support. `CensusCatalogPopulator.populate`
  accepts `year=None` to discover a Census timeseries dataset, building
  `{base}/timeseries/<program>/<dataset>/` variables and groups with no injected
  year; a `_TIMESERIES_PATHS` alias registry maps names like `eits/resconst`.
  `CensusCatalogDataset.year` becomes `int` or `None` and gains
  `timeseries_variables` and `timeseries_groups`, retained through the disk-cache
  round trip. Year-based discovery is unchanged and builds byte-identical URLs.
  (#1374.)
- Python 3.13 is now a blocking CI gate (previously allowed to fail). The full
  Linux suite passes on 3.13. Python 3.14 is tested as a non-blocking CI gate
  while its recently released native stack stabilizes. (#1365.)

### Changed

- Capped `pandas>=2.0.0,<3.0` across every extra that declares pandas (data,
  geo, reporting, analytics, survey, all; geo pins it explicitly because
  geopandas pulls pandas transitively). pandas 3.0 makes
  the default string dtype Arrow-backed, so `.str` operations dispatch into
  `pyarrow.compute` and segfault on 3.13 with the current native stack. The cap
  keeps strings on the stable backend; lift it once pandas 3.x + pyarrow string
  interop is verified green on the CI matrix. (#1365.)

### Fixed

- Docstring hygiene tool works on Python 3.14: it matches `ast.Constant` instead
  of the removed `ast.Str` alias, and renders rewritten source with stdlib
  `ast.unparse` rather than the unmaintained `astor` (which still reached for
  `ast.Str` when rendering f-strings and raised `AttributeError` on 3.14). The
  `astor` dependency is dropped from the dev extra (#1365).
- EPSG:2163 round-trip property test compares the minimal angular longitude
  difference, so the antimeridian (lon 180 emitted as -180 by newer PROJ) is no
  longer read as a 360-degree drift (#1365).

- Engine aggregation set honors advertised `stddev`/`variance` on the
  pandas-family engines (C17, #1359).
- Boundary normalization raises instead of silently returning un-normalized data
  on crosswalk failure (C3, #1351).
- Census sample datasets are flagged unavailable instead of advertised as working
  (C9/C10, #1360).
- `spark_to_geopandas` rejects a mixed-CRS metadata column instead of silently
  unifying it (C6, #1354).
- Snowflake connector is enabled on an installed SDK and its config-file factory
  works (C13/C14, #1357).
- DuckDB engine `query()` returns an eager, materialized frame with stable
  snapshot and lifetime semantics, converts native GEOMETRY to WKB by column
  position for every result-producing statement (including DML `RETURNING`),
  loads the spatial extension only when a result carries geometry so ordinary
  SQL runs under a restricted configuration, preserves DML affected-row counts,
  and matches prepared-statement names on engine token boundaries with a binary
  collation (#1369).
- Crosswalk intensive variables area-weight by true overlap area with
  real-tobler parity, exclude missing values per variable, treat zero-overlap
  sources as non-contributing instead of a false merge rejection, and areal
  interpolation leaves a no-valid-contributor target undefined rather than
  fabricating `0.0` (#1369).
- Census catalog rejects a dataset-path base URL keyed to the Census API host
  with percent-decoded path validation, so an arbitrary proxy prefix is accepted
  while a real dataset endpoint is rejected (#1369).
- DuckDB engine `read_spatial` is robust across DuckDB spatial 1.4.x and 1.5.x:
  geometry columns are identified by scalar type (bare `GEOMETRY` or
  `GEOMETRY(<crs>)`, never a `GEOMETRY[...]` collection), the scan is bound with
  collision-proof positional aliases so a property named `geom` no longer breaks
  the `SELECT *` bind on 1.5.x, and the driver-injected `OGC_FID` column that
  1.5.x emits is dropped so the output schema matches 1.4.x. Metadata-read
  failures propagate rather than silently changing the schema (#1380).

### Documentation

- Added [docs/EXPANDING_THE_LIBRARY.md](docs/EXPANDING_THE_LIBRARY.md), a
  contributor guide for adding an optional extra, a `DataFrameEngine` backend, a
  lazily-imported symbol, a provider, or a governed notebook, and linked it from
  the architecture and developer guides. It records the engine, geo, and census
  extension contracts hardened in #1369 and the Python and pandas version-support
  policy (#1369).

## [3.24.0] - 2026-09-12

Scope note: this release covers everything promoted to `main` since the
`v3.23.0` tag, including the 2026-09-12 develop→main promotion in #1257.
That promotion brought the public API, notebook governance/runtime,
geocoding contract, Parsons spike, lint-ratchet, and CI hardening work that
had landed on `develop` through #1256. The original release motivators remain
#1115/#1121 (RDH auth failure surfaced instead of empty datasets) and #1117
(`UserConfigManager` no longer crashes under unwritable `HOME`). Issue #1222
tracks final tag/publish/post-publish verification; no tag or PyPI publish is
implied by this changelog/version bump PR.


### Shelf alignment (2026-08-27 modernization session)

- **CI job `griffe api-diff (writing-releases:1)` (added in PR #1191) is now the reference implementation** cited by `claude-configs-public` writing-releases:1 as the tool-agnostic optional mechanical assist for signature-level BREAKING detection (see claude-configs-public#646). Behavior changes that preserve signatures (e.g., a validator becoming stricter) remain operator-judgment per the rule; a green griffe run is not evidence of non-BREAKING.
- **CRS round-trip property tests (added in PR #1193)** are consistent with the strengthened `_property-testing-rules.md` guidance for data-heavy libraries (claude-configs-public#646), which now flags "hypothesis-in-dev-extras-but-few-property-tests" as a coverage-debt signal. siege_utilities' `tests/property/` directory has 8 files post-#1193 covering grid, join, filter, read, spatial-join, to-geodataframe, engine-invariants, and CRS round-trip.
- **DRF serializers audited against the new `_django-rest-framework-rules.md` shelf (claude-configs-public#651, merged to main via #652).** `siege_utilities/geo/django/serializers/boundary_serializers.py` — the library's only DRF surface — is already compliant: every serializer uses an explicit `fields = [...]` allowlist (never `"__all__"`), `read_only_fields` is used for immutable timestamps, no `Meta.depth` (which the shelf forbids for real APIs), and `rest_framework_gis.GeoFeatureModelSerializer` is used with a graceful fallback to `ModelSerializer` when the extra is absent. Zero new violations introduced by the new shelf; documented here so future contributors know the DRF rules apply.

### Shelf additions (2026-08-28)

- `_react-rules.md` + `skills/react/` — new shelf domain, currently no library consumers (siege_utilities has no React frontend). Referenced here for future contributors who add browser-facing surfaces (e.g., embedded Streamlit alternatives, notebook widgets).
- `_django-rest-framework-rules.md` + `skills/django-rest-framework/` — new shelf domain, applies to `siege_utilities/geo/django/serializers/boundary_serializers.py` and any future DRF work.

### Removed

- **BREAKING (packaging):** the `[streamlit]` extra (streamlit + altair + bokeh
  + pydeck + ipywidgets + jupyter + notebook) is removed. No library code ever
  imported streamlit, altair, bokeh, or ipywidgets — the extra added 7 packages
  of ecosystem infrastructure without any siege_utilities-specific consumer.
  Users needing streamlit can `pip install streamlit altair bokeh` directly.
  Verified: `grep -rn "import streamlit\|from streamlit" siege_utilities/
  --include="*.py"` returns 0 matches. Closes #1180.
- **BREAKING (packaging):** the `[export]` extra (openpyxl + xlsxwriter + psutil
  + memory-profiler) is removed. No library code imported any of these — pandas
  reaches openpyxl transitively when needed, and xlsxwriter / psutil /
  memory-profiler had zero library-side consumers. Verified: `grep -rn
  "import xlsxwriter\|import psutil\|import memory_profiler"
  siege_utilities/ --include="*.py"` returns 0 matches. Closes #1179.

### Changed

- **BREAKING (packaging):** the native GDAL/OGR Python bindings (`gdal`) are now
  a dedicated optional `[gdal]` extra and are no longer pulled in by `[geo]` or
  `[all]`. The OSGeo `gdal` wheel requires a matching system `libgdal` +
  `gdal-config` and must be pinned to the installed libgdal version, which is
  unavailable on Databricks / Lambda / serverless and on CI jobs that exercise
  the documented no-GDAL path. The pure-Python geo path
  (geopandas/shapely/pyproj/fiona, bundled-GDAL wheels) continues to work via
  `[geo]` with no system GDAL. To install the native OSGeo bindings, pin to your
  system libgdal — the path CI exercises (a bare `[geo,gdal]` resolves the newest
  `gdal` in `>=3.6,<4` and fails to build against an older libgdal):

  ```bash
  pip install siege-utilities[geo]
  pip install "gdal==$(gdal-config --version)"
  ```

### Fixed

- The Django test settings and the GeoDjango-availability guards in nine test
  files now degrade cleanly when the GDAL shared library is absent **without**
  swallowing unrelated errors. `django.contrib.gis.gdal` raises
  `ImproperlyConfigured` ("Could not find the GDAL library") — not
  `ImportError`/`RuntimeError` — so the original guards aborted on no-GDAL
  runners; a subsequent broad `except Exception` over-corrected and would have
  hidden a real Django/GIS misconfiguration. The guards now catch exactly
  `(ImproperlyConfigured, ImportError, OSError)` (plus `RuntimeError` in the test
  guards), so a real misconfig surfaces loudly (writing-code:7).
- **`siege_geo` migration 0006 no longer re-adds `RedistrictingPlan.state`, which broke a fresh `migrate` with `DuplicateColumn`.**
  Migration 0005 already adds `redistrictingplan.state` (identical `ForeignKey` definition); 0006 added it a second time. On an already-migrated database the second `AddField` was a no-op, but on a fresh database (CI, new deploys) it ran `ALTER TABLE siege_geo_redistrictingplan ADD COLUMN state_id` on a column 0005 had just created, aborting the whole migration graph. `state` is now owned solely by 0005; 0006 keeps its four genuinely-new fields (`effective_from`, `effective_to`, `superseded_by`, `court_case`). Model state is unchanged. A new static guard `tests/test_geo_migration_graph.py` fails if any `(model, field)` is `AddField`-ed twice without an intervening removal, so this bug class cannot recur.

## [3.23.0] - 2026-06-19

Tag `v3.23.0` (`09bd9cac`, on `main`). Uploaded to PyPI 2026-06-20. The
Nexus wheel with this version number is not this tag (#1401).

- Fixes from a hostile review: the lazy loader distinguishes a missing
  dependency from an internal import bug (#1041); dead `shell=True`
  subprocess helper removed (#1042); the GA connector raises on missing
  credentials (#1043); `RDHProvider` raises `BoundaryFetchError` instead of
  returning `None` (#1044); overlay registry constructor errors propagate
  (#1045); reporting raises on missing ReportLab (#1046); `quote_ident`
  docstring corrected (#1047); config fallbacks log warnings (#1048).
- Packaging: `exclude-package-data` for Finder `" 2.py"` copies (#1049). It
  filters data files only, not modules; see #1420.
- CI: the `build` and `release` jobs no longer depend on the test jobs.
  Since #1419, publishing waits for the full CI run on the tag.

## [3.22.1] - 2026-06-04

Tag `v3.22.1` (`4ce78f52`, on `main`). Uploaded to PyPI 2026-06-20.

- `dir(siege_utilities)` no longer raises `NameError`, and the `connectors`
  package is registered in the lazy-import table (#1038).

## [3.22.0] - 2026-06-03

Tag `v3.22.0` (`a53f5cf1`, on `main`). Uploaded to PyPI 2026-06-04. The
wheel contains two Finder duplicates,
`examples/enhanced_features_demo 2.py` and
`geo/django/migrations/0010_seat_state_constraint 2.py` (#1420).

- New `connectors/` package (`ConnectorProtocol`, `UpsertResult`,
  `UpsertError`) (#1011); HubSpot, Zoho and Dynamics OAuth providers (#1014).
- Geo: GST geocoding helpers (#515), IRS SOI files (#539), DuckDB and Shapely
  areal-interpolation backends (#986), pure-numpy choropleth classification
  (#987), `from_geodataframe()` and `engine=` on boundary providers (#988).
- Fixes: HTTP session lifecycle (#979), CRS agreement before spatial joins
  (#976), equal-area compactness (#975), atomic file writes (#978).

## [3.21.0] - 2026-06-01

Tag `v3.21.0` (`7764b35d`, on `main`). **Not published to PyPI** and has no
GitHub release; a wheel exists on Nexus only (#1419). See RELEASING.md.

- Architectural principles codified and the developer docs aligned (#953,
  #955).
- SU-1/SU-2 sweep: return-empty-on-error removed in config, distributed,
  files, survey, geo providers and examples (#959-#961); `__all__` added
  across the package; star imports converted to lazy loading (#962);
  credential files written `0o600` (#950); large HTTP downloads streamed with
  a size cap (#910).

## [3.20.0] - 2026-05-30

Tag `v3.20.0` (`bd187ce4`, on `main`). Uploaded to PyPI 2026-06-20.

- **BREAKING:** functions in analytics, config, data/statistics, distributed,
  files, geo and reporting that returned empty results on failure now raise
  (SU-1). Callers that tested for an empty DataFrame, `{}`, `None` or `False`
  need exception handling instead.
- `__all__` completeness and annotation fixes (SU-2); `examples/` held to
  library standards (SU-3); `raise ... from e` throughout.

## [3.19.0] - 2026-05-28

Tag `v3.19.0` points at `75c8125f`, a version-string-only commit made on
2026-06-19 on top of `main`@`13a2653f` (2026-05-28); `75c8125f` is not on
`main`. Uploaded to PyPI 2026-06-20 from that commit. See RELEASING.md.

- Census table catalog with caching and search; `VARIABLE_GROUPS`
  deprecated in favour of `CensusCatalog` (SU#601-606).
- Place history with seats, demographics, urbanicity and events overlays
  (SU#607-612); NCES urbanicity batch classification (SU#615-616); NLRB
  clients and models (SU#617-621).
- Batch geocoding with Census, Nominatim and TAMU backends and fallback
  chaining (SU#622-626); codification pipeline (SU#627-632); Redistricting
  Data Hub catalog, plan lifecycle and precinct-to-VTD reconciliation
  (SU#633-636).
- Hostile-review fixes: SQL-injection and credential-exposure surfaces
  closed, silent `except: pass` sites narrowed (SU#558-761).

## [3.18.0] - 2026-05-26

Tag `v3.18.0` (`6eec45d9`, on `main`). Uploaded to PyPI 2026-06-20.

- Identifiers, schema `MigrationRunner`, the `political` namespace and its
  SQL migrations (#381). No wheel shipped those SQL files until #1420.
- Geo boundary models: TribalArea, CountySubdivision, PUMA and special
  districts (SU#535, SU#551); `RedistrictingPlan.plan_status` (SU#552);
  migrations 0006-0009.
- `detect_crs` and axis-order-aware `reproject_geom` (SU#546), format
  detection (SU#545), `.swmz` reader (SU#547); QCEW and NCES file lifts
  (SU#533, SU#534); Trino federation and OSS Unity Catalog external tables
  (#521).

## [3.17.2] - 2026-05-14

Patch release: hydra is an optional extra; importing siege_utilities without it must not emit a misleading "Pydantic config system" warning. Closes #498.

### Fixed

- **Hydra absence no longer surfaces as "Could not import Pydantic config system"** (#498).
  `siege_utilities/config/__init__.py` had `from .hydra_manager import HydraConfigManager` inside the pydantic try block. When hydra was absent, the whole block failed and emitted a WARNING blaming pydantic. The eager hydra-manager import is now in its own narrow try/except; hydra absence drops to DEBUG (it's an optional `[config-extras]` extra), and the dependency wrapper cites `hydra-core` / `omegaconf` rather than `pydantic` when the consumer tries to use `HydraConfigManager`.

  writing-code:8 (conditional-import callsite hygiene) territory. Three regression tests in `tests/test_config_hydra_optional.py` pin the new behavior.

## [3.17.1] - 2026-05-14

Patch release: package-hygiene fix surfaced by the v3.17.0 consumer-side verification (proposed claude-configs-public writing-releases:5).

### Fixed

- **`scripts/`, `tests/`, `docs/` no longer ship to `site-packages` root** (#496):
  setuptools `find_packages(include=["*"])` was matching every directory
  containing `.py` files at the repo root. `pip install siege-utilities`
  was installing `site-packages/scripts/` as a top-level package, polluting
  every downstream venv (a user could `from scripts import release_manager`
  and collide with their own top-level `scripts/` package). Pre-existing
  in v3.16.0 and earlier; v3.17.0 added `check_unbounded_io.py` to the
  polluted namespace.

  Fix: explicit `exclude` in `[tool.setuptools.packages.find]` for
  `scripts*`, `tests*`, `docs*`. Wheel verified post-fix: zero matches
  for those prefixes.

  Surfaced by the v3.17.0 consumer-side verification per the proposed
  writing-releases:5 rule: source-side green (25 CI jobs pass; twine
  check pass; scanner clean) but two real consumer-side bugs reached
  PyPI. Recurrence 3 of LESSON 323a0f5 family in the rule's originating
  arc.

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
