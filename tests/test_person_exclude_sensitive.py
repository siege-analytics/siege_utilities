"""Content regressions for credential redaction across person exports."""

import json
from typing import Any

import pytest
import yaml

from siege_utilities.config.models.actor_types import Client, Collaborator, User
from siege_utilities.config.models.export import export_entities
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from siege_utilities.config.models.person import Person
from siege_utilities.config.models.social_media_account import SocialMediaAccount


SECRETS = (
    "sentinel-oauth-client-secret",
    "sentinel-oauth-access-token",
    "sentinel-oauth-refresh-token",
    "sentinel-social-access-token",
    "sentinel-social-refresh-token",
)


@pytest.fixture
def oauth() -> OAuthIntegration:
    social = SocialMediaAccount(
        platform="instagram",
        account_id="public_account",
        account_name="Public Account",
        access_token=SECRETS[3],
        refresh_token=SECRETS[4],
    )
    return OAuthIntegration(
        name="public-integration",
        provider="google",
        service="analytics",
        client_id="public-client-id",
        client_secret=SECRETS[0],
        access_token=SECRETS[1],
        refresh_token=SECRETS[2],
        redirect_uri="https://example.com/oauth/callback",
        # Person has no social account field; metadata supports nested models.
        metadata={"social_media_accounts": [social]},
    )


@pytest.fixture(params=["user", "client", "collaborator"])
def actor(request: pytest.FixtureRequest, oauth: OAuthIntegration) -> Person:
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
        **fields,
    )


def _export(
    person: Person, surface: str, exclude_sensitive: bool,
) -> tuple[dict[str, Any], str]:
    if surface == "to_dict":
        data = person.to_dict(exclude_sensitive=exclude_sensitive)
        return data, json.dumps(data)
    if surface == "to_yaml":
        text = person.to_yaml(exclude_sensitive=exclude_sensitive)
        return yaml.safe_load(text), text
    group = {User: "users", Client: "clients", Collaborator: "collaborators"}[type(person)]
    text = export_entities(**{group: [person]}, exclude_sensitive=exclude_sensitive)
    return yaml.safe_load(text)["entities"][group][0], text


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml", "export_entities"])
def test_exclude_sensitive_redacts_nested_oauth_and_social_secrets(
    actor: Person, surface: str,
) -> None:
    original_data, original = _export(actor, surface, exclude_sensitive=False)
    assert all(secret in original for secret in SECRETS)

    data, text = _export(actor, surface, exclude_sensitive=True)
    assert [secret for secret in SECRETS if secret in text] == []
    oauth = data["oauth_integrations"][0]
    assert oauth["client_id"] == "public-client-id"
    assert oauth["provider"] == "google"
    assert oauth["redirect_uri"] == "https://example.com/oauth/callback"
    assert oauth["token_type"] == "Bearer"
    social = oauth["metadata"]["social_media_accounts"][0]
    assert social["platform"] == "instagram"
    assert social["account_id"] == "public_account"
    assert social["account_name"] == "Public Account"
    assert [oauth["client_secret"], oauth["access_token"], oauth["refresh_token"],
            social["access_token"], social["refresh_token"]] == ["***REDACTED***"] * 5
    assert _export(actor, surface, exclude_sensitive=False)[0] == original_data


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml"])
def test_person_exclude_sensitive_redacts_nested_secrets(
    oauth: OAuthIntegration, surface: str,
) -> None:
    person = Person(
        person_id="base-person", name="Base Person", email="base@example.com",
        oauth_integrations=[oauth],
    )
    data, text = _export(person, surface, exclude_sensitive=True)
    assert [secret for secret in SECRETS if secret in text] == []
    assert data["oauth_integrations"][0]["client_id"] == "public-client-id"
    assert data["oauth_integrations"][0]["provider"] == "google"


@pytest.mark.parametrize("field", [
    "private_key", "signing_secret", "session_token", "signing_key", "db_password",
])
def test_exclude_sensitive_redacts_secret_suffixes_in_nested_lists(
    oauth: OAuthIntegration, field: str,
) -> None:
    oauth.metadata = {"nested": [[{field: "sentinel-nested-secret", "client_id": "public-id"}]]}
    user = User(
        person_id="nested-user", name="Nested User", email="nested@example.com",
        username="nested_user", oauth_integrations=[oauth],
    )
    data = user.to_dict(exclude_sensitive=True)
    nested = data["oauth_integrations"][0]["metadata"]["nested"][0][0]
    assert nested[field] == "***REDACTED***"
    assert nested["client_id"] == "public-id"
    assert "sentinel-nested-secret" not in json.dumps(data)
