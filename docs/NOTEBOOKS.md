# siege_utilities — Notebook Inventory + Consolidation Plan

Per **ELE-2421** (audit sub-issue 6/6). This doc inventories the 27 notebooks currently under `notebooks/`, maps each to the capability it demonstrates, identifies overlaps, and proposes a curated set of canonical demos with a `README.md` index.

## Current inventory (27 notebooks)

| # | File | Title (first H1) | Capability | Status |
|---|---|---|---|---|
| 01 | `01_Configuration_System_Demo` | Hydra + Pydantic Configuration System Demo | Config loading / validation | **Keep** (rename to canonical "Configuration") |
| 02 | `02_Create_User_Client_Profiles` | Create User and Client Profiles | Profile management | **Keep** |
| 03 | `03_Person_Actor_Architecture` | Person/Actor Architecture | Person/Actor data model | **Merge into 02** (profile + actor overlap) |
| 04 | `04_Spatial_Data_Census_Boundaries` | Spatial Data & Census Boundaries | Census boundary retrieval | **Keep** (canonical geo intro) |
| 05 | `05_Choropleth_Maps` | Choropleth Maps | Map rendering | **Keep** |
| 06 | `06_Report_Generation` | Report Generation — Complete Chart Gallery | Chart gallery | **Fix + keep** (uses legacy `metric='sessions'`) |
| 07 | `07_Geocoding_Address_Processing` | Geocoding & Address Processing | Geocoding | **Keep** |
| 08 | `08_Sample_Data_Generation` | Data Utilities — Sample Generation, File Hashing, Downloads | Multi-concern grab bag | **Split** into sample-data + file-ops demos OR retire the file-ops half |
| 09 | `09_Analytics_Connectors` | Analytics Connectors | External analytics integrations | **Keep** |
| 10 | `10_Profile_Branding_Testing` | Profile & Branding System Testing | Branding | **Merge into 02** (profile concern) |
| 11 | `11_ReportLab_PDF_Features` | ReportLab PDF Features Testing | PDF output | **Merge into 06 or 12** (all reporting) |
| 12 | `12_PowerPoint_Generation` | PowerPoint Generation Testing | PPTX output | **Keep + refresh** with new Argument→Slides from #392 |
| 13 | `13_GeoDjango_Integration` | GeoDjango Integration | Django + PostGIS | **Keep** (niche but important) |
| 14 | `14_GA_Analytics_Report` | Google Analytics Performance Report | End-to-end GA → report | **Keep** as an end-to-end showcase |
| 15 | `15_Census_Demographics_Integration` | Census Demographics Integration — Quick Start | Census demographics | **Merge into 04** (census overlap) |
| 16 | `16_Spark_Distributed_Operations` | Spark & Sedona Distributed Operations | Distributed compute | **Keep** |
| 17 | `17_Developer_Tooling` | Developer Tooling | Internal tools (architecture diagrams, doc gen) | **Retire or move to `docs/`** — meta, not user demo |
| 18 | `18_Google_Workspace` | Google Workspace Write APIs | Workspace APIs (Sheets/Docs/Slides write) | **Merge into 09 or 12** |
| 19 | `19_NLRB_Data_Integration` | NLRB Data Integration | Specific dataset integration | **Archive** — example of how to integrate a new dataset; out of canonical set |
| 20 | `20_Multi_Source_Spatial_Tabulation` | Multi-Source Spatial Data Tabulation | Cross-source spatial joins | **Keep** (canonical dirty-data demo per `_data-trust-rules.md`) |
| 21 | `21_Enterprise_Onboarding_Presentation` | Enterprise Onboarding Presentation | Demo deck | **Retire** — marketing/onboarding, not a library feature demo |
| 22 | `22_Temporal_Political_Models` | Temporal Political Models | Domain modeling | **Archive** — sophisticated but narrow |
| 23 | `23_Redistricting_Analysis` | Redistricting Analysis | RDH + districting | **Keep** (exercises #386 RDHProvider + VTD routing) |
| 24 | `24_DuckDB_Engine_Abstraction` | DuckDB & Engine Abstraction | Multi-engine DataFrame ops | **Keep** (canonical engine-agnostic demo) |
| 25 | `25_SpatiaLite_Cache_Geocoding` | SpatiaLite Cache & Advanced Geocoding | SpatiaLite geocoding cache | **Merge into 07** |
| 26 | `26_International_Boundaries_GADM` | International Boundaries — GADM | GADM provider | **Merge into 04** or keep as a dedicated "non-US boundaries" demo |
| 27 | `27_Advanced_Census_MOE_NAICS` | Advanced Census — MOE Propagation & NAICS/SOC Crosswalks | Advanced census | **Keep** — unique content not elsewhere |

## Deprecated-API scan

Searched for:
- `metric='sessions'` / `metric="sessions"` (legacy PollingAnalyzer default before #389)
- `geographic_column='country'` (legacy default before #389)

**Sites found:** 1 — `06_Report_Generation.ipynb` uses `metric='sessions'` in 4 cells. Will be fixed when 06 is refreshed.

No other deprecated patterns detected. Good baseline.

## Consolidation target: ~12 curated notebooks

Ordered by "first notebook a new user should open":

| Slot | Notebook | Consolidates | Canonical capability |
|---|---|---|---|
| 01 | `01_Configuration.ipynb` | existing 01 | Config loading, Hydra+Pydantic, env handling |
| 02 | `02_Profiles_and_Actors.ipynb` | 02 + 03 + 10 | Users, clients, collaborators, branding |
| 03 | `03_Census_Boundaries.ipynb` | 04 + 15 + 26 | Census TIGER, demographics, GADM international |
| 04 | `04_Choropleth_and_Maps.ipynb` | 05 | Choropleth + bivariate + flow maps |
| 05 | `05_Geocoding.ipynb` | 07 + 25 | Address geocoding + SpatiaLite cache |
| 06 | `06_Polling_Survey_Analysis.ipynb` | (new) | Chain/Cluster/Stack + Argument — exercises #389+#390+#391 end-to-end |
| 07 | `07_Reports_Charts_PDF.ipynb` | 06 + 11 | Chart gallery + PDF output (refreshed) |
| 08 | `08_Slides_from_Arguments.ipynb` | 12 + 18 | PowerPoint / Google Slides from Argument (#392) |
| 09 | `09_Analytics_Connectors.ipynb` | 09 + 14 | GA, Facebook, Snowflake, data.world |
| 10 | `10_Redistricting.ipynb` | 23 | RDH + VTD routing (#386) — canonical dirty-data showcase |
| 11 | `11_Multi_Engine_DataFrames.ipynb` | 24 + parts of 16 | pandas / DuckDB / Spark comparison |
| 12 | `12_Distributed_Spark_Sedona.ipynb` | 16 | Spark + Sedona for scale work |

**Retired / archived:**
- `17_Developer_Tooling` → move to `docs/development/` as reference material
- `19_NLRB_Data_Integration` → `notebooks/archive/` with README pointer
- `21_Enterprise_Onboarding_Presentation` → marketing collateral, not a library demo; move to a sales repo
- `22_Temporal_Political_Models` → archive (narrow scope)
- `08_Sample_Data_Generation` half about file ops → replace with a standalone doc or a small `files/` cookbook

## Per-notebook structure (new canon)

Every curated notebook opens with:

```markdown
# <Title>

## What this shows
<one sentence>

## Why it matters
<one paragraph>

## Prereqs
- pip install siege-utilities[<relevant extras>]
- <any env vars / credentials>

## Next
- See notebook NN for <related capability>
```

And ends with a footer:

```markdown
## Related

- Source: siege_utilities/<module>/
- Tests: tests/test_<module>*.py
- Skills: <relevant skills from claude-configs-public>
```

## `notebooks/README.md` index

A new file listing all 12 canonical notebooks with a one-line summary. New-user entry point.

## nbmake CI

Add a job that runs every canonical notebook headless via `nbmake`:

```yaml
# .github/workflows/notebooks.yml
- name: Run canonical notebooks
  run: |
    uv pip install -e .[all,dev]
    pytest --nbmake notebooks/??_*.ipynb
```

Gating on notebooks only once 12 canonical are stable. During the migration (while old and new coexist), nbmake runs on the new set only.

## Dependencies

Gates on at least the first few ELE-2420 rewrites landing so the new notebooks don't reference about-to-be-removed APIs. Specifically:
- ADR 0006 (polling_analyzer location) — notebook 06 (polling) uses the new import path
- ADR 0007 (Argument location) — notebook 08 (slides) uses the new import path

Once those land, notebook rewrites can proceed.

## Sequencing

- **Step 1 (this PR):** land the inventory + plan; no notebook changes yet
- **Step 2:** after ADRs accepted and first rewrites shipped, open per-notebook PRs in the order of Slot 01 → 12
- **Step 3:** once new set is complete, move old notebooks to `notebooks/archive/` and add redirects in the README
- **Step 4:** enable nbmake CI on the canonical set

## Attribution

Per `skills/_output-rules.md`: no AI attribution in notebook cells or commits.
