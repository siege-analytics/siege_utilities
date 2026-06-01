Library Architecture
====================

Strategic Intent
----------------

siege_utilities is a thesaurus of space-time composition tools. Every piece
exists to serve one question: *what happened, where, when, and what does
proximity imply?*

The library ties events to coordinates in space-time, then extrapolates
significances and meanings from placement. Domain packages (political,
economic, education, survey, analytics) produce events. Geo locates them.
Engines scale them. Reporting presents them.

Composition Chain
-----------------

The canonical composition chain that drives the architecture::

    address → geocoder → GEOID → boundary provider → demographic overlay → choropleth or report

Every module's position in the library derives from where it sits in this
chain. Geo is at the center because everything passes through spatial location.

Layer Model
-----------

.. code-block:: text

    ┌─────────────────────────────────────────────────────────┐
    │                     REPORTING                           │
    │  charts · PDFs · PowerPoint · hex cartograms · 3D maps  │
    └────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────┐
    │                  DOMAIN PACKAGES                         │
    │  political · economic · education · survey · analytics   │
    └────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────┐
    │              GEO (gravitational center)                   │
    │                                                          │
    │  Boundaries    Census data    Redistricting   Isochrones │
    │  Geocoding     Spatial joins  CRS management  GEOID ops  │
    │  Interpolation Gazetteers     Place history   Overlays   │
    │                                                          │
    │  Providers: Census TIGER · GADM · RDH · Nominatim ·     │
    │             TAMU · Census Batch · ORS · Valhalla         │
    └────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────┐
    │                     ENGINES                              │
    │  pandas · DuckDB · Spark+Sedona · PostGIS                │
    │  (same analysis at different scales without rewriting)   │
    └────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────┐
    │                   FOUNDATION                             │
    │  core · config · files · data · reference · schema       │
    │  credentials · logging · lazy loading (PEP 562)          │
    └─────────────────────────────────────────────────────────┘

Package Structure
-----------------

.. code-block:: text

    siege_utilities/
    ├── geo/            ← gravitational center
    │   ├── providers/      boundary, geocoder, isochrone providers
    │   ├── census/         Census API, TIGER, catalog, variables
    │   ├── django/         GeoDjango models, services, management commands
    │   ├── gazetteers/     Census, Wikidata gazetteers
    │   ├── interpolation/  areal interpolation (tobler)
    │   ├── overlays/       demographic, election, redistricting overlays
    │   ├── schemas/        Pydantic schemas for geo entities
    │   ├── temporal/       temporal queries and store
    │   ├── timeseries/     longitudinal data, trend classification
    │   └── ...             CRS, geocoding, grids, isochrones, GEOID utils
    │
    ├── political/      DDL and entities (Seat, OfficeTerm, RedistrictingPlan)
    ├── economic/       BLS QCEW, economic indicators
    ├── education/      NCES data, school districts
    ├── survey/         Survey analysis, crosstabs, weighting
    ├── analytics/      GA, Snowflake, data.world, Facebook connectors
    │
    ├── engines/        Multi-engine DataFrame abstraction
    ├── distributed/    Spark utilities, HDFS operations
    ├── databricks/     Databricks bridge pattern (Spark ↔ GeoPandas)
    ├── trino/          Trino federation connector
    │
    ├── data/           Data loading, MOE propagation, sample datasets
    ├── reference/      Reference lookups (NAICS, SOC, state FIPS)
    ├── schema/         Schema definitions and migration
    ├── identifiers/    Entity identification, UUID generation
    ├── hygiene/        Data cleaning, docstring generation
    │
    ├── reporting/      Charts, PDFs, PowerPoint, hex cartograms, 3D maps
    ├── profiles/       Profile and branding management
    │
    ├── core/           Logging, string utilities, SQL safety
    ├── config/         User/project config, credentials, database connections
    ├── files/          File operations, hashing, remote downloads
    ├── git/            Git utilities and branch analysis
    ├── admin/          Administrative/org utilities
    ├── cache.py        Caching helpers
    ├── testing/        Test fixtures and helpers
    └── exceptions.py   SiegeError hierarchy

Architectural Decisions
-----------------------

1. **Geo is the gravitational center.** All domain modules produce events
   that need space-time location. Changes to geo propagate everywhere.

2. **Engine-agnostic DataFrame.** Same analysis at different scales: pandas
   for exploration, DuckDB for medium, Spark for distribution, PostGIS for
   persistence. Do not create single-consumer abstractions.

3. **OSGeo preferred, alternatives when constrained.** GDAL/OGR, PROJ, GEOS
   via Shapely are defaults. When the target cannot run C libraries
   (Databricks, Lambda), use Sedona, DuckDB-spatial, or pure-Python.

4. **Databricks and Snowflake are first-class targets.** The ``databricks/``
   bridge pattern (Spark → driver-side GeoPandas → back to Spark) is
   architectural, not a workaround.

5. **Pluggable providers with shared contracts.** Same failure mode, same
   return shape, same column names across all providers in a family.

6. **Lazy loading by design.** PEP 562 ``__getattr__`` so you can import one
   piece in a Lambda without pulling the whole library.

7. **Credential management via external tools.** 1Password CLI, env vars,
   Databricks secret scopes. Never hardcoded.

8. **Temporal awareness is first-class.** Redistricting plans have effective
   dates. Congressional districts depend on congress number matching vintage.
   Not just "where" but "where-when."

Design Tensions (Resolved)
--------------------------

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Tension
     - Resolution
   * - OSGeo vs. Databricks
     - OSGeo preferred; non-GDAL paths are gaps to fill, not choices to accept
   * - Engine-agnostic vs. technology-appropriate
     - Abstraction for general case; native idioms when dropping to Spark SQL or raw pandas
   * - Pythonic vs. PySpark
     - Python idioms always; Scala is a far-off dream
   * - Functional vs. logging
     - Composition and immutability, not strict purity; logging wraps pure cores
   * - Lazy loading vs. SU-1
     - ``__getattr__`` must never catch ImportError; let it propagate
   * - Notebooks: disposable vs. strategic
     - Demonstrate intent; must reflect current library state; foundations non-negotiable
   * - Fuzzy matching scope
     - Library provides the mechanism; heavy entity resolution belongs downstream
   * - siege_zsh dependency
     - Reference architecture showing target frameworks; code detects and leverages but doesn't hard-fail
   * - Legibility vs. elegance
     - Legibility within functions; elegance across modules; module boundary is the threshold
