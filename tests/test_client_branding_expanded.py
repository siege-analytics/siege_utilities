"""Expanded tests for siege_utilities.reporting.client_branding module."""

import pytest
import json
import yaml
from siege_utilities.reporting.client_branding import (
    ClientBrandingManager,
    ClientBrandingError,
    ClientBrandingNotFoundError,
)


class TestClientBrandingManagerInit:
    """Tests for ClientBrandingManager initialization."""

    def test_default_config_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        # Use explicit config_dir to avoid touching home
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        assert mgr.config_dir.exists()

    def test_custom_config_dir(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "custom_branding")
        assert mgr.config_dir == tmp_path / "custom_branding"
        assert mgr.config_dir.exists()

    def test_templates_loaded(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        assert "siege_analytics" in mgr.branding_templates
        assert "masai_interactive" in mgr.branding_templates
        assert "hillcrest" in mgr.branding_templates


class TestGetClientBranding:
    """Tests for get_client_branding."""

    def test_get_predefined_template(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        branding = mgr.get_client_branding("siege_analytics")
        assert branding is not None
        assert branding["name"] == "Siege Analytics"
        assert "colors" in branding
        assert "fonts" in branding

    def test_get_predefined_case_insensitive(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        branding = mgr.get_client_branding("SIEGE_ANALYTICS")
        assert branding is not None

    def test_get_nonexistent_raises(self, tmp_path):
        # SU-1 / ELE-2420: get_client_branding raises (documented contract),
        # it does not return None. Previously asserted `is None`.
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        with pytest.raises(ClientBrandingNotFoundError):
            mgr.get_client_branding("nonexistent_client")


class TestCreateClientBranding:
    """Tests for create_client_branding."""

    def test_create_valid_branding(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {
            "name": "Test Client",
            "colors": {"primary": "#FF0000"},
            "fonts": {"default_font": "Arial"},
        }
        result = mgr.create_client_branding("test_client", config)
        assert result.exists()
        assert result.suffix == ".yaml"

    def test_missing_required_field_raises(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {"name": "Test"}  # missing colors and fonts
        with pytest.raises(ValueError, match="Missing required field"):
            mgr.create_client_branding("test", config)

    def test_created_branding_is_loadable(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {
            "name": "New Client",
            "colors": {"primary": "#123456"},
            "fonts": {"default_font": "Times"},
        }
        mgr.create_client_branding("new_client", config)
        loaded = mgr.get_client_branding("new_client")
        assert loaded is not None
        assert loaded["name"] == "New Client"


class TestValidateBrandingConfig:
    """Tests for validate_branding_config."""

    def test_valid_config(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {
            "name": "Test",
            "colors": {"primary": "#FF0000", "text_color": "#000000"},
            "fonts": {"default_font": "Arial"},
        }
        errors = mgr.validate_branding_config(config)
        assert errors == []

    def test_missing_name(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {"colors": {}, "fonts": {}}
        errors = mgr.validate_branding_config(config)
        assert any("name" in e for e in errors)

    def test_missing_colors(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {"name": "Test", "fonts": {}}
        errors = mgr.validate_branding_config(config)
        assert any("colors" in e for e in errors)

    def test_missing_required_colors(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {
            "name": "Test",
            "colors": {},  # missing primary and text_color
            "fonts": {"default_font": "Arial"},
        }
        errors = mgr.validate_branding_config(config)
        assert any("primary" in e for e in errors)
        assert any("text_color" in e for e in errors)

    def test_missing_default_font(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {
            "name": "Test",
            "colors": {"primary": "#FF0000", "text_color": "#000000"},
            "fonts": {},  # missing default_font
        }
        errors = mgr.validate_branding_config(config)
        assert any("default_font" in e for e in errors)

    def test_logo_missing_image_url(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {
            "name": "Test",
            "colors": {"primary": "#FF0000", "text_color": "#000000"},
            "fonts": {"default_font": "Arial"},
            "logo": {},  # missing image_url
        }
        errors = mgr.validate_branding_config(config)
        assert any("image_url" in e for e in errors)


class TestListClients:
    """Tests for list_clients."""

    def test_includes_predefined(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        clients = mgr.list_clients()
        assert len(clients) >= 3  # at least the 3 templates
        assert any("siege" in c.lower() for c in clients)


class TestDeleteClientBranding:
    """Tests for delete_client_branding."""

    def test_cannot_delete_predefined(self, tmp_path):
        # delete raises ClientBrandingError on a predefined template (SU-1).
        # Previously asserted `is False`.
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        with pytest.raises(ClientBrandingError):
            mgr.delete_client_branding("siege_analytics")

    def test_delete_custom_client(self, tmp_path):
        # delete_client_branding returns None on success (#967 -> None signature);
        # success is verified by the client no longer being retrievable.
        # Previously asserted `is True`.
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        config = {
            "name": "Deletable",
            "colors": {"primary": "#FF0000"},
            "fonts": {"default_font": "Arial"},
        }
        mgr.create_client_branding("deletable", config)
        mgr.delete_client_branding("deletable")
        with pytest.raises(ClientBrandingNotFoundError):
            mgr.get_client_branding("deletable")

    def test_delete_nonexistent_raises(self, tmp_path):
        # delete raises ClientBrandingNotFoundError when nothing exists (SU-1).
        # Previously asserted `is False`.
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        with pytest.raises(ClientBrandingNotFoundError):
            mgr.delete_client_branding("nonexistent_xyz")


class TestCreateBrandingFromTemplate:
    """Tests for create_branding_from_template."""

    def test_from_template(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        result = mgr.create_branding_from_template("New Client", "siege_analytics")
        assert result.exists()

    def test_with_customizations(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        customizations = {"colors": {"primary": "#FF0000"}}
        result = mgr.create_branding_from_template(
            "Custom Client", "siege_analytics", customizations
        )
        assert result.exists()

    def test_invalid_template_raises(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        with pytest.raises(ValueError, match="not found"):
            mgr.create_branding_from_template("Client", "nonexistent_template")


class TestExportBrandingConfig:
    """Tests for export_branding_config."""

    def test_export_yaml(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        export_path = tmp_path / "export.yaml"
        # export_branding_config returns None and raises on failure (#967).
        # Success is verified by the exported file's contents, not a True return.
        mgr.export_branding_config("siege_analytics", export_path)
        assert export_path.exists()
        with open(export_path) as f:
            data = yaml.safe_load(f)
        assert data["name"] == "Siege Analytics"

    def test_export_json(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        export_path = tmp_path / "export.json"
        mgr.export_branding_config("siege_analytics", export_path)
        assert export_path.exists()
        with open(export_path) as f:
            data = json.load(f)
        assert data["name"] == "Siege Analytics"

    def test_export_nonexistent_client(self, tmp_path):
        from siege_utilities.reporting.client_branding import (
            ClientBrandingNotFoundError,
        )

        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        export_path = tmp_path / "export.yaml"
        with pytest.raises(ClientBrandingNotFoundError):
            mgr.export_branding_config("nonexistent", export_path)


class TestGetBrandingSummary:
    """Tests for get_branding_summary."""

    def test_summary_of_predefined(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        summary = mgr.get_branding_summary("siege_analytics")
        assert summary["client_name"] == "Siege Analytics"
        assert "colors" in summary
        assert "fonts" in summary
        assert "has_logo" in summary

    def test_summary_of_nonexistent_raises(self, tmp_path):
        # get_branding_summary delegates to get_client_branding, which raises
        # ClientBrandingNotFoundError for an unknown client (SU-1). Previously
        # asserted `summary == {}`.
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        with pytest.raises(ClientBrandingNotFoundError):
            mgr.get_branding_summary("nonexistent")


class TestImportBrandingConfig:
    """Tests for import_branding_config."""

    def test_import_yaml(self, tmp_path):
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        # Create a valid YAML config file
        config = {
            "name": "Imported Client",
            "colors": {"primary": "#123456", "text_color": "#000000"},
            "fonts": {"default_font": "Arial"},
        }
        import_file = tmp_path / "import.yaml"
        with open(import_file, "w") as f:
            yaml.dump(config, f)
        # import_branding_config returns None and raises on failure (#967).
        # Success is verified by the imported client becoming retrievable.
        mgr.import_branding_config(import_file)
        loaded = mgr.get_client_branding("Imported Client")
        assert loaded["name"] == "Imported Client"

    def test_import_invalid_config_raises(self, tmp_path):
        # Validation failure raises ValueError (documented contract, SU-1).
        # Previously asserted `is False`.
        mgr = ClientBrandingManager(config_dir=tmp_path / "branding")
        import_file = tmp_path / "bad.yaml"
        with open(import_file, "w") as f:
            yaml.dump({"invalid": True}, f)
        with pytest.raises(ValueError, match="Invalid branding configuration"):
            mgr.import_branding_config(import_file)
