"""Tests for NCES population service."""

from unittest.mock import MagicMock, patch

import pytest


class TestNCESPopulationResult:
    """Tests for the result dataclass."""

    def test_total_processed(self):
        from siege_utilities.geo.django.services.nces_service import NCESPopulationResult

        result = NCESPopulationResult(
            action="test", year=2023,
            records_created=10, records_updated=5, records_skipped=3,
        )
        assert result.total_processed == 18

    def test_success_no_errors(self):
        from siege_utilities.geo.django.services.nces_service import NCESPopulationResult

        result = NCESPopulationResult(action="test", year=2023)
        assert result.success is True

    def test_success_with_errors(self):
        from siege_utilities.geo.django.services.nces_service import NCESPopulationResult

        result = NCESPopulationResult(
            action="test", year=2023, errors=["something failed"]
        )
        assert result.success is False


class TestNCESPopulationService:
    """Tests for the NCESPopulationService class."""

    def test_init_default(self):
        from siege_utilities.geo.django.services.nces_service import NCESPopulationService

        service = NCESPopulationService()
        assert service.cache_dir is None

    def test_init_with_cache(self, tmp_path):
        from siege_utilities.geo.django.services.nces_service import NCESPopulationService

        service = NCESPopulationService(cache_dir=str(tmp_path))
        assert service.cache_dir == str(tmp_path)

    def test_get_downloader(self):
        from siege_utilities.geo.django.services.nces_service import NCESPopulationService
        from siege_utilities.geo.nces_download import NCESDownloader

        service = NCESPopulationService(cache_dir="/tmp/test")
        downloader = service._get_downloader()
        assert isinstance(downloader, NCESDownloader)


class TestPopulateNCESCommand:
    """Tests for the management command argument parsing."""

    def test_valid_actions(self):
        from siege_utilities.geo.django.management.commands.populate_nces import VALID_ACTIONS

        assert "locale_boundaries" in VALID_ACTIONS
        assert "school_locations" in VALID_ACTIONS
        assert "enrich_districts" in VALID_ACTIONS
        assert "all" in VALID_ACTIONS
