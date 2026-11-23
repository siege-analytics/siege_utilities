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

   about
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
   packages/connectors
   packages/config
   packages/conf
   packages/oss_unity_catalog

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
   packages/development
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

   **v5.0.0** (November 2026) — `PyPI <https://pypi.org/project/siege-utilities/5.0.0/>`_ · `Release notes <https://github.com/siege-analytics/siege_utilities/releases/tag/v5.0.0>`_

   This major release hardens file and directory creation against unsafe names,
   makes docstring generation a dry run by default, and changes the release
   process to publish only verified tags from ``main``. Review the
   `v5.0.0 migration notes <https://github.com/siege-analytics/siege_utilities/blob/main/CHANGELOG.md#500---2026-11-20>`_
   before upgrading.

   Install: ``pip install siege-utilities``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
