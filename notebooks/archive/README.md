# Archived notebooks

Notebooks retired from the canonical demo set during the ELE-2421 consolidation
(Apr 2026). They are kept here for reference but are **not** part of the
`pytest --nbmake` CI gate — expect drift and untested imports.

| File | Reason |
|---|---|
| `17_Developer_Tooling.ipynb` | Meta content (architecture diagrams, release workflow). Material belongs in `docs/development/`, not a user-facing demo. |
| `19_NLRB_Data_Integration.ipynb` | Narrow dataset demo; duplicates patterns shown more generally in `09_Analytics_Connectors.ipynb`. |
| `21_Enterprise_Onboarding_Presentation.ipynb` | Marketing/onboarding deck, not a library capability demo. |
| `22_Temporal_Political_Models.ipynb` | Narrow domain modeling (political ID longitudinal). Replaced by the general-purpose `WaveSet` demo in the new canonical slot 06 (`notebooks/06_Polling_Survey_Analysis.ipynb`). |

If you are looking for functionality previously illustrated here, the
replacement locations are:

- **Architecture / development docs** → `docs/ARCHITECTURE.md`, `docs/adr/`
- **NLRB / external datasets** → `notebooks/09_Analytics_Connectors.ipynb`
- **Longitudinal political modeling** → `notebooks/06_Polling_Survey_Analysis.ipynb`
  (uses `survey.WaveSet.compare_chain` instead of a domain-specific class)

Full retirement rationale: `docs/NOTEBOOKS.md`.
