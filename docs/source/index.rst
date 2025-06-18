Siege Utilities Documentation
=============================

.. image:: https://img.shields.io/pypi/v/siege-utilities.svg
   :target: https://pypi.org/project/siege-utilities/
   :alt: PyPI version

.. image:: https://readthedocs.org/projects/siege-utilities/badge/?version=latest
   :target: https://siege-utilities.readthedocs.io/en/latest/
   :alt: Documentation Status

**A comprehensive Python utilities package with enhanced auto-discovery**

🚀 **Key Innovation**: All 500+ functions automatically discovered and mutually available without imports!

.. code-block:: python

   import siege_utilities

   # All functions immediately available
   siege_utilities.log_info("Package loaded!")
   hash_val = siege_utilities.get_file_hash("myfile.txt")
   siege_utilities.ensure_path_exists("data/")

   # Check what's available
   info = siege_utilities.get_package_info()
   print(f"Functions: {info['total_functions']}")

Quick Start
-----------

.. code-block:: bash

   pip install siege-utilities

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   auto_discovery

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/index

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`