Installation Troubleshooting
============================

System Dependencies for Geospatial
------------------------------------

The ``[geo]`` and ``[geodjango]`` extras require system-level libraries
(GDAL, GEOS, PROJ) that cannot be installed via pip.

Ubuntu / Debian
~~~~~~~~~~~~~~~

::

    sudo apt-get update
    sudo apt-get install -y \
        gdal-bin libgdal-dev \
        libgeos-dev libgeos++-dev \
        libproj-dev proj-bin \
        libspatialindex-dev \
        libsqlite3-mod-spatialite

    # Set GDAL version for pip
    export GDAL_VERSION=$(gdal-config --version)
    pip install siege-utilities[geo]

macOS (Homebrew)
~~~~~~~~~~~~~~~~

::

    brew install gdal geos proj spatialindex
    pip install siege-utilities[geo]

Windows
~~~~~~~

Use conda or OSGeo4W::

    conda install -c conda-forge gdal geopandas
    pip install siege-utilities[geo-lite]  # Use geo-lite to skip GDAL requirement

Choosing the Right Extras
--------------------------

.. list-table::
   :header-rows: 1

   * - Extra
     - System Deps
     - What You Get
   * - ``[geo-lite]``
     - None
     - Census data, geocoding, schemas (no geometry operations)
   * - ``[geo]``
     - GDAL, GEOS, PROJ
     - Full GeoPandas, spatial joins, choropleths, isochrones
   * - ``[geodjango]``
     - GDAL, GEOS, PROJ, PostGIS
     - Everything + Django ORM with spatial queries

Common Errors
--------------

**"Could not find GDAL library"**
    GDAL is not installed or not on PATH. Install system GDAL first.

**"OSError: cannot load library 'libgeos_c.so'"**
    GEOS not installed. On Ubuntu: ``sudo apt install libgeos-dev``.

**"ModuleNotFoundError: No module named 'osgeo'"**
    GDAL Python bindings not installed. Try: ``pip install GDAL==$(gdal-config --version)``.

**"django.contrib.gis.gdal.error.GDALException"**
    GDAL library found but version mismatch. Ensure system GDAL version matches Python GDAL.

**DuckDB spatial "Extension ... not found"**
    DuckDB spatial extension needs internet access on first load. Run::

        import duckdb
        conn = duckdb.connect()
        conn.execute("INSTALL spatial; LOAD spatial")

**PostGIS "relation does not exist"**
    Run migrations first: ``python manage.py migrate``.
    Ensure PostGIS extension is enabled: ``CREATE EXTENSION IF NOT EXISTS postgis;``
