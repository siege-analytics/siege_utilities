Distributed Computing
====================

The distributed computing module provides utilities for working with Hadoop Distributed File System (HDFS) and Apache Spark.

Module Overview
--------------

.. automodule:: siege_utilities.distributed
   :members:
   :undoc-members:
   :show-inheritance:

HDFS Configuration
-----------------

.. automodule:: siege_utilities.distributed.hdfs_config
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.distributed.hdfs_config.create_cluster_config
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_config.create_geocoding_config
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_config.create_hdfs_config
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_config.create_local_config
   :noindex:

Usage Examples
-------------

Basic HDFS configuration:

.. code-block:: python

   import siege_utilities
   
   # Create local HDFS configuration
   local_config = siege_utilities.create_local_config()
   print(local_config)
   
   # Create cluster configuration
   cluster_config = siege_utilities.create_cluster_config(
       namenode='hdfs://namenode:8020',
       username='hdfs'
   )
   
   # Create geocoding-specific configuration
   geo_config = siege_utilities.create_geocoding_config(
       api_key='your_api_key',
       rate_limit=1000
   )

HDFS Operations
--------------

.. automodule:: siege_utilities.distributed.hdfs_operations
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.distributed.hdfs_operations.create_hdfs_operations
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_operations.setup_distributed_environment
   :noindex:

HDFS Legacy Operations
---------------------

.. automodule:: siege_utilities.distributed.hdfs_legacy
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.distributed.hdfs_legacy.check_hdfs_status
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_legacy.get_quick_file_signature
   :noindex:

Usage Examples
-------------

HDFS operations:

.. code-block:: python

   # Create HDFS operations instance
   hdfs_ops = siege_utilities.create_hdfs_operations()
   
   # Setup distributed environment
   siege_utilities.setup_distributed_environment()
   
   # Check HDFS status
   status = siege_utilities.check_hdfs_status()
   print(f"HDFS Status: {status}")
   
   # Get file signature
   signature = siege_utilities.get_quick_file_signature('/path/to/file')

Unit Tests
----------

The distributed computing modules have comprehensive test coverage:

.. code-block:: text

   ✅ test_spark_utils.py - Spark utilities tests pass
   
   Test Coverage:
   - HDFS configuration creation
   - HDFS operations setup
   - Distributed environment configuration
   - File signature generation
   - HDFS status checking

Test Results: All distributed computing tests pass successfully.
