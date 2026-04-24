# siege_utilities notebooks

End-to-end demos of the library, organized around capability areas. The
structure follows the `docs/NOTEBOOKS.md` consolidation plan (ELE-2421).

## Canonical demos

Start here. Each has a standard `What this shows / Why / Prereqs / Next`
header and a `## Related` footer pointing at source, tests, and consolidated
material.

| Slot | Notebook | Capability |
|---|---|---|
| 01 | `01_Configuration_System_Demo.ipynb` | Config loading (Hydra + Pydantic) |
| 02 | `02_Create_User_Client_Profiles.ipynb` | Profiles + branding (consolidates 03, 10) |
| 04 | `04_Spatial_Data_Census_Boundaries.ipynb` | Census TIGER (consolidates 15, parts of 26) |
| 05 | `05_Choropleth_Maps.ipynb` | Choropleth + bivariate + flow maps |
| 06 | `06_Report_Generation.ipynb` | Chart gallery + PDF (consolidates 11) |
| 07 | `07_Geocoding_Address_Processing.ipynb` | Geocoding + cache (consolidates 25) |
| 09 | `09_Analytics_Connectors.ipynb` | External analytics (GA, FB, Snowflake, data.world) |
| 12 | `12_PowerPoint_Generation.ipynb` | Argument → PPTX / Google Slides (consolidates 18) |
| 14 | `14_GA_Analytics_Report.ipynb` | GA → report end-to-end |
| 16 | `16_Spark_Distributed_Operations.ipynb` | Distributed compute |
| 20 | `20_Multi_Source_Spatial_Tabulation.ipynb` | Cross-source spatial joins |
| 23 | `23_Redistricting_Analysis.ipynb` | RDH + VTD routing |
| 24 | `24_DuckDB_Engine_Abstraction.ipynb` | Engine-agnostic DataFrames |
| 27 | `27_Advanced_Census_MOE_NAICS.ipynb` | MOE + crosswalks |
| 28 | `28_Polling_Survey_Analysis.ipynb` | **New:** survey pipeline + `WaveSet` (ELE-2440) |

## Consolidated-away notebooks

These still exist but open with a **Consolidation notice** pointing at the
canonical slot above. Retained for diffability and historical reference.

| Notebook | Consolidated into |
|---|---|
| `03_Person_Actor_Architecture.ipynb` | `02_Create_User_Client_Profiles.ipynb` |
| `10_Profile_Branding_Testing.ipynb` | `02_Create_User_Client_Profiles.ipynb` |
| `11_ReportLab_PDF_Features.ipynb` | `06_Report_Generation.ipynb` |
| `15_Census_Demographics_Integration.ipynb` | `04_Spatial_Data_Census_Boundaries.ipynb` |
| `18_Google_Workspace.ipynb` | `12_PowerPoint_Generation.ipynb` |
| `25_SpatiaLite_Cache_Geocoding.ipynb` | `07_Geocoding_Address_Processing.ipynb` |
| `26_International_Boundaries_GADM.ipynb` | `04_Spatial_Data_Census_Boundaries.ipynb` |

## Archive

Narrow/meta notebooks moved out of the primary set live in
[`archive/`](./archive/) with a README explaining the reason.

## Running notebooks

```bash
# Install the library editable plus extras for the notebook you want:
uv pip install -e '.[all,dev]'

# Execute a notebook headlessly (kernel must point at the project venv):
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/28_Polling_Survey_Analysis.ipynb
```

CI gating on `pytest --nbmake notebooks/??_*.ipynb` is tracked in
`docs/NOTEBOOKS.md` (step 4) and enabled once the canonical set is stable.

## See also

- `docs/NOTEBOOKS.md` — full consolidation plan and rationale
- `docs/INTENT.md` — module purpose catalogue
- `docs/ARCHITECTURE.md` — layered model the notebooks exercise
