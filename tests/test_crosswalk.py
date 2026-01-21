"""
Unit tests for Census boundary crosswalk module.

Tests the crosswalk client, processor, and relationship types with mocked responses.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from siege_utilities.geo.crosswalk import (
    # Enums
    RelationshipType,
    WeightMethod,
    # Data classes
    CrosswalkRelationship,
    CrosswalkMetadata,
    GeographyChange,
    # Client
    CrosswalkClient,
    get_crosswalk,
    get_crosswalk_client,
    get_crosswalk_metadata,
    list_available_crosswalks,
    # Processor
    CrosswalkProcessor,
    apply_crosswalk,
    normalize_to_year,
    identify_boundary_changes,
    get_split_tracts,
    get_merged_tracts,
    # Constants
    SUPPORTED_CROSSWALK_YEARS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def crosswalk_client(temp_cache_dir):
    """Create a CrosswalkClient with a temporary cache directory."""
    return CrosswalkClient(cache_dir=temp_cache_dir)


@pytest.fixture
def mock_crosswalk_df():
    """Create a mock crosswalk DataFrame for testing."""
    return pd.DataFrame({
        'source_geoid': ['06037010100', '06037010200', '06037010300', '06037010300'],
        'target_geoid': ['06037010100', '06037010201', '06037010301', '06037010302'],
        'area_weight': [1.0, 1.0, 0.6, 0.4],
        'source_area': [1000000, 800000, 1200000, 1200000],
        'target_area': [1000000, 800000, 720000, 480000],
        'overlap_area': [1000000, 800000, 720000, 480000],
    })


@pytest.fixture
def mock_crosswalk_response():
    """Create a mock pipe-delimited crosswalk file content."""
    return """GEOID_TRACT_20|GEOID_TRACT_10|NAMELSAD_TRACT_20|NAMELSAD_TRACT_10|AREALAND_TRACT_20|AREALAND_TRACT_10|AREALAND_PART
06037010100|06037010100|Census Tract 101|Census Tract 101|1000000|1000000|1000000
06037010201|06037010200|Census Tract 102.01|Census Tract 102|800000|800000|800000
06037010301|06037010300|Census Tract 103.01|Census Tract 103|720000|1200000|720000
06037010302|06037010300|Census Tract 103.02|Census Tract 103|480000|1200000|480000"""


@pytest.fixture
def mock_source_data():
    """Create mock source year data for transformation."""
    return pd.DataFrame({
        'GEOID': ['06037010100', '06037010200', '06037010300'],
        'population': [5000, 3000, 4000],
        'median_income': [50000, 60000, 45000],
    })


# =============================================================================
# RELATIONSHIP TYPES TESTS
# =============================================================================

class TestRelationshipTypes:
    """Tests for relationship type enums and data classes."""

    def test_relationship_type_values(self):
        """Test RelationshipType enum values."""
        assert RelationshipType.ONE_TO_ONE.value == "one_to_one"
        assert RelationshipType.SPLIT.value == "split"
        assert RelationshipType.MERGED.value == "merged"
        assert RelationshipType.PARTIAL_OVERLAP.value == "partial_overlap"

    def test_weight_method_values(self):
        """Test WeightMethod enum values."""
        assert WeightMethod.AREA.value == "area"
        assert WeightMethod.POPULATION.value == "population"
        assert WeightMethod.HOUSING.value == "housing"
        assert WeightMethod.EQUAL.value == "equal"


class TestCrosswalkRelationship:
    """Tests for CrosswalkRelationship data class."""

    def test_create_relationship(self):
        """Test creating a crosswalk relationship."""
        rel = CrosswalkRelationship(
            source_geoid='06037010100',
            target_geoid='06037010100',
            relationship_type=RelationshipType.ONE_TO_ONE,
            area_weight=1.0
        )
        assert rel.source_geoid == '06037010100'
        assert rel.target_geoid == '06037010100'
        assert rel.area_weight == 1.0

    def test_get_weight_area(self):
        """Test getting area weight."""
        rel = CrosswalkRelationship(
            source_geoid='06037010100',
            target_geoid='06037010101',
            area_weight=0.6
        )
        assert rel.get_weight(WeightMethod.AREA) == 0.6

    def test_get_weight_population(self):
        """Test getting population weight."""
        rel = CrosswalkRelationship(
            source_geoid='06037010100',
            target_geoid='06037010101',
            area_weight=0.6,
            population_weight=0.7
        )
        assert rel.get_weight(WeightMethod.POPULATION) == 0.7

    def test_get_weight_population_missing(self):
        """Test error when population weight is missing."""
        rel = CrosswalkRelationship(
            source_geoid='06037010100',
            target_geoid='06037010101',
            area_weight=0.6
        )
        with pytest.raises(ValueError, match="Population weight not available"):
            rel.get_weight(WeightMethod.POPULATION)

    def test_get_weight_equal(self):
        """Test equal weighting."""
        rel = CrosswalkRelationship(
            source_geoid='06037010100',
            target_geoid='06037010101',
            area_weight=0.6
        )
        assert rel.get_weight(WeightMethod.EQUAL) == 1.0


class TestCrosswalkMetadata:
    """Tests for CrosswalkMetadata data class."""

    def test_create_metadata(self):
        """Test creating crosswalk metadata."""
        meta = CrosswalkMetadata(
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            total_source_units=1000,
            total_target_units=1050,
            one_to_one_count=900,
            split_count=80,
            merged_count=20
        )
        assert meta.source_year == 2010
        assert meta.target_year == 2020
        assert meta.total_source_units == 1000

    def test_change_rate(self):
        """Test change rate calculation."""
        meta = CrosswalkMetadata(
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            total_source_units=1000,
            one_to_one_count=900,
            split_count=80,
            merged_count=20
        )
        assert meta.change_rate == 0.1  # 100/1000 = 10%

    def test_change_rate_empty(self):
        """Test change rate with no source units."""
        meta = CrosswalkMetadata(
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            total_source_units=0
        )
        assert meta.change_rate == 0.0

    def test_summary(self):
        """Test summary method."""
        meta = CrosswalkMetadata(
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            total_source_units=100,
            one_to_one_count=80,
            split_count=15,
            merged_count=5
        )
        summary = meta.summary()
        assert summary['source_year'] == 2010
        assert summary['target_year'] == 2020
        assert summary['unchanged'] == 80
        assert summary['splits'] == 15


class TestGeographyChange:
    """Tests for GeographyChange data class."""

    def test_create_geography_change(self):
        """Test creating a geography change object."""
        change = GeographyChange(
            source_geoid='06037010100',
            relationship_type=RelationshipType.SPLIT,
            target_geoids=['06037010101', '06037010102'],
            weights={'06037010101': 0.6, '06037010102': 0.4}
        )
        assert change.was_split
        assert not change.was_merged
        assert not change.is_unchanged
        assert change.num_targets == 2

    def test_unchanged_geography(self):
        """Test unchanged geography detection."""
        change = GeographyChange(
            source_geoid='06037010100',
            relationship_type=RelationshipType.ONE_TO_ONE,
            target_geoids=['06037010100'],
            weights={'06037010100': 1.0}
        )
        assert change.is_unchanged
        assert not change.was_split
        assert change.num_targets == 1


# =============================================================================
# CROSSWALK CLIENT TESTS
# =============================================================================

class TestCrosswalkClient:
    """Tests for CrosswalkClient."""

    def test_init_with_custom_cache_dir(self, temp_cache_dir):
        """Test client initialization with custom cache directory."""
        client = CrosswalkClient(cache_dir=temp_cache_dir)
        assert client.cache_dir == temp_cache_dir

    def test_list_available_crosswalks(self, crosswalk_client):
        """Test listing available crosswalks."""
        available = crosswalk_client.list_available_crosswalks()
        assert len(available) > 0
        # Check structure
        for item in available:
            assert 'source_year' in item
            assert 'target_year' in item
            assert 'geography_level' in item

    def test_unsupported_year_combination(self, crosswalk_client):
        """Test error for unsupported year combination."""
        with pytest.raises(ValueError, match="Crosswalk not supported"):
            crosswalk_client.get_crosswalk(
                source_year=1990,
                target_year=2000,
                geography_level='tract'
            )

    @patch('siege_utilities.geo.crosswalk.crosswalk_client.requests.get')
    def test_get_crosswalk_with_mock(self, mock_get, crosswalk_client, mock_crosswalk_response):
        """Test getting crosswalk with mocked response."""
        mock_response = Mock()
        mock_response.text = mock_crosswalk_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        df = crosswalk_client.get_crosswalk(
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )

        assert not df.empty
        assert 'source_geoid' in df.columns
        assert 'target_geoid' in df.columns
        assert 'area_weight' in df.columns

    @patch('siege_utilities.geo.crosswalk.crosswalk_client.requests.get')
    def test_get_crosswalk_with_state_filter(self, mock_get, crosswalk_client, mock_crosswalk_response):
        """Test getting crosswalk filtered by state."""
        mock_response = Mock()
        mock_response.text = mock_crosswalk_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        df = crosswalk_client.get_crosswalk(
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            state_fips='06'
        )

        # All GEOIDs should start with California FIPS
        assert df['source_geoid'].str.startswith('06').all() or df['target_geoid'].str.startswith('06').all()

    def test_clear_cache(self, crosswalk_client, temp_cache_dir):
        """Test cache clearing."""
        # Create a dummy cache file
        dummy_file = temp_cache_dir / 'test_cache.parquet'
        dummy_file.touch()

        deleted = crosswalk_client.clear_cache()
        assert deleted >= 1
        assert not dummy_file.exists()


# =============================================================================
# CROSSWALK PROCESSOR TESTS
# =============================================================================

class TestCrosswalkProcessor:
    """Tests for CrosswalkProcessor."""

    def test_init_processor(self, mock_crosswalk_df):
        """Test processor initialization."""
        processor = CrosswalkProcessor(
            crosswalk_df=mock_crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )
        assert len(processor.source_to_targets) > 0
        assert len(processor.target_to_sources) > 0

    def test_get_relationship_type_one_to_one(self, mock_crosswalk_df):
        """Test identifying one-to-one relationship."""
        processor = CrosswalkProcessor(
            crosswalk_df=mock_crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )
        rel_type = processor.get_relationship_type('06037010100')
        assert rel_type == RelationshipType.ONE_TO_ONE

    def test_get_relationship_type_split(self, mock_crosswalk_df):
        """Test identifying split relationship."""
        processor = CrosswalkProcessor(
            crosswalk_df=mock_crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )
        rel_type = processor.get_relationship_type('06037010300')
        assert rel_type == RelationshipType.SPLIT

    def test_get_geography_change(self, mock_crosswalk_df):
        """Test getting geography change details."""
        processor = CrosswalkProcessor(
            crosswalk_df=mock_crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )
        change = processor.get_geography_change('06037010300')
        assert change.was_split
        assert change.num_targets == 2
        assert '06037010301' in change.target_geoids
        assert '06037010302' in change.target_geoids

    def test_transform_simple(self, mock_crosswalk_df, mock_source_data):
        """Test basic data transformation."""
        processor = CrosswalkProcessor(
            crosswalk_df=mock_crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )

        result = processor.transform(
            df=mock_source_data,
            geoid_column='GEOID',
            value_columns=['population', 'median_income']
        )

        assert not result.empty
        assert 'GEOID' in result.columns
        # Split tract should produce two rows with weighted values
        assert len(result) >= len(mock_source_data)

    def test_transform_with_weighting(self, mock_crosswalk_df, mock_source_data):
        """Test transformation with proper weighting."""
        processor = CrosswalkProcessor(
            crosswalk_df=mock_crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )

        result = processor.transform(
            df=mock_source_data,
            geoid_column='GEOID',
            value_columns=['population'],
            weight_method=WeightMethod.AREA
        )

        # The split tract (4000 population) should be distributed
        # 0.6 * 4000 = 2400 and 0.4 * 4000 = 1600
        split_results = result[result['GEOID'].str.startswith('060370103')]
        assert len(split_results) == 2

    def test_transform_missing_geoid_column(self, mock_crosswalk_df, mock_source_data):
        """Test error when GEOID column is missing."""
        processor = CrosswalkProcessor(
            crosswalk_df=mock_crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )

        with pytest.raises(ValueError, match="GEOID column .* not found"):
            processor.transform(
                df=mock_source_data,
                geoid_column='missing_column'
            )


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('siege_utilities.geo.crosswalk.crosswalk_processor.get_crosswalk')
    def test_apply_crosswalk(self, mock_get_crosswalk, mock_crosswalk_df, mock_source_data):
        """Test apply_crosswalk convenience function."""
        mock_get_crosswalk.return_value = mock_crosswalk_df

        result = apply_crosswalk(
            df=mock_source_data,
            source_year=2010,
            target_year=2020,
            geography_level='tract',
            geoid_column='GEOID'
        )

        assert not result.empty
        mock_get_crosswalk.assert_called_once()

    @patch('siege_utilities.geo.crosswalk.crosswalk_processor.get_crosswalk')
    def test_normalize_to_year_same_year(self, mock_get_crosswalk, mock_source_data):
        """Test normalize_to_year when data already in target year."""
        result = normalize_to_year(
            df=mock_source_data,
            data_year=2020,
            target_year=2020,
            geography_level='tract'
        )

        # Should return copy without transformation
        assert len(result) == len(mock_source_data)
        mock_get_crosswalk.assert_not_called()

    @patch('siege_utilities.geo.crosswalk.crosswalk_processor.get_crosswalk')
    def test_identify_boundary_changes(self, mock_get_crosswalk, mock_crosswalk_df):
        """Test identify_boundary_changes function."""
        mock_get_crosswalk.return_value = mock_crosswalk_df

        changes = identify_boundary_changes(
            source_year=2010,
            target_year=2020,
            geography_level='tract'
        )

        assert not changes.empty
        assert 'source_geoid' in changes.columns
        assert 'relationship_type' in changes.columns
        assert 'num_targets' in changes.columns

    @patch('siege_utilities.geo.crosswalk.crosswalk_processor.get_crosswalk')
    def test_get_split_tracts(self, mock_get_crosswalk, mock_crosswalk_df):
        """Test get_split_tracts function."""
        mock_get_crosswalk.return_value = mock_crosswalk_df

        splits = get_split_tracts(source_year=2010, target_year=2020)

        # Should only return split relationships
        assert all(splits['relationship_type'] == 'split')

    def test_list_available_crosswalks_function(self):
        """Test list_available_crosswalks function."""
        available = list_available_crosswalks()
        assert len(available) > 0

        # Check 2010-2020 tract is available
        tract_2010_2020 = [
            a for a in available
            if a['source_year'] == 2010 and a['target_year'] == 2020 and a['geography_level'] == 'tract'
        ]
        assert len(tract_2010_2020) == 1


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_supported_crosswalk_years(self):
        """Test SUPPORTED_CROSSWALK_YEARS constant."""
        assert (2010, 2020) in SUPPORTED_CROSSWALK_YEARS
        assert SUPPORTED_CROSSWALK_YEARS[(2010, 2020)]['tract'] is True
        assert SUPPORTED_CROSSWALK_YEARS[(2010, 2020)]['block_group'] is True
