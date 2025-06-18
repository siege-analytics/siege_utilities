siege_utilities.distributed.hdfs_config
=======================================

.. py:module:: siege_utilities.distributed.hdfs_config

.. autoapi-nested-parse::

   Abstract HDFS Configuration
   Configurable settings for HDFS operations - no hard-coded project dependencies



Classes
-------

.. autoapisummary::

   siege_utilities.distributed.hdfs_config.HDFSConfig


Functions
---------

.. autoapisummary::

   siege_utilities.distributed.hdfs_config.create_cluster_config
   siege_utilities.distributed.hdfs_config.create_geocoding_config
   siege_utilities.distributed.hdfs_config.create_hdfs_config
   siege_utilities.distributed.hdfs_config.create_local_config


Module Contents
---------------

.. py:class:: HDFSConfig

   Configuration class for HDFS operations


   .. py:method:: __post_init__()

      Set up defaults after initialization



   .. py:method:: get_cache_path(filename: str) -> pathlib.Path

      Get path for cache files



   .. py:method:: get_optimal_partitions() -> int

      Calculate optimal partitions for I/O heavy workloads



   .. py:method:: log_error(message: str)

      Log error message using configured function



   .. py:method:: log_info(message: str)

      Log info message using configured function



   .. py:attribute:: app_name
      :type:  str
      :value: 'SparkDistributedProcessing'



   .. py:attribute:: cache_directory
      :type:  Optional[str]
      :value: None



   .. py:attribute:: data_path
      :type:  Optional[str]
      :value: None



   .. py:attribute:: enable_sedona
      :type:  bool
      :value: True



   .. py:attribute:: executor_cores
      :type:  Optional[int]
      :value: None



   .. py:attribute:: executor_memory
      :type:  str
      :value: '2g'



   .. py:attribute:: force_sync
      :type:  bool
      :value: False



   .. py:attribute:: hash_func
      :type:  Optional[Callable[[str], str]]
      :value: None



   .. py:attribute:: hdfs_base_directory
      :type:  str
      :value: '/data/'



   .. py:attribute:: hdfs_copy_timeout
      :type:  int
      :value: 300



   .. py:attribute:: hdfs_timeout
      :type:  int
      :value: 10



   .. py:attribute:: heartbeat_interval
      :type:  str
      :value: '60s'



   .. py:attribute:: log_error_func
      :type:  Optional[Callable[[str], None]]
      :value: None



   .. py:attribute:: log_info_func
      :type:  Optional[Callable[[str], None]]
      :value: None



   .. py:attribute:: network_timeout
      :type:  str
      :value: '800s'



   .. py:attribute:: num_executors
      :type:  Optional[int]
      :value: None



   .. py:attribute:: quick_signature_func
      :type:  Optional[Callable[[str], str]]
      :value: None



   .. py:attribute:: spark_log_level
      :type:  str
      :value: 'WARN'



.. py:function:: create_cluster_config(data_path: str, **kwargs) -> HDFSConfig

   Create config optimized for cluster deployment


.. py:function:: create_geocoding_config(data_path: str, **kwargs) -> HDFSConfig

   Create config optimized for geocoding workloads


.. py:function:: create_hdfs_config(**kwargs) -> HDFSConfig

   Factory function to create HDFS configuration


.. py:function:: create_local_config(data_path: str, **kwargs) -> HDFSConfig

   Create config optimized for local development


