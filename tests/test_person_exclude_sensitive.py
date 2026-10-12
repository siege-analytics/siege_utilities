"""Content regressions for credential redaction across person exports.

These tests exercise the real nested credential models reachable from every
User/Client/Collaborator export surface (to_dict, to_yaml, export_entities):

* OAuthIntegration (Person.oauth_integrations): client_secret, access_token,
  refresh_token.
* Credential (Person.credentials): password, api_key, token, secret.
* DatabaseConnection (Person.database_connections): password.

SocialMediaAccount is intentionally not exercised here: its only holder is
ClientProfile.social_media_accounts, and ClientProfile is a plain BaseModel
with no exclude_sensitive export path and is not nested in
User/Client/Collaborator/Person. Its presence in the redaction logic is
defensive-only and unreachable from these entity export surfaces.
"""

import json
from typing import Any

import pytest
import yaml

from siege_utilities.config.models.actor_types import Client, Collaborator, User
from siege_utilities.config.models.credential import Credential, CredentialType
from siege_utilities.config.models.database_connection import DatabaseConnection
from siege_utilities.config.models.export import export_entities
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from siege_utilities.config.models.person import Person


# Secret sentinel values. Each appears only in a declared credential field so
# that "no sentinel survives" assertions are unambiguous.
OAUTH_SECRETS = (
    "s3cret-oauth-clientsecret",
    "s3cret-oauth-accesstoken",
    "s3cret-oauth-refreshtoken",
)
CRED_SECRETS = (
    "s3cret-cred-password",
    "s3cret-cred-apikey99",
    "s3cret-cred-token",
    "s3cret-cred-secret",
)
DB_SECRET = "S3cretDbPassword9"


@pytest.fixture
def oauth() -> OAuthIntegration:
    return OAuthIntegration(
        name="public-integration",
        provider="google",
        service="analytics",
        client_id="public-client-id",
        client_secret=OAUTH_SECRETS[0],
        access_token=OAUTH_SECRETS[1],
        refresh_token=OAUTH_SECRETS[2],
        redirect_uri="https://example.com/oauth/callback",
    )


@pytest.fixture
def credential() -> Credential:
    return Credential(
        name="cred_public_name",
        credential_type=CredentialType.API_KEY,
        service="analytics",
        password=CRED_SECRETS[0],
        api_key=CRED_SECRETS[1],
        token=CRED_SECRETS[2],
        secret=CRED_SECRETS[3],
    )


@pytest.fixture
def database_connection() -> DatabaseConnection:
    return DatabaseConnection(
        name="sentinel-db",
        connection_type="postgresql",
        host="db.example.com",
        port=5432,
        database="analyticsdb",
        username="public_db_user",
        password=DB_SECRET,
    )


@pytest.fixture(params=["user", "client", "collaborator"])
def actor(
    request: pytest.FixtureRequest,
    oauth: OAuthIntegration,
    credential: Credential,
    database_connection: DatabaseConnection,
) -> Person:
    model, fields = {
        "user": (User, {"username": "export_user"}),
        "client": (Client, {
            "client_code": "EXPORT", "industry": "Analytics",
            "project_count": 0, "client_status": "active",
        }),
        "collaborator": (Collaborator, {"external_organization": "Partner"}),
    }[request.param]
    return model(
        person_id="export-person",
        name="Export Person",
        email="export@example.com",
        oauth_integrations=[oauth],
        credentials=[credential],
        database_connections=[database_connection],
        **fields,
    )


def _export(
    person: Person, surface: str, exclude_sensitive: bool,
) -> tuple[dict[str, Any], str]:
    """Return (parsed_entity_dict, raw_text) for a given export surface."""
    if surface == "to_dict":
        data = person.to_dict(exclude_sensitive=exclude_sensitive)
        return data, json.dumps(data)
    if surface == "to_yaml":
        text = person.to_yaml(exclude_sensitive=exclude_sensitive)
        return yaml.safe_load(text), text
    group = {User: "users", Client: "clients", Collaborator: "collaborators"}[type(person)]
    text = export_entities(**{group: [person]}, exclude_sensitive=exclude_sensitive)
    return yaml.safe_load(text)["entities"][group][0], text


ALL_SURFACES = ["to_dict", "to_yaml", "export_entities"]


@pytest.mark.parametrize("surface", ALL_SURFACES)
def test_exclude_sensitive_redacts_oauth_secrets(actor: Person, surface: str) -> None:
    """OAuthIntegration secrets are redacted; public fields survive."""
    original_data, original = _export(actor, surface, exclude_sensitive=False)
    assert all(secret in original for secret in OAUTH_SECRETS)

    data, text = _export(actor, surface, exclude_sensitive=True)
    assert [s for s in OAUTH_SECRETS if s in text] == []
    out_oauth = data["oauth_integrations"][0]
    assert out_oauth["client_secret"] == "***REDACTED***"
    assert out_oauth["access_token"] == "***REDACTED***"
    assert out_oauth["refresh_token"] == "***REDACTED***"
    # Public identifiers and provider configuration remain available.
    assert out_oauth["client_id"] == "public-client-id"
    assert out_oauth["provider"] == "google"
    assert out_oauth["redirect_uri"] == "https://example.com/oauth/callback"
    assert out_oauth["token_type"] == "Bearer"
    # Non-sensitive export is unchanged by a subsequent redacting pass.
    assert _export(actor, surface, exclude_sensitive=False)[0] == original_data


@pytest.mark.parametrize("surface", ALL_SURFACES)
def test_exclude_sensitive_redacts_person_credentials(actor: Person, surface: str) -> None:
    """Person.credentials (Credential) secrets are redacted; metadata-free
    public fields survive, on every export surface."""
    original_data, original = _export(actor, surface, exclude_sensitive=False)
    assert all(secret in original for secret in CRED_SECRETS)

    data, text = _export(actor, surface, exclude_sensitive=True)
    assert [s for s in CRED_SECRETS if s in text] == []
    cred = data["credentials"][0]
    assert cred["password"] == "***REDACTED***"
    assert cred["api_key"] == "***REDACTED***"
    assert cred["token"] == "***REDACTED***"
    assert cred["secret"] == "***REDACTED***"
    # Non-secret fields survive redaction.
    assert cred["name"] == "cred_public_name"
    assert cred["service"] == "analytics"
    assert cred["credential_type"] == "api_key"


@pytest.mark.parametrize("surface", ALL_SURFACES)
def test_exclude_sensitive_redacts_person_database_connections(
    actor: Person, surface: str,
) -> None:
    """Person.database_connections (DatabaseConnection) password is redacted;
    host/username/database survive, on every export surface."""
    original_data, original = _export(actor, surface, exclude_sensitive=False)
    assert DB_SECRET in original

    data, text = _export(actor, surface, exclude_sensitive=True)
    assert DB_SECRET not in text
    conn = data["database_connections"][0]
    assert conn["password"] == "***REDACTED***"
    # Non-secret connection fields survive redaction.
    assert conn["name"] == "sentinel-db"
    assert conn["host"] == "db.example.com"
    assert conn["username"] == "public_db_user"
    assert conn["database"] == "analyticsdb"


@pytest.mark.parametrize("surface", ALL_SURFACES)
def test_exclude_sensitive_preserves_free_form_metadata_keys(
    actor: Person, surface: str,
) -> None:
    """Free-form Dict[str, Any] metadata keys that merely look secret by
    suffix (public_key, partition_key, cache_key, sort_key, idempotency_key)
    round-trip UNREDACTED, while a real declared secret is still redacted."""
    legit_metadata = {
        "public_key": "pub-abc123",
        "partition_key": "part-def456",
        "cache_key": "cache-ghi789",
        "sort_key": "sort-jkl012",
        "idempotency_key": "idem-mno345",
    }
    actor.oauth_integrations[0].metadata = dict(legit_metadata)

    data, text = _export(actor, surface, exclude_sensitive=True)
    out_oauth = data["oauth_integrations"][0]
    # Free-form metadata is preserved exactly (no over-redaction).
    assert out_oauth["metadata"] == legit_metadata
    for value in legit_metadata.values():
        assert value in text
    # The real OAuth secret in a declared field is still redacted.
    assert out_oauth["client_secret"] == "***REDACTED***"
    assert out_oauth["access_token"] == "***REDACTED***"
    assert [s for s in OAUTH_SECRETS if s in text] == []


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml"])
def test_base_person_exclude_sensitive_redacts_nested_secrets(
    oauth: OAuthIntegration,
    credential: Credential,
    database_connection: DatabaseConnection,
    surface: str,
) -> None:
    """Base Person (not a User/Client/Collaborator subclass) redacts nested
    OAuth, Credential, and DatabaseConnection secrets via to_dict/to_yaml."""
    person = Person(
        person_id="base-person", name="Base Person", email="base@example.com",
        oauth_integrations=[oauth], credentials=[credential],
        database_connections=[database_connection],
    )
    data, text = _export(person, surface, exclude_sensitive=True)
    all_secrets = (*OAUTH_SECRETS, *CRED_SECRETS, DB_SECRET)
    assert [s for s in all_secrets if s in text] == []
    assert data["oauth_integrations"][0]["client_id"] == "public-client-id"
    assert data["credentials"][0]["service"] == "analytics"
    assert data["database_connections"][0]["host"] == "db.example.com"
