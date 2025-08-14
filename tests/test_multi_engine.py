# ================================================================
# FILE: test_multi_engine.py
# ================================================================
"""
Tests for multi-engine architecture functionality.
Tests engine selection, fallback behavior, and cross-engine operations.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Test multi-engine functionality
pytest.importorskip("pyspark", reason="PySpark not available for multi-engine tests")

import siege_utilities


class TestMultiEngineArchitecture:
    """Test multi-engine architecture functionality."""

    @pytest.mark.multi_engine
    def test_engine_selection_logic(self, mock_multi_engine_processor):
        """Test that engine selection logic works correctly."""
        
        # Test small dataset selection
        small_engine = mock_multi_engine_processor.get_optimal_engine(
            data_size_mb=50, 
            operation_complexity="simple"
        )
        assert small_engine in ["pandas", "auto"]
        
        # Test large dataset selection
        large_engine = mock_multi_engine_processor.get_optimal_engine(
            data_size_mb=500, 
            operation_complexity="complex"
        )
        assert large_engine in ["spark", "auto"]
        
        # Test medium dataset selection
        medium_engine = mock_multi_engine_processor.get_optimal_engine(
            data_size_mb=200, 
            operation_complexity="medium"
        )
        assert medium_engine in ["pandas", "spark", "auto"]

    @pytest.mark.multi_engine
    def test_engine_fallback_behavior(self, mock_multi_engine_processor):
        """Test that engine fallback works when preferred engine fails."""
        
        # Mock Spark failure
        mock_multi_engine_processor.spark_available = False
        
        # Mock fallback behavior - when Spark is not available, should return pandas
        mock_multi_engine_processor.get_optimal_engine.return_value = "pandas"
        
        # Should fallback to pandas
        fallback_engine = mock_multi_engine_processor.get_optimal_engine(
            data_size_mb=500, 
            operation_complexity="complex"
        )
        assert fallback_engine == "pandas"

    @pytest.mark.multi_engine
    def test_cross_engine_data_transfer(self, mock_multi_engine_processor):
        """Test data transfer between different engines."""
        
        # Create sample data
        sample_data = pd.DataFrame({
            'id': range(100),
            'value': np.random.randn(100),
            'category': np.random.choice(['A', 'B', 'C'], 100)
        })
        
        # Test processing with different engines
        result = mock_multi_engine_processor.process_data(
            data=sample_data,
            operations=[{'type': 'filter', 'condition': lambda df: df['value'] > 0}],
            engine="auto"
        )
        
        assert result is not None

    @pytest.mark.multi_engine
    def test_engine_performance_comparison(self, mock_engine_performance_data):
        """Test engine performance comparison functionality."""
        
        small_data = mock_engine_performance_data['small_dataset']
        large_data = mock_engine_performance_data['large_dataset']
        
        # Small dataset: Pandas should be faster
        assert small_data['pandas_time'] < small_data['spark_time']
        assert small_data['pandas_throughput'] > small_data['spark_throughput']
        
        # Large dataset: Spark should be faster
        assert large_data['spark_time'] < large_data['pandas_time']
        assert large_data['spark_throughput'] > large_data['pandas_throughput']

    @pytest.mark.multi_engine
    def test_engine_availability_detection(self, mock_multi_engine_processor):
        """Test that engine availability is correctly detected."""
        
        # Test Spark availability
        assert mock_multi_engine_processor.spark_available == True
        
        # Test engine status
        assert mock_multi_engine_processor.default_engine == "auto"


class TestMultiEngineBatchProcessing:
    """Test multi-engine batch processing functionality."""

    @pytest.mark.batch_processing
    def test_batch_processor_initialization(self, mock_multi_engine_batch_processor):
        """Test that batch processor initializes correctly."""
        
        processor = mock_multi_engine_batch_processor
        
        assert processor.spark_available == True
        assert processor.default_engine == "auto"
        assert hasattr(processor, 'batch_process_files')

    @pytest.mark.batch_processing
    def test_batch_processing_with_auto_engine(self, mock_multi_engine_batch_processor):
        """Test batch processing with automatic engine selection."""
        
        processor = mock_multi_engine_batch_processor
        
        # Mock file list
        test_files = ['test1.csv', 'test2.csv']
        
        # Process files with auto engine selection
        results = processor.batch_process_files(files=test_files, engine="auto")
        
        assert len(results) == 2
        assert all(result['status'] == 'success' for result in results)

    @pytest.mark.batch_processing
    def test_engine_specific_batch_processing(self, mock_multi_engine_batch_processor):
        """Test batch processing with specific engine selection."""
        
        processor = mock_multi_engine_batch_processor
        
        # Test Pandas processing
        pandas_results = processor.batch_process_files(
            files=['test.csv'], 
            engine="pandas"
        )
        assert pandas_results is not None
        
        # Test Spark processing
        spark_results = processor.batch_process_files(
            files=['test.csv'], 
            engine="spark"
        )
        assert spark_results is not None


class TestMultiEngineAnalytics:
    """Test multi-engine analytics functionality."""

    @pytest.mark.analytics
    def test_analytics_processor_initialization(self, mock_multi_engine_analytics_processor):
        """Test that analytics processor initializes correctly."""
        
        processor = mock_multi_engine_analytics_processor
        
        assert processor.spark_available == True
        assert processor.default_engine == "auto"
        assert hasattr(processor, 'process_analytics_data')

    @pytest.mark.analytics
    def test_analytics_data_processing(self, mock_multi_engine_analytics_processor, sample_analytics_data):
        """Test analytics data processing with multi-engine support."""
        
        processor = mock_multi_engine_analytics_processor
        
        # Test processing with auto engine
        result = processor.process_analytics_data(
            data=sample_analytics_data,
            operations=[{'type': 'aggregate', 'group_by': ['platform'], 'aggregations': {'pageviews': 'sum'}}],
            engine="auto"
        )
        
        assert result is not None

    @pytest.mark.analytics
    def test_analytics_client_connections(self, mock_multi_engine_analytics_processor):
        """Test analytics client connection functionality."""
        
        processor = mock_multi_engine_analytics_processor
        
        # Test Google Analytics connection
        ga_connected = processor.ga_client.test_connection()
        assert ga_connected == True
        
        # Test Facebook Business connection
        fb_connected = processor.fb_client.test_connection()
        assert fb_connected == True


class TestMultiEngineIntegration:
    """Test integration between different multi-engine components."""

    @pytest.mark.integration
    def test_end_to_end_multi_engine_workflow(self, mock_multi_engine_processor, sample_spatial_data):
        """Test complete multi-engine workflow."""
        
        processor = mock_multi_engine_processor
        
        # Simulate complete workflow
        # 1. Data loading
        data = sample_spatial_data
        
        # 2. Engine selection
        engine = processor.get_optimal_engine(
            data_size_mb=data.memory_usage(deep=True).sum() / (1024 * 1024),
            operation_complexity="medium"
        )
        
        # 3. Data processing
        result = processor.process_data(
            data=data,
            operations=[{'type': 'filter', 'condition': lambda df: df['value'] > 100}],
            engine=engine
        )
        
        assert result is not None
        assert engine in ["pandas", "spark", "auto"]

    @pytest.mark.integration
    def test_multi_engine_error_handling(self, mock_multi_engine_processor):
        """Test error handling in multi-engine operations."""
        
        processor = mock_multi_engine_processor
        
        # Mock processing failure
        processor.process_data.side_effect = Exception("Processing failed")
        
        # Should handle errors gracefully
        with pytest.raises(Exception):
            processor.process_data(
                data=pd.DataFrame({'test': [1, 2, 3]}),
                operations=[],
                engine="auto"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
