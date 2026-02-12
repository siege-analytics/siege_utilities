"""
Tests for Person/Actor Architecture additions:
- User↔Client bidirectional assignment
- Typed BrandingConfig/ReportPreferences on Client
- YAML round-trip for all models
- Bulk import/export
- HydraConfigManager modern model support
- Deprecation warnings
"""

import pytest
import tempfile
import warnings
import yaml
from pathlib import Path
from datetime import datetime, timedelta

pytestmark = pytest.mark.config

from siege_utilities.config.models.person import Person
from siege_utilities.config.models.actor_types import (
    User, Client, Collaborator, Organization, Collaboration,
)
from siege_utilities.config.models.branding_config import BrandingConfig
from siege_utilities.config.models.report_preferences import ReportPreferences
from siege_utilities.config.models.export import export_entities, import_entities
from siege_utilities.config.hydra_manager import HydraConfigManager


# ============================================================================
# Helpers
# ============================================================================

def make_user(**kw) -> User:
    defaults = dict(
        person_id="dheeraj", name="Dheeraj Chand", email="d@test.com", username="dheeraj"
    )
    defaults.update(kw)
    return User(**defaults)


def make_client(**kw) -> Client:
    defaults = dict(
        person_id="hillcrest", name="Hillcrest Analytics", email="h@test.com",
        client_code="HILL", industry="Technology", project_count=1, client_status="active",
    )
    defaults.update(kw)
    return Client(**defaults)


def make_collaborator(**kw) -> Collaborator:
    defaults = dict(
        person_id="tony", name="Tony Masai", email="t@test.com",
        external_organization="Masai Interactive",
        access_expires=datetime.now() + timedelta(days=365),
    )
    defaults.update(kw)
    return Collaborator(**defaults)


def make_organization(**kw) -> Organization:
    defaults = dict(
        org_id="siege", name="Siege Analytics", org_type="vendor",
        primary_email="info@siege.com",
    )
    defaults.update(kw)
    return Organization(**defaults)


def make_collaboration(**kw) -> Collaboration:
    defaults = dict(
        collab_id="proj1", name="Project Alpha",
        end_date=datetime.now() + timedelta(days=365),
    )
    defaults.update(kw)
    return Collaboration(**defaults)


def make_branding(**kw) -> BrandingConfig:
    defaults = dict(
        primary_color="#1f77b4", secondary_color="#ff7f0e", accent_color="#2ca02c",
        text_color="#000000", background_color="#ffffff",
        primary_font="Arial", secondary_font="Helvetica",
    )
    defaults.update(kw)
    return BrandingConfig(**defaults)


# ============================================================================
# 1. User↔Client Bidirectional Assignment
# ============================================================================

class TestUserClientAssignment:
    """Tests for User.assign_client / Client.assign_user and related methods."""

    def test_user_assign_client(self):
        u = make_user()
        u.assign_client("HILL")
        assert "HILL" in u.assigned_clients
        assert u.has_client("HILL")

    def test_user_assign_client_no_duplicate(self):
        u = make_user()
        u.assign_client("HILL")
        u.assign_client("HILL")
        assert u.assigned_clients.count("HILL") == 1

    def test_user_unassign_client(self):
        u = make_user()
        u.assign_client("HILL")
        result = u.unassign_client("HILL")
        assert result is True
        assert not u.has_client("HILL")

    def test_user_unassign_nonexistent(self):
        u = make_user()
        result = u.unassign_client("NOPE")
        assert result is False

    def test_user_set_primary_client(self):
        u = make_user()
        u.assign_client("HILL")
        u.set_primary_client("HILL")
        assert u.primary_client == "HILL"

    def test_user_set_primary_client_auto_assigns(self):
        u = make_user()
        u.set_primary_client("HILL")
        assert "HILL" in u.assigned_clients
        assert u.primary_client == "HILL"

    def test_user_unassign_clears_primary(self):
        u = make_user()
        u.assign_client("HILL")
        u.set_primary_client("HILL")
        u.unassign_client("HILL")
        assert u.primary_client is None

    def test_user_get_assigned_clients_returns_copy(self):
        u = make_user()
        u.assign_client("HILL")
        clients = u.get_assigned_clients()
        clients.append("FAKE")
        assert "FAKE" not in u.assigned_clients

    def test_user_has_client_false(self):
        u = make_user()
        assert not u.has_client("NOPE")

    def test_user_validator_rejects_duplicate_clients(self):
        with pytest.raises(Exception):
            User(
                person_id="x", name="X", email="x@x.com", username="x",
                assigned_clients=["HILL", "HILL"],
            )

    def test_user_validator_primary_must_be_in_list(self):
        with pytest.raises(Exception):
            User(
                person_id="x", name="X", email="x@x.com", username="x",
                assigned_clients=["HILL"], primary_client="OTHER",
            )

    def test_client_assign_user(self):
        c = make_client()
        c.assign_user("dheeraj")
        assert "dheeraj" in c.assigned_users
        assert c.has_user("dheeraj")

    def test_client_assign_user_no_duplicate(self):
        c = make_client()
        c.assign_user("dheeraj")
        c.assign_user("dheeraj")
        assert c.assigned_users.count("dheeraj") == 1

    def test_client_unassign_user(self):
        c = make_client()
        c.assign_user("dheeraj")
        result = c.unassign_user("dheeraj")
        assert result is True
        assert not c.has_user("dheeraj")

    def test_client_unassign_nonexistent(self):
        c = make_client()
        result = c.unassign_user("nobody")
        assert result is False

    def test_client_set_primary_user(self):
        c = make_client()
        c.assign_user("dheeraj")
        c.set_primary_user("dheeraj")
        assert c.primary_user == "dheeraj"

    def test_client_set_primary_user_auto_assigns(self):
        c = make_client()
        c.set_primary_user("dheeraj")
        assert "dheeraj" in c.assigned_users

    def test_client_unassign_clears_primary(self):
        c = make_client()
        c.set_primary_user("dheeraj")
        c.unassign_user("dheeraj")
        assert c.primary_user is None

    def test_client_get_assigned_users_returns_copy(self):
        c = make_client()
        c.assign_user("dheeraj")
        users = c.get_assigned_users()
        users.append("fake")
        assert "fake" not in c.assigned_users

    def test_client_validator_rejects_duplicate_users(self):
        with pytest.raises(Exception):
            Client(
                person_id="h", name="H", email="h@h.com", client_code="HILL",
                industry="Tech", project_count=0, client_status="active",
                assigned_users=["a", "a"],
            )

    def test_client_validator_primary_must_be_in_list(self):
        with pytest.raises(Exception):
            Client(
                person_id="h", name="H", email="h@h.com", client_code="HILL",
                industry="Tech", project_count=0, client_status="active",
                assigned_users=["a"], primary_user="b",
            )


# ============================================================================
# 2. Typed BrandingConfig / ReportPreferences on Client
# ============================================================================

class TestTypedClientConfig:
    """Tests for typed BrandingConfig/ReportPreferences on Client."""

    def test_client_accepts_branding_model(self):
        bc = make_branding()
        c = make_client(branding_config=bc)
        assert isinstance(c.branding_config, BrandingConfig)
        assert c.branding_config.primary_color == "#1f77b4"

    def test_client_accepts_branding_dict(self):
        c = make_client(branding_config={
            "primary_color": "#1f77b4", "secondary_color": "#ff7f0e",
            "accent_color": "#2ca02c", "text_color": "#000000",
            "background_color": "#ffffff", "primary_font": "Arial",
            "secondary_font": "Helvetica",
        })
        assert isinstance(c.branding_config, BrandingConfig)

    def test_client_accepts_report_prefs_model(self):
        rp = ReportPreferences()
        c = make_client(report_preferences=rp)
        assert isinstance(c.report_preferences, ReportPreferences)

    def test_client_accepts_report_prefs_dict(self):
        c = make_client(report_preferences={"chart_style": "minimal"})
        assert isinstance(c.report_preferences, ReportPreferences)
        assert c.report_preferences.chart_style == "minimal"

    def test_client_none_branding(self):
        c = make_client()
        assert c.branding_config is None

    def test_client_none_report_prefs(self):
        c = make_client()
        assert c.report_preferences is None

    def test_branding_rejects_bad_color(self):
        with pytest.raises(Exception):
            make_branding(primary_color="notahex")

    def test_branding_color_scheme(self):
        bc = make_branding()
        scheme = bc.get_color_scheme()
        assert scheme["primary"] == "#1f77b4"


# ============================================================================
# 3. YAML Round-trip
# ============================================================================

class TestYamlRoundTrip:
    """Tests for to_yaml/from_yaml/to_dict on all model types."""

    def test_user_yaml_roundtrip(self):
        u = make_user()
        yaml_str = u.to_yaml()
        u2 = User.from_yaml(yaml_str)
        assert u2.person_id == u.person_id
        assert u2.username == u.username

    def test_client_yaml_roundtrip(self):
        c = make_client()
        yaml_str = c.to_yaml()
        c2 = Client.from_yaml(yaml_str)
        assert c2.client_code == c.client_code

    def test_collaborator_yaml_roundtrip(self):
        co = make_collaborator()
        yaml_str = co.to_yaml()
        co2 = Collaborator.from_yaml(yaml_str)
        assert co2.external_organization == co.external_organization

    def test_organization_yaml_roundtrip(self):
        org = make_organization()
        yaml_str = org.to_yaml()
        org2 = Organization.from_yaml(yaml_str)
        assert org2.org_id == org.org_id

    def test_collaboration_yaml_roundtrip(self):
        collab = make_collaboration()
        yaml_str = collab.to_yaml()
        collab2 = Collaboration.from_yaml(yaml_str)
        assert collab2.collab_id == collab.collab_id

    def test_yaml_file_roundtrip(self):
        u = make_user()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "user.yaml"
            u.to_yaml(path=path)
            assert path.exists()
            u2 = User.from_yaml(path)
            assert u2.person_id == u.person_id

    def test_yaml_exclude_sensitive(self):
        u = make_user(google_analytics_key="supersecret123")
        safe = u.to_yaml(exclude_sensitive=True)
        assert "supersecret123" not in safe
        assert "REDACTED" in safe

    def test_to_dict(self):
        u = make_user()
        d = u.to_dict()
        assert isinstance(d, dict)
        assert d["person_id"] == "dheeraj"

    def test_to_dict_exclude_sensitive(self):
        u = make_user(google_analytics_key="secret12345")
        d = u.to_dict(exclude_sensitive=True)
        assert d["google_analytics_key"] == "***REDACTED***"

    def test_datetime_serialized_as_string(self):
        u = make_user()
        d = u.to_dict()
        assert isinstance(d["created_date"], str)

    def test_organization_to_dict(self):
        org = make_organization()
        d = org.to_dict()
        assert d["org_id"] == "siege"

    def test_collaboration_to_dict(self):
        collab = make_collaboration()
        d = collab.to_dict()
        assert d["collab_id"] == "proj1"


# ============================================================================
# 4. Bulk Import/Export
# ============================================================================

class TestBulkExportImport:
    """Tests for export_entities/import_entities."""

    def test_export_import_roundtrip(self):
        u = make_user()
        c = make_client()
        org = make_organization()
        collab = make_collaboration()

        yaml_str = export_entities(
            users=[u], clients=[c], organizations=[org], collaborations=[collab]
        )
        result = import_entities(yaml_str)

        assert len(result["users"]) == 1
        assert len(result["clients"]) == 1
        assert len(result["organizations"]) == 1
        assert len(result["collaborations"]) == 1
        assert result["users"][0].person_id == "dheeraj"
        assert result["clients"][0].client_code == "HILL"

    def test_export_partial(self):
        u = make_user()
        yaml_str = export_entities(users=[u])
        result = import_entities(yaml_str)
        assert len(result["users"]) == 1
        assert len(result["clients"]) == 0

    def test_export_empty(self):
        yaml_str = export_entities()
        result = import_entities(yaml_str)
        assert len(result["users"]) == 0

    def test_export_has_version(self):
        yaml_str = export_entities(users=[make_user()])
        data = yaml.safe_load(yaml_str)
        assert data["version"] == "1.0"
        assert "exported_at" in data

    def test_export_exclude_sensitive(self):
        u = make_user(google_analytics_key="secret12345")
        yaml_str = export_entities(users=[u], exclude_sensitive=True)
        assert "secret12345" not in yaml_str

    def test_export_file_roundtrip(self):
        u = make_user()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "entities.yaml"
            export_entities(users=[u], path=path)
            assert path.exists()
            result = import_entities(path)
            assert result["users"][0].person_id == "dheeraj"

    def test_export_multiple_users(self):
        u1 = make_user(person_id="user1", username="user1")
        u2 = make_user(person_id="user2", username="user2")
        yaml_str = export_entities(users=[u1, u2])
        result = import_entities(yaml_str)
        assert len(result["users"]) == 2


# ============================================================================
# 5. HydraConfigManager Modern Model Methods
# ============================================================================

class TestHydraConfigManagerModern:
    """Tests for load_user/load_client/save_user/save_client on HydraConfigManager."""

    @pytest.fixture
    def config_dir(self, tmp_path):
        """Create a minimal config directory for HydraConfigManager."""
        config_dir = tmp_path / "configs"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def manager(self, config_dir):
        return HydraConfigManager(config_dir=config_dir)

    def test_save_and_load_user(self, manager, tmp_path):
        profiles = tmp_path / "profiles" / "users"
        u = make_user()
        assert manager.save_user(u, profiles_dir=profiles) is True
        u2 = manager.load_user("dheeraj", profiles_dir=profiles)
        assert u2 is not None
        assert u2.person_id == "dheeraj"

    def test_save_and_load_client(self, manager, tmp_path):
        profiles = tmp_path / "profiles" / "clients"
        c = make_client()
        assert manager.save_client(c, profiles_dir=profiles) is True
        c2 = manager.load_client("HILL", profiles_dir=profiles)
        assert c2 is not None
        assert c2.client_code == "HILL"

    def test_load_user_not_found(self, manager, tmp_path):
        profiles = tmp_path / "profiles" / "users"
        profiles.mkdir(parents=True)
        result = manager.load_user("nonexistent", profiles_dir=profiles)
        assert result is None

    def test_load_client_not_found(self, manager, tmp_path):
        profiles = tmp_path / "profiles" / "clients"
        profiles.mkdir(parents=True)
        result = manager.load_client("NOPE", profiles_dir=profiles)
        assert result is None

    def test_save_user_creates_directory(self, manager, tmp_path):
        profiles = tmp_path / "new" / "path" / "users"
        u = make_user()
        assert manager.save_user(u, profiles_dir=profiles) is True
        assert profiles.exists()


# ============================================================================
# 6. Deprecation Warnings
# ============================================================================

class TestDeprecationWarnings:
    """Tests for deprecation warnings on legacy entry points."""

    def test_load_user_profile_warns(self):
        from siege_utilities.config.enhanced_config import load_user_profile
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_user_profile("nonexistent")
            assert len(w) >= 1
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_load_client_profile_warns(self):
        from siege_utilities.config.enhanced_config import load_client_profile
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_client_profile("NONEXISTENT")
            assert len(w) >= 1
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_save_user_profile_warns(self):
        from siege_utilities.config.enhanced_config import save_user_profile
        from siege_utilities.config.models import UserProfile
        profile = UserProfile(
            username="test", email="t@t.com", full_name="Test",
            github_login="test", organization="Test Org",
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            save_user_profile(profile, "test", config_dir=Path(tempfile.mkdtemp()))
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) >= 1

    def test_save_client_profile_warns(self):
        from siege_utilities.config.enhanced_config import save_client_profile
        from siege_utilities.config.models import ClientProfile, ContactInfo, BrandingConfig, ReportPreferences
        profile = ClientProfile(
            client_id="test", client_name="Test", client_code="TSTCLT",
            contact_info=ContactInfo(email="t@t.com"),
            industry="Tech", project_count=0, status="active",
            branding_config=BrandingConfig(
                primary_color="#1f77b4", secondary_color="#ff7f0e",
                accent_color="#2ca02c", text_color="#000000",
                background_color="#ffffff", primary_font="Arial",
                secondary_font="Helvetica",
            ),
            report_preferences=ReportPreferences(),
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            save_client_profile(profile, config_dir=Path(tempfile.mkdtemp()))
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) >= 1
