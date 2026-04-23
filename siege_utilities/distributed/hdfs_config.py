"""
Abstract HDFS Configuration
Configurable settings for HDFS operations - no hard-coded project dependencies
"""
import os
import pathlib
from dataclasses import dataclass
from typing import Optional, Callable

from siege_utilities.core.logging import log_info, log_error


@dataclass
class HDFSConfig:
    """Configuration class for HDFS and Spark operations.

    Supports local, standalone cluster, and YARN deployments.

    Attributes:
        master: Spark master URL ('local[*]', 'yarn', 'spark://host:7077')
        deploy_mode: Deployment mode for YARN ('client' or 'cluster')
        yarn_queue: YARN queue name for resource allocation
        driver_memory: Memory allocated to driver process
    """
    data_path: Optional[str] = None
    hdfs_base_directory: str = '/data/'
    cache_directory: Optional[str] = None
    app_name: str = 'SparkDistributedProcessing'
    spark_log_level: str = 'WARN'

    # Spark master configuration
    master: str = 'local[*]'
    deploy_mode: str = 'client'  # 'client' or 'cluster'
    yarn_queue: Optional[str] = None

    # Sedona configuration
    enable_sedona: bool = True
    sedona_global_index_type: str = 'rtree'  # 'rtree' or 'quadtree'
    sedona_join_broadcast_threshold: int = 10 * 1024 * 1024  # 10MB

    # Resource allocation
    num_executors: Optional[int] = None
    executor_cores: Optional[int] = None
    executor_memory: str = '2g'
    driver_memory: str = '2g'
    driver_cores: int = 1

    # Timeouts and networking
    network_timeout: str = '800s'
    heartbeat_interval: str = '60s'
    hdfs_timeout: int = 10
    hdfs_copy_timeout: int = 300

    # Sync behavior
    force_sync: bool = False

    # Logging and hashing functions
    log_info_func: Optional[Callable[[str], None]] = None
    log_error_func: Optional[Callable[[str], None]] = None
    hash_func: Optional[Callable[[str], str]] = None
    quick_signature_func: Optional[Callable[[str], str]] = None

    def __post_init__(self):
        """Set up defaults after initialization"""
        if self.cache_directory is None:
            self.cache_directory = str(pathlib.Path.home() /
                '.spark_hdfs_cache')
        if self.num_executors is None:
            self.num_executors = int(os.environ.get(
                'SPARK_EXECUTOR_INSTANCES', '4'))
        if self.executor_cores is None:
            self.executor_cores = int(os.environ.get('SPARK_EXECUTOR_CORES',
                '2'))
        if 'SPARK_EXECUTOR_MEMORY' in os.environ:
            self.executor_memory = os.environ['SPARK_EXECUTOR_MEMORY']
        if 'SPARK_DRIVER_MEMORY' in os.environ:
            self.driver_memory = os.environ['SPARK_DRIVER_MEMORY']
        if 'SPARK_MASTER' in os.environ:
            self.master = os.environ['SPARK_MASTER']
        if 'YARN_QUEUE' in os.environ:
            self.yarn_queue = os.environ['YARN_QUEUE']
        if self.log_info_func is None:
            self.log_info_func = lambda msg: log_info(msg)
        if self.log_error_func is None:
            self.log_error_func = lambda msg: log_error(msg)

    def get_cache_path(self, filename: str) ->pathlib.Path:
        """Get path for cache files"""
        return pathlib.Path(self.cache_directory) / filename

    def get_optimal_partitions(self) ->int:
        """Calculate optimal partitions for I/O heavy workloads"""
        return self.num_executors * self.executor_cores * 3

    @property
    def is_yarn(self) -> bool:
        """Check if this config targets a YARN cluster."""
        return self.master.lower() == 'yarn'

    @property
    def is_local(self) -> bool:
        """Check if this config targets local mode."""
        return self.master.lower().startswith('local')

    def log_info(self, message: str):
        """Log info message using configured function"""
        if self.log_info_func:
            self.log_info_func(message)

    def log_error(self, message: str):
        """Log error message using configured function"""
        if self.log_error_func:
            self.log_error_func(message)


def create_hdfs_config(**kwargs) ->HDFSConfig:
    """Factory function to create HDFS configuration"""
    return HDFSConfig(**kwargs)


def create_local_config(data_path: str, **kwargs) ->HDFSConfig:
    """Create config optimized for local development"""
    defaults = {'data_path': data_path, 'num_executors': 2,
        'executor_cores': 1, 'executor_memory': '1g', 'enable_sedona': 
        False, 'spark_log_level': 'WARN'}
    defaults.update(kwargs)
    return HDFSConfig(**defaults)


def create_cluster_config(data_path: str, **kwargs) ->HDFSConfig:
    """Create config optimized for cluster deployment"""
    defaults = {'data_path': data_path, 'num_executors': 8,
        'executor_cores': 4, 'executor_memory': '4g', 'enable_sedona': True,
        'spark_log_level': 'WARN'}
    defaults.update(kwargs)
    return HDFSConfig(**defaults)


def create_geocoding_config(data_path: str, **kwargs) ->HDFSConfig:
    """Create config optimized for geocoding workloads"""
    defaults = {'data_path': data_path, 'app_name': 'GeocodingPipeline',
        'num_executors': 4, 'executor_cores': 2, 'executor_memory': '2g',
        'enable_sedona': True, 'network_timeout': '1200s',
        'spark_log_level': 'WARN'}
    defaults.update(kwargs)
    return HDFSConfig(**defaults)


def create_yarn_config(data_path: str, **kwargs) -> HDFSConfig:
    """Create config optimized for YARN cluster deployment.

    This configuration is designed for production YARN clusters with:
    - YARN as the resource manager
    - Client deploy mode (driver runs locally)
    - Higher resource allocation for executors
    - Sedona enabled for spatial operations

    Args:
        data_path: Path to data (local or HDFS)
        **kwargs: Override any default settings

    Returns:
        HDFSConfig configured for YARN deployment

    Example:
        >>> config = create_yarn_config('/data/census', yarn_queue='analytics')
        >>> spark, path, _ = setup_distributed_environment(config)
    """
    defaults = {
        'data_path': data_path,
        'app_name': 'SiegeAnalyticsYARN',
        'master': 'yarn',
        'deploy_mode': 'client',
        'num_executors': 10,
        'executor_cores': 4,
        'executor_memory': '8g',
        'driver_memory': '4g',
        'driver_cores': 2,
        'enable_sedona': True,
        'sedona_global_index_type': 'rtree',
        'network_timeout': '600s',
        'heartbeat_interval': '60s',
        'spark_log_level': 'WARN',
    }
    defaults.update(kwargs)
    return HDFSConfig(**defaults)


def create_census_analysis_config(data_path: str, **kwargs) -> HDFSConfig:
    """Create config optimized for Census longitudinal analysis.

    Designed for processing large Census datasets with:
    - Sedona for spatial operations (boundary crosswalks)
    - Optimized partitioning for Census tract-level data
    - Memory settings for time-series joins

    Args:
        data_path: Path to Census data
        **kwargs: Override any default settings

    Returns:
        HDFSConfig optimized for Census analysis

    Example:
        >>> config = create_census_analysis_config('/data/census/acs')
        >>> spark, path, _ = setup_distributed_environment(config)
    """
    defaults = {
        'data_path': data_path,
        'app_name': 'CensusLongitudinalAnalysis',
        'num_executors': 6,
        'executor_cores': 4,
        'executor_memory': '4g',
        'driver_memory': '4g',
        'enable_sedona': True,
        'sedona_global_index_type': 'rtree',
        'sedona_join_broadcast_threshold': 50 * 1024 * 1024,  # 50MB for Census shapes
        'network_timeout': '900s',
        'spark_log_level': 'WARN',
    }
    defaults.update(kwargs)
    return HDFSConfig(**defaults)
