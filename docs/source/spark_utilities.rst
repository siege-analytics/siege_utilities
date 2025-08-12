Spark Utilities
==============

The Spark utilities module provides a comprehensive collection of PySpark functions for data manipulation, mathematical operations, and data processing.

Module Overview
--------------

.. automodule:: siege_utilities.distributed.spark_utils
   :members:
   :undoc-members:
   :show-inheritance:

Functions by Category
--------------------

Mathematical Functions
~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.distributed.spark_utils.abs
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.acos
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.acosh
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.add_months
   :noindex:

Array Functions
~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.distributed.spark_utils.array
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_agg
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_append
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_compact
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_contains
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_distinct
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_except
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_insert
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_intersect
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_join
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.array_max
   :noindex:

Aggregation Functions
~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.distributed.spark_utils.aggregate
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.any_value
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.approx_count_distinct
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.approx_percentile
   :noindex:

Cryptographic Functions
~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.distributed.spark_utils.aes_decrypt
   :noindex:

.. autofunction:: siege_utilities.distributed.spark_utils.aes_encrypt
   :noindex:

Usage Examples
-------------

Basic mathematical operations:

.. code-block:: python

   from pyspark.sql import SparkSession
   from pyspark.sql.functions import col
   import siege_utilities
   
   spark = SparkSession.builder.appName("MathExample").getOrCreate()
   
   # Create sample data
   data = [("A", 1.5), ("B", -2.3), ("C", 0.0)]
   df = spark.createDataFrame(data, ["id", "value"])
   
   # Apply mathematical functions
   df = df.withColumn("abs_value", siege_utilities.abs(col("value")))
   df = df.withColumn("acos_value", siege_utilities.acos(col("value")))
   
   df.show()

Array operations:

.. code-block:: python

   # Array manipulation
   df = df.withColumn("array_col", siege_utilities.array(col("id"), col("value")))
   df = df.withColumn("distinct_array", siege_utilities.array_distinct(col("array_col")))
   df = df.withColumn("array_contains", siege_utilities.array_contains(col("array_col"), "A"))
   
   # Array aggregation
   df = df.groupBy("id").agg(
       siege_utilities.array_agg(col("value")).alias("all_values")
   )

Date operations:

.. code-block:: python

   from pyspark.sql.functions import current_date
   
   # Add months to current date
   df = df.withColumn("future_date", 
                      siege_utilities.add_months(current_date(), 3))

Unit Tests
----------

The Spark utilities module has comprehensive test coverage:

.. code-block:: text

   ✅ test_spark_utils.py - All Spark utility tests pass
   
   Test Coverage:
   - Mathematical functions (abs, acos, acosh)
   - Array operations (creation, manipulation, aggregation)
   - Date functions (add_months)
   - Aggregation functions (aggregate, any_value)
   - Cryptographic functions (AES encryption/decryption)
   - Edge cases and error handling

Test Results: All Spark utility tests pass successfully with comprehensive coverage.
