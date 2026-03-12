Welcome to Siege Utilities documentation!
========================================

Siege Utilities is a comprehensive Python utilities package with **enhanced auto-discovery** that automatically imports and makes all functions mutually available across modules.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   getting_started
   architecture_diagram
   autodiscovery

.. toctree::
   :maxdepth: 2
   :caption: Core Utilities:

   core_utilities
   string_utilities
   logging_utilities

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

   **v3.10.0** (March 2026) — Latest on `PyPI <https://pypi.org/project/siege-utilities/>`_.

   Key capabilities:

   - **Tiered Geo Extras**: ``[geo-lite]`` (no GDAL) / ``[geo]`` / ``[geodjango]``
   - **Google Workspace Write APIs**: Sheets, Docs, Slides, Drive via ``GoogleWorkspaceClient``
   - **Multi-Account Management**: ``GoogleAccount`` model, ``GoogleAccountRegistry``, ``Person`` integration
   - **Isochrone Quality**: Domain exceptions, retry, configurable CRS, method dispatch
   - **Python 3.11–3.14** compatibility with raised dependency floors
   - **Census Data Intelligence**: API client, boundary downloads, dataset selection
   - **Person/Actor Models**: Pydantic-based identity and contact management
   - **Report Generation**: PDF (ReportLab), PowerPoint, branded multi-client reports
   - **Distributed Computing**: Spark utilities, HDFS operations
   - **1884 tests passing**

   Install: ``pip install siege-utilities``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
