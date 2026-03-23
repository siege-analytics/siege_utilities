"""Tests for GoogleAccount model, GoogleAccountRegistry, Person integration, and factory methods."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from siege_utilities.config.models.google_account import (
    GoogleAccount,
    GoogleAccountStatus,
    GoogleAccountType,
)
from siege_utilities.config.google_account_registry import (
    GoogleAccountRegistry,
    list_google_accounts_for_owner,
    load_google_account_profile,
    migrate_single_account,
    save_google_account_profile,
)


# ── Fixtures ─────────────────────────────────────────────────────


def _make_oauth_account(**overrides):
    defaults = dict(
        google_account_id="111222333",
        email="alice@gmail.com",
        display_name="Alice Personal",
        account_type=GoogleAccountType.OAUTH,
        status=GoogleAccountStatus.ACTIVE,
        oauth_integration_name="google-alice",
    )
    defaults.update(overrides)
    return GoogleAccount(**defaults)


def _make_sa_account(**overrides):
    defaults = dict(
        google_account_id="sa-bot@proj.iam.gserviceaccount.com",
        email="sa-bot@proj.iam.gserviceaccount.com",
        display_name="Automation SA",
        account_type=GoogleAccountType.SERVICE_ACCOUNT,
        status=GoogleAccountStatus.ACTIVE,
        service_account_ref="/secrets/sa.json",
    )
    defaults.update(overrides)
    return GoogleAccount(**defaults)


def _make_person(**overrides):
    from siege_utilities.config.models.person import Person

    defaults = dict(
        person_id="alice",
        name="Alice Smith",
        email="alice@example.com",
    )
    defaults.update(overrides)
    return Person(**defaults)


# ══════════════════════════════════════════════════════════════════
# GoogleAccount model tests
# ══════════════════════════════════════════════════════════════════


class TestGoogleAccountCreation:
    def test_create_oauth_account(self):
        acct = _make_oauth_account()
        assert acct.account_type == GoogleAccountType.OAUTH
        assert acct.is_active()
        assert not acct.is_default

    def test_create_service_account(self):
        acct = _make_sa_account()
        assert acct.account_type == GoogleAccountType.SERVICE_ACCOUNT
        assert acct.service_account_ref == "/secrets/sa.json"

    def test_defaults(self):
        acct = _make_oauth_account()
        assert acct.scopes_granted == []
        assert acct.last_used is None
        assert acct.notes is None

    def test_email_validation_strips_whitespace(self):
        acct = _make_oauth_account(email="  alice@gmail.com  ")
        assert acct.email == "alice@gmail.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(Exception):
            _make_oauth_account(email="not-an-email")

    def test_blank_account_id_rejected(self):
        with pytest.raises(Exception):
            _make_oauth_account(google_account_id="   ")


class TestGoogleAccountValidation:
    def test_oauth_with_service_account_ref_rejected(self):
        with pytest.raises(ValueError, match="OAuth accounts must not set service_account_ref"):
            GoogleAccount(
                google_account_id="x",
                email="x@x.com",
                display_name="X",
                account_type=GoogleAccountType.OAUTH,
                service_account_ref="/some/path",
            )

    def test_sa_with_oauth_integration_rejected(self):
        with pytest.raises(ValueError, match="Service accounts must not set oauth_integration_name"):
            GoogleAccount(
                google_account_id="x",
                email="x@x.com",
                display_name="X",
                account_type=GoogleAccountType.SERVICE_ACCOUNT,
                oauth_integration_name="my-oauth",
            )

    def test_sa_with_token_file_rejected(self):
        with pytest.raises(ValueError, match="Service accounts must not set token_file"):
            GoogleAccount(
                google_account_id="x",
                email="x@x.com",
                display_name="X",
                account_type=GoogleAccountType.SERVICE_ACCOUNT,
                token_file="/some/token.json",
            )


class TestGoogleAccountMethods:
    def test_is_active_true(self):
        assert _make_oauth_account(status=GoogleAccountStatus.ACTIVE).is_active()

    def test_is_active_false(self):
        assert not _make_oauth_account(status=GoogleAccountStatus.REVOKED).is_active()

    def test_update_last_used(self):
        acct = _make_oauth_account()
        assert acct.last_used is None
        acct.update_last_used()
        assert acct.last_used is not None

    def test_get_info_keys(self):
        info = _make_oauth_account().get_info()
        expected_keys = {
            "google_account_id", "email", "display_name", "account_type",
            "status", "is_default", "scopes_granted", "has_oauth_integration",
            "has_service_account_ref", "has_token_file", "created_date",
            "last_used", "notes",
        }
        assert set(info.keys()) == expected_keys


class TestGoogleAccountSerialization:
    def test_json_round_trip(self):
        acct = _make_oauth_account(scopes_granted=["https://www.googleapis.com/auth/spreadsheets"])
        data = acct.model_dump(mode="json")
        restored = GoogleAccount(**data)
        assert restored.google_account_id == acct.google_account_id
        assert restored.scopes_granted == acct.scopes_granted

    def test_sa_json_round_trip(self):
        acct = _make_sa_account()
        data = acct.model_dump(mode="json")
        restored = GoogleAccount(**data)
        assert restored.service_account_ref == acct.service_account_ref


# ══════════════════════════════════════════════════════════════════
# GoogleAccountRegistry tests
# ══════════════════════════════════════════════════════════════════


class TestRegistryCRUD:
    def test_register_and_get(self):
        reg = GoogleAccountRegistry()
        acct = _make_oauth_account()
        reg.register(acct)
        assert reg.get("111222333") is acct

    def test_remove(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        assert reg.remove("111222333")
        assert reg.get("111222333") is None

    def test_remove_nonexistent(self):
        reg = GoogleAccountRegistry()
        assert not reg.remove("nope")

    def test_register_overwrites(self):
        reg = GoogleAccountRegistry()
        acct1 = _make_oauth_account(display_name="V1")
        acct2 = _make_oauth_account(display_name="V2")
        reg.register(acct1)
        reg.register(acct2)
        assert len(reg) == 1
        assert reg.get("111222333").display_name == "V2"

    def test_contains(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        assert "111222333" in reg
        assert "nope" not in reg


class TestRegistryDefault:
    def test_single_default(self):
        reg = GoogleAccountRegistry()
        a1 = _make_oauth_account(is_default=True)
        a2 = _make_sa_account(is_default=True)
        reg.register(a1)
        reg.register(a2)
        # a2 was registered last with is_default=True, so a1 demoted
        assert not a1.is_default
        assert reg.get_default() is a2

    def test_set_default(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        reg.register(_make_sa_account())
        reg.set_default("111222333")
        assert reg.get_default().google_account_id == "111222333"

    def test_set_default_not_found(self):
        reg = GoogleAccountRegistry()
        with pytest.raises(ValueError, match="not found"):
            reg.set_default("nope")

    def test_get_default_none(self):
        reg = GoogleAccountRegistry()
        assert reg.get_default() is None

    def test_remove_default_promotes_another(self):
        reg = GoogleAccountRegistry()
        a1 = _make_oauth_account(is_default=True)
        a2 = _make_sa_account(is_default=False)
        reg.register(a1)
        reg.register(a2)
        assert reg.remove(a1.google_account_id)
        default = reg.get_default()
        assert default is not None
        assert default.google_account_id == a2.google_account_id


class TestRegistryListing:
    def test_list_accounts(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        reg.register(_make_sa_account())
        assert len(reg.list_accounts()) == 2

    def test_list_by_status(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        reg.register(_make_sa_account(status=GoogleAccountStatus.REVOKED))
        assert len(reg.list_accounts(status=GoogleAccountStatus.ACTIVE)) == 1

    def test_list_active(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        reg.register(_make_sa_account(status=GoogleAccountStatus.EXPIRED))
        active = reg.list_active()
        assert len(active) == 1

    def test_list_by_type(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        reg.register(_make_sa_account())
        assert len(reg.list_by_type(GoogleAccountType.OAUTH)) == 1
        assert len(reg.list_by_type(GoogleAccountType.SERVICE_ACCOUNT)) == 1

    def test_get_by_email(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())
        assert reg.get_by_email("alice@gmail.com") is not None
        assert reg.get_by_email("nobody@example.com") is None


class TestRegistryPersistence:
    def test_json_round_trip(self, tmp_path):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account(is_default=True))
        reg.register(_make_sa_account())

        path = tmp_path / "google_accounts.json"
        reg.save(path)

        reg2 = GoogleAccountRegistry(config_path=path)
        assert len(reg2) == 2
        assert reg2.get("111222333") is not None
        assert reg2.get("111222333").is_default

    def test_load_nonexistent(self, tmp_path):
        reg = GoogleAccountRegistry()
        reg.load(tmp_path / "nope.json")
        assert len(reg) == 0


# ── Module-level convenience functions ───────────────────────────


class TestConvenienceFunctions:
    def test_save_and_load_profile(self, tmp_path):
        acct = _make_oauth_account()
        path = save_google_account_profile(acct, "alice", str(tmp_path))
        assert Path(path).exists()

        loaded = load_google_account_profile("alice", "111222333", str(tmp_path))
        assert loaded is not None
        assert loaded.google_account_id == "111222333"

    def test_load_missing_profile(self, tmp_path):
        assert load_google_account_profile("alice", "nope", str(tmp_path)) is None

    def test_list_for_owner(self, tmp_path):
        save_google_account_profile(_make_oauth_account(), "alice", str(tmp_path))
        save_google_account_profile(_make_sa_account(), "alice", str(tmp_path))

        accounts = list_google_accounts_for_owner("alice", str(tmp_path))
        assert len(accounts) == 2


# ══════════════════════════════════════════════════════════════════
# Person integration tests
# ══════════════════════════════════════════════════════════════════


class TestPersonGoogleAccounts:
    def test_add_and_get(self):
        person = _make_person()
        acct = _make_oauth_account()
        person.add_google_account(acct)
        assert person.get_google_account("111222333") is acct

    def test_add_duplicate_rejected(self):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        with pytest.raises(ValueError, match="already exists"):
            person.add_google_account(_make_oauth_account())

    def test_remove(self):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        assert person.remove_google_account("111222333")
        assert person.get_google_account("111222333") is None

    def test_remove_nonexistent(self):
        person = _make_person()
        assert not person.remove_google_account("nope")

    def test_get_by_email(self):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        assert person.get_google_account_by_email("alice@gmail.com") is not None
        assert person.get_google_account_by_email("nope@x.com") is None

    def test_default_enforcement(self):
        person = _make_person()
        a1 = _make_oauth_account(is_default=True)
        a2 = _make_sa_account(is_default=True)
        person.add_google_account(a1)
        person.add_google_account(a2)
        # a2 added last with is_default=True, so a1 demoted
        assert not a1.is_default
        assert person.get_default_google_account() is a2

    def test_first_non_default_auto_promoted(self):
        person = _make_person()
        a1 = _make_oauth_account(is_default=False)
        person.add_google_account(a1)
        default = person.get_default_google_account()
        assert default is not None
        assert default.google_account_id == a1.google_account_id

    def test_remove_default_promotes_another(self):
        person = _make_person()
        a1 = _make_oauth_account(is_default=True)
        a2 = _make_sa_account(is_default=False)
        person.add_google_account(a1)
        person.add_google_account(a2)
        assert person.remove_google_account(a1.google_account_id)
        default = person.get_default_google_account()
        assert default is not None
        assert default.google_account_id == a2.google_account_id

    def test_set_default(self):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        person.add_google_account(_make_sa_account())
        person.set_default_google_account("111222333")
        assert person.get_default_google_account().google_account_id == "111222333"

    def test_set_default_not_found(self):
        person = _make_person()
        with pytest.raises(ValueError, match="not found"):
            person.set_default_google_account("nope")

    def test_list_active_only(self):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        person.add_google_account(_make_sa_account(
            google_account_id="revoked@x.com",
            email="revoked@x.com",
            status=GoogleAccountStatus.REVOKED,
        ))
        assert len(person.list_google_accounts(active_only=True)) == 1
        assert len(person.list_google_accounts(active_only=False)) == 2

    def test_get_summary_includes_google_accounts(self):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        summary = person.get_summary()
        assert "google_accounts" in summary
        assert summary["google_accounts"] == 1

    def test_get_credential_coverage_includes_google_accounts(self):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        coverage = person.get_credential_coverage()
        assert "google_accounts" in coverage
        assert coverage["google_accounts"]["total"] == 1


class TestPersonYAMLRoundTrip:
    def test_yaml_round_trip_with_google_accounts(self, tmp_path):
        person = _make_person()
        person.add_google_account(_make_oauth_account())
        person.add_google_account(_make_sa_account())

        yaml_path = tmp_path / "person.yaml"
        person.to_yaml(path=yaml_path)

        from siege_utilities.config.models.person import Person
        restored = Person.from_yaml(yaml_path)
        assert len(restored.google_accounts) == 2
        assert restored.get_google_account("111222333") is not None


# ══════════════════════════════════════════════════════════════════
# GoogleWorkspaceClient factory tests
# ══════════════════════════════════════════════════════════════════


class TestFromAccount:
    def test_from_account_service_account_file(self, tmp_path):
        sa_file = tmp_path / "sa.json"
        sa_file.write_text(json.dumps({
            "type": "service_account",
            "project_id": "test",
            "private_key_id": "k1",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "sa@proj.iam.gserviceaccount.com",
            "client_id": "123",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }))

        acct = _make_sa_account(service_account_ref=str(sa_file))

        with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True), \
             patch("siege_utilities.analytics.google_workspace.service_account") as mock_sa, \
             patch("siege_utilities.analytics.google_workspace.build"):
            mock_creds = MagicMock()
            mock_sa.Credentials.from_service_account_file.return_value = mock_creds

            from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
            client = GoogleWorkspaceClient.from_account(acct)
            assert client._credentials is mock_creds

    def test_from_account_oauth_no_creds_raises(self):
        acct = _make_oauth_account(token_file=None, oauth_integration_name=None)
        with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True):
            from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
            with pytest.raises(ValueError, match="Cannot resolve credentials"):
                GoogleWorkspaceClient.from_account(acct)

    def test_from_account_service_account_ref_title(self):
        acct = _make_sa_account(
            service_account_ref="My Specific 1Password SA Item"
        )

        with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True), \
             patch("siege_utilities.analytics.google_workspace.service_account") as mock_sa, \
             patch("siege_utilities.analytics.google_workspace.build"), \
             patch(
                 "siege_utilities.config.credential_manager.get_google_service_account_from_1password"
             ) as mock_1p:
            mock_creds = MagicMock()
            mock_sa.Credentials.from_service_account_info.return_value = mock_creds
            mock_1p.return_value = {"type": "service_account", "client_email": "sa@example.com"}

            from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
            client = GoogleWorkspaceClient.from_account(acct)
            assert client._credentials is mock_creds
            mock_1p.assert_called_once_with(
                item_title="My Specific 1Password SA Item"
            )

    def test_from_account_oauth_with_person(self):
        from siege_utilities.config.models.oauth_integration import (
            OAuthIntegration,
            OAuthProvider,
        )

        person = _make_person()
        integration = OAuthIntegration(
            name="google-alice",
            provider=OAuthProvider.GOOGLE,
            service="google-workspace",
            client_id="a" * 20,
            client_secret="b" * 20,
            redirect_uri="http://localhost:8080/callback",
        )
        person.add_oauth_integration(integration)

        acct = _make_oauth_account(token_file=None)

        with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True), \
             patch("siege_utilities.analytics.google_workspace.InstalledAppFlow") as mock_flow_cls, \
             patch("siege_utilities.analytics.google_workspace.build"):
            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_flow = MagicMock()
            mock_flow.run_local_server.return_value = mock_creds
            mock_flow_cls.from_client_config.return_value = mock_flow

            from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
            client = GoogleWorkspaceClient.from_account(acct, person=person)
            assert client._credentials is mock_creds


class TestFromRegistry:
    def test_from_registry_default(self):
        reg = GoogleAccountRegistry()
        acct = _make_sa_account(is_default=True, service_account_ref=None)
        reg.register(acct)

        with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True), \
             patch("siege_utilities.analytics.google_workspace.build"):
            from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

            # Service account with no ref falls through to 1Password
            with patch(
                "siege_utilities.config.credential_manager.get_google_service_account_from_1password"
            ) as mock_1p, \
                 patch("siege_utilities.analytics.google_workspace.service_account") as mock_sa:
                mock_creds = MagicMock()
                mock_sa.Credentials.from_service_account_info.return_value = mock_creds
                mock_1p.return_value = {"type": "service_account"}

                client = GoogleWorkspaceClient.from_registry(reg)
                assert client._credentials is mock_creds

    def test_from_registry_not_found(self):
        reg = GoogleAccountRegistry()
        with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True):
            from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
            with pytest.raises(ValueError, match="No Google account"):
                GoogleWorkspaceClient.from_registry(reg, google_account_id="nope")

    def test_from_registry_no_default(self):
        reg = GoogleAccountRegistry()
        reg.register(_make_oauth_account())  # not default
        with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True):
            from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
            with pytest.raises(ValueError, match="No Google account"):
                GoogleWorkspaceClient.from_registry(reg)


# ══════════════════════════════════════════════════════════════════
# Migration utility tests
# ══════════════════════════════════════════════════════════════════


class TestMigration:
    def test_migrate_single_account(self):
        from siege_utilities.config.models.oauth_integration import (
            OAuthIntegration,
            OAuthProvider,
            OAuthScope,
        )

        integration = OAuthIntegration(
            name="google-alice",
            provider=OAuthProvider.GOOGLE,
            service="google-workspace",
            client_id="c" * 20,
            client_secret="d" * 20,
            redirect_uri="http://localhost:8080/callback",
            scopes=[OAuthScope.READ, OAuthScope.WRITE],
        )

        acct = migrate_single_account(
            integration,
            google_account_id="111222333",
            email="alice@gmail.com",
            display_name="Alice",
        )

        assert acct.google_account_id == "111222333"
        assert acct.oauth_integration_name == "google-alice"
        assert acct.account_type == GoogleAccountType.OAUTH
        assert "read" in acct.scopes_granted
        assert "write" in acct.scopes_granted
        assert acct.created_date == integration.created_date
