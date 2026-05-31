"""
Abstract HDFS Operations - Fully Configurable and Reusable
Zero hard-coded project dependencies
"""
import hashlib
import logging
import pathlib
import subprocess
from typing import Optional, Tuple, Dict, List

log = logging.getLogger(__name__)

__all__ = [
    "AbstractHDFSOperations",
    "create_hdfs_operations",
    "setup_distributed_environment",
]


def _default_hash_function(file_path: str) -> str:
    """Default hash function using built-in hashlib."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def _default_quick_signature(file_path: str) -> str:
    """Default quick signature using file stats."""
    stat = pathlib.Path(file_path).stat()
    return f'{stat.st_size}_{stat.st_mtime}'


def _ensure_directory_exists(path: str):
    """Ensure directory exists"""
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


class AbstractHDFSOperations:
    """Abstract HDFS Operations class that can be configured for any project"""

    def __init__(self, config):
        """Initialize with HDFSConfig"""
        self.config = config
        _ensure_directory_exists(self.config.cache_directory)
        self.data_sync_cache = self.config.get_cache_path('data_sync_info.json'
            )
        self.dependencies_cache = self.config.get_cache_path(
            'dependencies_info.json')
        self.python_deps_zip = self.config.get_cache_path(
            'python_dependencies.zip')
        self.hash_func = config.hash_func or _default_hash_function
        self.quick_signature_func = (config.quick_signature_func or
            _default_quick_signature)

    def check_hdfs_status(self) ->bool:
        """Check if HDFS is accessible"""
        try:
            result = subprocess.run(['hdfs', 'dfs', '-ls', '/'],
                capture_output=True, text=True, timeout=self.config.
                hdfs_timeout)
            if result.returncode == 0:
                self.config.log_info('✓ HDFS is accessible')
                return True
            else:
                self.config.log_error(
                    'HDFS not accessible - start with: start-dfs.sh')
                return False
        except subprocess.TimeoutExpired:
            self.config.log_error('HDFS timeout - check if Hadoop is running')
            return False
        except FileNotFoundError:
            self.config.log_error(
                'HDFS command not found - check Hadoop installation')
            return False
        except (OSError, ValueError) as e:
            self.config.log_error(f'HDFS check failed: {e}')
            return False

    def create_spark_session(self):
        """Create Spark session using configuration.

        Supports local, standalone cluster, and YARN deployments based on
        the master URL in the config.
        """
        try:
            from pyspark.sql import SparkSession
            from pyspark.sql.utils import AnalysisException as _SparkAnalysisException
            try:
                from py4j.protocol import Py4JJavaError as _Py4JError
            except ImportError:
                _Py4JError = _SparkAnalysisException
            self.config.log_info(
                f'Creating Spark session: {self.config.app_name}')
            self.config.log_info(
                f'  Master: {self.config.master}')
            self.config.log_info(
                f'  Executors: {self.config.num_executors}, Cores: {self.config.executor_cores}, Memory: {self.config.executor_memory}'
                )

            # Start building the session
            builder = SparkSession.builder.appName(self.config.app_name)

            # Set master URL
            builder = builder.master(self.config.master)

            # YARN-specific configuration
            if self.config.is_yarn:
                builder = builder.config('spark.submit.deployMode',
                    self.config.deploy_mode)
                if self.config.yarn_queue:
                    builder = builder.config('spark.yarn.queue',
                        self.config.yarn_queue)
                self.config.log_info(
                    f'  YARN queue: {self.config.yarn_queue or "default"}, '
                    f'Deploy mode: {self.config.deploy_mode}')

            # Driver configuration
            builder = builder.config('spark.driver.memory',
                self.config.driver_memory)
            builder = builder.config('spark.driver.cores',
                str(self.config.driver_cores))

            # Common Spark settings
            builder = builder.config('spark.sql.adaptive.enabled', 'true'
                ).config('spark.sql.adaptive.coalescePartitions.enabled', 'true'
                ).config('spark.serializer',
                'org.apache.spark.serializer.KryoSerializer'
                ).config('spark.executor.instances', str(self.config.num_executors)
                ).config('spark.executor.cores', str(self.config.executor_cores)
                ).config('spark.executor.memory', self.config.executor_memory
                ).config('spark.network.timeout', self.config.network_timeout
                ).config('spark.executor.heartbeatInterval',
                self.config.heartbeat_interval
                ).config('spark.sql.execution.arrow.pyspark.enabled', 'true'
                ).config('spark.sql.shuffle.partitions',
                str(self.config.get_optimal_partitions()))

            spark = builder.getOrCreate()
            spark.sparkContext.setLogLevel(self.config.spark_log_level)

            # Register Sedona if enabled
            if self.config.enable_sedona:
                try:
                    from sedona.register import SedonaRegistrator
                    SedonaRegistrator.registerAll(spark)

                    # Apply Sedona configuration
                    spark.conf.set('sedona.global.index.type',
                        self.config.sedona_global_index_type)
                    spark.conf.set('sedona.join.autoBroadcastJoinThreshold',
                        str(self.config.sedona_join_broadcast_threshold))

                    self.config.log_info('✓ Sedona registered successfully')
                    self.config.log_info(
                        f'  Index type: {self.config.sedona_global_index_type}, '
                        f'Broadcast threshold: {self.config.sedona_join_broadcast_threshold // (1024*1024)}MB')
                except ImportError:
                    self.config.log_info('⚠️  Sedona not available')
                except (_Py4JError, RuntimeError, ValueError, AttributeError) as e:
                    self.config.log_info(f'⚠️  Sedona registration failed: {e}'
                        )

            self.config.log_info('✓ Spark session created successfully')
            return spark
        except ImportError as e:
            raise ImportError(
                'PySpark not available - install with: pip install pyspark'
            ) from e

    def sync_directory_to_hdfs(self, local_path: Optional[str]=None,
        hdfs_subdir: str='inputs') -> Tuple[str, Dict]:
        """Sync local directory/file to HDFS with proper verification.

        Raises:
            ValueError: If no data path is provided.
            FileNotFoundError: If the local path does not exist.
            RuntimeError: If HDFS is not accessible or sync verification fails.
            subprocess.CalledProcessError: If an HDFS command fails.
            subprocess.TimeoutExpired: If an HDFS command times out.
        """
        if local_path is None:
            local_path = self.config.data_path
        if local_path is None:
            raise ValueError('No data path provided')
        local_path = pathlib.Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f'Local path not found: {local_path}')
        if not self.check_hdfs_status():
            raise RuntimeError('HDFS not accessible')
        if local_path.is_file():
            hdfs_directory = (self.config.hdfs_base_directory +
                f'{hdfs_subdir}/')
            hdfs_full_path = hdfs_directory + local_path.name
        else:
            hdfs_directory = (self.config.hdfs_base_directory +
                f'{hdfs_subdir}/{local_path.name}/')
            hdfs_full_path = hdfs_directory
        self.config.log_info(f'Syncing: {local_path} -> {hdfs_full_path}')
        subprocess.run(['hdfs', 'dfs', '-mkdir', '-p', hdfs_directory],
            check=True, timeout=60)
        subprocess.run(['hdfs', 'dfs', '-put', '-f', str(local_path),
            hdfs_full_path], check=True, timeout=self.config.
            hdfs_copy_timeout)
        result = subprocess.run(['hdfs', 'dfs', '-test', '-e',
            hdfs_full_path], capture_output=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError('Sync verification failed: file not found on HDFS after put')
        self.config.log_info(f'✅ Sync complete: {hdfs_full_path}')
        return hdfs_full_path, {local_path.name: {'path': str(local_path)}}

    def setup_distributed_environment(self, data_path: Optional[str]=None,
        dependency_paths: Optional[List[str]]=None):
        """Main setup function with proper verification.

        Returns:
            Tuple of (spark_session, data_url, None).

        Raises:
            ValueError: If no data path is provided.
            FileNotFoundError: If the data path does not exist.
            ImportError: If PySpark is not available.
            RuntimeError: If HDFS sync or Spark session creation fails.
        """
        self.config.log_info('🚀 Setting up distributed environment...')
        if dependency_paths:
            self.config.log_info(
                f'⚠️  dependency_paths ({len(dependency_paths)} items) not yet '
                'supported — dependencies must be pre-installed on workers'
            )
        if data_path is None:
            data_path = self.config.data_path
        if data_path is None:
            raise ValueError('No data path provided')
        local_path = pathlib.Path(data_path)
        if not local_path.exists():
            raise FileNotFoundError(f'Data path not found: {data_path}')
        if self.check_hdfs_status():
            self.config.log_info('📁 HDFS available - attempting sync...')
            try:
                hdfs_path, files_info = self.sync_directory_to_hdfs(data_path)
                spark = self.create_spark_session()
                self.config.log_info(
                    '✅ Using HDFS for distributed processing')
                return spark, hdfs_path, None
            except (RuntimeError, subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as e:
                self.config.log_info(
                    f'⚠️  HDFS sync failed, falling back to local: {e}')
        self.config.log_info('💻 Using local filesystem...')
        file_url = f'file://{local_path.absolute()}'
        spark = self.create_spark_session()
        self.config.log_info(
            '✅ Distributed environment setup complete!')
        return spark, file_url, None


def setup_distributed_environment(config, data_path: Optional[str]=None,
    dependency_paths: Optional[List[str]]=None):
    """Convenience function to set up distributed environment"""
    hdfs_ops = AbstractHDFSOperations(config)
    return hdfs_ops.setup_distributed_environment(data_path, dependency_paths)


def create_hdfs_operations(config):
    """Factory function to create HDFS operations instance"""
    return AbstractHDFSOperations(config)
