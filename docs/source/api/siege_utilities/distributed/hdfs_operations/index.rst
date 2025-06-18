siege_utilities.distributed.hdfs_operations
===========================================

.. py:module:: siege_utilities.distributed.hdfs_operations

.. autoapi-nested-parse::

   Abstract HDFS Operations - Fully Configurable and Reusable
   Zero hard-coded project dependencies



Classes
-------

.. autoapisummary::

   siege_utilities.distributed.hdfs_operations.AbstractHDFSOperations


Functions
---------

.. autoapisummary::

   siege_utilities.distributed.hdfs_operations._default_hash_function
   siege_utilities.distributed.hdfs_operations._default_quick_signature
   siege_utilities.distributed.hdfs_operations._ensure_directory_exists
   siege_utilities.distributed.hdfs_operations.create_hdfs_operations
   siege_utilities.distributed.hdfs_operations.setup_distributed_environment


Module Contents
---------------

.. py:class:: AbstractHDFSOperations(config)

   Abstract HDFS Operations class that can be configured for any project


   .. py:method:: check_hdfs_status() -> bool

      Check if HDFS is accessible



   .. py:method:: create_spark_session()

      Create Spark session using configuration



   .. py:method:: setup_distributed_environment(data_path: Optional[str] = None, dependency_paths: Optional[List[str]] = None)

      Main setup function with proper verification



   .. py:method:: sync_directory_to_hdfs(local_path: Optional[str] = None, hdfs_subdir: str = 'inputs') -> Tuple[Optional[str], Optional[Dict]]

      Sync local directory/file to HDFS with proper verification



   .. py:attribute:: config


   .. py:attribute:: data_sync_cache


   .. py:attribute:: dependencies_cache


   .. py:attribute:: hash_func


   .. py:attribute:: python_deps_zip


   .. py:attribute:: quick_signature_func


.. py:function:: _default_hash_function(file_path: str) -> str

   Default hash function using built-in hashlib


.. py:function:: _default_quick_signature(file_path: str) -> str

   Default quick signature using file stats


.. py:function:: _ensure_directory_exists(path: str)

   Ensure directory exists


.. py:function:: create_hdfs_operations(config)

   Factory function to create HDFS operations instance


.. py:function:: setup_distributed_environment(config, data_path: Optional[str] = None, dependency_paths: Optional[List[str]] = None)

   Convenience function to set up distributed environment


