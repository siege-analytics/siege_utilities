"""Far-future and range-edge expiry values outside UTC (#1496).

A naive expiry such as ``datetime.max`` or ``datetime(9999, 12, 31, 23, 59, 59)``
is a conventional "never expires" value. Converting it from local time to UTC
leaves the supported datetime range in any zone east or west of UTC, so these
checks pin the process timezone to non-UTC zones. CI runs in UTC, where the
conversion never overflows.
"""

import time
from datetime import datetime, timedelta

import pytest

from siege_utilities.config.models.actor_types import Collaboration, Collaborator
from siege_utilities.config.models.credential import Credential
from siege_utilities.config.models.oauth_integration import OAuthIntegration

pytestmark = pytest.mark.skipif(
    not hasattr(time, "tzset"), reason="time.tzset is unavailable on this platform (Windows)"
)

ZONES = ["America/Chicago", "Asia/Kolkata", "UTC"]
FAR_FUTURE = {
    "datetime.max": datetime.max,
    "9999-12-31T23:59:59": datetime(9999, 12, 31, 23, 59, 59),
}


@pytest.fixture
def zone(request, monkeypatch):
    monkeypatch.setenv("TZ", request.param)
    time.tzset()
    yield request.param
    monkeypatch.undo()
    time.tzset()


def _credential(expires_at, name="cred"):
    return Credential(name=name, credential_type="api_key", service="github", expires_at=expires_at)


def _oauth(expires_at, name="oauth"):
    return OAuthIntegration(
        name=name, provider="github", service="github", client_id="test-client-id",
        client_secret="test-client-secret", redirect_uri="https://example.com/callback",
        access_token="token-value", expires_at=expires_at,
    )


def _collaborator(**kwargs):
    return Collaborator(
        person_id="collaborator", name="Test Collaborator", email="collaborator@example.com",
        external_organization="Example Organization", **kwargs,
    )


@pytest.mark.parametrize("zone", ZONES, indirect=True)
@pytest.mark.parametrize("value", list(FAR_FUTURE.values()), ids=list(FAR_FUTURE))
def test_far_future_naive_credential_and_oauth_never_expire(zone, value):
    credential = _credential(value)
    assert credential.is_expired() is False
    assert credential.is_valid() is True

    oauth = _oauth(value)
    assert oauth.is_token_expired() is False
    assert oauth.needs_refresh() is False
    assert oauth.is_valid() is True


@pytest.mark.parametrize("zone", ZONES, indirect=True)
@pytest.mark.parametrize("value", list(FAR_FUTURE.values()), ids=list(FAR_FUTURE))
def test_far_future_naive_actor_access_never_expires(zone, value):
    collaborator = _collaborator(access_expires=value)
    collaborator.accept_invitation()
    assert collaborator.is_access_expired() is False
    assert collaborator.is_collaboration_active() is True
    assert collaborator.can_access_service("github") is True
    assert collaborator.can_access_credential("cred") is True

    collaboration = Collaboration(
        collab_id="collab", name="Test Collaboration", status="active",
        start_date=datetime(2000, 1, 1), end_date=value,
    )
    assert collaboration.is_active() is True


@pytest.mark.parametrize("zone", ZONES, indirect=True)
@pytest.mark.parametrize("value", list(FAR_FUTURE.values()), ids=list(FAR_FUTURE))
def test_person_filters_keep_far_future_and_ordinary_items(zone, value):
    soon = datetime.now() + timedelta(days=1)
    person = _collaborator(
        credentials=[_credential(soon, "ordinary"), _credential(value, "sentinel")],
        oauth_integrations=[_oauth(soon, "ordinary"), _oauth(value, "sentinel")],
    )
    assert [c.name for c in person.get_valid_credentials()] == ["ordinary", "sentinel"]
    assert [i.name for i in person.get_valid_oauth_integrations()] == ["ordinary", "sentinel"]


@pytest.mark.parametrize("zone", ZONES, indirect=True)
def test_range_floor_values_report_expired_without_raising(zone):
    for value in (datetime.min, "0001-01-01T00:00:00Z"):
        assert _credential(value).is_expired() is True
        oauth = _oauth(value)
        assert oauth.is_token_expired() is True
        assert oauth.needs_refresh() is True
