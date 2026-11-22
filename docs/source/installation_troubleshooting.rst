Installation Troubleshooting
============================

Geospatial Extras and GDAL
--------------------------

As of the GDAL-optional-extra split, the ``[geo]`` extra installs the
geospatial stack (GeoPandas, Shapely, Fiona, PyProj, rtree, PySAL, etc.).
On supported Python/platform combinations, compatible binary wheels bundle
the needed GDAL/GEOS/PROJ libraries, so a normal pip install does not need
system GDAL::

    pip install siege-utilities[geo]

System GDAL is needed in these cases:

1. **You import ``osgeo`` directly** (``from osgeo import gdal, ogr,
   osr``). Install the dedicated ``[gdal]`` extra, pinned to your system
   libgdal — the OSGeo ``gdal`` wheel must match the installed libgdal
   version exactly, which a bare ``pip install siege-utilities[geo,gdal]``
   does *not* guarantee (it resolves the newest ``gdal`` in ``>=3.6,<4``).
   Install system GDAL first, then pin to it — this is the path CI
   exercises::

       # Ubuntu / Debian
       sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev
       pip install siege-utilities[geo]
       pip install "gdal==$(gdal-config --version)"

2. **GeoDjango / PostGIS** (``[geodjango]``). Django's
   ``django.contrib.gis`` backend loads the system libgdal directly (via
   ctypes), so it needs ``gdal-bin libgdal-dev`` installed, but **not**
   the OSGeo ``gdal`` Python package::

       sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev
       pip install siege-utilities[geodjango]

3. **Building Fiona or Pyogrio from source.** If pip cannot use a compatible
   wheel and builds either package locally, install the GDAL development
   libraries first. This does not mean the ``[gdal]`` extra is installed;
   that extra provides the native ``osgeo`` Python bindings. See the
   `Fiona <https://fiona.readthedocs.io/en/stable/install.html>`_ and
   `Pyogrio <https://pyogrio.readthedocs.io/en/latest/install.html>`_
   installation prerequisites.

System Dependencies (only for the cases above)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ubuntu / Debian::

    sudo apt-get update
    sudo apt-get install -y \
        gdal-bin libgdal-dev \
        libgeos-dev libgeos++-dev \
        libproj-dev proj-bin \
        libspatialindex-dev \
        libsqlite3-mod-spatialite
    pip install "gdal==$(gdal-config --version)"   # only if you need osgeo

macOS (Homebrew)::

    brew install gdal geos proj spatialindex
    pip install "gdal==$(gdal-config --version)"   # only if you need osgeo

Windows (conda)::

    conda install -c conda-forge gdal geopandas
    pip install siege-utilities[geo]

Choosing the Right Extras
-------------------------

.. list-table::
   :header-rows: 1

   * - Extra
     - System GDAL?
     - What You Get
   * - ``[geo]``
     - No (bundled in wheels)
     - GeoPandas, Shapely, Fiona, PyProj, spatial joins, choropleths,
       isochrones, interpolation — the full pure-Python geo stack
   * - ``[gdal]``
     - Yes (version-matched)
     - The native OSGeo ``gdal`` Python bindings (``from osgeo import
       gdal``). Add on top of ``[geo]`` only when you import ``osgeo``
       directly; pin to ``gdal==$(gdal-config --version)``
   * - ``[geodjango]``
     - Yes (libgdal at runtime)
     - Django ORM + DRF-GIS + PostGIS spatial queries

Common Errors
--------------

**"Could not find GDAL library" (django.core.exceptions.ImproperlyConfigured)**
    Only relevant to GeoDjango/PostGIS. Install system GDAL
    (``gdal-bin libgdal-dev``); plain ``[geo]`` does not need it.

**"OSError: cannot load library 'libgeos_c.so'"**
    GEOS not installed (GeoDjango path). On Ubuntu: ``sudo apt install libgeos-dev``.

**"ModuleNotFoundError: No module named 'osgeo'"**
    You imported the native OSGeo bindings without the ``[gdal]`` extra.
    Install system GDAL, then ``pip install "gdal==$(gdal-config --version)"``.

**"Python bindings of GDAL X require at least libgdal X, but Y was found"**
    The OSGeo ``gdal`` wheel does not match your system libgdal. Pin it:
    ``pip install "gdal==$(gdal-config --version)"``. Do not rely on a bare
    ``[geo,gdal]``, which installs the newest compatible ``gdal``.

**DuckDB spatial "Extension ... not found"**
    DuckDB spatial extension needs internet access on first load. Run::

        import duckdb
        conn = duckdb.connect()
        conn.execute("INSTALL spatial; LOAD spatial")

**PostGIS "relation does not exist"**
    Run migrations first: ``python manage.py migrate``.
    Ensure PostGIS extension is enabled: ``CREATE EXTENSION IF NOT EXISTS postgis;``
