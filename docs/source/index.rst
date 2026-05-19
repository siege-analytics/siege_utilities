Welcome to Siege Utilities documentation!
========================================

Siege Utilities is a comprehensive Python utilities package with **enhanced auto-discovery** that automatically imports and makes all functions mutually available across modules.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   getting_started
   installation_troubleshooting
   architecture_diagram
   autodiscovery

.. toctree::
   :maxdepth: 2
   :caption: Core Utilities:

   core_utilities
   string_utilities
   logging_utilities
   exception_hierarchy

.. toctree::
   :maxdepth: 2
   :caption: Distributed Computing:

   distributed_computing
   hdfs_operations
   spark_utilities

.. toctree::
   :maxdepth: 2
   :caption: File Operations:

   file_operations
   file_hashing
   remote_operations
   shell_operations

.. toctree::
   :maxdepth: 2
   :caption: Geographic & Analytics:

   geo
   google_workspace
   analytics
   mapping_and_reporting

.. toctree::
   :maxdepth: 2
   :caption: Notebooks & Examples:

   notebooks

.. toctree::
   :maxdepth: 2
   :caption: Development & Testing:

   contributor_governance
   coding_style
   pr_review_rubric
   lint_ratchet_plan
   change_classification_and_release_policy
   repository_hygiene
   coderabbit_workflow
   license_model
   testing_guide
   api/index

.. note::

   **v3.13.0** (March 2026) — Latest on `PyPI <https://pypi.org/project/siege-utilities/>`_.

   Key capabilities:

   - **First-class geospatial** in every DataFrame engine (Pandas, DuckDB, Spark+Sedona, PostGIS)
   - **Temporal political models**: CongressionalTerm, Seat, Race, ReturnSnapshot
   - **Redistricting analysis**: Plans, districts, compactness scores, demographics
   - **Census data intelligence**: API client, boundary downloads, MOE propagation, NAICS/SOC
   - **27 Jupyter notebooks** with papermill-based automated testing
   - **Tiered Geo Extras**: ``[geo-lite]`` (no GDAL) / ``[geo]`` / ``[geodjango]``
   - **Google Workspace Write APIs**: Sheets, Docs, Slides, Drive
   - **Person/Actor Models**: Pydantic-based identity and contact management
   - **Report Generation**: PDF (ReportLab), PowerPoint, branded multi-client reports
   - **Distributed Computing**: Spark + Sedona, HDFS operations, DuckDB engine
   - **3442 tests passing**, 56% coverage

   Install: ``pip install siege-utilities``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
