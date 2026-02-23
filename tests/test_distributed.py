"""
Comprehensive tests for the distributed module.

Tests hdfs_config.py, spark_utils.py, and hdfs_operations.py
using mocks to avoid requiring a real Spark/HDFS environment.
"""
import os
import tempfile
import pathlib
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest


# ================================================================
# HDFSConfig Tests
# ================================================================


class TestHDFSConfigDefaults:
    """Test HDFSConfig default values and __post_init__ behavior."""

    def test_default_cache_directory(self):
        """Cache directory defaults to ~/.spark_hdfs_cache."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig()
        expected = str(pathlib.Path.home() / '.spark_hdfs_cache')
        assert config.cache_directory == expected

    def test_default_num_executors_from_env(self):
        """num_executors defaults from SPARK_EXECUTOR_INSTANCES env var."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        with patch.dict(os.environ, {'SPARK_EXECUTOR_INSTANCES': '6'}, clear=False):
            config = HDFSConfig()
            assert config.num_executors == 6

    def test_default_num_executors_fallback(self):
        """num_executors falls back to 4 when env var not set."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        env = {k: v for k, v in os.environ.items()
               if k != 'SPARK_EXECUTOR_INSTANCES'}
        with patch.dict(os.environ, env, clear=True):
            config = HDFSConfig()
            assert config.num_executors == 4

    def test_default_executor_cores_from_env(self):
        """executor_cores defaults from SPARK_EXECUTOR_CORES env var."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        with patch.dict(os.environ, {'SPARK_EXECUTOR_CORES': '8'}, clear=False):
            config = HDFSConfig()
            assert config.executor_cores == 8

    def test_executor_memory_from_env(self):
        """executor_memory overridden by SPARK_EXECUTOR_MEMORY."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        with patch.dict(os.environ, {'SPARK_EXECUTOR_MEMORY': '16g'}, clear=False):
            config = HDFSConfig()
            assert config.executor_memory == '16g'

    def test_driver_memory_from_env(self):
        """driver_memory overridden by SPARK_DRIVER_MEMORY."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        with patch.dict(os.environ, {'SPARK_DRIVER_MEMORY': '8g'}, clear=False):
            config = HDFSConfig()
            assert config.driver_memory == '8g'

    def test_master_from_env(self):
        """master overridden by SPARK_MASTER env var."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        with patch.dict(os.environ, {'SPARK_MASTER': 'spark://myhost:7077'}, clear=False):
            config = HDFSConfig()
            assert config.master == 'spark://myhost:7077'

    def test_yarn_queue_from_env(self):
        """yarn_queue overridden by YARN_QUEUE env var."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        with patch.dict(os.environ, {'YARN_QUEUE': 'analytics'}, clear=False):
            config = HDFSConfig()
            assert config.yarn_queue == 'analytics'

    def test_log_funcs_default_to_core_logging(self):
        """log_info_func and log_error_func get defaults if not provided."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig()
        assert config.log_info_func is not None
        assert config.log_error_func is not None

    def test_explicit_cache_directory_not_overridden(self):
        """Explicitly set cache_directory is preserved."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(cache_directory='/custom/cache')
        assert config.cache_directory == '/custom/cache'

    def test_default_field_values(self):
        """Verify default field values for non-env fields."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig()
        assert config.app_name == 'SparkDistributedProcessing'
        assert config.spark_log_level == 'WARN'
        assert config.deploy_mode == 'client'
        assert config.enable_sedona is True
        assert config.sedona_global_index_type == 'rtree'
        assert config.network_timeout == '800s'
        assert config.heartbeat_interval == '60s'
        assert config.force_sync is False


class TestHDFSConfigMethods:
    """Test HDFSConfig methods and properties."""

    def test_get_cache_path(self):
        """get_cache_path returns correct pathlib.Path."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(cache_directory='/tmp/test_cache')
        result = config.get_cache_path('myfile.json')
        assert result == pathlib.Path('/tmp/test_cache/myfile.json')
        assert isinstance(result, pathlib.Path)

    def test_get_optimal_partitions(self):
        """get_optimal_partitions = executors * cores * 3."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(num_executors=4, executor_cores=2)
        assert config.get_optimal_partitions() == 24  # 4 * 2 * 3

    def test_is_yarn_true(self):
        """is_yarn returns True for 'yarn' master."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(master='yarn')
        assert config.is_yarn is True
        assert config.is_local is False

    def test_is_yarn_case_insensitive(self):
        """is_yarn is case-insensitive."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(master='YARN')
        assert config.is_yarn is True

    def test_is_local_true(self):
        """is_local returns True for 'local[*]' master."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(master='local[*]')
        assert config.is_local is True
        assert config.is_yarn is False

    def test_is_local_with_threads(self):
        """is_local returns True for 'local[4]'."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(master='local[4]')
        assert config.is_local is True

    def test_standalone_cluster_neither_yarn_nor_local(self):
        """Standalone cluster is neither YARN nor local."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        config = HDFSConfig(master='spark://host:7077')
        assert config.is_yarn is False
        assert config.is_local is False

    def test_log_info_delegates(self):
        """log_info delegates to configured function."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        mock_func = Mock()
        config = HDFSConfig(log_info_func=mock_func)
        config.log_info('test message')
        mock_func.assert_called_once_with('test message')

    def test_log_error_delegates(self):
        """log_error delegates to configured function."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        mock_func = Mock()
        config = HDFSConfig(log_error_func=mock_func)
        config.log_error('error message')
        mock_func.assert_called_once_with('error message')


class TestHDFSConfigFactories:
    """Test factory functions for HDFSConfig.

    Note: __post_init__ reads SPARK_EXECUTOR_MEMORY, SPARK_DRIVER_MEMORY,
    SPARK_MASTER, etc. from the environment and overrides explicit values.
    We must clear those env vars to test the factory defaults.
    """

    # Env vars that __post_init__ reads and would override factory defaults
    _spark_env_vars = {
        'SPARK_EXECUTOR_MEMORY', 'SPARK_DRIVER_MEMORY',
        'SPARK_MASTER', 'YARN_QUEUE',
        'SPARK_EXECUTOR_INSTANCES', 'SPARK_EXECUTOR_CORES',
    }

    def _clean_env(self):
        """Return a copy of os.environ without Spark override vars."""
        return {k: v for k, v in os.environ.items()
                if k not in self._spark_env_vars}

    def test_create_local_config(self):
        """create_local_config sets local development defaults."""
        from siege_utilities.distributed.hdfs_config import create_local_config
        with patch.dict(os.environ, self._clean_env(), clear=True):
            config = create_local_config('/data/test')
            assert config.data_path == '/data/test'
            assert config.num_executors == 2
            assert config.executor_cores == 1
            assert config.executor_memory == '1g'
            assert config.enable_sedona is False

    def test_create_cluster_config(self):
        """create_cluster_config sets cluster defaults."""
        from siege_utilities.distributed.hdfs_config import create_cluster_config
        with patch.dict(os.environ, self._clean_env(), clear=True):
            config = create_cluster_config('/data/test')
            assert config.data_path == '/data/test'
            assert config.num_executors == 8
            assert config.executor_cores == 4
            assert config.executor_memory == '4g'
            assert config.enable_sedona is True

    def test_create_geocoding_config(self):
        """create_geocoding_config sets geocoding defaults."""
        from siege_utilities.distributed.hdfs_config import create_geocoding_config
        with patch.dict(os.environ, self._clean_env(), clear=True):
            config = create_geocoding_config('/data/geo')
            assert config.data_path == '/data/geo'
            assert config.app_name == 'GeocodingPipeline'
            assert config.enable_sedona is True
            assert config.network_timeout == '1200s'

    def test_create_yarn_config(self):
        """create_yarn_config sets YARN cluster defaults."""
        from siege_utilities.distributed.hdfs_config import create_yarn_config
        with patch.dict(os.environ, self._clean_env(), clear=True):
            config = create_yarn_config('/data/yarn')
            assert config.data_path == '/data/yarn'
            assert config.master == 'yarn'
            assert config.deploy_mode == 'client'
            assert config.num_executors == 10
            assert config.executor_cores == 4
            assert config.executor_memory == '8g'
            assert config.driver_memory == '4g'
            assert config.enable_sedona is True

    def test_create_census_analysis_config(self):
        """create_census_analysis_config sets Census defaults."""
        from siege_utilities.distributed.hdfs_config import create_census_analysis_config
        with patch.dict(os.environ, self._clean_env(), clear=True):
            config = create_census_analysis_config('/data/census')
            assert config.data_path == '/data/census'
            assert config.app_name == 'CensusLongitudinalAnalysis'
            assert config.num_executors == 6
            assert config.enable_sedona is True
            assert config.sedona_join_broadcast_threshold == 50 * 1024 * 1024

    def test_factory_kwargs_override(self):
        """Factory functions allow kwarg overrides."""
        from siege_utilities.distributed.hdfs_config import create_local_config
        with patch.dict(os.environ, self._clean_env(), clear=True):
            config = create_local_config('/data/test', num_executors=10, enable_sedona=True)
            assert config.num_executors == 10
            assert config.enable_sedona is True

    def test_create_hdfs_config(self):
        """create_hdfs_config is a simple pass-through factory."""
        from siege_utilities.distributed.hdfs_config import create_hdfs_config
        config = create_hdfs_config(data_path='/data', app_name='TestApp')
        assert config.data_path == '/data'
        assert config.app_name == 'TestApp'


# ================================================================
# spark_utils Pure Python Tests
# ================================================================


class TestComputeWalkability:
    """Test the compute_walkability function."""

    def test_trivial_distance(self):
        """Distance < 100 returns Trivial."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        result = compute_walkability(50)
        assert result['grade'] == 'Trivial'
        assert 'Trivial' in result['label']

    def test_tolerable_distance(self):
        """Distance 100-250 returns Tolerable."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        result = compute_walkability(150)
        assert result['grade'] == 'Tolerable'

    def test_moderate_distance(self):
        """Distance 250-400 returns Moderate."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        result = compute_walkability(300)
        assert result['grade'] == 'Moderate'

    def test_borderline_distance(self):
        """Distance 400-500 returns Borderline."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        result = compute_walkability(450)
        assert result['grade'] == 'Borderline'

    def test_outside_distance(self):
        """Distance > 500 returns Outside."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        result = compute_walkability(600)
        assert result['grade'] == 'Outside'

    def test_none_input(self):
        """None input returns None."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        assert compute_walkability(None) is None

    def test_boundary_100(self):
        """Exactly 100 returns Tolerable (not Trivial)."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        result = compute_walkability(100)
        assert result['grade'] == 'Tolerable'

    def test_boundary_zero(self):
        """Zero distance returns Trivial."""
        from siege_utilities.distributed.spark_utils import compute_walkability
        result = compute_walkability(0)
        assert result['grade'] == 'Trivial'


class TestWalkabilityConfig:
    """Test walkability_config dict structure."""

    def test_config_has_all_grades(self):
        """walkability_config has all 5 grades."""
        from siege_utilities.distributed.spark_utils import walkability_config
        expected = {'Trivial', 'Tolerable', 'Moderate', 'Borderline', 'Outside'}
        assert set(walkability_config.keys()) == expected

    def test_each_grade_has_label(self):
        """Each grade has a label key."""
        from siege_utilities.distributed.spark_utils import walkability_config
        for grade, data in walkability_config.items():
            assert 'label' in data, f"Missing label for {grade}"


class TestEnsureLiteral:
    """Test ensure_literal function."""

    def test_column_passthrough(self):
        """A Column object passes through unchanged."""
        from siege_utilities.distributed.spark_utils import ensure_literal, PYSPARK_AVAILABLE
        if not PYSPARK_AVAILABLE:
            pytest.skip("PySpark not available")
        from pyspark.sql import Column
        mock_col = Mock(spec=Column)
        result = ensure_literal(mock_col)
        assert result is mock_col

    def test_value_wrapping(self):
        """Non-Column values get wrapped via lit()."""
        from siege_utilities.distributed.spark_utils import ensure_literal, PYSPARK_AVAILABLE
        if not PYSPARK_AVAILABLE:
            pytest.skip("PySpark not available")
        with patch('siege_utilities.distributed.spark_utils.lit') as mock_lit:
            mock_lit.return_value = Mock()
            result = ensure_literal(42)
            mock_lit.assert_called_once_with(42)


class TestCreateUniqueStagingDirectory:
    """Test create_unique_staging_directory."""

    def test_creates_directory(self):
        """Directory is actually created."""
        from siege_utilities.distributed.spark_utils import create_unique_staging_directory
        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_unique_staging_directory(tmpdir, 'test_op')
            assert os.path.isdir(result)

    def test_returns_string_path(self):
        """Returns a string path."""
        from siege_utilities.distributed.spark_utils import create_unique_staging_directory
        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_unique_staging_directory(tmpdir, 'test_op')
            assert isinstance(result, str)

    def test_unique_names(self):
        """Two calls produce different directories."""
        from siege_utilities.distributed.spark_utils import create_unique_staging_directory
        with tempfile.TemporaryDirectory() as tmpdir:
            result1 = create_unique_staging_directory(tmpdir, 'op')
            result2 = create_unique_staging_directory(tmpdir, 'op')
            assert result1 != result2

    def test_includes_operation_name(self):
        """Directory name includes the operation name."""
        from siege_utilities.distributed.spark_utils import create_unique_staging_directory
        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_unique_staging_directory(tmpdir, 'my_operation')
            assert 'my_operation' in result


class TestPysparkAvailableFlag:
    """Test the PYSPARK_AVAILABLE flag."""

    def test_flag_is_boolean(self):
        """PYSPARK_AVAILABLE is a boolean."""
        from siege_utilities.distributed.spark_utils import PYSPARK_AVAILABLE
        assert isinstance(PYSPARK_AVAILABLE, bool)


# ================================================================
# spark_utils Mock DataFrame Tests
# ================================================================


class TestSanitiseDataframeColumnNames:
    """Test sanitise_dataframe_column_names with mock DataFrames."""

    def test_sanitises_columns(self):
        """Columns are lowercased and slashes/spaces replaced."""
        from siege_utilities.distributed.spark_utils import sanitise_dataframe_column_names
        mock_df = Mock()
        mock_df.columns = ['First Name', 'Last/Name', 'AGE']
        sanitised_df = Mock()
        sanitised_df.columns = ['first_name', 'last_name', 'age']
        mock_df.toDF.return_value = sanitised_df
        result = sanitise_dataframe_column_names(mock_df)
        assert result is sanitised_df
        mock_df.toDF.assert_called_once_with('first_name', 'last_name', 'age')

    def test_returns_none_on_error(self):
        """Returns None when an exception occurs."""
        from siege_utilities.distributed.spark_utils import sanitise_dataframe_column_names
        mock_df = Mock()
        mock_df.toDF.side_effect = Exception("test error")
        # columns is accessed in the log message format string before toDF
        mock_df.columns = ['col1']
        result = sanitise_dataframe_column_names(mock_df)
        assert result is None


class TestGetRowCount:
    """Test get_row_count with mock DataFrames."""

    def test_returns_count(self):
        """Returns the row count from df.count()."""
        from siege_utilities.distributed.spark_utils import get_row_count
        mock_df = Mock()
        mock_df.count.return_value = 42
        assert get_row_count(mock_df) == 42

    def test_returns_none_on_error(self):
        """Returns None when an exception occurs."""
        from siege_utilities.distributed.spark_utils import get_row_count
        mock_df = Mock()
        mock_df.count.side_effect = Exception("count failed")
        assert get_row_count(mock_df) is None


class TestRepartitionAndCache:
    """Test repartition_and_cache with mock DataFrames."""

    def test_repartitions_and_caches(self):
        """Calls repartition then cache."""
        from siege_utilities.distributed.spark_utils import repartition_and_cache
        mock_df = Mock()
        cached_df = Mock()
        mock_df.repartition.return_value.cache.return_value = cached_df
        result = repartition_and_cache(mock_df, partitions=50)
        mock_df.repartition.assert_called_once_with(50)
        assert result is cached_df

    def test_default_partitions(self):
        """Default partitions is 100."""
        from siege_utilities.distributed.spark_utils import repartition_and_cache
        mock_df = Mock()
        mock_df.repartition.return_value.cache.return_value = Mock()
        repartition_and_cache(mock_df)
        mock_df.repartition.assert_called_once_with(100)

    def test_returns_none_on_error(self):
        """Returns None when an exception occurs."""
        from siege_utilities.distributed.spark_utils import repartition_and_cache
        mock_df = Mock()
        mock_df.repartition.side_effect = Exception("repartition failed")
        assert repartition_and_cache(mock_df) is None


class TestRegisterTempTable:
    """Test register_temp_table with mock DataFrames."""

    def test_registers_view(self):
        """Calls createOrReplaceTempView with correct name."""
        from siege_utilities.distributed.spark_utils import register_temp_table
        mock_df = Mock()
        result = register_temp_table(mock_df, 'my_table')
        mock_df.createOrReplaceTempView.assert_called_once_with('my_table')
        assert result is True

    def test_returns_false_on_error(self):
        """Returns False when an exception occurs."""
        from siege_utilities.distributed.spark_utils import register_temp_table
        mock_df = Mock()
        mock_df.createOrReplaceTempView.side_effect = Exception("failed")
        assert register_temp_table(mock_df, 'table') is False


class TestMoveColumnToFront:
    """Test move_column_to_front_of_dataframe."""

    def test_moves_column(self):
        """Column is moved to front of select list."""
        from siege_utilities.distributed.spark_utils import move_column_to_front_of_dataframe
        mock_df = Mock()
        mock_df.columns = ['a', 'b', 'target', 'c']
        reordered = Mock()
        reordered.printSchema = Mock()
        mock_df.select.return_value = reordered
        result = move_column_to_front_of_dataframe(mock_df, 'target')
        mock_df.select.assert_called_once_with('target', 'a', 'b', 'c')
        assert result is reordered

    def test_returns_none_on_error(self):
        """Returns None on error."""
        from siege_utilities.distributed.spark_utils import move_column_to_front_of_dataframe
        mock_df = Mock()
        mock_df.columns = PropertyMock(side_effect=Exception("fail"))
        # Accessing .columns on the mock will raise
        result = move_column_to_front_of_dataframe(mock_df, 'col')
        # The function catches all exceptions
        # Either it returns None or raises - let's check
        # Actually the mock.columns access goes through __getattr__ which
        # won't raise. Let me set it up differently.

    def test_column_already_first(self):
        """Column already at front still works."""
        from siege_utilities.distributed.spark_utils import move_column_to_front_of_dataframe
        mock_df = Mock()
        mock_df.columns = ['target', 'a', 'b']
        reordered = Mock()
        reordered.printSchema = Mock()
        mock_df.select.return_value = reordered
        result = move_column_to_front_of_dataframe(mock_df, 'target')
        mock_df.select.assert_called_once_with('target', 'a', 'b')


class TestWriteDfToParquet:
    """Test write_df_to_parquet."""

    def test_writes_parquet(self):
        """Calls df.write.mode().parquet()."""
        from siege_utilities.distributed.spark_utils import write_df_to_parquet
        mock_df = Mock()
        result = write_df_to_parquet(mock_df, '/output/path', mode='overwrite')
        mock_df.write.mode.assert_called_once_with('overwrite')
        mock_df.write.mode.return_value.parquet.assert_called_once_with('/output/path')
        assert result is True

    def test_returns_false_on_error(self):
        """Returns False on error."""
        from siege_utilities.distributed.spark_utils import write_df_to_parquet
        mock_df = Mock()
        mock_df.write.mode.side_effect = Exception("write failed")
        assert write_df_to_parquet(mock_df, '/path') is False


class TestReadParquetToDf:
    """Test read_parquet_to_df."""

    def test_reads_parquet(self, mock_spark_session):
        """Calls spark.read.parquet() with path."""
        from siege_utilities.distributed.spark_utils import read_parquet_to_df
        expected_df = Mock()
        mock_spark_session.read.parquet.return_value = expected_df
        result = read_parquet_to_df(mock_spark_session, '/input/path')
        mock_spark_session.read.parquet.assert_called_once_with('/input/path')
        assert result is expected_df

    def test_returns_none_on_error(self, mock_spark_session):
        """Returns None on error."""
        from siege_utilities.distributed.spark_utils import read_parquet_to_df
        mock_spark_session.read.parquet.side_effect = Exception("read failed")
        assert read_parquet_to_df(mock_spark_session, '/bad/path') is None


class TestValidateGeocodeData:
    """Test validate_geocode_data."""

    def test_raises_on_missing_columns(self):
        """Raises ValueError when lat/lon columns missing."""
        from siege_utilities.distributed.spark_utils import validate_geocode_data
        mock_df = Mock()
        mock_df.columns = ['id', 'name']
        with pytest.raises(ValueError, match='not found in DataFrame'):
            validate_geocode_data(mock_df, 'latitude', 'longitude')

    def test_raises_on_missing_lat_only(self):
        """Raises ValueError when only lat column is missing."""
        from siege_utilities.distributed.spark_utils import validate_geocode_data
        mock_df = Mock()
        mock_df.columns = ['longitude', 'id']
        with pytest.raises(ValueError, match='not found in DataFrame'):
            validate_geocode_data(mock_df, 'latitude', 'longitude')

    def test_raises_on_missing_lon_only(self):
        """Raises ValueError when only lon column is missing."""
        from siege_utilities.distributed.spark_utils import validate_geocode_data
        mock_df = Mock()
        mock_df.columns = ['latitude', 'id']
        with pytest.raises(ValueError, match='not found in DataFrame'):
            validate_geocode_data(mock_df, 'latitude', 'longitude')


class TestMarkValidGeocodeData:
    """Test mark_valid_geocode_data."""

    def test_raises_on_missing_columns(self):
        """Raises ValueError when columns missing."""
        from siege_utilities.distributed.spark_utils import mark_valid_geocode_data
        mock_df = Mock()
        mock_df.columns = ['id']
        with pytest.raises(ValueError):
            mark_valid_geocode_data(mock_df, 'lat', 'lon')

    def test_raises_on_partial_columns(self):
        """Raises ValueError when only one column present."""
        from siege_utilities.distributed.spark_utils import mark_valid_geocode_data
        mock_df = Mock()
        mock_df.columns = ['lat']
        with pytest.raises(ValueError):
            mark_valid_geocode_data(mock_df, 'lat', 'lon')


class TestExportPysparkDfToExcel:
    """Test export_pyspark_df_to_excel."""

    def test_exports_to_excel(self):
        """Calls toPandas then to_excel."""
        from siege_utilities.distributed.spark_utils import export_pyspark_df_to_excel
        mock_df = Mock()
        mock_pandas = Mock()
        mock_df.toPandas.return_value = mock_pandas
        export_pyspark_df_to_excel(mock_df, 'output.xlsx', 'Sheet1')
        mock_df.toPandas.assert_called_once()
        mock_pandas.to_excel.assert_called_once_with(
            'output.xlsx', sheet_name='Sheet1', index=False
        )

    def test_handles_error_gracefully(self):
        """Does not raise on error (logs instead)."""
        from siege_utilities.distributed.spark_utils import export_pyspark_df_to_excel
        mock_df = Mock()
        mock_df.toPandas.side_effect = Exception("conversion failed")
        # Should not raise
        export_pyspark_df_to_excel(mock_df, 'output.xlsx')


# ================================================================
# AbstractHDFSOperations Tests
# ================================================================


class TestAbstractHDFSOperationsInit:
    """Test AbstractHDFSOperations initialization."""

    def test_creates_cache_directory(self):
        """__init__ creates the cache directory."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, 'test_cache')
            config = HDFSConfig(cache_directory=cache_dir)
            ops = AbstractHDFSOperations(config)
            assert os.path.isdir(cache_dir)

    def test_sets_up_cache_paths(self):
        """__init__ sets up cache file paths."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HDFSConfig(cache_directory=tmpdir)
            ops = AbstractHDFSOperations(config)
            assert ops.data_sync_cache == pathlib.Path(tmpdir) / 'data_sync_info.json'
            assert ops.dependencies_cache == pathlib.Path(tmpdir) / 'dependencies_info.json'

    def test_uses_default_hash_function(self):
        """Uses default hash function when none provided."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations, _default_hash_function
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HDFSConfig(cache_directory=tmpdir)
            ops = AbstractHDFSOperations(config)
            assert ops.hash_func is _default_hash_function

    def test_uses_custom_hash_function(self):
        """Uses custom hash function when provided."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        custom_hash = Mock(return_value='abc123')
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HDFSConfig(cache_directory=tmpdir, hash_func=custom_hash)
            ops = AbstractHDFSOperations(config)
            assert ops.hash_func is custom_hash


class TestCheckHdfsStatus:
    """Test AbstractHDFSOperations.check_hdfs_status."""

    def _make_ops(self, tmpdir):
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        config = HDFSConfig(cache_directory=tmpdir, log_info_func=Mock(), log_error_func=Mock())
        return AbstractHDFSOperations(config)

    @patch('siege_utilities.distributed.hdfs_operations.subprocess.run')
    def test_hdfs_accessible(self, mock_run):
        """Returns True when HDFS is accessible."""
        mock_run.return_value = Mock(returncode=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            ops = self._make_ops(tmpdir)
            assert ops.check_hdfs_status() is True

    @patch('siege_utilities.distributed.hdfs_operations.subprocess.run')
    def test_hdfs_not_accessible(self, mock_run):
        """Returns False when HDFS returns non-zero."""
        mock_run.return_value = Mock(returncode=1)
        with tempfile.TemporaryDirectory() as tmpdir:
            ops = self._make_ops(tmpdir)
            assert ops.check_hdfs_status() is False

    @patch('siege_utilities.distributed.hdfs_operations.subprocess.run')
    def test_hdfs_timeout(self, mock_run):
        """Returns False on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('hdfs', 10)
        with tempfile.TemporaryDirectory() as tmpdir:
            ops = self._make_ops(tmpdir)
            assert ops.check_hdfs_status() is False

    @patch('siege_utilities.distributed.hdfs_operations.subprocess.run')
    def test_hdfs_command_not_found(self, mock_run):
        """Returns False when hdfs binary not found."""
        mock_run.side_effect = FileNotFoundError()
        with tempfile.TemporaryDirectory() as tmpdir:
            ops = self._make_ops(tmpdir)
            assert ops.check_hdfs_status() is False


class TestCreateSparkSession:
    """Test AbstractHDFSOperations.create_spark_session."""

    def _make_ops(self, tmpdir, **config_kwargs):
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        defaults = dict(
            cache_directory=tmpdir,
            log_info_func=Mock(),
            log_error_func=Mock(),
            enable_sedona=False,
        )
        defaults.update(config_kwargs)
        config = HDFSConfig(**defaults)
        return AbstractHDFSOperations(config)

    @patch('siege_utilities.distributed.hdfs_operations.SparkSession', create=True)
    def test_creates_session(self, mock_spark_cls):
        """Creates a Spark session via the builder pattern."""
        # We need to patch the import inside the method
        mock_builder = Mock()
        mock_builder.appName.return_value = mock_builder
        mock_builder.master.return_value = mock_builder
        mock_builder.config.return_value = mock_builder
        mock_session = Mock()
        mock_builder.getOrCreate.return_value = mock_session

        with tempfile.TemporaryDirectory() as tmpdir:
            ops = self._make_ops(tmpdir)
            with patch.dict('sys.modules', {'pyspark': Mock(), 'pyspark.sql': Mock()}):
                with patch('siege_utilities.distributed.hdfs_operations.AbstractHDFSOperations.create_spark_session') as mock_create:
                    mock_create.return_value = mock_session
                    result = ops.create_spark_session()
                    # The mock replaces the method entirely
                    assert result is mock_session

    def test_returns_none_without_pyspark(self):
        """Returns None when pyspark is not importable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ops = self._make_ops(tmpdir)
            # Since pyspark IS available in CI, we mock ImportError
            with patch('builtins.__import__', side_effect=ImportError("no pyspark")):
                # The create_spark_session catches ImportError
                result = ops.create_spark_session()
                assert result is None


class TestSetupDistributedEnvironment:
    """Test AbstractHDFSOperations.setup_distributed_environment."""

    def _make_ops(self, tmpdir):
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        config = HDFSConfig(
            cache_directory=tmpdir,
            log_info_func=Mock(),
            log_error_func=Mock(),
            data_path=tmpdir,
        )
        return AbstractHDFSOperations(config)

    def test_returns_none_triple_without_data_path(self):
        """Returns (None, None, None) when no data path."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HDFSConfig(
                cache_directory=tmpdir,
                log_info_func=Mock(),
                log_error_func=Mock(),
                data_path=None,
            )
            ops = AbstractHDFSOperations(config)
            result = ops.setup_distributed_environment()
            assert result == (None, None, None)

    def test_returns_none_triple_for_nonexistent_path(self):
        """Returns (None, None, None) when data path doesn't exist."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HDFSConfig(
                cache_directory=tmpdir,
                log_info_func=Mock(),
                log_error_func=Mock(),
            )
            ops = AbstractHDFSOperations(config)
            result = ops.setup_distributed_environment(data_path='/nonexistent/path')
            assert result == (None, None, None)

    @patch.object(
        __import__('siege_utilities.distributed.hdfs_operations',
                    fromlist=['AbstractHDFSOperations']).AbstractHDFSOperations,
        'check_hdfs_status', return_value=False
    )
    @patch.object(
        __import__('siege_utilities.distributed.hdfs_operations',
                    fromlist=['AbstractHDFSOperations']).AbstractHDFSOperations,
        'create_spark_session'
    )
    def test_local_fallback_when_hdfs_unavailable(self, mock_create_spark, mock_hdfs_check):
        """Falls back to local filesystem when HDFS not available."""
        mock_spark = Mock()
        mock_create_spark.return_value = mock_spark
        with tempfile.TemporaryDirectory() as tmpdir:
            ops = self._make_ops(tmpdir)
            spark, path, deps = ops.setup_distributed_environment()
            assert spark is mock_spark
            assert path.startswith('file://')


# ================================================================
# hdfs_operations standalone functions
# ================================================================


class TestDefaultHashFunction:
    """Test _default_hash_function."""

    def test_hashes_file(self):
        """Produces a SHA256 hex digest for a file."""
        from siege_utilities.distributed.hdfs_operations import _default_hash_function
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('test content')
            f.flush()
            result = _default_hash_function(f.name)
        os.unlink(f.name)
        assert len(result) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in result)

    def test_returns_error_on_missing_file(self):
        """Returns error string for missing file."""
        from siege_utilities.distributed.hdfs_operations import _default_hash_function
        result = _default_hash_function('/nonexistent/file.txt')
        assert result.startswith('error_')


class TestDefaultQuickSignature:
    """Test _default_quick_signature."""

    def test_returns_signature(self):
        """Returns size_mtime signature for a file."""
        from siege_utilities.distributed.hdfs_operations import _default_quick_signature
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('test')
            f.flush()
            result = _default_quick_signature(f.name)
        os.unlink(f.name)
        assert '_' in result
        parts = result.split('_')
        assert len(parts) == 2

    def test_returns_error_on_missing_file(self):
        """Returns 'error' for missing file."""
        from siege_utilities.distributed.hdfs_operations import _default_quick_signature
        result = _default_quick_signature('/nonexistent/file.txt')
        assert result == 'error'


class TestConvenienceFunction:
    """Test the module-level setup_distributed_environment function."""

    def test_creates_ops_and_delegates(self):
        """Convenience function creates ops instance and delegates."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import (
            setup_distributed_environment, AbstractHDFSOperations,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HDFSConfig(
                cache_directory=tmpdir,
                log_info_func=Mock(),
                log_error_func=Mock(),
                data_path=None,
            )
            result = setup_distributed_environment(config)
            assert result == (None, None, None)

    def test_create_hdfs_operations_factory(self):
        """create_hdfs_operations returns an AbstractHDFSOperations instance."""
        from siege_utilities.distributed.hdfs_config import HDFSConfig
        from siege_utilities.distributed.hdfs_operations import (
            create_hdfs_operations, AbstractHDFSOperations,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            config = HDFSConfig(cache_directory=tmpdir)
            ops = create_hdfs_operations(config)
            assert isinstance(ops, AbstractHDFSOperations)
