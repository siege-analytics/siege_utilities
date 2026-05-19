# siege_utilities — Notebook system

**Status:** Complete (ELE-2456 shipped 2026-04-24 across PRs #418 / #419 / #420 / #421).

## Shape

17 canonical notebooks across 5 themed folders. Every notebook is a capability
showcase, not an API tour: one user intent, 10–15 cells, one coherent
deliverable. Structural rules are enforced by `tests/test_notebook_hygiene.py`
(102 checks at time of writing).

```
notebooks/
  foundations/   config, profiles, branding
  spatial/       boundaries, geocoding, maps, joins, redistricting, GeoDjango
  reports/       charts+PDF, slides (PPTX + Google), polling/survey
  analytics/     external connectors, GA end-to-end
  engines/       multi-engine DF, Spark, Databricks, statistics primitives
  archive/       retired / superseded — not part of CI
```

## Running example — two Siege Analytics partner firms

- **ElectInfo** — political / civic analytics. 13 of 17 notebooks: foundations,
  all spatial, engines, statistics, PDF reports, polling waves.
- **Masai Interactive** — web / social analytics. 3 notebooks: external
  connectors, GA end-to-end, slides/Google Workspace delivery.

Both firms ship as branding templates in `siege_utilities/reporting/client_branding.py`
(`elect_info` and `masai_interactive`). `foundations/02_profiles_branding.ipynb`
introduces both and proves the wire-up by rendering the same chart under each brand.

## Canonical set

| Folder | Slot | Task | Firm |
|---|---|---|---|
| foundations | 01 | Bootstrap reporting env — Hydra + Pydantic config | ElectInfo |
| foundations | 02 | Onboard two clients as branded profiles | Both |
| spatial | 01 | Pull TX boundaries (TIGER + ACS demographics + GADM) | ElectInfo |
| spatial | 02 | Resolve donor list to FIPS (Census batch geocoder) | ElectInfo |
| spatial | 03 | Bivariate choropleth (dem share × turnout) | ElectInfo |
| spatial | 04 | Redistricting diff — 116th vs 118th TX-32 | ElectInfo |
| spatial | 05 | Unify 3 polling vendors onto TX-32 precincts | ElectInfo |
| spatial | 06 | GeoDjango API for TX-32 precincts | ElectInfo |
| analytics | 01 | Three connectors, one call-shape pattern | Masai |
| analytics | 02 | Weekly GA digest PDF | Masai |
| engines | 01 | Same ranking, pandas vs DuckDB | ElectInfo |
| engines | 02 | Scale to Spark (call shape) | ElectInfo |
| engines | 03 | Azure Databricks — no Sedona workaround | ElectInfo |
| engines | 04 | MOE + NAICS + cross-tab primitives | ElectInfo |
| reports | 01 | Assemble Q1 PDF for Acme Campaign | ElectInfo |
| reports | 02 | Same data as branded deck (PPTX + Google Slides) | Masai |
| reports | 03 | 3-wave TX-32 party-ID tracker | ElectInfo |

## Data policy

**No spatial or large data is committed to the repo.** Every notebook that needs
a dataset uses one of three paths:

1. The library's own cache (e.g. `CensusDataSource` downloads + caches TIGER
   shapefiles under `~/Downloads/siege_utilities/`)
2. `siege_utilities.cache.ensure_sample_dataset(name, url)` — download-on-first-run,
   user-scoped cache under `~/.cache/siege_utilities/notebooks/`
   (overridable via `SIEGE_UTILITIES_CACHE_DIR`)
3. Synthetic data generated inline (small CSVs / DataFrames)

Small non-spatial fixtures (under ~50 KB each) may be committed under
`notebooks/fixtures/` when truly needed.

## Structural rules (enforced by `test_notebook_hygiene.py`)

Every canonical notebook must:

- Open with `# Title` markdown
- Have a `## What this shows` cell in the first two cells
- Have exactly one `## Related` cell at the end
- Have no `NB0\d` / `NB1\d` / `NB2\d` stale cross-references
- Have no `try: import X` guards at cell top level
- Have no `if HAS_X:` guards wrapping main content

Violations fail CI.

## Credentials & graceful fallback

Notebooks that need credentials gate the live path behind an env var / config
check and fall back to either a fixture (for analytics) or a synthetic
stand-in (for spatial). The user-visible call shape always runs, whether or
not credentials are present.

| Credential | Used by | Absent behavior |
|---|---|---|
| `CENSUS_API_KEY` | `spatial/01` (ACS demographics) | Skip income join, render boundary map without overlay |
| `GOOGLE_APPLICATION_CREDENTIALS` | `analytics/01`, `analytics/02` | Call shape printed; analysis runs on fixture |
| `SNOWFLAKE_CONFIG_FILE` | `analytics/01` | Call shape printed |
| `DW_AUTH_TOKEN` | `analytics/01` | Call shape printed |
| RDH API | `spatial/04` | Synthetic stand-in polygons with call shape in comments |
| Azure Databricks workspace | `engines/03` | Pure-Python URL / SQL builder cells run; cluster-dependent cells conceptual |
| Local PostGIS | `spatial/06` | Full call-shape recipe, not executed inline (needs live DB) |

## Why `engines/02` and `spatial/06` don't execute their primary cells

Local Spark inside nbconvert is fragile (JVM startup, Py4J gateway lifetime,
serializer registration). Likewise a Django + PostGIS server spun up inside a
notebook is unsafe to provision from CI. Both notebooks ship complete,
copy-pasteable call shapes rather than fake execution. The analysis pattern
is the point; provisioning is out-of-band.

## CI (follow-up)

```yaml
- name: Structural hygiene
  run: pytest tests/test_notebook_hygiene.py

- name: Execute canonical notebooks  # gated on credentials being wired
  run: |
    uv pip install -e '.[all,dev]'
    pytest --nbmake \
      notebooks/foundations/*.ipynb \
      notebooks/analytics/01_connectors.ipynb \
      notebooks/engines/01_multi_engine_dataframes.ipynb \
      notebooks/engines/04_statistics_primitives.ipynb \
      notebooks/reports/03_polling_survey_analysis.ipynb \
      notebooks/spatial/02_geocoding.ipynb \
      notebooks/spatial/03_choropleth_maps.ipynb \
      notebooks/spatial/04_redistricting.ipynb \
      notebooks/spatial/05_multi_source_joins.ipynb
```

`nbmake` gating is the explicit next step. Notebooks that need external
credentials (`spatial/01` for ACS, `analytics/02` for GA, etc.) are excluded
until secrets are wired in CI.

## See also

- [INTENT.md](INTENT.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [TEST_UPGRADES.md](TEST_UPGRADES.md)
