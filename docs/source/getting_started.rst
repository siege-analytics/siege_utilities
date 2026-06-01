Getting Started
===============

siege_utilities is a thesaurus of space-time composition tools. The library
ties events to coordinates in space-time, then extrapolates significances from
placement. **Geo is the gravitational center** — all domain modules produce
events that need space-time location before they become analytically useful.

Installation
------------

.. code-block:: bash

   # Core (lightweight, no geospatial C deps)
   pip install siege-utilities

   # Geo-lite (shapely, pyproj, geopy — no GDAL)
   pip install siege-utilities[geo-lite]

   # Full geospatial (requires GDAL/GEOS/PROJ system libraries)
   pip install siege-utilities[geo]

   # GeoDjango spatial platform
   pip install siege-utilities[geodjango]

Quick Start: The Composition Chain
----------------------------------

The canonical workflow is: **address → geocoder → GEOID → boundary → overlay → report**.

1. Geocode an Address
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.geocoding import geocode_address

   result = geocode_address("1600 Pennsylvania Ave NW, Washington, DC")
   # Returns lat/lon coordinates for spatial operations

2. Normalize a GEOID
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.geoid_utils import normalize_geoid

   # Census GEOIDs are the universal join key
   geoid = normalize_geoid("06037", level="county")  # Los Angeles County

3. Download Census Boundaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.spatial_data import census_source

   counties = census_source.get_geographic_boundaries(
       year=2020,
       geographic_level="county",
       state_fips="06",
   )

4. Use Pluggable Boundary Providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.providers.boundary_providers import resolve_boundary_provider

   provider = resolve_boundary_provider("census_tiger")
   boundary = provider.get_boundary(state_fips="06", level="county", year=2020)

5. Set a Project-Wide CRS
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.crs import set_default_crs

   set_default_crs("EPSG:2263")  # NY State Plane

Engine-Agnostic DataFrames
--------------------------

Same analysis at different scales without rewriting:

.. code-block:: python

   from siege_utilities.engines import DataFrameEngine

   # pandas for exploration
   engine = DataFrameEngine("pandas")

   # DuckDB for medium scale
   engine = DataFrameEngine("duckdb")

   # Spark for distribution
   engine = DataFrameEngine("spark")

Credential Management
---------------------

Credentials come from environment variables first, with 1Password CLI fallback:

.. code-block:: python

   from siege_utilities.config.credential_manager import get_credential

   api_key = get_credential("CENSUS_API_KEY")

Lazy Loading
------------

The library uses PEP 562 ``__getattr__`` for lazy loading. You can import one
piece in a Lambda or notebook without pulling the whole dependency tree:

.. code-block:: python

   # Only loads geo when you access it
   from siege_utilities.geo import normalize_geoid

   # Only loads reporting when you access it
   from siege_utilities.reporting import ReportGenerator

Package Overview
----------------

.. list-table::
   :widths: 20 60 20
   :header-rows: 1

   * - Package
     - Purpose
     - Layer
   * - **geo/**
     - Boundaries, geocoding, spatial transforms, Census data, isochrones, redistricting
     - Core (gravitational center)
   * - **political/**
     - DDL and entities: Seat, OfficeTerm, RedistrictingPlan
     - Domain
   * - **economic/**
     - BLS QCEW, economic indicators
     - Domain
   * - **education/**
     - NCES data, school districts
     - Domain
   * - **survey/**
     - Survey analysis, crosstabs, weighting, significance
     - Domain
   * - **analytics/**
     - GA, Snowflake, data.world, Facebook connectors
     - Domain
   * - **engines/**
     - Multi-engine DataFrame abstraction (pandas, DuckDB, Spark, PostGIS)
     - Infrastructure
   * - **distributed/**
     - Spark utilities, HDFS operations
     - Infrastructure
   * - **databricks/**
     - Databricks-specific connectors and bridge pattern
     - Infrastructure
   * - **config/**
     - User/project config, credentials, database connections
     - Infrastructure
   * - **data/**
     - Data loading, MOE propagation, cross-tabulation, sample datasets
     - Data
   * - **reference/**
     - Reference lookups (NAICS, SOC, state FIPS)
     - Data
   * - **reporting/**
     - Charts, PDFs, PowerPoint, hex cartograms, 3D maps
     - Output
   * - **core/**
     - Logging, string utilities, SQL safety
     - Foundation
   * - **files/**
     - File operations, hashing, remote downloads
     - Foundation
