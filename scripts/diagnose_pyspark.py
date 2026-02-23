#!/usr/bin/env python3
"""
Comprehensive PySpark diagnosis script.
This will help identify the exact cause of the JavaPackage error.
"""

import os
import sys
import subprocess
import importlib


def check_environment():
    """Check environment variables and paths."""
    print("=== ENVIRONMENT CHECK ===")
    print(f"Python: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"JAVA_HOME: {os.environ.get('JAVA_HOME', 'NOT SET')}")
    print(f"SPARK_HOME: {os.environ.get('SPARK_HOME', 'NOT SET')}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
    print(f"PATH: {os.environ.get('PATH', 'NOT SET')[:200]}...")

    # Check Java
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        print(f"Java version: {result.stderr.split(chr(10))[0]}")
    except Exception as e:
        print(f"Java check failed: {e}")


def check_imports():
    """Check PySpark and related imports."""
    print("\n=== IMPORT CHECK ===")

    try:
        import pyspark
        print(f"✅ PySpark version: {pyspark.__version__}")
        print(f"PySpark location: {pyspark.__file__}")
    except Exception as e:
        print(f"❌ PySpark import failed: {e}")
        return False

    try:
        import py4j
        print(f"✅ Py4J version: {py4j.__version__}")
        print(f"Py4J location: {py4j.__file__}")
    except Exception as e:
        print(f"❌ Py4J import failed: {e}")
        return False

    try:
        from py4j.java_gateway import JavaGateway, GatewayParameters
        print("✅ JavaGateway imports successfully")
    except Exception as e:
        print(f"❌ JavaGateway import failed: {e}")
        return False

    return True


def test_spark_context():
    """Test SparkContext creation (lower level than SparkSession)."""
    print("\n=== SPARK CONTEXT TEST ===")

    try:
        from pyspark import SparkContext, SparkConf
        from pyspark.sql import SparkSession

        # Clean any existing context
        if SparkContext._active_spark_context:
            print("Found existing SparkContext, stopping it...")
            SparkContext._active_spark_context.stop()

        # Test SparkContext first
        print("Creating SparkContext...")
        conf = SparkConf() \
            .setAppName("diagnosis") \
            .setMaster("local[1]") \
            .set("spark.driver.memory", "1g")

        sc = SparkContext(conf=conf)
        print("✅ SparkContext created successfully!")

        # Test basic RDD operation
        rdd = sc.parallelize([1, 2, 3])
        count = rdd.count()
        print(f"✅ RDD operation successful: {count} elements")

        sc.stop()
        print("✅ SparkContext stopped cleanly")

        return True

    except Exception as e:
        print(f"❌ SparkContext test failed: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_spark_session():
    """Test SparkSession creation."""
    print("\n=== SPARK SESSION TEST ===")

    try:
        from pyspark.sql import SparkSession
        from pyspark import SparkContext

        # Clean any existing context
        if SparkContext._active_spark_context:
            SparkContext._active_spark_context.stop()

        print("Creating SparkSession...")
        spark = SparkSession.builder \
            .appName("diagnosis") \
            .master("local[1]") \
            .config("spark.driver.memory", "1g") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
            .getOrCreate()

        print("✅ SparkSession created successfully!")

        # Test DataFrame operation
        df = spark.createDataFrame([(1, "test")], ["id", "name"])
        count = df.count()
        print(f"✅ DataFrame operation successful: {count} rows")

        spark.stop()
        print("✅ SparkSession stopped cleanly")

        return True

    except Exception as e:
        print(f"❌ SparkSession test failed: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_processes():
    """Check for conflicting Spark processes."""
    print("\n=== PROCESS CHECK ===")

    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        spark_processes = [line for line in result.stdout.split('\n') if 'spark' in line.lower()]

        if spark_processes:
            print("Found Spark processes:")
            for proc in spark_processes[:5]:  # Show first 5
                print(f"  {proc}")
        else:
            print("No Spark processes found")

    except Exception as e:
        print(f"Process check failed: {e}")


def main():
    """Run comprehensive diagnosis."""
    print("🔍 PYSPARK DIAGNOSIS TOOL")
    print("=" * 50)

    check_environment()

    if not check_imports():
        print("\n❌ Import issues detected. Try:")
        print("pip uninstall pyspark py4j")
        print("pip install pyspark")
        return

    check_processes()

    if test_spark_context():
        print("\n✅ SparkContext works! Testing SparkSession...")
        if test_spark_session():
            print("\n🎉 Everything works! The issue might be test-specific.")
        else:
            print("\n❌ SparkSession fails but SparkContext works.")
            print("This suggests a SparkSession-specific issue.")
    else:
        print("\n❌ SparkContext fails. This is a fundamental issue.")
        print("\nPossible solutions:")
        print("1. Reinstall PySpark: pip uninstall pyspark py4j && pip install pyspark")
        print("2. Check JAVA_HOME points to Java 11")
        print("3. Create fresh Python environment")


if __name__ == "__main__":
    main()