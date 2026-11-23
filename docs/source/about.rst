About Siege Utilities
=====================

Siege Utilities is the shared Python toolkit behind Siege Analytics data
engineering, data science, and geospatial workflows. It helps compose domain
data with location and time, scale analysis across compute engines, and
communicate results through reports and maps.

What it provides
----------------

- **Geospatial foundations:** geocoding, Census data and boundaries, GEOID
  handling, coordinate reference systems, spatial operations, and pluggable
  providers.
- **Data and compute tools:** common utilities for pandas, DuckDB, Spark and
  distributed environments, plus domain packages for political, economic,
  education, survey, and analytics workflows.
- **Outputs and integrations:** reporting and chart generation, Google
  Workspace APIs, configuration, connectors, and reusable file operations.

The package is modular: install only the extras your workflow needs. With
compatible binary wheels, ``[geo]`` can be installed without system GDAL;
building Fiona or Rasterio from source requires libgdal. Pyogrio is available
depending on the resolved GeoPandas version; if installed from source, it also
requires libgdal. Native ``osgeo`` bindings and
GeoDjango/PostGIS have separate installation paths. See :doc:`getting_started`
and the :doc:`installation_troubleshooting` guide.

Current release
---------------

The current release is **5.0.0**. It strengthens path validation for files and
directories, defaults docstring generation to a dry run, and publishes PyPI
releases only from verified version tags on ``main``. Read the
`release notes <https://github.com/siege-analytics/siege_utilities/releases/tag/v5.0.0>`_
and `migration notes <https://github.com/siege-analytics/siege_utilities/blob/main/CHANGELOG.md#500---2026-11-20>`_
before upgrading.

Project links
-------------

- `Source code and issue tracker <https://github.com/siege-analytics/siege_utilities>`_
- `PyPI package <https://pypi.org/project/siege-utilities/>`_
- `Siege Analytics <https://siegeanalytics.com/>`_
