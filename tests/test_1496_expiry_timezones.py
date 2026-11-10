"""Expiry checks accept naive and timezone-aware values without TypeError (#1496).

Each of the four expiry fields is checked with a ``Z``-suffixed ISO string, a
non-UTC offset, and a naive value. Naive values are local wall-clock time, the
convention of the config models (``datetime.now()``), so their expiry instant
is the one v4.0.0 compared against ``datetime.now()``.
"""

from datetime import datetime, timedelta, timezone

import pytest

from siege_utilities.config.models.actor_types import Collaboration, Collaborator, User
from siege_utilities.config.models.credential import Credential
from siege_utilities.config.models.oauth_integration import OAuthIntegration


def _collaborator(**kwargs):
    return Collaborator(
        person_id="collaborator", name="Test Collaborator", email="collaborator@example.com",
        external_organization="Example Organization", **kwargs,
    )


def _credential(expires_at):
    return Credential(name="cred", credential_type="api_key", service="github", expires_at=expires_at)


def _oauth(expires_at):
    return OAuthIntegration(
        name="oauth", provider="github", service="github", client_id="test-client-id",
        client_secret="test-client-secret", redirect_uri="https://example.com/callback",
        access_token="token-value", expires_at=expires_at,
    )


def _collaboration(end_date):
    return Collaboration(
        collab_id="collab", name="Test Collaboration", status="active",
        start_date=datetime(2000, 1, 1), end_date=end_date,
    )


# (build, expired-check) for each of the four expiry fields.
FIELDS = {
    "Credential.expires_at": (_credential, lambda m: m.is_expired()),
    "OAuthIntegration.expires_at": (_oauth, lambda m: m.is_token_expired()),
    "Collaborator.access_expires": (lambda v: _collaborator(access_expires=v), lambda m: m.is_access_expired()),
    "Collaboration.end_date": (_collaboration, lambda m: not m.is_active()),
}


def _iso_utc(delta):
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.parametrize("field", list(FIELDS))
@pytest.mark.parametrize("delta, expired", [(timedelta(hours=-1), True), (timedelta(hours=1), False)])
def test_z_suffixed_value_compares_without_type_error(field, delta, expired):
    build, is_expired = FIELDS[field]
    model = build(_iso_utc(delta))
    assert is_expired(model) is expired


@pytest.mark.parametrize("field", list(FIELDS))
@pytest.mark.parametrize("offset_hours", [5, -8])
@pytest.mark.parametrize("delta, expired", [(timedelta(minutes=-30), True), (timedelta(minutes=30), False)])
def test_non_utc_offset_compares_the_instant(field, offset_hours, delta, expired):
    build, is_expired = FIELDS[field]
    zone = timezone(timedelta(hours=offset_hours))
    value = (datetime.now(timezone.utc) + delta).astimezone(zone)
    assert is_expired(build(value)) is expired


@pytest.mark.parametrize("field", list(FIELDS))
@pytest.mark.parametrize("delta, expired", [(timedelta(minutes=-30), True), (timedelta(minutes=30), False)])
def test_naive_value_is_local_wall_clock_time(field, delta, expired):
    build, is_expired = FIELDS[field]
    assert is_expired(build(datetime.now() + delta)) is expired


@pytest.mark.parametrize("delta", [timedelta(minutes=-30), timedelta(minutes=30)])
def test_naive_expiry_keeps_its_v400_instant(delta):
    # Control: the helper must not move a naive expiry. The instant is the one
    # v4.0.0 compared against naive datetime.now(), and the result matches the
    # v4.0.0 rule computed directly.
    from siege_utilities.config.models._expiry import as_utc

    naive = datetime.now() + delta
    assert as_utc(naive).timestamp() == naive.timestamp()
    v400_expired = datetime.now() > naive
    assert _credential(naive).is_expired() is v400_expired
    assert _credential(naive).expires_at.tzinfo is None  # stored as given


def test_aware_value_is_stored_as_given():
    credential = _credential("2099-01-01T00:00:00Z")
    assert credential.expires_at.tzinfo is not None
    assert credential.expires_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize("field", list(FIELDS))
def test_past_aware_value_reloads_and_reports_expired(field):
    build, is_expired = FIELDS[field]
    model = build(_iso_utc(timedelta(days=-1)))
    reloaded = type(model).model_validate(model.model_dump())
    assert is_expired(reloaded) is True


def test_valid_credential_and_oauth_with_future_aware_expiry():
    assert _credential(_iso_utc(timedelta(days=1))).is_valid() is True
    assert _oauth(_iso_utc(timedelta(days=1))).is_valid() is True


def test_credential_and_user_reload_after_their_expiry_passes(monkeypatch):
    # The ticket's scenario: an expiry one second ahead, saved, then reloaded
    # after it has passed. v4.0.0 rejected the reload. Time is a controlled
    # clock (each model module's utc_now), not a real sleep.
    from siege_utilities.config.models import actor_types, credential, oauth_integration

    start = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
    current = {"now": start}
    for module in (credential, oauth_integration, actor_types):
        monkeypatch.setattr(module, "utc_now", lambda: current["now"])
    soon = start + timedelta(seconds=1)
    credential_model = _credential(soon)
    user = User(person_id="u1", name="Test User", email="u1@example.com", username="u1",
                oauth_integrations=[_oauth(soon)])
    assert credential_model.is_expired() is False
    credential_blob, user_blob = credential_model.model_dump_json(), user.model_dump_json()

    current["now"] = start + timedelta(seconds=2)

    reloaded_credential = Credential.model_validate_json(credential_blob)
    reloaded_user = User.model_validate_json(user_blob)
    assert reloaded_credential.is_expired() is True
    assert reloaded_user.oauth_integrations[0].is_token_expired() is True
    assert reloaded_user.get_valid_oauth_integrations() == []


def test_filter_selection_leaves_out_expired_aware_items_without_crashing():
    # Filter selection only: get_valid_* choose which items to return. This is
    # not a consumer gate on secret use.
    person = _collaborator(
        credentials=[
            Credential(name="expired", credential_type="api_key", service="github",
                       expires_at=_iso_utc(timedelta(days=-1))),
            Credential(name="current", credential_type="api_key", service="github",
                       expires_at=_iso_utc(timedelta(days=1))),
        ],
        oauth_integrations=[
            _oauth(_iso_utc(timedelta(days=-1))).model_copy(update={"name": "expired"}),
            _oauth(_iso_utc(timedelta(days=1))).model_copy(update={"name": "current"}),
        ],
    )

    assert [c.name for c in person.get_valid_credentials()] == ["current"]
    assert [o.name for o in person.get_valid_oauth_integrations()] == ["current"]
