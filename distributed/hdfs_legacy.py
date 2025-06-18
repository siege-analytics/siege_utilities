#!/usr/bin/env python3
"""
Fixed HDFS Operations - Properly working version
Fixes all import issues, hash functions, and HDFS verification
"""

import os
import subprocess
import pathlib
import json
import time
import zipfile
import hashlib
from typing import Optional, Tuple, Dict

# Import your utilities (with fallbacks for missing functions)
try:
except ImportError:

    def log_info(msg):
        print(f"INFO: {msg}")

    def log_error(msg):
        print(f"ERROR: {msg}")


try:
except ImportError:

    def ensure_path_exists(path):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)


# Import hash functions - with proper fallbacks
try:
        generate_sha256_hash_for_file,
        get_file_hash,
        get_quick_file_signature,
    )
except ImportError:
    log_error("Hash functions not found in utilities - using built-in fallbacks")

    # Fallback hash functions
    def generate_sha256_hash_for_file(file_path):
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            log_error(f"Error generating hash for {file_path}: {e}")
            return None

    def get_file_hash(file_path, algorithm="sha256"):
        return generate_sha256_hash_for_file(file_path)

    def get_quick_file_signature(file_path):
        try:
            stat = pathlib.Path(file_path).stat()
            return f"{stat.st_size}_{stat.st_mtime}"
        except:
            return "error"


# Try to get settings
try:
    from settings import PATH_TO_TAN_INPUTS
except ImportError:
    PATH_TO_TAN_INPUTS = None

# =============================================================================
# CONFIGURATION VARIABLES
# =============================================================================

DEFAULT_SPARK_LOG_LEVEL = "WARN"
ENABLE_SEDONA = True

HDFS_CACHE_DIR = pathlib.Path.home() / ".spark_hdfs_cache"
HDFS_CACHE_DIR.mkdir(exist_ok=True)

DATA_SYNC_CACHE = HDFS_CACHE_DIR / "data_sync_info.json"
DEPENDENCIES_CACHE = HDFS_CACHE_DIR / "dependencies_info.json"
PYTHON_DEPS_ZIP = HDFS_CACHE_DIR / "python_dependencies.zip"


# =============================================================================
# CORE FUNCTIONS
# =============================================================================


def check_hdfs_status():
    """Check if HDFS is accessible"""
    try:
        result = subprocess.run(
            ["hdfs", "dfs", "-ls", "/"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            log_info("✓ HDFS is accessible")
            return True
        else:
            log_error("HDFS not accessible - start with: start-dfs.sh")
            return False
    except subprocess.TimeoutExpired:
        log_error("HDFS timeout - check if Hadoop is running")
        return False
    except FileNotFoundError:
        log_error("HDFS command not found - check Hadoop installation")
        return False
    except Exception as e:
        log_error(f"HDFS check failed: {e}")
        return False


def verify_hdfs_file_exists(hdfs_path):
    """Verify that a file actually exists in HDFS"""
    try:
        log_info(f"🔍 Verifying HDFS file exists: {hdfs_path}")

        # Test if file exists
        result = subprocess.run(
            ["hdfs", "dfs", "-test", "-e", hdfs_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            # Get file info to confirm
            ls_result = subprocess.run(
                ["hdfs", "dfs", "-ls", hdfs_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if ls_result.returncode == 0:
                file_info = ls_result.stdout.strip()
                log_info(f"✅ HDFS file verified: {file_info}")
                return True
            else:
                log_error(f"File test passed but ls failed: {ls_result.stderr}")
                return False
        else:
            log_error(f"HDFS file does not exist: {hdfs_path}")
            return False

    except Exception as e:
        log_error(f"Error verifying HDFS file: {e}")
        return False


def create_spark_session(
    app_name="DistributedGeocoding",
    enable_sedona=ENABLE_SEDONA,
    log_level=DEFAULT_SPARK_LOG_LEVEL,
):
    """Create Spark session with configurable Sedona and logging"""
    try:
        from pyspark.sql import SparkSession

        # Get environment settings
        num_executors = int(os.environ.get("SPARK_EXECUTOR_INSTANCES", "4"))
        executor_cores = int(os.environ.get("SPARK_EXECUTOR_CORES", "2"))
        executor_memory = os.environ.get("SPARK_EXECUTOR_MEMORY", "2g")

        log_info(f"Creating Spark session: {app_name}")
        log_info(
            f"  Executors: {num_executors}, Cores: {executor_cores}, Memory: {executor_memory}"
        )
        log_info(f"  Log level: {log_level}, Sedona enabled: {enable_sedona}")

        # Build Spark session
        builder = (
            SparkSession.builder.appName(app_name)
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .config("spark.executor.instances", str(num_executors))
            .config("spark.executor.cores", str(executor_cores))
            .config("spark.executor.memory", executor_memory)
            .config("spark.network.timeout", "800s")
            .config("spark.executor.heartbeatInterval", "60s")
        )

        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel(log_level)

        # Sedona registration
        if enable_sedona:
            try:
                from sedona.register import SedonaRegistrator

                SedonaRegistrator.registerAll(spark)
                log_info("✓ Sedona registered successfully")
            except ImportError:
                log_info(
                    "⚠️  Sedona not available - install with: pip install apache-sedona"
                )
            except Exception as e:
                log_info(
                    f"⚠️  Sedona registration failed: {e} - continuing without geospatial functions"
                )
        else:
            log_info("⚠️  Sedona registration skipped (disabled in configuration)")

        log_info("✓ Spark session created successfully")
        return spark

    except ImportError:
        log_error("PySpark not available - install with: pip install pyspark")
        return None
    except Exception as e:
        log_error(f"Failed to create Spark session: {e}")
        return None


def get_local_files_info(directory_path):
    """Get info about local files using proper hash functions"""
    dir_path = pathlib.Path(directory_path)
    if not dir_path.exists():
        return {}

    files_info = {}

    if dir_path.is_file():
        files_info[dir_path.name] = {
            "mtime": dir_path.stat().st_mtime,
            "size": dir_path.stat().st_size,
            "path": str(dir_path),
            "hash": get_quick_file_signature(str(dir_path)),
        }
    else:
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(dir_path)
                files_info[str(relative_path)] = {
                    "mtime": file_path.stat().st_mtime,
                    "size": file_path.stat().st_size,
                    "path": str(file_path),
                    "hash": get_quick_file_signature(str(file_path)),
                }

    return files_info


def sync_directory_to_hdfs(local_path, hdfs_base_directory="/data/", force_sync=False):
    """Sync local directory/file to HDFS with proper verification"""
    try:
        local_path = pathlib.Path(local_path)
        if not local_path.exists():
            log_error(f"Local path not found: {local_path}")
            return None, None

        # Check HDFS first
        if not check_hdfs_status():
            log_error("HDFS not accessible - cannot sync")
            return None, None

        # Determine HDFS destination
        if local_path.is_file():
            hdfs_directory = hdfs_base_directory + "inputs/"
            hdfs_full_path = hdfs_directory + local_path.name
            operation_type = "file"
        else:
            hdfs_directory = hdfs_base_directory + local_path.name + "/"
            hdfs_full_path = hdfs_directory
            operation_type = "directory"

        log_info(f"Syncing {operation_type}: {local_path} -> {hdfs_full_path}")

        # Get current file info
        files_info = get_local_files_info(str(local_path))

        # Check if we need to sync (unless forced)
        if not force_sync and DATA_SYNC_CACHE.exists():
            try:
                with open(DATA_SYNC_CACHE, "r") as f:
                    cached_info = json.load(f)

                if (
                    cached_info.get("local_path") == str(local_path)
                    and cached_info.get("hdfs_path") == hdfs_full_path
                    and cached_info.get("files_info") == files_info
                ):

                    # Verify the file still exists in HDFS
                    if verify_hdfs_file_exists(hdfs_full_path):
                        log_info(
                            f"✓ {operation_type.title()} unchanged and verified in HDFS"
                        )
                        return hdfs_full_path, files_info
                    else:
                        log_info("Cached file not found in HDFS - forcing sync")

            except (json.JSONDecodeError, KeyError):
                log_info("Cache invalid - syncing")

        # Create HDFS directory
        try:
            log_info(f"Creating HDFS directory: {hdfs_directory}")
            result = subprocess.run(
                ["hdfs", "dfs", "-mkdir", "-p", hdfs_directory],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            log_info("✅ HDFS directory created")
        except subprocess.CalledProcessError as e:
            log_error(f"Failed to create HDFS directory: {e.stderr}")
            return None, None

        # Copy files to HDFS
        try:
            if local_path.is_file():
                # Single file copy
                log_info(f"Copying file: {local_path} -> {hdfs_full_path}")
                copy_result = subprocess.run(
                    ["hdfs", "dfs", "-put", "-f", str(local_path), hdfs_full_path],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300,  # 5 minute timeout for large files
                )
                log_info("✅ File copied to HDFS")
            else:
                # Directory copy
                log_info(f"Copying directory contents...")
                for file_path in local_path.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(local_path)
                        hdfs_file_path = hdfs_directory + str(relative_path)

                        # Ensure parent directory exists
                        hdfs_parent = "/".join(hdfs_file_path.split("/")[:-1])
                        if hdfs_parent:
                            subprocess.run(
                                ["hdfs", "dfs", "-mkdir", "-p", hdfs_parent],
                                check=True,
                                timeout=30,
                            )

                        # Copy the file
                        subprocess.run(
                            [
                                "hdfs",
                                "dfs",
                                "-put",
                                "-f",
                                str(file_path),
                                hdfs_file_path,
                            ],
                            check=True,
                            timeout=60,
                        )
                        log_info(f"     ✓ {relative_path}")

        except subprocess.CalledProcessError as e:
            log_error(f"Failed to copy to HDFS: {e.stderr}")
            return None, None
        except subprocess.TimeoutExpired:
            log_error("HDFS copy operation timed out")
            return None, None

        # Verify the sync worked
        if verify_hdfs_file_exists(hdfs_full_path):
            # Update cache
            cache_data = {
                "local_path": str(local_path),
                "hdfs_path": hdfs_full_path,
                "files_info": files_info,
                "sync_timestamp": time.time(),
            }
            with open(DATA_SYNC_CACHE, "w") as f:
                json.dump(cache_data, f, indent=2)

            log_info(
                f"📁 {operation_type.title()} sync complete and verified: {hdfs_full_path}"
            )
            return hdfs_full_path, files_info
        else:
            log_error("❌ Sync completed but file verification failed")
            return None, None

    except Exception as e:
        log_error(f"Error syncing {local_path} to HDFS: {e}")
        return None, None


def setup_distributed_environment(
    data_path=None,
    force_refresh=False,
    app_name="DistributedGeocoding",
    enable_sedona=ENABLE_SEDONA,
    log_level=DEFAULT_SPARK_LOG_LEVEL,
):
    """
    Main setup function with proper verification
    """
    try:
        log_info("🚀 Setting up distributed environment...")

        # Get data path
        if data_path is None:
            if PATH_TO_TAN_INPUTS is None:
                log_error(
                    "No data path provided and PATH_TO_TAN_INPUTS not found in settings"
                )
                return None, None
            data_path = PATH_TO_TAN_INPUTS

        local_path = pathlib.Path(data_path)
        if not local_path.exists():
            log_error(f"Data path not found: {data_path}")
            return None, None

        log_info(f"Using data path: {data_path}")

        # Try HDFS first if available
        if check_hdfs_status():
            log_info("📁 HDFS available - attempting sync...")
            hdfs_path, files_info = sync_directory_to_hdfs(
                data_path, force_sync=force_refresh
            )

            if hdfs_path and verify_hdfs_file_exists(hdfs_path):
                # Create Spark session
                spark = create_spark_session(app_name, enable_sedona, log_level)
                if spark:
                    log_info("✅ Using HDFS for distributed processing")
                    log_info(f"   Data: {hdfs_path} ({len(files_info)} files)")
                    return spark, hdfs_path
                else:
                    log_error("Spark session creation failed")
            else:
                log_info("HDFS sync failed - falling back to local filesystem")

        # Fall back to local filesystem
        log_info("💻 Using local filesystem with file:// protocol...")
        file_url = f"file://{local_path.absolute()}"

        spark = create_spark_session(app_name, enable_sedona, log_level)
        if spark:
            log_info("✅ Distributed environment setup complete!")
            log_info(f"   Data: {file_url}")
            log_info(f"   Spark: {spark.sparkContext.appName}")
            return spark, file_url
        else:
            log_error("Failed to create Spark session")
            return None, None

    except Exception as e:
        log_error(f"Error setting up distributed environment: {e}")
        return None, None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def quick_hdfs_setup(
    data_path=None, enable_sedona=ENABLE_SEDONA, log_level=DEFAULT_SPARK_LOG_LEVEL
):
    """Quick setup with smart caching"""
    return setup_distributed_environment(
        data_path, force_refresh=False, enable_sedona=enable_sedona, log_level=log_level
    )


def force_hdfs_refresh(
    data_path=None, enable_sedona=ENABLE_SEDONA, log_level=DEFAULT_SPARK_LOG_LEVEL
):
    """Force refresh of all caches"""
    clear_hdfs_cache()
    return setup_distributed_environment(
        data_path, force_refresh=True, enable_sedona=enable_sedona, log_level=log_level
    )


def clear_hdfs_cache():
    """Clear HDFS cache files"""
    try:
        cache_files = [DATA_SYNC_CACHE, DEPENDENCIES_CACHE, PYTHON_DEPS_ZIP]
        cleared = 0
        for cache_file in cache_files:
            if cache_file.exists():
                cache_file.unlink()
                cleared += 1
        log_info(f"✓ Cleared {cleared} HDFS cache files")
    except Exception as e:
        log_error(f"Error clearing cache: {e}")


def test_hdfs_module():
    """Test function to verify module is working"""
    try:
        log_info("🧪 Testing HDFS module...")

        # Test hash functions
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test data for hash")
            test_file = f.name

        hash_result = get_file_hash(test_file)
        log_info(f"Hash test: {hash_result[:16]}... ✓")

        # Clean up
        os.unlink(test_file)

        # Test HDFS status
        hdfs_available = check_hdfs_status()
        log_info(f"HDFS available: {hdfs_available}")

        return "HDFS operations module loaded and working!"

    except Exception as e:
        log_error(f"Module test failed: {e}")
        return f"Module test failed: {e}"


# Configuration helpers
def set_sedona_enabled(enabled=True):
    global ENABLE_SEDONA
    ENABLE_SEDONA = enabled
    log_info(f"Sedona registration {'enabled' if enabled else 'disabled'}")


def set_spark_log_level(level="WARN"):
    global DEFAULT_SPARK_LOG_LEVEL
    valid_levels = ["ALL", "DEBUG", "ERROR", "FATAL", "INFO", "OFF", "TRACE", "WARN"]
    if level.upper() in valid_levels:
        DEFAULT_SPARK_LOG_LEVEL = level.upper()
        log_info(f"Spark log level set to: {DEFAULT_SPARK_LOG_LEVEL}")
    else:
        log_error(f"Invalid log level: {level}. Valid options: {valid_levels}")


def get_current_config():
    return {
        "sedona_enabled": ENABLE_SEDONA,
        "spark_log_level": DEFAULT_SPARK_LOG_LEVEL,
        "cache_directory": str(HDFS_CACHE_DIR),
    }


# Module test
if __name__ == "__main__":
    result = test_hdfs_module()
    log_info(f"✅ {result}")
