# Examples Index

Canonical runnable examples are kept with package code.

## Primary Examples

- `siege_utilities/examples/enhanced_features_demo.py`
- `siege_utilities/reporting/examples/comprehensive_mapping_example.py`
- `siege_utilities/reporting/examples/bivariate_choropleth_example.py`
- `siege_utilities/reporting/examples/ga_geographic_analysis.py`
- `siege_utilities/reporting/examples/google_analytics_report_example.py`

## Primary Notebooks

The notebooks are organized into topical subdirectories under `notebooks/`.
Canonical entry points by capability:

- **Reporting / charts / PDF:** `notebooks/reports/01_charts_and_pdf.ipynb`
- **Slides + Google Workspace:** `notebooks/reports/02_slides_pptx_and_google.ipynb`
- **Geocoding (public + configurable Nominatim `server_url`):** `notebooks/spatial/02_geocoding.ipynb`
- **Boundary retrieval + choropleth:** `notebooks/spatial/01_boundaries.ipynb`, `notebooks/spatial/03_choropleth_maps.ipynb`
- **Multi-source spatial joins:** `notebooks/spatial/05_multi_source_joins.ipynb`
- **Natural-language geometry parsing:** `notebooks/spatial/07_natural_language_to_geometry.ipynb`
- **Analytics connectors (GA, Facebook, Snowflake):** `notebooks/analytics/01_connectors.ipynb` and siblings
- **Configuration + credentials:** `notebooks/foundations/01_configuration.ipynb`, `notebooks/config/credential_management.ipynb`

See `notebooks/README.md` for the full index.

## Execution

Run examples from repository root:

```bash
python -m siege_utilities.examples.enhanced_features_demo
python siege_utilities/reporting/examples/bivariate_choropleth_example.py
```

## Scope Rule

Examples are for demonstrations and integration guidance. Contributor-facing policy and operational workflow documentation should live in `docs/` and not inside ad hoc example markdown files.
