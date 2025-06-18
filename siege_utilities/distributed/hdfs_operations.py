"""
Abstract HDFS Operations - Fully Configurable and Reusable
Zero hard-coded project dependencies
"""
import os
import subprocess
import pathlib
import json
import time
import zipfile
import hashlib
from typing import Optional, Tuple, Dict, List


def _default_hash_function(file_path: str) ->str:
    """Default hash function using built-in hashlib"""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda : f.read(65536), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception:
        return f'error_{int(time.time())}'


def _default_quick_signature(file_path: str) ->str:
    """Default quick signature using file stats"""
    try:
        stat = pathlib.Path(file_path).stat()
        return f'{stat.st_size}_{stat.st_mtime}'
    except Exception:
        return 'error'


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
        except Exception as e:
            self.config.log_error(f'HDFS check failed: {e}')
            return False

    def create_spark_session(self):
        """Create Spark session using configuration"""
        try:
            from pyspark.sql import SparkSession
            self.config.log_info(
                f'Creating Spark session: {self.config.app_name}')
            self.config.log_info(
                f'  Executors: {self.config.num_executors}, Cores: {self.config.executor_cores}, Memory: {self.config.executor_memory}'
                )
            builder = SparkSession.builder.appName(self.config.app_name
                ).config('spark.sql.adaptive.enabled', 'true').config(
                'spark.sql.adaptive.coalescePartitions.enabled', 'true'
                ).config('spark.serializer',
                'org.apache.spark.serializer.KryoSerializer').config(
                'spark.executor.instances', str(self.config.num_executors)
                ).config('spark.executor.cores', str(self.config.
                executor_cores)).config('spark.executor.memory', self.
                config.executor_memory).config('spark.network.timeout',
                self.config.network_timeout).config(
                'spark.executor.heartbeatInterval', self.config.
                heartbeat_interval).config(
                'spark.sql.execution.arrow.pyspark.enabled', 'true').config(
                'spark.sql.shuffle.partitions', str(self.config.
                get_optimal_partitions()))
            spark = builder.getOrCreate()
            spark.sparkContext.setLogLevel(self.config.spark_log_level)
            if self.config.enable_sedona:
                try:
                    from sedona.register import SedonaRegistrator
                    SedonaRegistrator.registerAll(spark)
                    self.config.log_info('✓ Sedona registered successfully')
                except ImportError:
                    self.config.log_info('⚠️  Sedona not available')
                except Exception as e:
                    self.config.log_info(f'⚠️  Sedona registration failed: {e}'
                        )
            self.config.log_info('✓ Spark session created successfully')
            return spark
        except ImportError:
            self.config.log_error(
                'PySpark not available - install with: pip install pyspark')
            return None
        except Exception as e:
            self.config.log_error(f'Failed to create Spark session: {e}')
            return None

    def sync_directory_to_hdfs(self, local_path: Optional[str]=None,
        hdfs_subdir: str='inputs') ->Tuple[Optional[str], Optional[Dict]]:
        """Sync local directory/file to HDFS with proper verification"""
        try:
            if local_path is None:
                local_path = self.config.data_path
            if local_path is None:
                self.config.log_error('No data path provided')
                return None, None
            local_path = pathlib.Path(local_path)
            if not local_path.exists():
                self.config.log_error(f'Local path not found: {local_path}')
                return None, None
            if not self.check_hdfs_status():
                self.config.log_error('HDFS not accessible')
                return None, None
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
                hdfs_full_path], capture_output=True)
            if result.returncode == 0:
                self.config.log_info(f'✅ Sync complete: {hdfs_full_path}')
                return hdfs_full_path, {local_path.name: {'path': str(
                    local_path)}}
            else:
                self.config.log_error('❌ Sync verification failed')
                return None, None
        except Exception as e:
            self.config.log_error(f'Error syncing to HDFS: {e}')
            return None, None

    def setup_distributed_environment(self, data_path: Optional[str]=None,
        dependency_paths: Optional[List[str]]=None):
        """Main setup function with proper verification"""
        try:
            self.config.log_info('🚀 Setting up distributed environment...')
            if data_path is None:
                data_path = self.config.data_path
            if data_path is None:
                self.config.log_error('No data path provided')
                return None, None, None
            local_path = pathlib.Path(data_path)
            if not local_path.exists():
                self.config.log_error(f'Data path not found: {data_path}')
                return None, None, None
            if self.check_hdfs_status():
                self.config.log_info('📁 HDFS available - attempting sync...')
                hdfs_path, files_info = self.sync_directory_to_hdfs(data_path)
                if hdfs_path:
                    spark = self.create_spark_session()
                    if spark:
                        self.config.log_info(
                            '✅ Using HDFS for distributed processing')
                        return spark, hdfs_path, None
                    else:
                        self.config.log_error('Spark session creation failed')
            self.config.log_info('💻 Using local filesystem...')
            file_url = f'file://{local_path.absolute()}'
            spark = self.create_spark_session()
            if spark:
                self.config.log_info(
                    '✅ Distributed environment setup complete!')
                return spark, file_url, None
            else:
                self.config.log_error('Failed to create Spark session')
                return None, None, None
        except Exception as e:
            self.config.log_error(f'Error setting up environment: {e}')
            return None, None, None


def setup_distributed_environment(config, data_path: Optional[str]=None,
    dependency_paths: Optional[List[str]]=None):
    """Convenience function to set up distributed environment"""
    hdfs_ops = AbstractHDFSOperations(config)
    return hdfs_ops.setup_distributed_environment(data_path, dependency_paths)


def create_hdfs_operations(config):
    """Factory function to create HDFS operations instance"""
    return AbstractHDFSOperations(config)
