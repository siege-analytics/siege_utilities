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
   analytics
   mapping_and_reporting

.. toctree::
   :maxdepth: 2
   :caption: Development & Testing:

   coding_style
   pr_review_rubric
   lint_ratchet_plan
   change_classification_and_release_policy
   testing_guide
   api/index

.. note::

   **v2.0.0** (February 2026) — Released to `PyPI <https://pypi.org/project/siege-utilities/2.0.0/>`_.

   Key capabilities:

   - **Auto-Discovery**: 500+ functions automatically imported and mutually available
   - **Person/Actor Models**: Pydantic-based identity and contact management
   - **Geographic Data**: Census boundaries, TIGER/Line, spatial queries, choropleths
   - **Analytics Connectors**: Google Analytics (GA4), with OAuth2 and service account support
   - **Report Generation**: PDF (ReportLab), PowerPoint, branded multi-client reports
   - **Distributed Computing**: Spark utilities, HDFS operations
   - **Client Profiles**: Client information, contact details, and design artifacts
   - **724 tests passing**, 30% coverage

   Install: ``pip install siege-utilities==2.0.0``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
