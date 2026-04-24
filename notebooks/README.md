# siege_utilities notebooks

Capability-focused demos, organized by what a user is trying to do rather than
by module tree. Each notebook opens with a standard `What this shows / Why it
matters / Prereqs / Next` header and ends with a `## Related` footer pointing
at source, tests, and architectural decisions.

## Layout

```
notebooks/
  foundations/   config, profiles, branding — everything else depends on these
  spatial/       geographies, geocoding, maps, spatial joins, GeoDjango
  reports/       chart gallery + PDF, slides (PPTX & Google), polling/survey
  analytics/     external data connectors, GA end-to-end
  engines/       pandas ↔ DuckDB ↔ Spark ↔ Databricks, statistics primitives
  archive/       retired / superseded notebooks — not part of CI
```

## Canonical demos

### `foundations/`
| File | Capability |
|---|---|
| [`01_configuration.ipynb`](./foundations/01_configuration.ipynb) | Hydra + Pydantic config, env handling |
| [`02_profiles_branding.ipynb`](./foundations/02_profiles_branding.ipynb) | Users, clients, Actor model, branding (consolidates Person/Actor + branding deep-dive) |

### `spatial/`
| File | Capability |
|---|---|
| [`01_boundaries.ipynb`](./spatial/01_boundaries.ipynb) | Census TIGER + demographics + GADM (consolidates 3 notebooks) |
| [`02_geocoding.ipynb`](./spatial/02_geocoding.ipynb) | Census geocoder + SpatiaLite cache |
| [`03_choropleth_maps.ipynb`](./spatial/03_choropleth_maps.ipynb) | Choropleth / bivariate / flow |
| [`04_redistricting.ipynb`](./spatial/04_redistricting.ipynb) | RDH + VTD routing |
| [`05_multi_source_joins.ipynb`](./spatial/05_multi_source_joins.ipynb) | Cross-source spatial joins (dirty-data canonical) |
| [`06_geodjango.ipynb`](./spatial/06_geodjango.ipynb) | GeoDjango + PostGIS |

### `reports/`
| File | Capability |
|---|---|
| [`01_charts_and_pdf.ipynb`](./reports/01_charts_and_pdf.ipynb) | ChartGenerator gallery + ReportLab PDF (consolidates PDF features) |
| [`02_slides_pptx_and_google.ipynb`](./reports/02_slides_pptx_and_google.ipynb) | `Argument` → PowerPoint + Google Slides (consolidates Workspace notebook) |
| [`03_polling_survey_analysis.ipynb`](./reports/03_polling_survey_analysis.ipynb) | Survey pipeline end-to-end incl. `WaveSet.compare_chain` |

### `analytics/`
| File | Capability |
|---|---|
| [`01_connectors.ipynb`](./analytics/01_connectors.ipynb) | External analytics source zoo (GA, Facebook, Snowflake, data.world) |
| [`02_ga_end_to_end.ipynb`](./analytics/02_ga_end_to_end.ipynb) | GA → report showcase |

### `engines/`
| File | Capability |
|---|---|
| [`01_multi_engine_dataframes.ipynb`](./engines/01_multi_engine_dataframes.ipynb) | pandas / DuckDB / Spark via one abstraction |
| [`02_distributed_spark.ipynb`](./engines/02_distributed_spark.ipynb) | Spark + Sedona at scale |
| [`03_databricks_geo.ipynb`](./engines/03_databricks_geo.ipynb) | Databricks bridges, LakeBase, Unity Catalog (no Sedona) |
| [`04_statistics_primitives.ipynb`](./engines/04_statistics_primitives.ipynb) | MOE propagation, NAICS/SOC crosswalks, cross-tab primitive |

## Old path → new path

If you have a bookmark or external link pointing at the old flat numbering, this is where it went:

| Old | New |
|---|---|
| `01_Configuration_System_Demo` | `foundations/01_configuration` |
| `02_Create_User_Client_Profiles` | `foundations/02_profiles_branding` |
| `03_Person_Actor_Architecture` | merged into `foundations/02_profiles_branding` |
| `04_Spatial_Data_Census_Boundaries` | `spatial/01_boundaries` |
| `05_Choropleth_Maps` | `spatial/03_choropleth_maps` |
| `06_Report_Generation` | `reports/01_charts_and_pdf` |
| `07_Geocoding_Address_Processing` | `spatial/02_geocoding` |
| `08_Sample_Data_Generation` | dissolved — utility; sample generators inlined where used |
| `09_Analytics_Connectors` | `analytics/01_connectors` |
| `10_Profile_Branding_Testing` | merged into `foundations/02_profiles_branding` |
| `11_ReportLab_PDF_Features` | merged into `reports/01_charts_and_pdf` |
| `12_PowerPoint_Generation` | `reports/02_slides_pptx_and_google` |
| `13_GeoDjango_Integration` | `spatial/06_geodjango` |
| `14_GA_Analytics_Report` | `analytics/02_ga_end_to_end` |
| `15_Census_Demographics_Integration` | merged into `spatial/01_boundaries` |
| `16_Spark_Distributed_Operations` | `engines/02_distributed_spark` |
| `17_Developer_Tooling` | `archive/` (meta, not a library demo) |
| `18_Google_Workspace` | merged into `reports/02_slides_pptx_and_google` |
| `19_NLRB_Data_Integration` | `archive/` (narrow) |
| `20_Multi_Source_Spatial_Tabulation` | `spatial/05_multi_source_joins` |
| `21_Enterprise_Onboarding_Presentation` | `archive/` (marketing, not a demo) |
| `22_Temporal_Political_Models` | `archive/` (superseded by `WaveSet`) |
| `23_Redistricting_Analysis` | `spatial/04_redistricting` |
| `24_DuckDB_Engine_Abstraction` | `engines/01_multi_engine_dataframes` |
| `25_SpatiaLite_Cache_Geocoding` | merged into `spatial/02_geocoding` |
| `26_International_Boundaries_GADM` | merged into `spatial/01_boundaries` |
| `27_Advanced_Census_MOE_NAICS` | `engines/04_statistics_primitives` |
| `28_Polling_Survey_Analysis` | `reports/03_polling_survey_analysis` |

## Running notebooks

```bash
# Install the library editable plus all extras:
uv pip install -e '.[all,dev]'

# Execute a notebook headlessly against the project venv:
uv run jupyter nbconvert \
    --to notebook --execute --inplace \
    --ExecutePreprocessor.kernel_name=siege-utilities-venv \
    notebooks/reports/03_polling_survey_analysis.ipynb
```

## Archive

Notebooks in [`archive/`](./archive/) are retained for historical reference
only. They are not part of the `pytest --nbmake` gate and may reference
deprecated APIs. See [`archive/README.md`](./archive/README.md) for the retirement rationale.

## See also

- [`docs/NOTEBOOKS.md`](../docs/NOTEBOOKS.md) — inventory + consolidation history
- [`docs/INTENT.md`](../docs/INTENT.md) — per-module purpose catalogue
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) — layered model the notebooks exercise
