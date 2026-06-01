Siege Utilities
===============

A thesaurus of space-time composition tools. Every piece exists to serve one
question: *what happened, where, when, and what does proximity imply?*

The library ties events to coordinates in space-time, then extrapolates
significances and meanings from placement. Domain packages produce events.
**Geo** locates them. **Engines** scale them. **Reporting** presents them.

The canonical composition chain::

    address → geocoder → GEOID → boundary provider → demographic overlay → choropleth or report

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started
   installation_troubleshooting
   architecture_diagram

.. toctree::
   :maxdepth: 2
   :caption: Geospatial (the gravitational center)

   packages/geo
   geocoding
   packages/geo_django

.. toctree::
   :maxdepth: 2
   :caption: Domain Packages

   packages/political
   packages/economic
   packages/education
   packages/survey
   packages/analytics

.. toctree::
   :maxdepth: 2
   :caption: Engines & Infrastructure

   packages/engines
   packages/distributed
   packages/databricks
   packages/trino
   packages/config

.. toctree::
   :maxdepth: 2
   :caption: Data & Reference

   packages/data
   packages/reference
   packages/schema
   packages/identifiers
   packages/hygiene

.. toctree::
   :maxdepth: 2
   :caption: Output & Reporting

   packages/reporting
   packages/profiles

.. toctree::
   :maxdepth: 2
   :caption: Utilities

   packages/core
   packages/files
   packages/git
   packages/admin
   packages/cache
   packages/testing
   exception_hierarchy

.. toctree::
   :maxdepth: 2
   :caption: Examples & Notebooks

   notebooks

.. toctree::
   :maxdepth: 2
   :caption: Development

   contributor_governance
   coding_style
   pr_review_rubric
   testing_guide
   change_classification_and_release_policy
   repository_hygiene
   license_model

.. note::

   **v3.21.0** (June 2026) — `PyPI <https://pypi.org/project/siege-utilities/>`_

   Key capabilities:

   - **Geo is the gravitational center** — boundaries, geocoding, spatial transforms,
     isochrones, Census data intelligence, redistricting analysis
   - **Engine-agnostic DataFrame** — pandas, DuckDB, Spark+Sedona, PostGIS
   - **Temporal political models** — CongressionalTerm, Seat, Race, RedistrictingPlan
   - **Pluggable providers** — Census TIGER, GADM, RDH boundary providers; Census,
     Nominatim, TAMU geocoders
   - **PEP 562 lazy loading** — import one piece without pulling the whole library
   - **Tiered geo extras** — ``[geo-lite]`` / ``[geo]`` / ``[geodjango]``
   - **32 Jupyter notebooks** organized by domain
   - **Report generation** — PDF, PowerPoint, branded multi-client reports, hex cartograms

   Install: ``pip install siege-utilities``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
