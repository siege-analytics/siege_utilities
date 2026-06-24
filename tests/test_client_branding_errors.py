"""Tests for the typed exception hierarchy in reporting.client_branding (ELE-2420)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from siege_utilities.reporting.client_branding import (
    ClientBrandingError,
    ClientBrandingManager,
    ClientBrandingNotFoundError,
)


@pytest.fixture
def manager(tmp_path):
    return ClientBrandingManager(config_dir=tmp_path)


class TestExceptionHierarchy:
    def test_client_branding_error_is_runtime_error(self):
        assert issubclass(ClientBrandingError, RuntimeError)

    def test_not_found_is_lookup_error(self):
        assert issubclass(ClientBrandingNotFoundError, LookupError)


class TestGetClientBranding:
    def test_not_found_raises(self, manager):
        # SU-1 + ELE-2420 typed hierarchy: get_client_branding documents
        # "Raises ClientBrandingNotFoundError if no branding configuration
        # exists". Previously asserted `is None`, contradicting the contract.
        with pytest.raises(ClientBrandingNotFoundError):
            manager.get_client_branding("nonexistent_xyz")

    def test_io_error_raises(self, manager, tmp_path):
        client_dir = tmp_path / "corrupt_client"
        client_dir.mkdir()
        (client_dir / "corrupt_client_branding.yaml").write_text("not: valid: yaml: [")
        with pytest.raises(ClientBrandingError) as exc_info:
            manager.get_client_branding("corrupt_client")
        assert exc_info.value.__cause__ is not None


class TestUpdateClientBranding:
    def test_unknown_client_raises_not_found(self, manager):
        with pytest.raises(ClientBrandingNotFoundError):
            manager.update_client_branding("nonexistent_xyz", {"colors": {}})

    def test_io_error_raises_branding_error(self, manager, tmp_path):
        # Stage an existing client
        manager.create_client_branding(
            "tester",
            {"name": "tester", "colors": {"primary": "#000", "text_color": "#111"}, "fonts": {"default_font": "Helvetica"}},
        )
        with patch("builtins.open", side_effect=OSError("disk full")):
            with pytest.raises(ClientBrandingError) as exc_info:
                manager.update_client_branding("tester", {"colors": {"primary": "#fff"}})
            assert isinstance(exc_info.value.__cause__, OSError)


class TestDeleteClientBranding:
    def test_predefined_template_raises(self, manager):
        # delete_client_branding documents "Raises ClientBrandingError if
        # attempting to delete a predefined template". Previously asserted
        # `is False`, contradicting the documented contract (SU-1).
        with pytest.raises(ClientBrandingError):
            manager.delete_client_branding("siege_analytics")

    def test_missing_dir_raises_not_found(self, manager):
        # delete_client_branding documents "Raises ClientBrandingNotFoundError
        # if no configuration exists for the client". Previously asserted
        # `is False`.
        with pytest.raises(ClientBrandingNotFoundError):
            manager.delete_client_branding("never_existed")

    def test_io_error_raises(self, manager, tmp_path):
        manager.create_client_branding(
            "tester",
            {"name": "tester", "colors": {"primary": "#000", "text_color": "#111"}, "fonts": {"default_font": "Helvetica"}},
        )
        with patch("siege_utilities.reporting.client_branding.shutil.rmtree", side_effect=OSError("permission denied")):
            with pytest.raises(ClientBrandingError) as exc_info:
                manager.delete_client_branding("tester")
            assert isinstance(exc_info.value.__cause__, OSError)


class TestExportBrandingConfig:
    def test_unknown_client_raises_not_found(self, manager, tmp_path):
        with pytest.raises(ClientBrandingNotFoundError):
            manager.export_branding_config("nonexistent_xyz", tmp_path / "out.yaml")

    def test_io_error_raises(self, manager, tmp_path):
        with patch("builtins.open", side_effect=OSError("disk full")):
            with pytest.raises(ClientBrandingError) as exc_info:
                manager.export_branding_config("siege_analytics", tmp_path / "out.yaml")
            assert isinstance(exc_info.value.__cause__, OSError)


class TestImportBrandingConfig:
    def test_malformed_yaml_raises(self, manager, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("not: valid: yaml: [")
        with pytest.raises(ClientBrandingError) as exc_info:
            manager.import_branding_config(bad)
        assert exc_info.value.__cause__ is not None

    def test_unsupported_format_raises(self, manager, tmp_path):
        # import_branding_config documents "Raises ValueError if the file
        # format is unsupported or validation fails". Previously asserted
        # `is False` (SU-1: input validation failure is not a False return).
        bogus = tmp_path / "config.txt"
        bogus.write_text("whatever")
        with pytest.raises(ValueError, match="Unsupported file format"):
            manager.import_branding_config(bogus)


class TestGetBrandingSummary:
    def test_raises_on_corrupt_config(self, manager, tmp_path):
        client_dir = tmp_path / "corrupt_client"
        client_dir.mkdir()
        (client_dir / "corrupt_client_branding.yaml").write_text("not: valid: yaml: [")
        with pytest.raises(ClientBrandingError):
            manager.get_branding_summary("corrupt_client")
