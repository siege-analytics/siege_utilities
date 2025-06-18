# python standard
from typing import Optional, Union, Tuple
import os
import pathlib
import json
import time
import logging

try:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.types import *
    from pyspark.sql.functions import *
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False

logger = logging.getLogger(__name__)

def sanitise_dataframe_column_names(df: DataFrame) -> Optional[DataFrame]:
    """
    Cleans dataframe column names by converting them to lowercase and replacing
    slashes/spaces with underscores.

    Args:
        df (DataFrame): Input Spark DataFrame.

    Returns:
        Optional[DataFrame]: Sanitised DataFrame or None if an error occurred.
    """
    try:
        message = f"Sanitising column names for dataframe {df}"
        log_info(message)

        df = df.toDF(
            *[c.lower().strip().replace("/", "_").replace(" ", "_") for c in df.columns]
        )

        message = (
            f"Successfully sanitised columns for dataframe {df}: {list(df.columns)}"
        )
        log_info(message)

        return df

    except Exception as e:
        message = (
            f"There was a problem sanitising column names for dataframe {df}:\n{e}"
        )
        log_error(message)
        return None


def tabulate_null_vs_not_null(df: DataFrame, column_name: str) -> Optional[DataFrame]:
    """
    Returns a dataframe showing the count of null and non-null values for a given column.

    Args:
        df (DataFrame): Input Spark DataFrame.
        column_name (str): Name of the column to analyze.

    Returns:
        Optional[DataFrame]: Resulting DataFrame with null vs non-null counts.
    """
    try:
        NULL_COLUMNS_NAME = f"{column_name}_null_count"
        NOT_NULL_COLUMNS_NAME = f"{column_name}_not_null_count"

        result_df = df.groupBy(column_name).agg(
            sum(when(col(column_name).isNull(), 1).otherwise(0)).alias(
                NULL_COLUMNS_NAME
            ),
            sum(when(col(column_name).isNotNull(), 1).otherwise(0)).alias(
                NOT_NULL_COLUMNS_NAME
            ),
        )

        result_df.show(truncate=False)
        return result_df

    except Exception as e:
        log_error(f"Error in tabulate_null_vs_not_null for column {column_name}: {e}")
        return None


def get_row_count(df: DataFrame) -> Optional[int]:
    """
    Returns the count of rows in the dataframe.

    Args:
        df (DataFrame): Input Spark DataFrame.

    Returns:
        Optional[int]: Row count or None if an error occurred.
    """
    try:
        count = df.count()
        log_info(f"Row count for dataframe: {count}")
        return count
    except Exception as e:
        log_error(f"Error getting row count: {e}")
        return None


def repartition_and_cache(df: DataFrame, partitions: int = 100) -> Optional[DataFrame]:
    """
    Repartitions and caches a dataframe.

    Args:
        df (DataFrame): Input Spark DataFrame.
        partitions (int, optional): Number of partitions. Default is 100.

    Returns:
        Optional[DataFrame]: Repartitioned and cached DataFrame or None if an error occurred.
    """
    try:
        df = df.repartition(partitions).cache()
        log_info(f"Dataframe repartitioned to {partitions} partitions and cached.")
        return df
    except Exception as e:
        log_error(f"Error repartitioning and caching dataframe: {e}")
        return None


def register_temp_table(df: DataFrame, table_name: str) -> bool:
    """
    Registers a temporary view from a dataframe.

    Args:
        df (DataFrame): Input Spark DataFrame.
        table_name (str): Name for the temporary view.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        df.createOrReplaceTempView(table_name)
        log_info(f"Temporary view '{table_name}' registered.")
        return True
    except Exception as e:
        log_error(f"Error registering temporary table '{table_name}': {e}")
        return False


def move_column_to_front_of_dataframe(
    df: DataFrame, column_name: str
) -> Optional[DataFrame]:
    try:

        # Get columns from d
        columns = list(df.columns)
        # Column to move to the front
        column_to_move = column_name

        # Get the column names, placing the desired column first
        new_column_order = [column_to_move] + [
            col for col in df.columns if col != column_to_move
        ]

        # Select columns in the new order
        df_reordered = df.select(*new_column_order)

        # Display the reordered DataFrame
        df_reordered.printSchema()
        return df
    except Exception as e:
        log_error(f"Error repartitioning and caching dataframe: {e}")
        return None


def write_df_to_parquet(df: DataFrame, path: str, mode: str = "overwrite") -> bool:
    """
    Writes a DataFrame to a Parquet file.

    Args:
        df (DataFrame): Input Spark DataFrame.
        path (str): Output path.
        mode (str): Write mode. Defaults to "overwrite".

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        df.write.mode(mode).parquet(path)
        log_info(f"Dataframe written to parquet at {path} with mode '{mode}'")
        return True
    except Exception as e:
        log_error(f"Error writing dataframe to parquet at {path}: {e}")
        return False


def read_parquet_to_df(spark: SparkSession, path: str) -> Optional[DataFrame]:
    """
    Reads a Parquet file into a Spark DataFrame.

    Args:
        spark (SparkSession): Active Spark session.
        path (str): Path to the Parquet file.

    Returns:
        Optional[DataFrame]: Loaded DataFrame or None if an error occurred.
    """
    try:
        df = spark.read.parquet(path)
        log_info(f"Successfully read parquet from {path}")
        return df
    except Exception as e:
        log_error(f"Error reading parquet from {path}: {e}")
        return None


def flatten_json_column_and_join_back_to_df(
    df: DataFrame,
    json_column: str,
    prefix: str = "json_column_",
    logger: Optional[any] = None,
    drop_original: bool = True,
    explode_arrays: bool = False,
    flatten_level: str = "shallow",  # "shallow" or "deep" flattening
    verbose: bool = False,  # Controls whether to log detailed messages
    sample_size: int = 5,  # Number of samples to check
    show_samples: bool = True,  # Whether to display sample data
) -> DataFrame:
    """
    Flattens a JSON column in a Spark DataFrame, extracting fields and adding them as columns.
    Has fallback mechanisms for corrupt JSON data.

    Args:
        df (DataFrame): The input Spark DataFrame.
        json_column (str): The name of the column containing JSON strings.
        prefix (str, optional): Prefix to add to the flattened column names. Defaults to "json_column_".
        logger (Optional[any], optional): Logger object for logging messages. Defaults to None.
        drop_original (bool, optional): Whether to drop the original JSON column after flattening. Defaults to True.
        explode_arrays (bool, optional): Whether to explode array columns. Defaults to False.
        flatten_level (str, optional):  "shallow" or "deep" flattening. Defaults to "shallow".
        verbose (bool, optional): Controls whether to log detailed messages. Defaults to False.
        sample_size (int, optional): Number of samples to check. Defaults to 5.
        show_samples (bool, optional): Whether to display sample data. Defaults to False.

    Returns:
        DataFrame: The DataFrame with the JSON column flattened.
    """

    def log_info(message):
        if logger:
            logger.info(message)
        else:
            print(message)  # Fallback to print if no logger

    def log_error(message):
        if logger:
            logger.error(message)
        else:
            print(f"ERROR: {message}")  # print errors

    if verbose:
        log_info(f"Flattening JSON in column: {json_column} with prefix: {prefix}")

    # Create a temp view for easier debugging if needed
    if show_samples:
        df.createOrReplaceTempView("json_data_view")
        sample_df = (
            df.filter(col(json_column).isNotNull())
            .select(json_column)
            .limit(sample_size)
        )
        log_info(f"Sample of JSON data in {json_column}:")
        sample_df.show(truncate=False)

    # Get a sample of the JSON data for schema inference
    sample_json = (
        df.filter(col(json_column).isNotNull() & (length(trim(col(json_column))) > 2))
        .select(json_column)
        .limit(sample_size)
        .collect()
    )

    if not sample_json or len(sample_json) == 0 or not sample_json[0][0]:
        log_info(
            f"No valid JSON sample available in column {json_column}, skipping flattening"
        )
        return df.drop(json_column) if drop_original else df

    # Try to infer schema, with fallbacks
    try:
        log_info(f"Inferring schema from sample JSON in column {json_column}")
        sample_rdd = df.sparkSession.sparkContext.parallelize([sample_json[0][0]])
        inferred_schema = df.sparkSession.read.json(sample_rdd).schema

        # Check if we got corrupt records
        if "_corrupt_record" in [field.name for field in inferred_schema.fields]:
            log_info(
                f"Found corrupt JSON records in column {json_column}. Sample: {sample_json[0][0][:100]}..."
            )

            # Try with a different sample if available
            if len(sample_json) > 1:
                for i in range(1, len(sample_json)):
                    if sample_json[i][0]:
                        log_info(f"Trying with another sample (#{i + 1})")
                        sample_rdd = df.sparkSession.sparkContext.parallelize(
                            [sample_json[i][0]]
                        )
                        inferred_schema = df.sparkSession.read.json(sample_rdd).schema
                        if "_corrupt_record" not in [
                            field.name for field in inferred_schema.fields
                        ]:
                            log_info(f"Found valid schema with sample #{i + 1}")
                            break

            # If still corrupt, fallback to string schema
            if "_corrupt_record" in [field.name for field in inferred_schema.fields]:
                log_info(
                    f"All samples contain corrupt JSON. Falling back to string schema for {json_column}"
                )

                def validate_json(s):
                    if s is None:
                        return None
                    try:
                        json.loads(s)
                        return s
                    except (TypeError, json.JSONDecodeError):
                        return None

                df_with_json = (
                    df.withColumn(
                        "validated_json",
                        when(col(json_column).isNull(), lit(None)).otherwise(
                            validate_json(col(json_column))
                        ),
                    )
                    .withColumn(
                        "parsed_json",
                        from_json(
                            col("validated_json"),  # Pass the column
                            StringType(),
                            {"mode": "PERMISSIVE"},
                        ),  # Use PERMISSIVE mode with StringType
                    )
                    .drop("validated_json")
                )
                df_with_json = df_with_json.withColumn(
                    "parsed_json",
                    when(
                        col("parsed_json").isNull(), lit(None).cast(StringType())
                    ).otherwise(col("parsed_json")),
                )
                return df.drop(json_column) if drop_original else df

        log_info(f"Inferred schema: {inferred_schema}")
        df_with_json = df.withColumn(
            "parsed_json", from_json(col(json_column), inferred_schema)
        )

    except Exception as e:
        log_error(f"Error inferring schema for {json_column}: {e}")
        log_info(f"Falling back to string schema for {json_column}")
        # Fallback to string schema
        try:

            def validate_json(s):
                if s is None:
                    return None
                try:
                    json.loads(s)
                    return s
                except (TypeError, json.JSONDecodeError):
                    return None

            df_with_json = (
                df.withColumn(
                    "validated_json",
                    when(col(json_column).isNull(), lit(None)).otherwise(
                        validate_json(col(json_column))
                    ),
                )
                .withColumn(
                    "parsed_json",
                    from_json(
                        col("validated_json"),  # Pass the column
                        StringType(),
                        {"mode": "PERMISSIVE"},
                    ),  # Use PERMISSIVE mode with StringType
                )
                .drop("validated_json")
            )
            # Add a step to handle the case where the string is not a valid JSON
            df_with_json = df_with_json.withColumn(
                "parsed_json",
                when(
                    col("parsed_json").isNull(), lit(None).cast(StringType())
                ).otherwise(col("parsed_json")),
            )
        except:
            log_error(
                f"Failed even with string schema for {json_column}. Returning original dataframe."
            )
            return df.drop(json_column) if drop_original else df

    # For simple flattening, add all top-level fields with the specified prefix
    columns_to_extract = df_with_json.select("parsed_json.*").columns
    result_df = df_with_json

    if flatten_level == "shallow":
        # Simple top-level field extraction
        for field in columns_to_extract:
            result_df = result_df.withColumn(
                f"{prefix}{field}", col(f"parsed_json.{field}")
            )
    else:
        # Use recursive flattening for deep mode
        def flatten_struct(
            df: DataFrame, struct_col: str, prefix: str, flatten_level: str
        ) -> DataFrame:
            """Recursively flattens all struct and array fields in a column."""
            try:
                schema = df.select(struct_col).schema[0].dataType
                if isinstance(schema, StructType):
                    for field in schema.fields:
                        field_name = field.name
                        full_field = f"{struct_col}.{field_name}"
                        new_col_name = f"{prefix}{field_name}"

                        if isinstance(field.dataType, StructType):
                            if flatten_level == "deep":
                                df = flatten_struct(
                                    df.withColumn(new_col_name, col(full_field)),
                                    new_col_name,
                                    f"{new_col_name}_",
                                    flatten_level,
                                )
                            else:
                                df = df.withColumn(new_col_name, col(full_field))

                        elif isinstance(field.dataType, ArrayType) and isinstance(
                            field.dataType.elementType, StructType
                        ):
                            df = df.withColumn(new_col_name, col(full_field))
                            if flatten_level == "deep":
                                df = flatten_struct(
                                    df, new_col_name, f"{new_col_name}_", flatten_level
                                )
                        else:
                            df = df.withColumn(new_col_name, col(full_field))
                    df = df.drop(struct_col)
                return df
            except Exception as e:
                log_error(f"Error in flatten_struct: {e}")
                return df

        # Begin deep flattening
        result_df = flatten_struct(df_with_json, "parsed_json", prefix, flatten_level)

    # Exploding array fields if needed
    if explode_arrays:
        try:
            array_columns = [
                col_name
                for col_name, data_type in result_df.dtypes
                if "array" in data_type.lower()
            ]

            for array_column in array_columns:
                result_df = result_df.withColumn(
                    array_column, explode_outer(col(array_column))
                )
        except Exception as e:
            log_error(f"Error exploding arrays: {e}")

    # Cleanup: drop temporary columns and original if requested
    columns_to_drop = ["parsed_json"]
    if drop_original:
        columns_to_drop.append(json_column)

    result_df = result_df.drop(*columns_to_drop)

    log_info(
        f"Finished flattening JSON column {json_column}. Drop original: {drop_original}"
    )

    if verbose:
        log_info("Columns after flattening:")
        log_info(str(result_df.columns))

    return result_df


def validate_geocode_data(df, lat_col_name: str, lon_col_name: str):
    """Filters out rows with invalid geographic coordinates using string-based column names."""

    # Ensure columns exist before applying filters
    if lat_col_name not in df.columns or lon_col_name not in df.columns:
        raise ValueError(
            f"Columns {lat_col_name}, {lon_col_name} not found in DataFrame"
        )

    # Explicitly reference column names using `col()` within transformations
    return df.filter(
        df[lat_col_name].isNotNull()
        & df[lon_col_name].isNotNull()
        & df[lat_col_name].between(-90, 90)
        & df[lon_col_name].between(-180, 180)
    )


def mark_valid_geocode_data(
    df, lat_col_name: str, lon_col_name: str, output_col_name: str = "is_valid"
):
    """
    Adds a boolean flag column to the DataFrame indicating whether the geographic coordinates are valid.

    A set of coordinates is considered valid if:
    - The latitude and longitude columns are not null.
    - The latitude is between -90 and 90.
    - The longitude is between -180 and 180.

    Unlike filtering functions, this function preserves all rows in the DataFrame by simply marking
    each row with a True (valid) or False (invalid) value in the new output column.

    Parameters:
      df (DataFrame): The Spark DataFrame containing geocode data.
      lat_col_name (str): The name of the latitude column.
      lon_col_name (str): The name of the longitude column.
      output_col_name (str, optional): The name of the output column to store the validity flag.
                                       Defaults to "is_valid".

    Returns:
      DataFrame: A new DataFrame with an additional column indicating geocode validity.
    """
    # Ensure the specified columns exist
    if lat_col_name not in df.columns or lon_col_name not in df.columns:
        raise ValueError(
            f"Columns '{lat_col_name}', '{lon_col_name}' not found in DataFrame"
        )

    # Add a new column with boolean values indicating coordinate validity.
    return df.withColumn(
        output_col_name,
        col(lat_col_name).isNotNull()
        & col(lon_col_name).isNotNull()
        & col(lat_col_name).between(-90, 90)
        & col(lon_col_name).between(-180, 180),
    )


def clean_and_reorder_bbox(df, bbox_col):
    """Removes brackets from bounding box strings and reorders coordinates for Sedona.

    Assumes input is a comma separated list in the order:
      min latitude, max latitude, min longitude, max longitude
    Produces an array in the order: [min_lon, min_lat, max_lon, max_lat]
    """
    # Define column names dynamically
    cleaned_bbox_col_name = f"{bbox_col}_cleaned"
    split_bbox_col_name = f"{bbox_col}_split"
    min_lat_col_name = f"{bbox_col}_min_lat"
    max_lat_col_name = f"{bbox_col}_max_lat"
    min_lon_col_name = f"{bbox_col}_min_lon"
    max_lon_col_name = f"{bbox_col}_max_lon"
    reordered_bbox_col_name = f"{bbox_col}_reordered"

    # Apply transformations using correct dynamic column references:
    # Note: Input order is [min_lat, max_lat, min_lon, max_lon]
    df = (
        df.withColumn(cleaned_bbox_col_name, translate(col(bbox_col), "[]", ""))
        .withColumn(split_bbox_col_name, split(col(cleaned_bbox_col_name), ","))
        .withColumn(min_lat_col_name, col(split_bbox_col_name)[0].cast("double"))
        .withColumn(max_lat_col_name, col(split_bbox_col_name)[1].cast("double"))
        .withColumn(min_lon_col_name, col(split_bbox_col_name)[2].cast("double"))
        .withColumn(max_lon_col_name, col(split_bbox_col_name)[3].cast("double"))
        .withColumn(
            reordered_bbox_col_name,
            # For Sedona we want [min_lon, min_lat, max_lon, max_lat]
            array(
                col(min_lon_col_name),
                col(min_lat_col_name),
                col(max_lon_col_name),
                col(max_lat_col_name),
            ),
        )
    )

    return df


def ensure_literal(value):
    """
    Convert any value to a Spark literal (Column) unless it is already a Spark Column.

    Parameters:
      value: Any value to be converted.

    Returns:
      A pyspark.sql.Column containing the value (or its Spark literal),
      unless the value is already a Column.
    """
    if isinstance(value, Column):
        return value
    return lit(value)


from pyspark.sql.functions import expr, col
from pyspark.sql import SparkSession

from pyspark.sql import functions as F
from pyspark.sql.functions import expr


def reproject_geom_columns(df, geom_columns, source_srid, target_srid):
    """
    Reprojects geometry columns using the three-argument version of ST_Transform:
    ST_Transform(geom, 'source_srid', 'target_srid')

    Only reprojects if the current SRID is not equal to the target.

    Parameters:
      df (DataFrame): Spark DataFrame containing the geometry columns.
      geom_columns (list): List of column names (strings) to reproject.
      source_srid (str): The source CRS (e.g. "EPSG:4326").
      target_srid (str): The target CRS (e.g. "EPSG:27700").

    Returns:
      DataFrame: The DataFrame with each specified geometry column conditionally reprojected.
    """
    print("I LOVE LEENA")
    try:
        # Extract the numeric part of the target CRS.
        target_srid_int = int(target_srid.split(":")[1])
        for geom_col in geom_columns:
            # If ST_SRID(geom_col) already equals target_srid_int then pass it.
            # Otherwise, apply ST_Transform.
            df = df.withColumn(
                geom_col,
                expr(
                    f"CASE WHEN ST_SRID({geom_col}) = {target_srid_int} THEN {geom_col} ELSE ST_Transform({geom_col}, '{source_srid}', '{target_srid}') END"
                ),
            )
        return df

    except Exception as e:
        print("AN ERROR OCCURRED in reproject_geom_columns:", e)
        try:
            spark = SparkSession.getActiveSession()
            if spark is not None:
                spark.stop()
                print("Spark session stopped due to error.")
            else:
                print("No active Spark session to stop.")
        except Exception as stop_exc:
            print("Failed to stop Spark session:", stop_exc)
        raise e


def prepare_dataframe_for_export(df, logger_func=None):
    """
    Prepares a DataFrame for export (e.g., to CSV) by:
      - Converting binary columns to Base64-encoded strings.
      - Casting simple scalar fields (non-string, non-complex) to strings.
      - Dropping intermediate columns (e.g., 'parsed_json') if present.
      - Converting complex (StructType/ArrayType) columns to JSON strings.
      - Handling null values appropriately.

    Args:
        df: Spark DataFrame to prepare
        logger_func: Optional logging function (defaults to print)

    Returns:
        The transformed DataFrame with all columns as strings or JSON strings.
    """
    from pyspark.sql.types import (
        BinaryType,
        StringType,
        StructType,
        ArrayType,
        IntegerType,
        LongType,
        DoubleType,
        FloatType,
        BooleanType,
        DateType,
        TimestampType,
    )
    from pyspark.sql.functions import base64, col, to_json, when, isnan, isnull

    # Use provided logger or fall back to print
    log = logger_func if logger_func else print

    try:
        log("🔄 Preparing DataFrame for export...")
        original_columns = len(df.columns)

        # 1. Convert binary columns (if any) to Base64 strings
        binary_columns = [
            field.name
            for field in df.schema.fields
            if isinstance(field.dataType, BinaryType)
        ]

        if binary_columns:
            log(f"   Converting {len(binary_columns)} binary columns to Base64")
            for bcol in binary_columns:
                df = df.withColumn(bcol, base64(col(bcol)))

        # 2. Cast simple scalar fields to strings with null handling
        simple_fields = []
        for field in df.schema.fields:
            if (
                not isinstance(field.dataType, StringType)
                and not isinstance(field.dataType, (StructType, ArrayType))
                and field.name != "parsed_json"
            ):
                simple_fields.append(field.name)

        if simple_fields:
            log(f"   Converting {len(simple_fields)} scalar fields to strings")
            for field_name in simple_fields:
                # Handle different numeric types and nulls more gracefully
                df = df.withColumn(
                    field_name,
                    when(col(field_name).isNull(), "")
                    .when(isnan(col(field_name)), "")
                    .otherwise(col(field_name).cast(StringType())),
                )

        # 3. Remove intermediate columns if necessary
        intermediate_columns = ["parsed_json"]
        columns_to_drop = [
            col_name for col_name in intermediate_columns if col_name in df.columns
        ]

        if columns_to_drop:
            log(
                f"   Dropping {len(columns_to_drop)} intermediate columns: {columns_to_drop}"
            )
            df = df.drop(*columns_to_drop)

        # 4. Convert complex columns (Structs/Arrays) to JSON strings
        def identify_complex_columns(dframe):
            complex_cols = []
            for field in dframe.schema.fields:
                if isinstance(field.dataType, (StructType, ArrayType)):
                    complex_cols.append(field.name)
            return complex_cols

        complex_columns = identify_complex_columns(df)

        if complex_columns:
            log(
                f"   Converting {len(complex_columns)} complex columns to JSON: {complex_columns}"
            )
            for column_name in complex_columns:
                df = df.withColumn(
                    column_name,
                    when(col(column_name).isNull(), "").otherwise(
                        to_json(col(column_name))
                    ),
                )

        # 5. Verify conversion success
        remaining_complex = identify_complex_columns(df)
        if remaining_complex:
            log(f"⚠️  Some complex columns could not be converted: {remaining_complex}")
        else:
            log("✅ All columns successfully prepared for export")

        final_columns = len(df.columns)
        log(f"   DataFrame prepared: {original_columns} → {final_columns} columns")

        return df

    except Exception as e:
        log(f"❌ Error preparing DataFrame for export: {e}")
        raise


def prepare_summary_dataframe(
    data_tuples, column_names=["metric", "value"], logger_func=None
):
    """
    Helper function to create summary DataFrames with consistent string types.
    Prevents type merging errors by ensuring all values are strings.

    Args:
        data_tuples: List of tuples with data
        column_names: Column names for the DataFrame
        logger_func: Optional logging function

    Returns:
        Spark DataFrame with all string columns
    """
    log = logger_func if logger_func else print

    try:
        # Convert all values to strings to prevent type conflicts
        string_data = []
        for row in data_tuples:
            string_row = tuple(str(value) if value is not None else "" for value in row)
            string_data.append(string_row)

        # Create DataFrame with explicit string schema
        from pyspark.sql.types import StructType, StructField, StringType

        schema = StructType(
            [StructField(col_name, StringType(), True) for col_name in column_names]
        )

        # Use current Spark session
        from pyspark.sql import SparkSession

        spark = SparkSession.getActiveSession()

        if spark is None:
            raise Exception("No active Spark session found")

        df = spark.createDataFrame(string_data, schema)
        log(f"✅ Created summary DataFrame with {len(data_tuples)} rows")

        return df

    except Exception as e:
        log(f"❌ Error creating summary DataFrame: {e}")
        raise


def export_pyspark_df_to_excel(df, file_name="output.xlsx", sheet_name="Sheet1"):
    """
    Converts a PySpark DataFrame to a Pandas DataFrame and exports it to an Excel file.

    Parameters:
        spark_df (pyspark.sql.DataFrame): The PySpark DataFrame to export.
        file_name (str): The name of the output Excel file.
        sheet_name (str): The sheet name in the Excel file.

    Returns:
        None
    """
    try:
        # Convert PySpark DataFrame to Pandas DataFrame
        pandas_df = df.toPandas()

        # Export to Excel
        pandas_df.to_excel(file_name, sheet_name=sheet_name, index=False)
        print(f"DataFrame successfully exported to {file_name}")
    except Exception as e:
        print(f"Error exporting DataFrame: {e}")


def pivot_summary_table_for_bools(df, columns, spark):
    """
    Generate a pivot table summary for given boolean flag columns in a DataFrame.
    The pivot table includes three metrics:
       - "Count": Sum of rows where the flag is True.
       - "Percentage (%)": Percentage relative to total records.
       - "Total": The total number of records (repeated for each column).
    All numeric values are converted to float to ensure a consistent type.

    Parameters:
      df (DataFrame): The source Spark DataFrame.
      columns (list): List of column names (assumed to be boolean flags) to summarize.
      spark (SparkSession): The active Spark session.
    Returns:
      DataFrame: A Spark DataFrame representing the pivot table.
    """
    from pyspark.sql import functions as F

    # Get the total number of records and convert to float.
    total_records = df.count()
    total_records_float = float(total_records)

    # Build aggregation expressions for each flag column: sum the True values.
    agg_exprs = [
        F.sum(F.when(F.col(col_name), 1).otherwise(0)).alias(col_name)
        for col_name in columns
    ]

    # Execute the aggregated query in one go.
    agg_results = df.agg(*agg_exprs).collect()[0]

    # Build a dictionary mapping each column to its count (cast as float).
    counts = {col: float(agg_results[col]) for col in columns}
    # Compute percentages and cast to float using py_round.
    percentages = {
        col: (
            py_round(float(agg_results[col]) / total_records_float * 100, 2)
            if total_records > 0
            else 0.0
        )
        for col in columns
    }

    # Construct pivot data: each dictionary represents a metric row.
    pivot_data = [
        {"Metric": "Count", **counts},
        {"Metric": "Percentage (%)", **percentages},
        {"Metric": "Total", **{col: total_records_float for col in columns}},
    ]

    # Create and return a small Spark DataFrame for the pivot table.
    pivot_df = spark.createDataFrame(pivot_data)
    return pivot_df


def pivot_summary_with_metrics(df, group_col, pivot_col, spark):
    """
    Generate a pivot summary for a categorical column against one or more grouping columns,
    including rows for "Count", "Percentage (%)", and "Total" for each group.

    Parameters:
      df (DataFrame): The source Spark DataFrame.
      group_col (str or list): The column name (or list of column names) used for grouping.
                               For example, "geocode_granularity" or ["state", "region"].
      pivot_col (str): The categorical column to pivot on (e.g., "final_geocode_choice").
      spark (SparkSession): The active Spark session.

    Returns:
      DataFrame: A Spark DataFrame in which each original group appears as three rows:
                 one for the counts, one for the percentages, and one for the total count.
                 The non-grouping columns represent each distinct pivot column value.
    """

    # Ensure group_col is treated as a list.
    if not isinstance(group_col, list):
        group_cols = [group_col]
    else:
        group_cols = group_col

    # 1. Generate the pivot counts.
    pivot_df = df.groupBy(*group_cols).pivot(pivot_col).count()

    # 2. Compute the overall total for each group.
    total_df = df.groupBy(*group_cols).count().withColumnRenamed("count", "Total")

    # 3. Join the pivot counts with the totals.
    agg_df = pivot_df.join(total_df, on=group_cols)

    # 4. Determine which columns are the pivot categories.
    pivot_categories = [c for c in agg_df.columns if c not in group_cols + ["Total"]]

    # 5. For each row (each grouping), build three rows: one for counts,
    #    one for percentages, and one for the total count repeated.
    rows = []
    for row in agg_df.collect():
        # Extract the group key (all fixed grouping columns)
        group_vals = {col: row[col] for col in group_cols}
        total_val = row["Total"]

        # Build the counts row.
        count_dict = {"Metric": "Count"}
        for cat in pivot_categories:
            count_dict[cat] = float(row[cat]) if row[cat] is not None else 0.0
        count_dict.update(group_vals)

        # Build the percentage row.
        percent_dict = {"Metric": "Percentage (%)"}
        for cat in pivot_categories:
            count_val = float(row[cat]) if row[cat] is not None else 0.0
            percent = py_round(
                (count_val / total_val * 100) if total_val > 0 else 0.0, 2
            )
            percent_dict[cat] = percent
        percent_dict.update(group_vals)

        # Build the total row.
        total_dict = {"Metric": "Total"}
        for cat in pivot_categories:
            total_dict[cat] = float(total_val)
        total_dict.update(group_vals)

        rows.extend([count_dict, percent_dict, total_dict])

    # 6. Define a desired ordering for the output columns.
    out_cols = group_cols + ["Metric"] + sorted(pivot_categories)

    # 7. Create and return the final pivot summary DataFrame.
    final_df = spark.createDataFrame(rows)
    return final_df.select(*out_cols)


def export_prepared_df_as_csv_to_path_using_delimiter(
    df: DataFrame, write_path: pathlib.Path, delimiter: str = ","
) -> bool:
    """
    Exports DataFrame **with necessary transformations** to ensure Spark compatibility.

    :param df: Target DataFrame
    :param write_path: Pathlib object for export destination
    :param delimiter: CSV delimiter (default is comma)
    :return: bool indicating success/failure

    Applies `prepare_dataframe_for_export()` to prevent Spark export issues.
    """

    try:
        # ✅ Apply transformations to **guarantee successful Spark export**
        prepared_df = prepare_dataframe_for_export(df)

        prepared_df.coalesce(1).write.format(RESULTS_OUTPUT_FORMAT).option(
            "header", "true"
        ).option("delimiter", delimiter).mode("overwrite").save(str(write_path))

        log_info(f"Data successfully exported for step: {write_path.stem}")
        return True

    except Exception as e:
        log_error(f"Error exporting DataFrame for {write_path.stem}: {e}")
        return False


def print_debug_table(spark_df, title):
    """
    Helper function to convert a Spark DataFrame into a Pandas DataFrame,
    format it using tabulate, and print the result with a title.
    """
    pdf = spark_df.toPandas()
    table_str = tabulate(pdf, headers="keys", tablefmt="psql", showindex=False)
    log_info(title)  # Log the title via your logger
    print(f"\n{title}:\n")
    print(table_str)
    print("\n")


from pyspark.sql.types import MapType, StringType
import pyspark.sql.functions as F

# New walkability configuration in dictionary form.
walkability_config = {
    "Trivial": {"max": 100, "label": "Trivial (<100m)"},
    "Tolerable": {"min": 100, "max": 250, "label": "Tolerable (100-250m)"},
    "Moderate": {"min": 250, "max": 400, "label": "Moderate (250-400m)"},
    "Borderline": {"min": 400, "max": 500, "label": "Borderline (400-500m)"},
    "Outside": {"min": 500, "label": "Outside (>500m)"},
}


def compute_walkability(distance):
    if distance is None:
        return None
    if distance < walkability_config["Trivial"]["max"]:
        return {"grade": "Trivial", "label": walkability_config["Trivial"]["label"]}
    elif distance < walkability_config["Tolerable"]["max"]:
        if distance >= walkability_config["Tolerable"].get("min", 0):
            return {
                "grade": "Tolerable",
                "label": walkability_config["Tolerable"]["label"],
            }
    elif distance < walkability_config["Moderate"]["max"]:
        if distance >= walkability_config["Moderate"].get("min", 0):
            return {
                "grade": "Moderate",
                "label": walkability_config["Moderate"]["label"],
            }
    elif distance < walkability_config["Borderline"]["max"]:
        if distance >= walkability_config["Borderline"].get("min", 0):
            return {
                "grade": "Borderline",
                "label": walkability_config["Borderline"]["label"],
            }
    else:
        return {"grade": "Outside", "label": walkability_config["Outside"]["label"]}


new_walkability_udf = F.udf(compute_walkability, MapType(StringType(), StringType()))

from pyspark.sql.functions import expr


def validate_geometry(df, geom_col, step_name):
    """
    Validates a single geometry column.

    Parameters:
    - df (DataFrame): Spark DataFrame containing geometry data.
    - geom_col (str): Name of the geometry column to check.
    - step_name (str): Label for the debug output.
    """
    log_info(f"Validating geometry in step: {step_name} for column: {geom_col}")

    validation_df = df.select(
        "postal_code",
        geom_col,
        F.expr(f"typeof({geom_col})").alias("geometry_type"),
        F.expr(f"ST_SRID({geom_col})").alias("srid"),
    )

    validation_df.show(10, truncate=False)

    log_info(f"Completed validation for '{geom_col}' in step: {step_name}")

    return df


# ✅ Generalized Full Backup Function
def backup_full_dataframe(df, step_name):
    backup_path = DEBUG_SUBDIRECTORY / f"{step_name}_full_persisted"
    df.write.format(RESULTS_OUTPUT_FORMAT).option("header", "true").option(
        "delimiter", RESULTS_OUTPUT_DELIMITER
    ).save(str(backup_path))
    log_info(f"{step_name}: Full DataFrame successfully backed up.")


# ========================================
# ESSENTIAL ATOMIC WRITE FUNCTIONS (working versions)
# ========================================


def atomic_write_with_staging(
    df: DataFrame,
    final_destination: str,
    staging_directory: str,
    file_format: str = "csv",
    delimiter: str = ",",
    header: bool = True,
    mode: str = "overwrite",
) -> bool:
    """
    Performs atomic write operations using a staging directory to prevent partial/corrupted files.
    """
    try:
        log_info(f"Starting atomic write operation to {final_destination}")
        log_info(f"Using staging directory: {staging_directory}")

        # Ensure staging directory exists and is clean
        if os.path.exists(staging_directory):
            shutil.rmtree(staging_directory)
        os.makedirs(staging_directory, exist_ok=True)

        # Write to staging directory first
        log_info(f"Writing data to staging directory")

        writer = df.write.mode(mode)

        if file_format.lower() == "csv":
            writer = (
                writer.format("csv")
                .option("header", str(header).lower())
                .option("delimiter", delimiter)
            )
        elif file_format.lower() == "parquet":
            writer = writer.format("parquet")
        elif file_format.lower() == "json":
            writer = writer.format("json")
        else:
            writer = writer.format(file_format)

        writer.save(staging_directory)
        log_info("Successfully wrote data to staging directory")

        # Create backup of existing data if it exists
        if os.path.exists(final_destination):
            backup_dir = f"{final_destination}_backup_{int(time.time())}"

            if os.path.isdir(final_destination) and os.listdir(final_destination):
                log_info(f"Backing up existing data to {backup_dir}")
                shutil.move(final_destination, backup_dir)
                log_info(f"Existing data backed up successfully")
            else:
                # Remove empty directory
                shutil.rmtree(final_destination, ignore_errors=True)
                log_info("Removed empty destination directory")

        # Create destination directory
        os.makedirs(final_destination, exist_ok=True)

        # Atomically move files from staging to final destination
        log_info("Moving staged files to final destination")
        files_moved = 0

        for item in os.listdir(staging_directory):
            source_path = os.path.join(staging_directory, item)
            dest_path = os.path.join(final_destination, item)

            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
            files_moved += 1

        log_info(f"Successfully moved {files_moved} items to final destination")
        log_info(f"Atomic write operation completed successfully")
        return True

    except Exception as e:
        log_error(f"Error in atomic write operation: {e}")
        return False
    finally:
        # Always clean up staging directory
        try:
            if os.path.exists(staging_directory):
                shutil.rmtree(staging_directory)
                log_info("Cleaned up staging directory")
        except Exception as cleanup_error:
            log_error(f"Error cleaning up staging directory: {cleanup_error}")


def create_unique_staging_directory(base_path, operation_name="operation"):
    """
    Creates a unique staging directory for atomic operations.
    """
    staging_dir = Path(base_path) / f"staging_{operation_name}_{uuid.uuid4().hex}"
    staging_dir.mkdir(parents=True, exist_ok=True)
    return str(staging_dir)
