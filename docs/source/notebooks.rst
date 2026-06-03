Jupyter Notebooks
=================

The ``notebooks/`` directory contains 24 active Jupyter notebooks organized
by domain, plus 12 archived notebooks from prior reorganizations.

Foundations
-----------

- **01_configuration** — Hydra + Pydantic configuration system with client overlays
- **02_profiles_branding** — Client profile registration and branded chart rendering
- **entity_identification** — Deduplicating donors across vendor lists (normalize, UUID5, namespace)
- **file_operations_and_security** — Atomic writes, path security, safe I/O, command restriction

Engines
-------

- **01_multi_engine_dataframes** — Same ranking query against pandas and DuckDB backends
- **02_distributed_spark** — Spark + Sedona call shapes for scaled operations (conceptual)
- **03_databricks_geo** — Asset Bundles, LakeBase, Unity Catalog DDL, Spark-GeoPandas bridge
- **04_statistics_primitives** — MOE propagation, NAICS/SOC hierarchies, contingency tables

Spatial
-------

- **01_boundaries** — Census TIGER geographies (state, county, tract) with ACS join
- **02_geocoding** — Batch geocoding with Census geocoder, cache, quality flags
- **03_choropleth_maps** — Bivariate choropleths (Dem share x turnout), tertile binning
- **04_redistricting** — Congressional district boundary comparison across cycles
- **05_multi_source_joins** — Unifying three polling vendors via exact + fuzzy joins
- **06_geodjango** — GeoDjango model + PostGIS + FeatureCollection endpoint (conceptual)
- **07_natural_language_to_geometry** — NL query to Shapely polygon via WKLS/Etter

Analytics
---------

- **01_connectors** — GA, Snowflake, data.world connector patterns
- **02_ga_end_to_end** — Weekly GA digest pipeline: fetch, chart, PDF

Reports
-------

- **01_charts_and_pdf** — Branded Q1 deliverable assembly (chart + table + PDF)
- **02_slides_pptx_and_google** — 5-slide deck generation (PPTX + Google Slides)
- **03_polling_survey_analysis** — Three-wave party-ID tracker with crosstabs and trends
- **04_survey_full_showcase** — All seven TableTypes with branded multi-section PDF

Economic
--------

- **economic_data_irs_bls** — IRS SOI ZIP-code income data and BLS QCEW employment context

Git
---

- **repo_analysis** — Repository status, commit history, branch analysis (read-only)

Config
------

- **credential_management** — Credential backend discovery and management patterns
