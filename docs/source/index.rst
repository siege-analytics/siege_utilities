Siege Utilities Documentation
=============================

.. image:: https://img.shields.io/pypi/v/siege-utilities.svg
   :target: https://pypi.org/project/siege-utilities/
   :alt: PyPI version

.. image:: https://img.shields.io/badge/docs-GitHub%20Pages-blue
   :target: https://siege-analytics.github.io/siege_utilities/
   :alt: Documentation

**Enhanced Auto-Discovery Python Utilities Package**

🚀 **Revolutionary Feature**: All 500+ functions automatically discovered and mutually available without imports!

Quick Start
-----------

.. code-block:: python

   import siege_utilities

   # Instant access to ALL functions
   info = siege_utilities.get_package_info()
   print(f"Functions available: {info['total_functions']}")

   # File operations
   hash_val = siege_utilities.get_file_hash("myfile.txt")
   siege_utilities.ensure_path_exists("data/processed")

   # Logging (available everywhere)
   siege_utilities.log_info("Processing started")

   # Distributed computing (if PySpark available)
   try:
       config = siege_utilities.create_hdfs_config("/data")
       spark, data_path = siege_utilities.setup_distributed_environment()
   except NameError:
       siege_utilities.log_warning("Distributed features not available")

Installation
------------

.. code-block:: bash

   # Basic installation
   pip install siege-utilities

   # With optional features
   pip install siege-utilities[distributed,geo,dev]

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   auto_discovery_system
   examples

.. toctree::
   :maxdepth: 1
   :caption: Complete API Reference

   all_functions
   api/index

.. toctree::
   :maxdepth: 2
   :caption: Modules

   api/siege_utilities

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`