#!/usr/bin/env python3
"""
Live Spark utilities tests - requires actual Spark environment.

Run with: python tests/test_spark_utils_live.py
Skipped by default in pytest (marked integration).
"""

import pytest
import sys

pytestmark = pytest.mark.integration
import tempfile
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_spark_utilities():
    """Test Spark utility functions with a live Spark session."""

    print("=" * 60)
    print("SPARK UTILITIES LIVE TESTS")
    print("=" * 60)

    results = {}

    # Test 1: Import pyspark
    print("\n1. Testing PySpark import...")
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import col, lit
        print("   PySpark imported successfully")
        results['pyspark_import'] = True
    except ImportError as e:
        print(f"   FAILED: {e}")
        results['pyspark_import'] = False
        return results

    # Test 2: Import siege_utilities spark_utils
    print("\n2. Testing spark_utils import...")
    try:
        from siege_utilities.distributed.spark_utils import (
            sanitise_dataframe_column_names,
            get_row_count,
            repartition_and_cache,
            register_temp_table,
            write_df_to_parquet,
            read_parquet_to_df,
            validate_geocode_data,
            mark_valid_geocode_data,
            PYSPARK_AVAILABLE
        )
        print(f"   spark_utils imported successfully")
        print(f"   PYSPARK_AVAILABLE = {PYSPARK_AVAILABLE}")
        results['spark_utils_import'] = True
    except ImportError as e:
        print(f"   FAILED: {e}")
        results['spark_utils_import'] = False
        return results

    # Test 3: Create Spark session
    print("\n3. Creating Spark session...")
    try:
        spark = SparkSession.builder \
            .appName("siege_utilities_test") \
            .master("local[2]") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.shuffle.partitions", "4") \
            .getOrCreate()

        spark.sparkContext.setLogLevel("WARN")
        print(f"   Spark session created: {spark.version}")
        results['spark_session'] = True
    except Exception as e:
        print(f"   FAILED: {e}")
        results['spark_session'] = False
        return results

    try:
        # Test 4: Create test DataFrame
        print("\n4. Creating test DataFrame...")
        test_data = [
            (1, "New York", 40.7128, -74.0060),
            (2, "Los Angeles", 34.0522, -118.2437),
            (3, "Chicago", 41.8781, -87.6298),
            (4, "Invalid City", None, None),
            (5, "Bad Coords", 999.0, -999.0),
        ]
        df = spark.createDataFrame(test_data, ["id", "City Name", "Latitude", "Longitude"])
        print(f"   Created DataFrame with {df.count()} rows")
        df.show()
        results['create_dataframe'] = True

        # Test 5: sanitise_dataframe_column_names
        print("\n5. Testing sanitise_dataframe_column_names...")
        df_clean = sanitise_dataframe_column_names(df)
        if df_clean is not None:
            print(f"   Columns before: {df.columns}")
            print(f"   Columns after: {df_clean.columns}")
            assert 'city_name' in df_clean.columns, "Column name not sanitized"
            results['sanitise_columns'] = True
        else:
            results['sanitise_columns'] = False

        # Test 6: get_row_count
        print("\n6. Testing get_row_count...")
        count = get_row_count(df_clean)
        print(f"   Row count: {count}")
        assert count == 5, f"Expected 5, got {count}"
        results['get_row_count'] = True

        # Test 7: register_temp_table
        print("\n7. Testing register_temp_table...")
        success = register_temp_table(df_clean, "test_cities")
        print(f"   Registered temp table: {success}")
        # Verify with SQL
        sql_result = spark.sql("SELECT COUNT(*) as cnt FROM test_cities").collect()[0]['cnt']
        print(f"   SQL query result: {sql_result}")
        assert sql_result == 5, f"Expected 5 from SQL, got {sql_result}"
        results['register_temp_table'] = True

        # Test 8: validate_geocode_data
        print("\n8. Testing validate_geocode_data...")
        df_valid = validate_geocode_data(df_clean, 'latitude', 'longitude')
        valid_count = df_valid.count()
        print(f"   Valid geocode rows: {valid_count} (from 5)")
        assert valid_count == 3, f"Expected 3 valid rows, got {valid_count}"
        results['validate_geocode'] = True

        # Test 9: mark_valid_geocode_data
        print("\n9. Testing mark_valid_geocode_data...")
        df_marked = mark_valid_geocode_data(df_clean, 'latitude', 'longitude', 'geo_valid')
        df_marked.select('city_name', 'latitude', 'longitude', 'geo_valid').show()
        valid_marked = df_marked.filter(col('geo_valid') == True).count()
        print(f"   Rows marked as valid: {valid_marked}")
        assert valid_marked == 3, f"Expected 3 valid, got {valid_marked}"
        results['mark_valid_geocode'] = True

        # Test 10: Write and read parquet
        print("\n10. Testing parquet write/read...")
        with tempfile.TemporaryDirectory() as tmpdir:
            parquet_path = f"{tmpdir}/test_cities.parquet"
            write_success = write_df_to_parquet(df_clean, parquet_path)
            print(f"   Write success: {write_success}")

            if write_success:
                df_read = read_parquet_to_df(spark, parquet_path)
                if df_read is not None:
                    read_count = df_read.count()
                    print(f"   Read back {read_count} rows")
                    assert read_count == 5, f"Expected 5, got {read_count}"
                    results['parquet_io'] = True
                else:
                    results['parquet_io'] = False
            else:
                results['parquet_io'] = False

        # Test 11: repartition_and_cache
        print("\n11. Testing repartition_and_cache...")
        df_cached = repartition_and_cache(df_clean, partitions=2)
        if df_cached is not None:
            print(f"   Partitions: {df_cached.rdd.getNumPartitions()}")
            results['repartition_cache'] = True
        else:
            results['repartition_cache'] = False

    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n" + "=" * 60)
        print("Stopping Spark session...")
        spark.stop()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")

    return results


if __name__ == "__main__":
    results = test_spark_utilities()

    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)
