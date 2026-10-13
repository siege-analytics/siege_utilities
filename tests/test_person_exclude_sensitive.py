"""Content regressions for credential redaction across person exports.

These tests exercise the real nested credential models reachable from every
User/Client/Collaborator export surface (to_dict, to_yaml, export_entities):

* OAuthIntegration (Person.oauth_integrations): client_secret, access_token,
  refresh_token.
* Credential (Person.credentials): password, api_key, token, secret.
* DatabaseConnection (Person.database_connections): password.

User subclasses exercise additional model fields, including SocialMediaAccount
and UserProfile, without changing the base Person schema.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, create_model
import pytest
import yaml

from siege_utilities.config.models.actor_types import Client, Collaborator, User
from siege_utilities.config.models.credential import Credential, CredentialType
from siege_utilities.config.models.database_connection import DatabaseConnection
from siege_utilities.config.models.export import export_entities, import_entities
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from siege_utilities.config.models.person import Person
from siege_utilities.config.models.social_media_account import SocialMediaAccount
from siege_utilities.config.models.user_profile import UserProfile


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
    group = next(
        group for model, group in ((User, "users"), (Client, "clients"), (Collaborator, "collaborators"))
        if isinstance(person, model)
    )
    text = export_entities(**{group: [person]}, exclude_sensitive=exclude_sensitive)
    return yaml.safe_load(text)["entities"][group][0], text


ALL_SURFACES = ["to_dict", "to_yaml", "export_entities"]
SECRET_NAMES = (
    "webhook_secret", "bot_token", "signing_key", "api_keys",
    "connection_string", "connectionString", "passphrase", "apikey", "apiKey",
    "privateKey", "passwd", "pwd", "dsn",
)


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
        "token_type": "Bearer",
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


@pytest.mark.parametrize("surface", ALL_SURFACES)
@pytest.mark.parametrize("marked", [True, False], ids=["marked", "unmarked"])
@pytest.mark.parametrize("name", SECRET_NAMES)
def test_subclass_secret_fields_are_redacted(surface: str, marked: bool, name: str) -> None:
    """New subclass fields cannot leak, even when their markers are missing."""
    policy = {"json_schema_extra": {"sensitive": True}} if marked else {}
    extended_user = create_model(
        "WebhookUser", __base__=User,
        **{name: (str, Field(**policy))},
    )
    person = extended_user(
        person_id="webhook-user", name="Webhook User", email="webhook@example.com",
        username="webhook_user", **{name: "sentinel-secret"},
    )
    original, _ = _export(person, surface, exclude_sensitive=False)
    data, text = _export(person, surface, exclude_sensitive=True)
    assert data[name] == "***REDACTED***"
    assert "sentinel-" not in text
    assert _export(person, surface, exclude_sensitive=False)[0] == original


@pytest.mark.parametrize("surface", ALL_SURFACES)
@pytest.mark.parametrize("name", [
    "public_key", "partition_key", "sort_key", "cache_key", "idempotency_key", "token_type",
])
def test_subclass_public_fields_survive_name_floor(surface: str, name: str) -> None:
    extended_user = create_model("PublicUser", __base__=User, **{name: (str, ...)})
    person = extended_user(
        person_id="public-user", name="Public User", email="public@example.com",
        username="public_user", **{name: "public-value"},
    )
    data, text = _export(person, surface, exclude_sensitive=True)
    assert data[name] == "public-value"
    assert "public-value" in text


@pytest.mark.parametrize("surface", ALL_SURFACES)
def test_marked_fields_redacted_in_nested_model_subclasses(surface: str, oauth: OAuthIntegration) -> None:
    """Markers on runtime types work even for names with no secret suffix."""
    class ExtendedOAuth(OAuthIntegration):
        material: str = Field(json_schema_extra={"sensitive": True})

    class Envelope(BaseModel):
        payload: str = Field(json_schema_extra={"sensitive": True})
        label: str

    integration = ExtendedOAuth(**oauth.model_dump(), material="sentinel-material")
    integration.metadata = {"items": [{"envelope": Envelope(payload="sentinel-payload", label="public")}]}
    person = User(
        person_id="nested-user", name="Nested User", email="nested@example.com",
        username="nested_user", oauth_integrations=[integration],
    )
    data, text = _export(person, surface, exclude_sensitive=True)
    exported = data["oauth_integrations"][0]
    assert exported["material"] == "***REDACTED***"
    assert exported["metadata"]["items"][0]["envelope"] == {
        "payload": "***REDACTED***", "label": "public",
    }
    assert "sentinel-" not in text
    assert integration.material == "sentinel-material"


@pytest.mark.parametrize("surface", ALL_SURFACES)
def test_social_media_tokens_marked_and_redacted(surface: str, oauth: OAuthIntegration) -> None:
    """A User holding OAuth and social accounts redacts both model types."""
    class SocialUser(User):
        social_media_accounts: list[SocialMediaAccount]

    account = SocialMediaAccount(
        platform="twitter", account_id="export_user", account_name="Public Account",
        access_token="sentinel-social-access-token", refresh_token="sentinel-social-refresh-token",
    )
    person = SocialUser(
        person_id="social-user", name="Social User", email="social@example.com",
        username="social_user", oauth_integrations=[oauth], social_media_accounts=[account],
    )
    data, text = _export(person, surface, exclude_sensitive=True)
    assert "sentinel-social-" not in text
    assert not any(secret in text for secret in OAUTH_SECRETS)
    assert data["social_media_accounts"][0]["access_token"] == "***REDACTED***"
    assert data["social_media_accounts"][0]["refresh_token"] == "***REDACTED***"
    assert data["social_media_accounts"][0]["account_name"] == "Public Account"
    assert SocialMediaAccount.model_fields["access_token"].json_schema_extra == {"sensitive": True}
    assert SocialMediaAccount.model_fields["refresh_token"].json_schema_extra == {"sensitive": True}
    assert account.access_token == "sentinel-social-access-token"


@pytest.mark.parametrize("surface", ALL_SURFACES)
def test_user_and_profile_secrets_redacted(surface: str) -> None:
    class ProfileUser(User):
        profile: UserProfile

    secrets = {
        "google_analytics_key": "sentinel-google-key", "facebook_business_key": "sentinel-facebook-key",
        "census_api_key": "sentinel-census-key", "postgresql_connection": "sentinel-postgres-dsn",
        "duckdb_path": "sentinel-duckdb-path",
    }
    profile = UserProfile(username="profile_user", email="profile@example.com", **secrets)
    person = ProfileUser(
        person_id="profile-user", name="Profile User", email="profile@example.com",
        username="profile_user", profile=profile, **secrets,
    )
    original, _ = _export(person, surface, exclude_sensitive=False)
    data, text = _export(person, surface, exclude_sensitive=True)
    assert {name: data[name] for name in secrets} == dict.fromkeys(secrets, "***REDACTED***")
    assert {name: data["profile"][name] for name in secrets} == dict.fromkeys(secrets, "***REDACTED***")
    assert "sentinel-" not in text
    assert _export(person, surface, exclude_sensitive=False)[0] == original


@pytest.mark.parametrize("surface", ALL_SURFACES)
@pytest.mark.parametrize("name", SECRET_NAMES)
def test_metadata_secret_names_redacted_recursively(actor: Person, surface: str, name: str) -> None:
    actor.oauth_integrations[0].metadata = {
        "items": [{"api_secret": "sentinel-api-secret", "nested": {
            "bot_token": "sentinel-bot-token", "signing_key": "sentinel-signing-key",
            "public_key": "public", "token_type": "Bearer",
            name: "sentinel-secret",
        }}],
    }
    data, text = _export(actor, surface, exclude_sensitive=True)
    assert "sentinel-secret" not in text
    assert "sentinel-" not in json.dumps(data["oauth_integrations"][0]["metadata"])
    assert data["oauth_integrations"][0]["metadata"] == {
        "items": [{"api_secret": "***REDACTED***", "nested": {
            "bot_token": "***REDACTED***", "signing_key": "***REDACTED***",
            "public_key": "public", "token_type": "Bearer",
            name: "***REDACTED***",
        }}],
    }


@pytest.mark.parametrize("surface", ["from_yaml", "import_entities"])
@pytest.mark.parametrize("source_kind", ["text", "path", "path_string"])
@pytest.mark.parametrize("location", ["user_key", "oauth", "credential", "database"])
def test_redacted_import_raises(
    surface: str, source_kind: str, location: str, tmp_path: Path,
    oauth: OAuthIntegration, credential: Credential, database_connection: DatabaseConnection,
) -> None:
    """Reject placeholders before validation can accept them as credentials."""
    fields = {
        "user_key": {"census_api_key": "sentinel-census-key"},
        "oauth": {"oauth_integrations": [oauth]},
        "credential": {"credentials": [credential]},
        "database": {"database_connections": [database_connection]},
    }[location]
    person = User(
        person_id="import-user", name="Import User", email="import@example.com",
        username="import_user", **fields,
    )
    export = person.to_yaml if surface == "from_yaml" else lambda **kw: export_entities(users=[person], **kw)
    restore = User.from_yaml if surface == "from_yaml" else import_entities
    original = person.model_dump()
    redacted = export(exclude_sensitive=True)
    path = tmp_path / "redacted.yaml"
    path.write_text(redacted)
    source = {"text": redacted, "path": path, "path_string": str(path)}[source_kind]
    with pytest.raises(ValueError, match="Cannot import redacted values.*use an unredacted export"):
        restore(source)
    restored = restore(export(exclude_sensitive=False))
    restored_user = restored if surface == "from_yaml" else restored["users"][0]
    assert restored_user.model_dump() == original
    assert person.model_dump() == original


@pytest.mark.parametrize("surface", ["from_yaml", "import_entities"])
def test_nested_metadata_redacted_import_raises(surface: str, oauth: OAuthIntegration) -> None:
    """Scan all dict/list values, including placeholders outside model fields."""
    oauth.metadata = {"items": [{"value": " ***REDACTED*** "}]}
    person = User(
        person_id="metadata-user", name="Metadata User", email="metadata@example.com",
        username="metadata_user", oauth_integrations=[oauth],
    )
    source = person.to_yaml() if surface == "from_yaml" else export_entities(users=[person])
    restore = User.from_yaml if surface == "from_yaml" else import_entities
    with pytest.raises(ValueError, match="Cannot import redacted values"):
        restore(source)
