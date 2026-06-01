Jupyter Notebooks
=================

The ``notebooks/`` directory contains 27 runnable Jupyter notebooks
demonstrating all major library capabilities. Run them headlessly
via the test runner::

    pytest tests/test_notebooks.py -k pure_python -v

Configuration & Profiles
------------------------

- **NB01** — Configuration System Demo (Hydra + Pydantic)
- **NB02** — Create User & Client Profiles
- **NB03** — Person/Actor Architecture (full model reference)

Geospatial & Census
--------------------

- **NB04** — Spatial Data & Census Boundaries (comprehensive reference)
- **NB05** — Choropleth Maps & Classification
- **NB07** — Geocoding & Address Processing
- **NB15** — Census Demographics Quick Start
- **NB25** — SpatiaLite Cache & Advanced Geocoding
- **NB26** — International Boundaries (GADM)
- **NB27** — Advanced Census (MOE Propagation, NAICS/SOC)

Political & Redistricting
--------------------------

- **NB22** — Temporal Political Models (CongressionalTerm, Seat, Race)
- **NB23** — Redistricting Analysis (Plans, Compactness, Demographics)

Data Engines
------------

- **NB24** — DuckDB & Engine Abstraction (engine switching, spatial ops)
- **NB16** — Spark & Sedona Distributed Operations

Reporting
---------

- **NB06** — Report Generation (chart gallery)
- **NB11** — ReportLab PDF Features
- **NB12** — PowerPoint Generation
- **NB21** — Enterprise Onboarding Presentation

Analytics & Integrations
-------------------------

- **NB09** — Analytics Connectors (Facebook, GA4, Snowflake)
- **NB14** — GA Analytics Report
- **NB18** — Google Workspace Write APIs

Data & Development
------------------

- **NB08** — Sample Data Generation
- **NB10** — Profile & Branding Testing
- **NB13** — GeoDjango Integration
- **NB17** — Developer Tooling
- **NB19** — NLRB Data Integration
- **NB20** — Multi-Source Spatial Tabulation

Dependency Groups
-----------------

Notebooks are grouped by dependency for selective execution:

.. list-table::
   :header-rows: 1

   * - Group
     - Marker
     - Count
   * - Pure Python
     - (none)
     - 13
   * - Geo (GDAL)
     - ``requires_gdal``
     - 5
   * - Django (PostGIS)
     - ``requires_gdal`` + ``django_db``
     - 2
   * - Analytics (credentials)
     - ``integration``
     - 3
   * - Spark
     - ``integration``
     - 1
   * - External downloads
     - ``integration``
     - 3
