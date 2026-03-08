# Examples Index

Canonical runnable examples are kept with package code.

## Primary Examples

- `siege_utilities/examples/enhanced_features_demo.py`
- `siege_utilities/reporting/examples/comprehensive_mapping_example.py`
- `siege_utilities/reporting/examples/bivariate_choropleth_example.py`
- `siege_utilities/reporting/examples/ga_geographic_analysis.py`
- `siege_utilities/reporting/examples/google_analytics_report_example.py`

## Primary Notebooks

- `notebooks/06_Report_Generation.ipynb` includes an explicit `create_3d_map` demonstration (Section 5, 3D Visualization).
- `notebooks/07_Geocoding_Address_Processing.ipynb` includes public and custom `server_url` Nominatim usage.

## Execution

Run examples from repository root:

```bash
python -m siege_utilities.examples.enhanced_features_demo
python siege_utilities/reporting/examples/bivariate_choropleth_example.py
```

## Scope Rule

Examples are for demonstrations and integration guidance. Contributor-facing policy and operational workflow documentation should live in `docs/` and not inside ad hoc example markdown files.
