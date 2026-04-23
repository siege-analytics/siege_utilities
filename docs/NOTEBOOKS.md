# siege_utilities — Notebook Inventory + Consolidation Plan

**Goal:** 27 notebooks → 12 curated canonical demos + archive.

**Scope:** ELE-2421 (audit sub-issue 6/6). Snapshot: 2026-04-22.

## Current inventory (27 notebooks)

| # | File | Capability | Disposition |
|---|---|---|---|
| 01 | Configuration_System_Demo | Config / Hydra + Pydantic | **Keep** (rename canonical) |
| 02 | Create_User_Client_Profiles | Profile management | **Keep** |
| 03 | Person_Actor_Architecture | Person/Actor model | Merge → 02 |
| 04 | Spatial_Data_Census_Boundaries | Census boundaries | **Keep** (canonical geo intro) |
| 05 | Choropleth_Maps | Map rendering | **Keep** |
| 06 | Report_Generation | Chart gallery | **Fix + keep** (legacy `metric='sessions'` in 4 cells) |
| 07 | Geocoding_Address_Processing | Geocoding | **Keep** |
| 08 | Sample_Data_Generation | Multi-concern grab bag | Split — sample-data kept; file-ops half retired |
| 09 | Analytics_Connectors | External analytics | **Keep** |
| 10 | Profile_Branding_Testing | Branding | Merge → 02 |
| 11 | ReportLab_PDF_Features | PDF output | Merge → 06/12 |
| 12 | PowerPoint_Generation | PPTX output | **Keep + refresh** (Argument→Slides from #392) |
| 13 | GeoDjango_Integration | Django + PostGIS | **Keep** (niche but important) |
| 14 | GA_Analytics_Report | GA → report end-to-end | **Keep** (showcase) |
| 15 | Census_Demographics_Integration | Census demographics | Merge → 04 |
| 16 | Spark_Distributed_Operations | Distributed compute | **Keep** |
| 17 | Developer_Tooling | Meta / architecture diagrams | Retire → `docs/development/` |
| 18 | Google_Workspace | Workspace write APIs | Merge → 09/12 |
| 19 | NLRB_Data_Integration | NLRB dataset | Archive (narrow) |
| 20 | Multi_Source_Spatial_Tabulation | Cross-source spatial joins | **Keep** (dirty-data canonical) |
| 21 | Enterprise_Onboarding_Presentation | Marketing deck | Retire (not a library demo) |
| 22 | Temporal_Political_Models | Domain modeling | Archive (narrow) |
| 23 | Redistricting_Analysis | RDH + districting | **Keep** (exercises #386) |
| 24 | DuckDB_Engine_Abstraction | Multi-engine DF ops | **Keep** (canonical engine demo) |
| 25 | SpatiaLite_Cache_Geocoding | SpatiaLite cache | Merge → 07 |
| 26 | International_Boundaries_GADM | GADM non-US | Merge → 04 or keep dedicated |
| 27 | Advanced_Census_MOE_NAICS | MOE + crosswalks | **Keep** (unique content) |

## Canonical 12 — consolidated

| Slot | Notebook | Consolidates | Canonical capability |
|---|---|---|---|
| 01 | Configuration | 01 | Config loading, Hydra+Pydantic, env handling |
| 02 | Profiles_and_Actors | 02 + 03 + 10 | Users, clients, collaborators, branding |
| 03 | Census_Boundaries | 04 + 15 + 26 | Census TIGER + demographics + GADM |
| 04 | Choropleth_and_Maps | 05 | Choropleth + bivariate + flow maps |
| 05 | Geocoding | 07 + 25 | Address geocoding + SpatiaLite cache |
| 06 | Polling_Survey_Analysis | new | Chain/Cluster/Stack + Argument (#389/#390/#391 end-to-end) |
| 07 | Reports_Charts_PDF | 06 + 11 | Chart gallery + PDF output (refreshed) |
| 08 | Slides_from_Arguments | 12 + 18 | PowerPoint / Google Slides from Argument (#392) |
| 09 | Analytics_Connectors | 09 + 14 | GA, Facebook, Snowflake, data.world |
| 10 | Redistricting | 23 | RDH + VTD routing (#386) |
| 11 | Multi_Engine_DataFrames | 24 + parts of 16 | pandas / DuckDB / Spark comparison |
| 12 | Distributed_Spark_Sedona | 16 | Spark + Sedona at scale |

## Retired / archived

| Notebook | Action | Reason |
|---|---|---|
| 17 Developer_Tooling | Move to `docs/development/` | Meta, not user demo |
| 19 NLRB_Data_Integration | `notebooks/archive/` | Narrow scope |
| 21 Enterprise_Onboarding_Presentation | External repo | Marketing collateral |
| 22 Temporal_Political_Models | `notebooks/archive/` | Narrow scope |
| 08 file-ops half | Replace with cookbook in docs | Grab-bag structure |

## Deprecated-API scan

| Pattern | Hits | Action |
|---|---:|---|
| `metric='sessions'` (legacy PollingAnalyzer default) | 4 cells in `06_Report_Generation` | Fix during 06 refresh |
| `geographic_column='country'` (legacy default) | 0 | — |

## Per-notebook canonical structure

Every curated notebook opens with:

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
- See notebook NN for <related capability>
```

And ends with:

```markdown
## Related
- Source: siege_utilities/<module>/
- Tests: tests/test_<module>*.py
- Skills: <relevant skills>
```

## CI

```yaml
- name: Run canonical notebooks
  run: |
    uv pip install -e .[all,dev]
    pytest --nbmake notebooks/??_*.ipynb
```

Gating on nbmake begins once the 12 canonical are stable.

## Dependencies + sequencing

| Step | What | Gates on |
|---|---|---|
| 1 | Land this inventory + plan (no notebook changes) | — |
| 2 | Per-notebook PRs in slot order 01 → 12 | ADRs 0006, 0007 accepted + first rewrites shipped |
| 3 | Move old notebooks to `notebooks/archive/`; add README redirects | Step 2 complete |
| 4 | Enable nbmake CI on canonical set | Step 3 complete |

See also: [INTENT.md](INTENT.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [TEST_UPGRADES.md](TEST_UPGRADES.md)
