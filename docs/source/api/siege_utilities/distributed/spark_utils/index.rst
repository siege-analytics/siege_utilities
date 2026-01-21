siege_utilities.distributed.spark_utils
=======================================

.. py:module:: siege_utilities.distributed.spark_utils


Attributes
----------

.. autoapisummary::

   siege_utilities.distributed.spark_utils.PYSPARK_AVAILABLE
   siege_utilities.distributed.spark_utils.logger
   siege_utilities.distributed.spark_utils.new_walkability_udf
   siege_utilities.distributed.spark_utils.walkability_config


Functions
---------

.. autoapisummary::

   siege_utilities.distributed.spark_utils.atomic_write_with_staging
   siege_utilities.distributed.spark_utils.backup_full_dataframe
   siege_utilities.distributed.spark_utils.clean_and_reorder_bbox
   siege_utilities.distributed.spark_utils.compute_walkability
   siege_utilities.distributed.spark_utils.create_unique_staging_directory
   siege_utilities.distributed.spark_utils.ensure_literal
   siege_utilities.distributed.spark_utils.export_prepared_df_as_csv_to_path_using_delimiter
   siege_utilities.distributed.spark_utils.export_pyspark_df_to_excel
   siege_utilities.distributed.spark_utils.flatten_json_column_and_join_back_to_df
   siege_utilities.distributed.spark_utils.get_row_count
   siege_utilities.distributed.spark_utils.mark_valid_geocode_data
   siege_utilities.distributed.spark_utils.move_column_to_front_of_dataframe
   siege_utilities.distributed.spark_utils.pivot_summary_table_for_bools
   siege_utilities.distributed.spark_utils.pivot_summary_with_metrics
   siege_utilities.distributed.spark_utils.prepare_dataframe_for_export
   siege_utilities.distributed.spark_utils.prepare_summary_dataframe
   siege_utilities.distributed.spark_utils.print_debug_table
   siege_utilities.distributed.spark_utils.read_parquet_to_df
   siege_utilities.distributed.spark_utils.register_temp_table
   siege_utilities.distributed.spark_utils.repartition_and_cache
   siege_utilities.distributed.spark_utils.reproject_geom_columns
   siege_utilities.distributed.spark_utils.sanitise_dataframe_column_names
   siege_utilities.distributed.spark_utils.tabulate_null_vs_not_null
   siege_utilities.distributed.spark_utils.validate_geocode_data
   siege_utilities.distributed.spark_utils.validate_geometry
   siege_utilities.distributed.spark_utils.write_df_to_parquet


Module Contents
---------------

.. py:function:: atomic_write_with_staging(df: pyspark.sql.DataFrame, final_destination: str, staging_directory: str, file_format: str = 'csv', delimiter: str = ',', header: bool = True, mode: str = 'overwrite') -> bool

   Performs atomic write operations using a staging directory to prevent partial/corrupted files.


.. py:function:: backup_full_dataframe(df, step_name)

   """
   Utility function: backup full dataframe.

   Part of Siege Utilities Utilities module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.backup_full_dataframe()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: clean_and_reorder_bbox(df, bbox_col)

   Removes brackets from bounding box strings and reorders coordinates for Sedona.

   Assumes input is a comma separated list in the order:
     min latitude, max latitude, min longitude, max longitude
   Produces an array in the order: [min_lon, min_lat, max_lon, max_lat]


.. py:function:: compute_walkability(distance)

   """
   Utility function: compute walkability.

   Part of Siege Utilities Utilities module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.compute_walkability()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: create_unique_staging_directory(base_path, operation_name='operation')

   Creates a unique staging directory for atomic operations.


.. py:function:: ensure_literal(value)

   Convert any value to a Spark literal (Column) unless it is already a Spark Column.

   :param value: Any value to be converted.

   :returns: A pyspark.sql.Column containing the value (or its Spark literal),
             unless the value is already a Column.


.. py:function:: export_prepared_df_as_csv_to_path_using_delimiter(df: pyspark.sql.DataFrame, write_path: pathlib.Path, delimiter: str = ',') -> bool

   Exports DataFrame **with necessary transformations** to ensure Spark compatibility.

   :param df: Target DataFrame
   :param write_path: Pathlib object for export destination
   :param delimiter: CSV delimiter (default is comma)
   :return: bool indicating success/failure

   Applies `prepare_dataframe_for_export()` to prevent Spark export issues.


.. py:function:: export_pyspark_df_to_excel(df, file_name='output.xlsx', sheet_name='Sheet1')

   Converts a PySpark DataFrame to a Pandas DataFrame and exports it to an Excel file.

   :param spark_df: The PySpark DataFrame to export.
   :type spark_df: pyspark.sql.DataFrame
   :param file_name: The name of the output Excel file.
   :type file_name: str
   :param sheet_name: The sheet name in the Excel file.
   :type sheet_name: str

   :returns: None


.. py:function:: flatten_json_column_and_join_back_to_df(df: pyspark.sql.DataFrame, json_column: str, prefix: str = 'json_column_', logger: Optional[any] = None, drop_original: bool = True, explode_arrays: bool = False, flatten_level: str = 'shallow', verbose: bool = False, sample_size: int = 5, show_samples: bool = True) -> pyspark.sql.DataFrame

   Flattens a JSON column in a Spark DataFrame, extracting fields and adding them as columns.
   Has fallback mechanisms for corrupt JSON data.

   :param df: The input Spark DataFrame.
   :type df: DataFrame
   :param json_column: The name of the column containing JSON strings.
   :type json_column: str
   :param prefix: Prefix to add to the flattened column names. Defaults to "json_column_".
   :type prefix: str, optional
   :param logger: Logger object for logging messages. Defaults to None.
   :type logger: Optional[any], optional
   :param drop_original: Whether to drop the original JSON column after flattening. Defaults to True.
   :type drop_original: bool, optional
   :param explode_arrays: Whether to explode array columns. Defaults to False.
   :type explode_arrays: bool, optional
   :param flatten_level: "shallow" or "deep" flattening. Defaults to "shallow".
   :type flatten_level: str, optional
   :param verbose: Controls whether to log detailed messages. Defaults to False.
   :type verbose: bool, optional
   :param sample_size: Number of samples to check. Defaults to 5.
   :type sample_size: int, optional
   :param show_samples: Whether to display sample data. Defaults to False.
   :type show_samples: bool, optional

   :returns: The DataFrame with the JSON column flattened.
   :rtype: DataFrame


.. py:function:: get_row_count(df: pyspark.sql.DataFrame) -> Optional[int]

   Returns the count of rows in the dataframe.

   :param df: Input Spark DataFrame.
   :type df: DataFrame

   :returns: Row count or None if an error occurred.
   :rtype: Optional[int]


.. py:function:: mark_valid_geocode_data(df, lat_col_name: str, lon_col_name: str, output_col_name: str = 'is_valid')

   Adds a boolean flag column to the DataFrame indicating whether the geographic coordinates are valid.

   A set of coordinates is considered valid if:
   - The latitude and longitude columns are not null.
   - The latitude is between -90 and 90.
   - The longitude is between -180 and 180.

   Unlike filtering functions, this function preserves all rows in the DataFrame by simply marking
   each row with a True (valid) or False (invalid) value in the new output column.

   :param df: The Spark DataFrame containing geocode data.
   :type df: DataFrame
   :param lat_col_name: The name of the latitude column.
   :type lat_col_name: str
   :param lon_col_name: The name of the longitude column.
   :type lon_col_name: str
   :param output_col_name: The name of the output column to store the validity flag.
                           Defaults to "is_valid".
   :type output_col_name: str, optional

   :returns: A new DataFrame with an additional column indicating geocode validity.
   :rtype: DataFrame


.. py:function:: move_column_to_front_of_dataframe(df: pyspark.sql.DataFrame, column_name: str) -> Optional[pyspark.sql.DataFrame]

   """
   Utility function: move column to front of dataframe.

   Part of Siege Utilities Utilities module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.move_column_to_front_of_dataframe()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: pivot_summary_table_for_bools(df, columns, spark)

   Generate a pivot table summary for given boolean flag columns in a DataFrame.
   The pivot table includes three metrics:
      - "Count": Sum of rows where the flag is True.
      - "Percentage (%)": Percentage relative to total records.
      - "Total": The total number of records (repeated for each column).
   All numeric values are converted to float to ensure a consistent type.

   :param df: The source Spark DataFrame.
   :type df: DataFrame
   :param columns: List of column names (assumed to be boolean flags) to summarize.
   :type columns: list
   :param spark: The active Spark session.
   :type spark: SparkSession

   :returns: A Spark DataFrame representing the pivot table.
   :rtype: DataFrame


.. py:function:: pivot_summary_with_metrics(df, group_col, pivot_col, spark)

   Generate a pivot summary for a categorical column against one or more grouping columns,
   including rows for "Count", "Percentage (%)", and "Total" for each group.

   :param df: The source Spark DataFrame.
   :type df: DataFrame
   :param group_col: The column name (or list of column names) used for grouping.
                     For example, "geocode_granularity" or ["state", "region"].
   :type group_col: str or list
   :param pivot_col: The categorical column to pivot on (e.g., "final_geocode_choice").
   :type pivot_col: str
   :param spark: The active Spark session.
   :type spark: SparkSession

   :returns:

             A Spark DataFrame in which each original group appears as three rows:
                        one for the counts, one for the percentages, and one for the total count.
                        The non-grouping columns represent each distinct pivot column value.
   :rtype: DataFrame


.. py:function:: prepare_dataframe_for_export(df, logger_func=None)

   Prepares a DataFrame for export (e.g., to CSV) by:
     - Converting binary columns to Base64-encoded strings.
     - Casting simple scalar fields (non-string, non-complex) to strings.
     - Dropping intermediate columns (e.g., 'parsed_json') if present.
     - Converting complex (StructType/ArrayType) columns to JSON strings.
     - Handling null values appropriately.

   :param df: Spark DataFrame to prepare
   :param logger_func: Optional logging function (defaults to print)

   :returns: The transformed DataFrame with all columns as strings or JSON strings.


.. py:function:: prepare_summary_dataframe(data_tuples, column_names=['metric', 'value'], logger_func=None)

   Helper function to create summary DataFrames with consistent string types.
   Prevents type merging errors by ensuring all values are strings.

   :param data_tuples: List of tuples with data
   :param column_names: Column names for the DataFrame
   :param logger_func: Optional logging function

   :returns: Spark DataFrame with all string columns


.. py:function:: print_debug_table(spark_df, title)

   Helper function to convert a Spark DataFrame into a Pandas DataFrame,
   format it using tabulate, and print the result with a title.


.. py:function:: read_parquet_to_df(spark: pyspark.sql.SparkSession, path: str) -> Optional[pyspark.sql.DataFrame]

   Reads a Parquet file into a Spark DataFrame.

   :param spark: Active Spark session.
   :type spark: SparkSession
   :param path: Path to the Parquet file.
   :type path: str

   :returns: Loaded DataFrame or None if an error occurred.
   :rtype: Optional[DataFrame]


.. py:function:: register_temp_table(df: pyspark.sql.DataFrame, table_name: str) -> bool

   Registers a temporary view from a dataframe.

   :param df: Input Spark DataFrame.
   :type df: DataFrame
   :param table_name: Name for the temporary view.
   :type table_name: str

   :returns: True if successful, False otherwise.
   :rtype: bool


.. py:function:: repartition_and_cache(df: pyspark.sql.DataFrame, partitions: int = 100) -> Optional[pyspark.sql.DataFrame]

   Repartitions and caches a dataframe.

   :param df: Input Spark DataFrame.
   :type df: DataFrame
   :param partitions: Number of partitions. Default is 100.
   :type partitions: int, optional

   :returns: Repartitioned and cached DataFrame or None if an error occurred.
   :rtype: Optional[DataFrame]


.. py:function:: reproject_geom_columns(df, geom_columns, source_srid, target_srid)

   Reprojects geometry columns using the three-argument version of ST_Transform:
   ST_Transform(geom, 'source_srid', 'target_srid')

   Only reprojects if the current SRID is not equal to the target.

   :param df: Spark DataFrame containing the geometry columns.
   :type df: DataFrame
   :param geom_columns: List of column names (strings) to reproject.
   :type geom_columns: list
   :param source_srid: The source CRS (e.g. "EPSG:4326").
   :type source_srid: str
   :param target_srid: The target CRS (e.g. "EPSG:27700").
   :type target_srid: str

   :returns: The DataFrame with each specified geometry column conditionally reprojected.
   :rtype: DataFrame


.. py:function:: sanitise_dataframe_column_names(df: pyspark.sql.DataFrame) -> Optional[pyspark.sql.DataFrame]

   Cleans dataframe column names by converting them to lowercase and replacing
   slashes/spaces with underscores.

   :param df: Input Spark DataFrame.
   :type df: DataFrame

   :returns: Sanitised DataFrame or None if an error occurred.
   :rtype: Optional[DataFrame]


.. py:function:: tabulate_null_vs_not_null(df: pyspark.sql.DataFrame, column_name: str) -> Optional[pyspark.sql.DataFrame]

   Returns a dataframe showing the count of null and non-null values for a given column.

   :param df: Input Spark DataFrame.
   :type df: DataFrame
   :param column_name: Name of the column to analyze.
   :type column_name: str

   :returns: Resulting DataFrame with null vs non-null counts.
   :rtype: Optional[DataFrame]


.. py:function:: validate_geocode_data(df, lat_col_name: str, lon_col_name: str)

   Filters out rows with invalid geographic coordinates using string-based column names.


.. py:function:: validate_geometry(df, geom_col, step_name)

   Validates a single geometry column.

   Parameters:
   - df (DataFrame): Spark DataFrame containing geometry data.
   - geom_col (str): Name of the geometry column to check.
   - step_name (str): Label for the debug output.


.. py:function:: write_df_to_parquet(df: pyspark.sql.DataFrame, path: str, mode: str = 'overwrite') -> bool

   Writes a DataFrame to a Parquet file.

   :param df: Input Spark DataFrame.
   :type df: DataFrame
   :param path: Output path.
   :type path: str
   :param mode: Write mode. Defaults to "overwrite".
   :type mode: str

   :returns: True if successful, False otherwise.
   :rtype: bool


.. py:data:: PYSPARK_AVAILABLE
   :value: True


.. py:data:: logger

.. py:data:: new_walkability_udf
   :value: None


.. py:data:: walkability_config

