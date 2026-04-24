# Archived notebooks

Notebooks retired from the canonical themed set during the ELE-2421
consolidation (Apr 2026). Retained here for historical reference and to
preserve any embedded outputs or narrative; **not** part of the `pytest
--nbmake` CI gate. Expect drift and deprecated API references.

## Retired — narrow / meta / marketing

| File | Reason |
|---|---|
| `17_Developer_Tooling.ipynb` | Meta content (architecture diagrams, release workflow). Material belongs in `docs/development/`. |
| `19_NLRB_Data_Integration.ipynb` | Narrow dataset demo; patterns are covered generally in `analytics/01_connectors`. |
| `21_Enterprise_Onboarding_Presentation.ipynb` | Marketing / onboarding deck, not a library capability demo. |
| `22_Temporal_Political_Models.ipynb` | Narrow domain modeling (political-ID longitudinal). Replaced by the general-purpose `WaveSet` demo in `reports/03_polling_survey_analysis.ipynb`. |

## Dissolved — content absorbed into canonical notebooks

| File | Absorbed into |
|---|---|
| `03_Person_Actor_Architecture.ipynb` | [`foundations/02_profiles_branding.ipynb`](../foundations/02_profiles_branding.ipynb) |
| `08_Sample_Data_Generation.ipynb` | Dissolved — sample-data generators were fixture utilities, not a capability. Inlined where used. |
| `10_Profile_Branding_Testing.ipynb` | [`foundations/02_profiles_branding.ipynb`](../foundations/02_profiles_branding.ipynb) |
| `11_ReportLab_PDF_Features.ipynb` | [`reports/01_charts_and_pdf.ipynb`](../reports/01_charts_and_pdf.ipynb) |
| `15_Census_Demographics_Integration.ipynb` | [`spatial/01_boundaries.ipynb`](../spatial/01_boundaries.ipynb) |
| `18_Google_Workspace.ipynb` | [`reports/02_slides_pptx_and_google.ipynb`](../reports/02_slides_pptx_and_google.ipynb) |
| `25_SpatiaLite_Cache_Geocoding.ipynb` | [`spatial/02_geocoding.ipynb`](../spatial/02_geocoding.ipynb) |
| `26_International_Boundaries_GADM.ipynb` | [`spatial/01_boundaries.ipynb`](../spatial/01_boundaries.ipynb) |

Full retirement rationale: [`docs/NOTEBOOKS.md`](../../docs/NOTEBOOKS.md).
Path map (old numeric → new themed): [`notebooks/README.md`](../README.md).
