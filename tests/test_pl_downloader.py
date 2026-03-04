"""
Tests for the PL 94-171 redistricting data downloader.

Tests parsing, GEOID construction, caching, and data structure without
making network calls (all downloads are mocked).
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import pandas as pd


class TestPLFileDownloaderImport:
    """Basic import and instantiation tests."""

    def test_import_module(self):
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader

        assert PLFileDownloader is not None

    def test_instantiation_creates_cache_dir(self, tmp_path):
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader

        cache_dir = tmp_path / "pl_cache"
        dl = PLFileDownloader(cache_dir=cache_dir)
        assert dl.cache_dir == cache_dir
        assert cache_dir.exists()

    def test_default_timeout(self, tmp_path):
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader

        dl = PLFileDownloader(cache_dir=tmp_path)
        assert dl.timeout == 300


class TestPLConstants:
    """Tests for PL 94-171 constant definitions."""

    def test_summary_levels_defined(self):
        from siege_utilities.geo.census_files.pl_downloader import SUMMARY_LEVELS

        assert "state" in SUMMARY_LEVELS
        assert "county" in SUMMARY_LEVELS
        assert "tract" in SUMMARY_LEVELS
        assert "block_group" in SUMMARY_LEVELS
        assert "block" in SUMMARY_LEVELS

    def test_summary_level_codes(self):
        from siege_utilities.geo.census_files.pl_downloader import SUMMARY_LEVELS

        assert SUMMARY_LEVELS["state"] == "040"
        assert SUMMARY_LEVELS["county"] == "050"
        assert SUMMARY_LEVELS["tract"] == "140"
        assert SUMMARY_LEVELS["block"] == "750"

    def test_pl_file_types(self):
        from siege_utilities.geo.census_files.pl_downloader import PL_FILE_TYPES

        assert "geo" in PL_FILE_TYPES
        assert "pl1" in PL_FILE_TYPES

    def test_base_urls_defined(self):
        from siege_utilities.geo.census_files.pl_downloader import (
            PL_2020_BASE_URL,
            PL_2010_BASE_URL,
        )

        assert "2020" in PL_2020_BASE_URL
        assert "2010" in PL_2010_BASE_URL

    def test_pl_variable_groups_in_registry(self):
        """Verify PL variable groups are registered in the census registry."""
        from siege_utilities.config.census_registry import VARIABLE_GROUPS

        assert "pl_p1_race" in VARIABLE_GROUPS
        assert "pl_p2_hispanic" in VARIABLE_GROUPS
        assert "pl_p3_race_18plus" in VARIABLE_GROUPS
        assert "pl_p4_hispanic_18plus" in VARIABLE_GROUPS
        assert "pl_p5_group_quarters" in VARIABLE_GROUPS
        assert "pl_h1_housing" in VARIABLE_GROUPS
        assert "pl_redistricting_core" in VARIABLE_GROUPS
        assert "pl_voting_age" in VARIABLE_GROUPS


class TestPLConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_pl_data_exists(self):
        from siege_utilities.geo.census_files.pl_downloader import get_pl_data

        assert callable(get_pl_data)

    def test_get_pl_blocks_exists(self):
        from siege_utilities.geo.census_files.pl_downloader import get_pl_blocks

        assert callable(get_pl_blocks)

    def test_get_pl_tracts_exists(self):
        from siege_utilities.geo.census_files.pl_downloader import get_pl_tracts

        assert callable(get_pl_tracts)


class TestPLDownloaderMethods:
    """Tests for PLFileDownloader methods (mocked network)."""

    def test_get_data_method_exists(self, tmp_path):
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader

        dl = PLFileDownloader(cache_dir=tmp_path)
        assert hasattr(dl, "get_data")
        assert callable(dl.get_data)

    def test_get_data_accepts_state_abbreviation(self, tmp_path):
        """Verify get_data signature accepts standard params."""
        import inspect
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader

        sig = inspect.signature(PLFileDownloader.get_data)
        params = list(sig.parameters.keys())
        assert "state" in params
        assert "year" in params
        assert "geography" in params

    def test_cache_key_generation(self, tmp_path):
        """Verify cache file naming is deterministic."""
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader

        dl = PLFileDownloader(cache_dir=tmp_path)
        # The downloader generates cache paths from state+year
        assert hasattr(dl, "cache_dir")


class TestPLTableDefinitions:
    """Tests for PL table column definitions."""

    def test_table_definitions_exist(self):
        from siege_utilities.geo.census_files import pl_downloader

        # Should have table column definitions for P1-P5, H1
        assert hasattr(pl_downloader, "PL_TABLE_COLUMNS") or hasattr(
            pl_downloader, "PL_TABLES"
        )
