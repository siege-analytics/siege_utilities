"""
Unit tests for HDFS configuration module.

Tests HDFSConfig dataclass, factory functions, and configuration management.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from siege_utilities.distributed.hdfs_config import (
    HDFSConfig,
    create_hdfs_config,
    create_local_config,
    create_cluster_config,
    create_geocoding_config,
    create_yarn_config,
    create_census_analysis_config,
)


# =============================================================================
# HDFSCONFIG INITIALIZATION TESTS
# =============================================================================

class TestHDFSConfigInit:
    """Tests for HDFSConfig initialization."""

    def test_default_values(self):
        """Test that HDFSConfig has sensible defaults."""
        config = HDFSConfig()

        assert config.hdfs_base_directory == '/data/'
        assert config.app_name == 'SparkDistributedProcessing'
        assert config.spark_log_level == 'WARN'
        assert config.master == 'local[*]'
        assert config.deploy_mode == 'client'
        assert config.enable_sedona is True
        assert config.executor_memory == '2g'
        assert config.driver_memory == '2g'
        assert config.network_timeout == '800s'

    def test_custom_values(self):
        """Test that custom values override defaults."""
        # Clear env vars that might override our values
        env_clear = {
            'SPARK_EXECUTOR_MEMORY': '',
            'SPARK_EXECUTOR_INSTANCES': '',
            'SPARK_EXECUTOR_CORES': '',
            'SPARK_MASTER': '',
        }
        with patch.dict(os.environ, env_clear, clear=False):
            # Remove the keys entirely
            for key in env_clear:
                os.environ.pop(key, None)

            config = HDFSConfig(
                app_name='TestApp',
                master='yarn',
                num_executors=10,
                executor_memory='8g',
            )

            assert config.app_name == 'TestApp'
            assert config.master == 'yarn'
            assert config.num_executors == 10
            assert config.executor_memory == '8g'

    def test_cache_directory_default(self):
        """Test that cache directory defaults to home directory."""
        config = HDFSConfig()
        expected = str(Path.home() / '.spark_hdfs_cache')
        assert config.cache_directory == expected

    def test_custom_cache_directory(self):
        """Test that custom cache directory is used."""
        config = HDFSConfig(cache_directory='/tmp/my_cache')
        assert config.cache_directory == '/tmp/my_cache'


class TestHDFSConfigEnvVars:
    """Tests for environment variable handling."""

    def test_executor_instances_from_env(self):
        """Test that SPARK_EXECUTOR_INSTANCES is respected."""
        with patch.dict(os.environ, {'SPARK_EXECUTOR_INSTANCES': '16'}):
            config = HDFSConfig()
            assert config.num_executors == 16

    def test_executor_cores_from_env(self):
        """Test that SPARK_EXECUTOR_CORES is respected."""
        with patch.dict(os.environ, {'SPARK_EXECUTOR_CORES': '8'}):
            config = HDFSConfig()
            assert config.executor_cores == 8

    def test_executor_memory_from_env(self):
        """Test that SPARK_EXECUTOR_MEMORY is respected."""
        with patch.dict(os.environ, {'SPARK_EXECUTOR_MEMORY': '16g'}):
            config = HDFSConfig()
            assert config.executor_memory == '16g'

    def test_driver_memory_from_env(self):
        """Test that SPARK_DRIVER_MEMORY is respected."""
        with patch.dict(os.environ, {'SPARK_DRIVER_MEMORY': '8g'}):
            config = HDFSConfig()
            assert config.driver_memory == '8g'

    def test_master_from_env(self):
        """Test that SPARK_MASTER is respected."""
        with patch.dict(os.environ, {'SPARK_MASTER': 'yarn'}):
            config = HDFSConfig()
            assert config.master == 'yarn'

    def test_yarn_queue_from_env(self):
        """Test that YARN_QUEUE is respected."""
        with patch.dict(os.environ, {'YARN_QUEUE': 'analytics'}):
            config = HDFSConfig()
            assert config.yarn_queue == 'analytics'


# =============================================================================
# HDFSCONFIG METHODS TESTS
# =============================================================================

class TestHDFSConfigMethods:
    """Tests for HDFSConfig methods."""

    def test_get_cache_path(self):
        """Test cache path generation."""
        config = HDFSConfig(cache_directory='/tmp/cache')
        path = config.get_cache_path('test.json')
        assert path == Path('/tmp/cache/test.json')

    def test_get_optimal_partitions(self):
        """Test optimal partition calculation."""
        config = HDFSConfig(num_executors=4, executor_cores=2)
        # Formula: executors * cores * 3
        assert config.get_optimal_partitions() == 24

    def test_get_optimal_partitions_large_cluster(self):
        """Test optimal partitions for larger cluster."""
        config = HDFSConfig(num_executors=10, executor_cores=4)
        assert config.get_optimal_partitions() == 120

    def test_is_yarn_true(self):
        """Test is_yarn property when master is yarn."""
        config = HDFSConfig(master='yarn')
        assert config.is_yarn is True

    def test_is_yarn_false(self):
        """Test is_yarn property when master is local."""
        config = HDFSConfig(master='local[*]')
        assert config.is_yarn is False

    def test_is_local_true(self):
        """Test is_local property for local mode."""
        config = HDFSConfig(master='local[4]')
        assert config.is_local is True

    def test_is_local_false(self):
        """Test is_local property for cluster mode."""
        config = HDFSConfig(master='spark://master:7077')
        assert config.is_local is False

    def test_log_info(self):
        """Test log_info method."""
        messages = []
        config = HDFSConfig(log_info_func=lambda m: messages.append(m))
        config.log_info("Test message")
        assert "Test message" in messages

    def test_log_error(self):
        """Test log_error method."""
        messages = []
        config = HDFSConfig(log_error_func=lambda m: messages.append(m))
        config.log_error("Error message")
        assert "Error message" in messages


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_hdfs_config(self):
        """Test basic factory function."""
        config = create_hdfs_config(app_name='TestApp')
        assert isinstance(config, HDFSConfig)
        assert config.app_name == 'TestApp'

    def test_create_local_config(self):
        """Test local development config."""
        # Clear env vars that override factory defaults
        with patch.dict(os.environ, {}, clear=False):
            for key in ['SPARK_EXECUTOR_MEMORY', 'SPARK_EXECUTOR_INSTANCES', 'SPARK_EXECUTOR_CORES']:
                os.environ.pop(key, None)

            config = create_local_config('/data/test')

            assert config.data_path == '/data/test'
            assert config.num_executors == 2
            assert config.executor_cores == 1
            assert config.executor_memory == '1g'
            assert config.enable_sedona is False

    def test_create_cluster_config(self):
        """Test cluster deployment config."""
        # Clear env vars that override factory defaults
        with patch.dict(os.environ, {}, clear=False):
            for key in ['SPARK_EXECUTOR_MEMORY', 'SPARK_EXECUTOR_INSTANCES', 'SPARK_EXECUTOR_CORES']:
                os.environ.pop(key, None)

            config = create_cluster_config('/data/test')

            assert config.data_path == '/data/test'
            assert config.num_executors == 8
            assert config.executor_cores == 4
            assert config.executor_memory == '4g'
            assert config.enable_sedona is True

    def test_create_geocoding_config(self):
        """Test geocoding workload config."""
        config = create_geocoding_config('/data/addresses')

        assert config.data_path == '/data/addresses'
        assert config.app_name == 'GeocodingPipeline'
        assert config.enable_sedona is True
        assert config.network_timeout == '1200s'

    def test_create_yarn_config(self):
        """Test YARN cluster config."""
        # Clear env vars that override factory defaults
        with patch.dict(os.environ, {}, clear=False):
            for key in ['SPARK_EXECUTOR_MEMORY', 'SPARK_EXECUTOR_INSTANCES',
                        'SPARK_EXECUTOR_CORES', 'SPARK_DRIVER_MEMORY', 'SPARK_MASTER']:
                os.environ.pop(key, None)

            config = create_yarn_config('/data/census')

            assert config.data_path == '/data/census'
            assert config.master == 'yarn'
            assert config.deploy_mode == 'client'
            assert config.num_executors == 10
            assert config.executor_cores == 4
            assert config.executor_memory == '8g'
            assert config.driver_memory == '4g'
            assert config.enable_sedona is True

    def test_create_yarn_config_with_queue(self):
        """Test YARN config with custom queue."""
        config = create_yarn_config('/data/test', yarn_queue='analytics')
        assert config.yarn_queue == 'analytics'

    def test_create_census_analysis_config(self):
        """Test Census analysis config."""
        config = create_census_analysis_config('/data/census/acs')

        assert config.data_path == '/data/census/acs'
        assert config.app_name == 'CensusLongitudinalAnalysis'
        assert config.enable_sedona is True
        assert config.sedona_global_index_type == 'rtree'
        assert config.sedona_join_broadcast_threshold == 50 * 1024 * 1024

    def test_factory_override(self):
        """Test that factory kwargs override defaults."""
        config = create_local_config(
            '/data/test',
            num_executors=4,
            enable_sedona=True
        )
        assert config.num_executors == 4
        assert config.enable_sedona is True


# =============================================================================
# SEDONA CONFIGURATION TESTS
# =============================================================================

class TestSedonaConfig:
    """Tests for Sedona configuration options."""

    def test_default_sedona_settings(self):
        """Test default Sedona configuration."""
        config = HDFSConfig()

        assert config.enable_sedona is True
        assert config.sedona_global_index_type == 'rtree'
        assert config.sedona_join_broadcast_threshold == 10 * 1024 * 1024

    def test_custom_sedona_index_type(self):
        """Test custom Sedona index type."""
        config = HDFSConfig(sedona_global_index_type='quadtree')
        assert config.sedona_global_index_type == 'quadtree'

    def test_custom_broadcast_threshold(self):
        """Test custom broadcast join threshold."""
        config = HDFSConfig(sedona_join_broadcast_threshold=100 * 1024 * 1024)
        assert config.sedona_join_broadcast_threshold == 100 * 1024 * 1024
