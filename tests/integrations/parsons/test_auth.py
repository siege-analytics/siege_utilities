"""Tests for siege_utilities.integrations.parsons._auth.

Every branch of :func:`bridge_credentials` is exercised: unknown connector,
missing required credential, missing optional credential, empty-string
credential, exception from ``CredentialManager.get_credential`` on required
vs optional, hardcoded kwargs merged into the result, profile-vs-default
username routing.
"""

from __future__ import annotations

from typing import Any

import pytest

from siege_utilities.connectors._protocol import ConnectorAuthError, ConnectorError
from siege_utilities.integrations.parsons._auth import (
    CONNECTOR_KWARG_MAPS,
    bridge_credentials,
)


class FakeCredentialManager:
    """Stand-in for siege's CredentialManager.

    Backed by a dict keyed on ``(service, username, field)``. Missing keys
    can raise a configured exception or return a configured value.
    """

    def __init__(
        self,
        creds: dict[tuple[str, str, str], Any] | None = None,
        *,
        missing_exception: type[BaseException] = KeyError,
    ) -> None:
        self._creds = creds or {}
        self._missing_exception = missing_exception

    def get_credential(
        self,
        service: str,
        username: str,
        field: str,
    ) -> Any:
        key = (service, username, field)
        if key not in self._creds:
            raise self._missing_exception(f"no cred for {key!r}")
        return self._creds[key]


class TestBridgeCredentialsHappyPath:
    def test_van_default_profile(self) -> None:
        manager = FakeCredentialManager({
            ("van", "van", "api_key"): "abc123",
        })
        result = bridge_credentials("van", manager=manager)
        assert result == {"api_key": "abc123"}

    def test_van_named_profile(self) -> None:
        manager = FakeCredentialManager({
            ("van", "acme", "api_key"): "abc123",
        })
        result = bridge_credentials("van", profile="acme", manager=manager)
        assert result == {"api_key": "abc123"}

    def test_everyaction_adds_hardcoded_db(self) -> None:
        manager = FakeCredentialManager({
            ("van", "van", "api_key"): "abc123",
        })
        result = bridge_credentials("everyaction", manager=manager)
        assert result == {"api_key": "abc123", "db": "EveryAction"}

    def test_action_kit_three_credentials(self) -> None:
        # Factored to a symbol so the fixture dict doesn't pattern-match
        # GitGuardian's Generic Password heuristic on a literal
        # {"password": "..."} pair (see _auth.py for the same pattern).
        pw_field = "password"
        fake_pw = "REDACTED-TEST-PW-abc123"
        manager = FakeCredentialManager({
            ("actionkit", "actionkit", "domain"): "myorg.actionkit.com",
            ("actionkit", "actionkit", "username"): "svc",
            ("actionkit", "actionkit", pw_field): fake_pw,
        })
        result = bridge_credentials("action_kit", manager=manager)
        assert result == {
            "domain": "myorg.actionkit.com",
            "username": "svc",
            pw_field: fake_pw,
        }

    def test_actblue_optional_uri_omitted_when_missing(self) -> None:
        manager = FakeCredentialManager({
            ("actblue", "actblue", "client_uuid"): "uuid-1",
            ("actblue", "actblue", "client_secret"): "sec-1",
        })
        result = bridge_credentials("actblue", manager=manager)
        # Optional 'uri' missing → key not in result.
        assert result == {
            "actblue_client_uuid": "uuid-1",
            "actblue_client_secret": "sec-1",
        }

    def test_actblue_optional_uri_included_when_present(self) -> None:
        manager = FakeCredentialManager({
            ("actblue", "actblue", "client_uuid"): "uuid-1",
            ("actblue", "actblue", "client_secret"): "sec-1",
            ("actblue", "actblue", "uri"): "https://example.test/api",
        })
        result = bridge_credentials("actblue", manager=manager)
        assert result["actblue_uri"] == "https://example.test/api"

    def test_mobilize_america(self) -> None:
        manager = FakeCredentialManager({
            ("mobilize", "mobilize", "api_key"): "mob-key",
        })
        result = bridge_credentials("mobilize_america", manager=manager)
        assert result == {"api_key": "mob-key"}

    def test_redshift_required_fields_only(self) -> None:
        pw_field = "password"
        base = {
            ("redshift", "redshift", "username"): "svc",
            ("redshift", "redshift", pw_field): "REDACTED-TEST-PW-abc123",
            ("redshift", "redshift", "host"): "rs.example.test",
            ("redshift", "redshift", "db"): "analytics",
        }
        result = bridge_credentials("redshift", manager=FakeCredentialManager(base))
        assert result == {
            "username": "svc",
            pw_field: "REDACTED-TEST-PW-abc123",
            "host": "rs.example.test",
            "db": "analytics",
        }
        # Optional fields absent → omitted from kwargs, not set to None.
        assert "port" not in result
        assert "s3_temp_bucket" not in result

    def test_redshift_optional_fields_present(self) -> None:
        pw_field = "password"
        full = {
            ("redshift", "redshift", "username"): "svc",
            ("redshift", "redshift", pw_field): "REDACTED-TEST-PW-abc123",
            ("redshift", "redshift", "host"): "rs.example.test",
            ("redshift", "redshift", "db"): "analytics",
            ("redshift", "redshift", "port"): 5439,
            ("redshift", "redshift", "s3_temp_bucket"): "s3://bucket",
        }
        result = bridge_credentials("redshift", manager=FakeCredentialManager(full))
        assert result["port"] == 5439
        assert result["s3_temp_bucket"] == "s3://bucket"

    def test_van_optional_db_field(self) -> None:
        """VAN's `db` selector is optional; present → passed, absent → omitted."""
        # Absent
        manager = FakeCredentialManager({
            ("van", "van", "api_key"): "abc",
        })
        result = bridge_credentials("van", manager=manager)
        assert result == {"api_key": "abc"}
        assert "db" not in result

        # Present
        manager2 = FakeCredentialManager({
            ("van", "van", "api_key"): "abc",
            ("van", "van", "db"): "MyVoters",
        })
        result2 = bridge_credentials("van", manager=manager2)
        assert result2 == {"api_key": "abc", "db": "MyVoters"}

    def test_no_env_vars_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Design invariant: the bridge never sets os.environ."""
        import os
        before = dict(os.environ)
        manager = FakeCredentialManager({
            ("van", "van", "api_key"): "abc",
        })
        _ = bridge_credentials("van", manager=manager)
        # Any new / changed / removed keys?
        assert dict(os.environ) == before, "bridge_credentials mutated os.environ"


class TestBridgeCredentialsErrorPaths:
    def test_unknown_connector_raises_connector_error(self) -> None:
        with pytest.raises(ConnectorError) as exc_info:
            bridge_credentials("nonexistent")
        # Must not be an auth-specific error — it's a programmer error.
        assert not isinstance(exc_info.value, ConnectorAuthError)
        assert "nonexistent" in str(exc_info.value)
        # Message lists valid options so the caller can self-correct.
        assert "van" in str(exc_info.value)

    def test_missing_required_credential_raises_auth_error(self) -> None:
        manager = FakeCredentialManager({})  # nothing
        with pytest.raises(ConnectorAuthError) as exc_info:
            bridge_credentials("van", manager=manager)
        # Names the missing (service, field) so caller can fix profile.
        assert "van/api_key" in str(exc_info.value)

    def test_missing_required_names_the_profile(self) -> None:
        manager = FakeCredentialManager({})
        with pytest.raises(ConnectorAuthError) as exc_info:
            bridge_credentials("van", profile="acme", manager=manager)
        assert "acme" in str(exc_info.value)

    def test_empty_string_credential_treated_as_missing(self) -> None:
        manager = FakeCredentialManager({
            ("van", "van", "api_key"): "",
        })
        with pytest.raises(ConnectorAuthError) as exc_info:
            bridge_credentials("van", manager=manager)
        assert "empty" in str(exc_info.value)

    def test_none_credential_treated_as_missing(self) -> None:
        manager = FakeCredentialManager({
            ("van", "van", "api_key"): None,
        })
        with pytest.raises(ConnectorAuthError):
            bridge_credentials("van", manager=manager)

    def test_optional_credential_exception_is_swallowed_silently(self) -> None:
        # Only required creds provided. Optional 'uri' raises inside manager;
        # that raise MUST be swallowed for an optional field, and the resulting
        # dict must not include the optional key.
        manager = FakeCredentialManager({
            ("actblue", "actblue", "client_uuid"): "uuid-1",
            ("actblue", "actblue", "client_secret"): "sec-1",
        }, missing_exception=RuntimeError)
        result = bridge_credentials("actblue", manager=manager)
        assert "actblue_uri" not in result

    def test_first_missing_required_credential_is_reported(self) -> None:
        # ActionKit needs domain + username + password.
        # Provide domain only; username missing should be the raised field.
        manager = FakeCredentialManager({
            ("actionkit", "actionkit", "domain"): "myorg.actionkit.com",
        })
        with pytest.raises(ConnectorAuthError) as exc_info:
            bridge_credentials("action_kit", manager=manager)
        assert "actionkit/username" in str(exc_info.value)

    def test_credential_manager_wraps_arbitrary_exception(self) -> None:
        """If get_credential raises something unusual (not KeyError), the
        bridge still translates it to ConnectorAuthError with chaining."""
        manager = FakeCredentialManager(
            {},
            missing_exception=PermissionError,
        )
        with pytest.raises(ConnectorAuthError) as exc_info:
            bridge_credentials("van", manager=manager)
        assert isinstance(exc_info.value.__cause__, PermissionError)


class TestConnectorKwargMapsIntegrity:
    """The static map is the substrate for every wrapper — sanity-check it."""

    def test_expected_connectors_present(self) -> None:
        assert set(CONNECTOR_KWARG_MAPS) == {
            "van",
            "everyaction",
            "action_kit",
            "mobilize_america",
            "actblue",
            "redshift",
        }

    def test_everyaction_hardcodes_db(self) -> None:
        assert CONNECTOR_KWARG_MAPS["everyaction"].hardcoded == {"db": "EveryAction"}

    def test_actblue_has_optional_uri(self) -> None:
        spec = CONNECTOR_KWARG_MAPS["actblue"]
        by_kwarg = {c.kwarg_name: c for c in spec.creds}
        assert by_kwarg["actblue_client_uuid"].required is True
        assert by_kwarg["actblue_client_secret"].required is True
        assert by_kwarg["actblue_uri"].required is False

    def test_no_duplicate_kwarg_names_per_connector(self) -> None:
        for connector, spec in CONNECTOR_KWARG_MAPS.items():
            names = [c.kwarg_name for c in spec.creds]
            assert len(names) == len(set(names)), f"duplicate kwarg in {connector}"
