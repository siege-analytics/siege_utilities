#!/usr/bin/env python3
"""
Abstract HDFS Configuration
Configurable settings for HDFS operations - no hard-coded project dependencies
"""

import os
import pathlib
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class HDFSConfig:
    """Configuration class for HDFS operations"""

    # === CORE PATHS ===
    data_path: Optional[str] = None
    hdfs_base_directory: str = "/data/"
    cache_directory: Optional[str] = None

    # === SPARK CONFIGURATION ===
    app_name: str = "SparkDistributedProcessing"
    spark_log_level: str = "WARN"
    enable_sedona: bool = True

    # === SPARK RESOURCES ===
    num_executors: Optional[int] = None
    executor_cores: Optional[int] = None
    executor_memory: str = "2g"
    network_timeout: str = "800s"
    heartbeat_interval: str = "60s"

    # === HDFS SETTINGS ===
    hdfs_timeout: int = 10
    hdfs_copy_timeout: int = 300
    force_sync: bool = False

    # === DEPENDENCY INJECTION ===
    log_info_func: Optional[Callable[[str], None]] = None
    log_error_func: Optional[Callable[[str], None]] = None
    hash_func: Optional[Callable[[str], str]] = None
    quick_signature_func: Optional[Callable[[str], str]] = None

    def __post_init__(self):
        """Set up defaults after initialization"""
        if self.cache_directory is None:
            self.cache_directory = str(pathlib.Path.home() / ".spark_hdfs_cache")

        if self.num_executors is None:
            self.num_executors = int(os.environ.get("SPARK_EXECUTOR_INSTANCES", "4"))

        if self.executor_cores is None:
            self.executor_cores = int(os.environ.get("SPARK_EXECUTOR_CORES", "2"))

        if "SPARK_EXECUTOR_MEMORY" in os.environ:
            self.executor_memory = os.environ["SPARK_EXECUTOR_MEMORY"]

        if self.log_info_func is None:
            self.log_info_func = lambda msg: print(f"INFO: {msg}")

        if self.log_error_func is None:
            self.log_error_func = lambda msg: print(f"ERROR: {msg}")

    def get_cache_path(self, filename: str) -> pathlib.Path:
        """Get path for cache files"""
        return pathlib.Path(self.cache_directory) / filename

    def get_optimal_partitions(self) -> int:
        """Calculate optimal partitions for I/O heavy workloads"""
        return self.num_executors * self.executor_cores * 3

    def log_info(self, message: str):
        """Log info message using configured function"""
        if self.log_info_func:
            self.log_info_func(message)

    def log_error(self, message: str):
        """Log error message using configured function"""
        if self.log_error_func:
            self.log_error_func(message)


def create_hdfs_config(**kwargs) -> HDFSConfig:
    """Factory function to create HDFS configuration"""
    return HDFSConfig(**kwargs)


def create_local_config(data_path: str, **kwargs) -> HDFSConfig:
    """Create config optimized for local development"""
    defaults = {
        "data_path": data_path,
        "num_executors": 2,
        "executor_cores": 1,
        "executor_memory": "1g",
        "enable_sedona": False,
        "spark_log_level": "WARN",
    }
    defaults.update(kwargs)
    return HDFSConfig(**defaults)


def create_cluster_config(data_path: str, **kwargs) -> HDFSConfig:
    """Create config optimized for cluster deployment"""
    defaults = {
        "data_path": data_path,
        "num_executors": 8,
        "executor_cores": 4,
        "executor_memory": "4g",
        "enable_sedona": True,
        "spark_log_level": "WARN",
    }
    defaults.update(kwargs)
    return HDFSConfig(**defaults)


def create_geocoding_config(data_path: str, **kwargs) -> HDFSConfig:
    """Create config optimized for geocoding workloads"""
    defaults = {
        "data_path": data_path,
        "app_name": "GeocodingPipeline",
        "num_executors": 4,
        "executor_cores": 2,
        "executor_memory": "2g",
        "enable_sedona": True,
        "network_timeout": "1200s",
        "spark_log_level": "WARN",
    }
    defaults.update(kwargs)
    return HDFSConfig(**defaults)
