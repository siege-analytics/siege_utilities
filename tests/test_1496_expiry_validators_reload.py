"""Expired config models must remain constructible and reloadable (#1496)."""

from datetime import datetime, timedelta

from siege_utilities.config.models.actor_types import Collaboration, Collaborator
from siege_utilities.config.models.credential import Credential
from siege_utilities.config.models.oauth_integration import OAuthIntegration


def test_expired_collaborator_reloads():
    past = datetime.now() - timedelta(days=1)
    collaborator = Collaborator(
        person_id="collaborator",
        name="Test Collaborator",
        email="collaborator@example.com",
        external_organization="Example Organization",
        access_expires=past,
    )
    assert collaborator.is_access_expired() is True

    reloaded = Collaborator.model_validate(collaborator.model_dump())
    assert reloaded.access_expires == past
    assert reloaded.is_access_expired() is True


def test_ended_collaboration_reloads():
    past = datetime.now() - timedelta(days=1)
    collaboration = Collaboration(
        collab_id="collaboration",
        name="Test Collaboration",
        status="active",
        start_date=past - timedelta(days=1),
        end_date=past,
    )
    # Active status isolates the end date as the reason this is inactive.
    assert collaboration.is_active() is False

    reloaded = Collaboration.model_validate(collaboration.model_dump())
    assert reloaded.end_date == past
    assert reloaded.status == "active"
    assert reloaded.is_active() is False


def test_expired_credential_reloads():
    past = datetime.now() - timedelta(days=1)
    credential = Credential(
        name="test-credential",
        credential_type="api_key",
        service="github",
        expires_at=past,
    )
    assert credential.is_expired() is True

    reloaded = Credential.model_validate(credential.model_dump())
    assert reloaded.expires_at == past
    assert reloaded.is_expired() is True


def test_expired_oauth_integration_reloads():
    past = datetime.now() - timedelta(days=1)
    integration = OAuthIntegration(
        name="test-integration",
        provider="github",
        service="github",
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="https://example.com/callback",
        expires_at=past,
    )
    assert integration.is_token_expired() is True

    reloaded = OAuthIntegration.model_validate(integration.model_dump())
    assert reloaded.expires_at == past
    assert reloaded.is_token_expired() is True
