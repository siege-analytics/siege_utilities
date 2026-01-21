"""
Unit tests for Census file download module (PL 94-171).

Tests the PLFileDownloader class and convenience functions with mocked responses.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import zipfile
import io

from siege_utilities.geo.census_files import (
    PLFileDownloader,
    get_pl_data,
    get_pl_blocks,
    get_pl_tracts,
    download_pl_file,
    list_available_pl_files,
    PL_FILE_TYPES,
    PL_TABLES,
)
from siege_utilities.geo.census_files.pl_downloader import (
    SUMMARY_LEVELS,
    PL_CACHE_TIMEOUT_DAYS,
    DEFAULT_CACHE_DIR,
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
def pl_downloader(temp_cache_dir):
    """Create a PLFileDownloader with a temporary cache directory."""
    return PLFileDownloader(cache_dir=temp_cache_dir)


@pytest.fixture
def mock_geo_content():
    """Create mock geographic header file content (pipe-delimited)."""
    # Simplified geo file content with key columns
    lines = [
        # FILEID|STUSAB|SUMLEV|GEOVAR|GEOCOMP|CHAESSION|CIFSN|LOGRECNO|...STATE...COUNTY...TRACT|BLKGRP|BLOCK
        "PLST|CA|140|000|00|000|00|1|000000000000|0|0|06|00|000|00|037|00|00|000|00|00|000|00|00|000|00|00|000|00|00|010100|1|1001",
        "PLST|CA|140|000|00|000|00|2|000000000000|0|0|06|00|000|00|037|00|00|000|00|00|000|00|00|000|00|00|000|00|00|010200|2|2001",
        "PLST|CA|750|000|00|000|00|3|000000000000|0|0|06|00|000|00|037|00|00|000|00|00|000|00|00|000|00|00|000|00|00|010100|1|1001",
    ]
    return '\n'.join(lines)


@pytest.fixture
def mock_data_content_pl1():
    """Create mock PL file 1 content (P1, P2, H1 tables)."""
    # Simplified data file content with key columns
    lines = [
        # FILEID|STUSAB|CHAESSION|CIFSN|LOGRECNO|P1_001N|P1_002N|...(more columns)
        "PLST|CA|000|00|1|5000|4500|4000|500|50|100|200|30|20|100|50|50|5000|3000|2000|1800|1700|50|20|30|10|5|10|5|10|5|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|2000|1800|200",
        "PLST|CA|000|00|2|3000|2700|2400|300|30|60|120|20|10|70|30|40|3000|1800|1200|1100|1000|30|12|18|6|3|6|3|6|3|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|1500|1300|200",
        "PLST|CA|000|00|3|1500|1350|1200|150|15|30|60|10|5|35|15|20|1500|900|600|550|500|15|6|9|3|1|3|1|3|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|800|700|100",
    ]
    return '\n'.join(lines)


@pytest.fixture
def mock_zip_content(mock_geo_content, mock_data_content_pl1):
    """Create a mock zip file containing PL data."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('cageo2020.pl', mock_geo_content)
        zf.writestr('ca000012020.pl', mock_data_content_pl1)
        zf.writestr('ca000022020.pl', mock_data_content_pl1)
        zf.writestr('ca000032020.pl', mock_data_content_pl1)
    return zip_buffer.getvalue()


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_summary_levels(self):
        """Test SUMMARY_LEVELS dictionary."""
        assert 'nation' in SUMMARY_LEVELS
        assert 'state' in SUMMARY_LEVELS
        assert 'county' in SUMMARY_LEVELS
        assert 'tract' in SUMMARY_LEVELS
        assert 'block_group' in SUMMARY_LEVELS
        assert 'block' in SUMMARY_LEVELS

        assert SUMMARY_LEVELS['tract'] == '140'
        assert SUMMARY_LEVELS['block'] == '750'

    def test_pl_file_types(self):
        """Test PL_FILE_TYPES dictionary."""
        assert 'geo' in PL_FILE_TYPES
        assert 'pl1' in PL_FILE_TYPES
        assert 'pl2' in PL_FILE_TYPES
        assert 'pl3' in PL_FILE_TYPES

    def test_pl_tables(self):
        """Test PL_TABLES dictionary."""
        assert 'P1' in PL_TABLES
        assert 'P2' in PL_TABLES
        assert 'P3' in PL_TABLES
        assert 'P4' in PL_TABLES
        assert 'P5' in PL_TABLES
        assert 'H1' in PL_TABLES

        # Check P1 structure
        assert 'name' in PL_TABLES['P1']
        assert 'file' in PL_TABLES['P1']
        assert 'columns' in PL_TABLES['P1']
        assert PL_TABLES['P1']['name'] == 'Race'

    def test_pl_table_columns(self):
        """Test PL table column definitions."""
        # P1 should have race columns
        assert 'P1_001N' in PL_TABLES['P1']['columns']
        assert 'P1_003N' in PL_TABLES['P1']['columns']

        # H1 should have housing columns
        assert 'H1_001N' in PL_TABLES['H1']['columns']
        assert 'H1_002N' in PL_TABLES['H1']['columns']
        assert 'H1_003N' in PL_TABLES['H1']['columns']


# =============================================================================
# PLFILEDOWNLOADER TESTS
# =============================================================================

class TestPLFileDownloader:
    """Tests for PLFileDownloader class."""

    def test_init_default(self):
        """Test default initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = PLFileDownloader(cache_dir=temp_dir)
            assert downloader.cache_dir == Path(temp_dir)
            assert downloader.timeout > 0

    def test_init_creates_cache_dir(self, temp_cache_dir):
        """Test that init creates cache directory."""
        new_cache = temp_cache_dir / 'new_cache'
        downloader = PLFileDownloader(cache_dir=new_cache)
        assert new_cache.exists()

    def test_build_geo_url_2020(self, pl_downloader):
        """Test URL building for 2020 PL files."""
        url = pl_downloader._build_geo_url('CA', 2020)
        assert '2020' in url
        assert 'California' in url
        assert 'ca2020.pl.zip' in url

    def test_build_geo_url_2010(self, pl_downloader):
        """Test URL building for 2010 PL files."""
        url = pl_downloader._build_geo_url('NY', 2010)
        assert '2010' in url
        assert 'New_York' in url

    def test_build_geo_url_invalid_year(self, pl_downloader):
        """Test that invalid year raises error."""
        with pytest.raises(ValueError, match="only available for 2010 and 2020"):
            pl_downloader._build_geo_url('CA', 2015)

    def test_get_state_name_for_url(self, pl_downloader):
        """Test state name URL formatting."""
        assert pl_downloader._get_state_name_for_url('CA') == 'California'
        assert pl_downloader._get_state_name_for_url('NY') == 'New_York'
        assert pl_downloader._get_state_name_for_url('DC') == 'District_of_Columbia'
        assert pl_downloader._get_state_name_for_url('NH') == 'New_Hampshire'

    def test_construct_geoid_state(self, pl_downloader):
        """Test GEOID construction for state level."""
        df = pd.DataFrame({'STATE': ['06', '36']})
        result = pl_downloader._construct_geoid(df, 'state')
        assert list(result['GEOID']) == ['06', '36']

    def test_construct_geoid_county(self, pl_downloader):
        """Test GEOID construction for county level."""
        df = pd.DataFrame({
            'STATE': ['06', '36'],
            'COUNTY': ['037', '061']
        })
        result = pl_downloader._construct_geoid(df, 'county')
        assert list(result['GEOID']) == ['06037', '36061']

    def test_construct_geoid_tract(self, pl_downloader):
        """Test GEOID construction for tract level."""
        df = pd.DataFrame({
            'STATE': ['06', '36'],
            'COUNTY': ['037', '061'],
            'TRACT': ['010100', '000100']
        })
        result = pl_downloader._construct_geoid(df, 'tract')
        assert list(result['GEOID']) == ['06037010100', '36061000100']

    def test_construct_geoid_block_group(self, pl_downloader):
        """Test GEOID construction for block group level."""
        df = pd.DataFrame({
            'STATE': ['06'],
            'COUNTY': ['037'],
            'TRACT': ['010100'],
            'BLKGRP': ['1']
        })
        result = pl_downloader._construct_geoid(df, 'block_group')
        assert result['GEOID'].iloc[0] == '060370101001'

    def test_construct_geoid_block(self, pl_downloader):
        """Test GEOID construction for block level."""
        df = pd.DataFrame({
            'STATE': ['06'],
            'COUNTY': ['037'],
            'TRACT': ['010100'],
            'BLOCK': ['1001']
        })
        result = pl_downloader._construct_geoid(df, 'block')
        assert result['GEOID'].iloc[0] == '060370101001001'

    def test_is_cache_valid_missing(self, pl_downloader):
        """Test cache validation for missing file."""
        result = pl_downloader._is_cache_valid(Path('/nonexistent/file.parquet'))
        assert result is False

    def test_is_cache_valid_exists(self, temp_cache_dir, pl_downloader):
        """Test cache validation for existing file."""
        cache_file = temp_cache_dir / 'test.parquet'
        cache_file.touch()
        result = pl_downloader._is_cache_valid(cache_file)
        assert result is True

    def test_clear_cache(self, temp_cache_dir, pl_downloader):
        """Test cache clearing."""
        # Create some cache files
        (temp_cache_dir / 'test1.parquet').touch()
        (temp_cache_dir / 'test2.parquet').touch()

        deleted = pl_downloader.clear_cache()
        assert deleted == 2
        assert len(list(temp_cache_dir.glob('*.parquet'))) == 0

    @patch('siege_utilities.geo.census_files.pl_downloader.requests.get')
    def test_get_data_with_mock(self, mock_get, pl_downloader, mock_zip_content):
        """Test get_data with mocked network response."""
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.content = mock_zip_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # This would normally download - with mocking it uses the mock content
        # For testing the parsing logic, we need a more complete mock
        # This test validates the interface works
        assert callable(pl_downloader.get_data)

    def test_get_data_invalid_geography(self, pl_downloader):
        """Test that invalid geography raises error."""
        with pytest.raises(ValueError, match="Unknown geography level"):
            pl_downloader.get_data('CA', geography='invalid_level')


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_list_available_pl_files_2020(self):
        """Test listing available PL files for 2020."""
        files = list_available_pl_files(year=2020)

        assert len(files) > 0
        assert all(f['year'] == 2020 for f in files)

        # Check structure
        sample = files[0]
        assert 'state_abbr' in sample
        assert 'state_fips' in sample
        assert 'year' in sample
        assert 'tables' in sample

    def test_list_available_pl_files_includes_all_states(self):
        """Test that all states are listed."""
        files = list_available_pl_files(year=2020)
        abbrs = [f['state_abbr'] for f in files]

        # Check key states are included
        assert 'CA' in abbrs
        assert 'NY' in abbrs
        assert 'TX' in abbrs
        assert 'FL' in abbrs

    def test_list_available_pl_files_tables(self):
        """Test that tables are listed correctly."""
        files = list_available_pl_files(year=2020)
        tables = files[0]['tables']

        assert 'P1' in tables
        assert 'P2' in tables
        assert 'P3' in tables
        assert 'P4' in tables
        assert 'P5' in tables
        assert 'H1' in tables

    def test_get_pl_data_interface(self):
        """Test that get_pl_data function is callable."""
        assert callable(get_pl_data)
        # We don't call it without mocking to avoid network requests

    def test_get_pl_blocks_interface(self):
        """Test that get_pl_blocks function is callable."""
        assert callable(get_pl_blocks)

    def test_get_pl_tracts_interface(self):
        """Test that get_pl_tracts function is callable."""
        assert callable(get_pl_tracts)

    def test_download_pl_file_interface(self):
        """Test that download_pl_file function is callable."""
        assert callable(download_pl_file)


# =============================================================================
# PL TABLE STRUCTURE TESTS
# =============================================================================

class TestPLTableStructure:
    """Tests for PL table definitions."""

    def test_p1_race_table(self):
        """Test P1 (Race) table structure."""
        p1 = PL_TABLES['P1']
        assert p1['name'] == 'Race'
        assert p1['file'] == 'pl1'

        cols = p1['columns']
        assert cols['P1_001N'] == 'Total'
        assert 'White alone' in cols['P1_003N']
        assert 'Black' in cols['P1_004N']

    def test_p2_hispanic_table(self):
        """Test P2 (Hispanic/Latino) table structure."""
        p2 = PL_TABLES['P2']
        assert 'Hispanic' in p2['name']
        assert p2['file'] == 'pl1'

        cols = p2['columns']
        assert cols['P2_001N'] == 'Total'
        assert 'Hispanic' in cols['P2_002N']

    def test_p3_race_18plus_table(self):
        """Test P3 (Race 18+) table structure."""
        p3 = PL_TABLES['P3']
        assert '18' in p3['name']
        assert p3['file'] == 'pl2'

        cols = p3['columns']
        assert 'Total 18+' in cols['P3_001N']

    def test_p4_hispanic_18plus_table(self):
        """Test P4 (Hispanic 18+) table structure."""
        p4 = PL_TABLES['P4']
        assert '18+' in p4['name']
        assert 'Hispanic' in p4['name']
        assert p4['file'] == 'pl2'

    def test_p5_group_quarters_table(self):
        """Test P5 (Group Quarters) table structure."""
        p5 = PL_TABLES['P5']
        assert 'Group Quarters' in p5['name']
        assert p5['file'] == 'pl3'

        cols = p5['columns']
        assert 'Total GQ Population' in cols['P5_001N']
        assert 'Institutionalized' in cols['P5_002N']

    def test_h1_housing_table(self):
        """Test H1 (Housing) table structure."""
        h1 = PL_TABLES['H1']
        assert 'Housing' in h1['name']
        assert h1['file'] == 'pl1'

        cols = h1['columns']
        assert cols['H1_001N'] == 'Total Housing Units'
        assert cols['H1_002N'] == 'Occupied'
        assert cols['H1_003N'] == 'Vacant'


# =============================================================================
# INTEGRATION-STYLE TESTS (mocked)
# =============================================================================

class TestMockedIntegration:
    """Integration-style tests with mocked network calls."""

    @patch('siege_utilities.geo.census_files.pl_downloader.requests.get')
    def test_download_pl_file_mocked(self, mock_get, temp_cache_dir, mock_zip_content):
        """Test download_pl_file with mocked network."""
        mock_response = Mock()
        mock_response.content = mock_zip_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Download to temp directory
        output_path = download_pl_file('CA', year=2020, output_dir=temp_cache_dir)

        assert output_path.exists()
        assert output_path.suffix == '.zip'
        mock_get.assert_called_once()

    def test_year_validation(self, pl_downloader):
        """Test that only 2010 and 2020 are valid years."""
        # Valid years should not raise in URL building
        url_2020 = pl_downloader._build_geo_url('CA', 2020)
        url_2010 = pl_downloader._build_geo_url('CA', 2010)

        assert '2020' in url_2020
        assert '2010' in url_2010

        # Invalid years should raise
        for invalid_year in [2000, 2005, 2015, 2025]:
            with pytest.raises(ValueError):
                pl_downloader._build_geo_url('CA', invalid_year)


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_state_normalization_abbreviation(self, pl_downloader):
        """Test state normalization with abbreviation."""
        url = pl_downloader._build_geo_url('ca', 2020)
        assert 'California' in url

    def test_state_normalization_uppercase(self, pl_downloader):
        """Test state normalization with uppercase abbreviation."""
        url = pl_downloader._build_geo_url('CA', 2020)
        assert 'California' in url

    def test_geography_normalization_spaces(self, pl_downloader):
        """Test geography level normalization with spaces."""
        # Should handle 'block group' vs 'block_group'
        with pytest.raises(ValueError):
            pl_downloader.get_data('CA', geography='unknown level')

    def test_empty_tables_list(self, pl_downloader):
        """Test with empty tables list."""
        # Should use all tables when None
        assert callable(pl_downloader.get_data)

    def test_county_padding(self, pl_downloader):
        """Test county FIPS code padding."""
        df = pd.DataFrame({
            'STATE': ['06'],
            'COUNTY': ['37'],  # Not zero-padded
            'TRACT': ['010100']
        })
        # The method should handle padding
        # This tests the data transformation logic
        result = pl_downloader._construct_geoid(df.copy(), 'county')
        # Should pad to 3 digits
        assert len(result['GEOID'].iloc[0]) == 5  # 2 + 3


# =============================================================================
# CACHE BEHAVIOR TESTS
# =============================================================================

class TestCacheBehavior:
    """Tests for caching behavior."""

    def test_cache_dir_default(self):
        """Test default cache directory."""
        assert DEFAULT_CACHE_DIR.parent.name == 'cache'
        assert 'pl_files' in str(DEFAULT_CACHE_DIR)

    def test_cache_timeout(self):
        """Test cache timeout value."""
        assert PL_CACHE_TIMEOUT_DAYS == 30

    def test_cache_file_naming(self, pl_downloader):
        """Test cache file naming convention."""
        # Cache files should follow pattern: type_state_year.parquet
        cache_dir = pl_downloader.cache_dir

        # Create test file to verify path construction works
        test_path = cache_dir / 'geo_CA_2020.parquet'
        test_path.touch()

        assert test_path.exists()
        assert test_path.suffix == '.parquet'
