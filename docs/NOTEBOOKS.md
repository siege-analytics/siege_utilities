# siege_utilities — Notebook organization

**Outcome:** 27 flat legacy notebooks → 17 canonical notebooks across 5 themed
folders + 12 archived. Every user-facing module has a notebook home; nothing
duplicates.

**Snapshot:** 2026-04-23 (post-reorg). Supersedes the 2026-04-22 plan.

## Final layout

```
notebooks/
  foundations/   config, profiles, branding
  spatial/       geographies, geocoding, maps, spatial joins, GeoDjango
  reports/       chart gallery + PDF, slides (PPTX & Google), polling/survey
  analytics/     external data connectors, GA end-to-end
  engines/       pandas ↔ DuckDB ↔ Spark ↔ Databricks, statistics primitives
  archive/       retired / superseded notebooks — not part of CI
```

## Canonical set (17)

| Folder | Slot | Notebook | Capability |
|---|---|---|---|
| foundations | 01 | `01_configuration` | Hydra + Pydantic config |
| foundations | 02 | `02_profiles_branding` | Users, clients, Actor model, branding |
| spatial | 01 | `01_boundaries` | Census TIGER + demographics + GADM |
| spatial | 02 | `02_geocoding` | Census geocoder + SpatiaLite cache |
| spatial | 03 | `03_choropleth_maps` | Choropleth + bivariate + flow |
| spatial | 04 | `04_redistricting` | RDH + VTD routing |
| spatial | 05 | `05_multi_source_joins` | Cross-source spatial joins |
| spatial | 06 | `06_geodjango` | GeoDjango + PostGIS |
| reports | 01 | `01_charts_and_pdf` | ChartGenerator gallery + ReportLab PDF |
| reports | 02 | `02_slides_pptx_and_google` | `Argument` → PPTX + Google Slides |
| reports | 03 | `03_polling_survey_analysis` | Survey pipeline incl. `WaveSet.compare_chain` |
| analytics | 01 | `01_connectors` | External analytics source zoo |
| analytics | 02 | `02_ga_end_to_end` | GA → report showcase |
| engines | 01 | `01_multi_engine_dataframes` | pandas / DuckDB / Spark via one abstraction |
| engines | 02 | `02_distributed_spark` | Spark + Sedona at scale |
| engines | 03 | `03_databricks_geo` | Databricks bridges, LakeBase, Unity Catalog (no Sedona) |
| engines | 04 | `04_statistics_primitives` | MOE propagation, NAICS/SOC, cross-tab primitive |

## What changed (old flat → new themed)

Consolidations performed in the reorg PR:

| Merge | Result |
|---|---|
| 02 + 03 + 10 | `foundations/02_profiles_branding` |
| 04 + 15 + 26 | `spatial/01_boundaries` |
| 07 + 25 | `spatial/02_geocoding` |
| 06 + 11 | `reports/01_charts_and_pdf` |
| 12 + 18 | `reports/02_slides_pptx_and_google` |
| 27 (rename) | `engines/04_statistics_primitives` (+ new cross-tab section) |

New capability coverage (previously unnotebooked):

| Target | Notebook |
|---|---|
| `siege_utilities/databricks/` | `engines/03_databricks_geo` (new) |
| `data/statistics/cross_tabulation` primitive | appended section in `engines/04_statistics_primitives` |

Retired / dissolved:

| Notebook | Reason |
|---|---|
| `08_Sample_Data_Generation` | Fixture utility, not a capability — inline where used |
| `17_Developer_Tooling` | Meta; belongs in `docs/development/` |
| `19_NLRB_Data_Integration` | Narrow dataset |
| `21_Enterprise_Onboarding_Presentation` | Marketing |
| `22_Temporal_Political_Models` | Superseded by `WaveSet` in `reports/03` |

Full old→new path map lives in [`notebooks/README.md`](../notebooks/README.md#old-path--new-path).

## Per-notebook canonical structure

Every canonical notebook opens with:

```markdown
# <Title>

## What this shows
<one sentence>

## Why it matters
<one paragraph>

## Prereqs
- pip install siege-utilities[<extras>]
- <env vars / credentials>

## Next
- See <neighbor notebook> for <related capability>
```

And ends with:

```markdown
## Related
- Source: siege_utilities/<module>/
- Tests: tests/test_<module>*.py
- ADR / docs as relevant
```

## CI

```yaml
- name: Run canonical notebooks
  run: |
    uv pip install -e '.[all,dev]'
    pytest --nbmake \
      notebooks/foundations/*.ipynb \
      notebooks/spatial/*.ipynb \
      notebooks/reports/*.ipynb \
      notebooks/analytics/*.ipynb \
      notebooks/engines/*.ipynb
```

Gating is the follow-up step: enabling nbmake requires first wiring credentials
for the notebooks that hit external services (GA, LakeBase, GeoDjango).
Non-credentialed notebooks that already execute clean in this PR:
- `reports/03_polling_survey_analysis.ipynb`
- `engines/03_databricks_geo.ipynb` (pure-Python string builders + conceptual cells)
- `engines/04_statistics_primitives.ipynb`

## See also

- [INTENT.md](INTENT.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [TEST_UPGRADES.md](TEST_UPGRADES.md)
