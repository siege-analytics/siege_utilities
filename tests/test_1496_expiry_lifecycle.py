"""Expiry lifecycle of the config models and Person filter selection (#1496).

What these tests prove:
- Expired items load, report themselves expired, and are left out by the
  Person filter-selection helpers (``get_valid_credentials`` and
  ``get_valid_oauth_integrations``).
- An absent expiry does not make an otherwise inactive or tokenless object
  valid.

What they do NOT prove: that any consumer refuses to use an expired or
inactive credential's secret. The library's one secret-using path,
``GoogleWorkspaceClient.from_account``, has no such gate (see the PR's
plain-risk note). The ``is_valid`` mutant test below shows only that the
filter selection depends on ``is_valid``.

Time is a controlled clock: each model module's ``utc_now`` is patched. There
is no real sleep, network or secret.
"""

from datetime import datetime, timedelta, timezone

import pytest

from siege_utilities.config.models import actor_types, credential, oauth_integration
from siege_utilities.config.models.actor_types import Collaboration, Collaborator
from siege_utilities.config.models.credential import Credential, CredentialStatus
from siege_utilities.config.models.oauth_integration import OAuthIntegration

T0 = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    frozen = Clock(T0)
    for module in (credential, oauth_integration, actor_types):
        monkeypatch.setattr(module, "utc_now", frozen)
    return frozen


def _credential(name="cred", **kwargs):
    return Credential(name=name, credential_type="api_key", service="github", **kwargs)


def _oauth(name="oauth", **kwargs):
    kwargs.setdefault("access_token", "token-value")
    return OAuthIntegration(
        name=name, provider="github", service="github", client_id="test-client-id",
        client_secret="test-client-secret", redirect_uri="https://example.com/callback", **kwargs,
    )


def _person(credentials=(), oauth=()):
    return Collaborator(
        person_id="collaborator", name="Test Collaborator", email="collaborator@example.com",
        external_organization="Example Organization",
        credentials=list(credentials), oauth_integrations=list(oauth),
    )


# -- the clock crosses a previously future expiry; the field never changes --

def test_controlled_clock_crosses_a_future_expiry_without_changing_the_field(clock):
    expires = T0 + timedelta(hours=1)
    person = _person(credentials=[_credential(expires_at=expires)], oauth=[_oauth(expires_at=expires)])
    assert person.credentials[0].is_expired() is False
    assert person.oauth_integrations[0].is_token_expired() is False
    assert [c.name for c in person.get_valid_credentials()] == ["cred"]
    saved = person.model_dump_json()  # dumped before the crossing

    clock.now = T0 + timedelta(hours=2)

    # The live object reports the crossing (v4.0.0 could also do this) ...
    assert person.credentials[0].expires_at == expires
    assert person.credentials[0].is_expired() is True
    assert person.oauth_integrations[0].is_token_expired() is True
    # ... and, unlike v4.0.0, the dump saved earlier still reloads after it.
    reloaded = Collaborator.model_validate_json(saved)
    assert reloaded.credentials[0].expires_at == expires
    assert reloaded.credentials[0].is_expired() is True
    assert reloaded.oauth_integrations[0].is_token_expired() is True
    assert reloaded.get_valid_credentials() == []
    assert reloaded.get_valid_oauth_integrations() == []


def test_assigning_a_past_expiry_is_accepted_and_reported(clock):
    # Assignment validation, separate from the clock test: a past value is
    # accepted on assignment (no future-only validator) and reports expired.
    item = _credential(expires_at=T0 + timedelta(hours=1))
    item.expires_at = T0 - timedelta(seconds=1)
    assert item.is_expired() is True
    assert item.is_valid() is False


# -- loading --

def test_direct_past_load_reports_expired(clock):
    past = (T0 - timedelta(days=1)).isoformat()
    loaded = Credential.model_validate(
        {"name": "c", "credential_type": "api_key", "service": "github", "expires_at": past})
    assert loaded.is_expired() is True
    assert loaded.is_valid() is False


def test_json_and_yaml_round_trips_keep_expiry(clock):
    past = T0 - timedelta(days=1)
    person = _person(credentials=[_credential(expires_at=past)], oauth=[_oauth(expires_at=past)])

    from_json = Collaborator.model_validate_json(person.model_dump_json())
    from_yaml = Collaborator.from_yaml(person.to_yaml())

    for reloaded in (from_json, from_yaml):
        assert reloaded.credentials[0].is_expired() is True
        assert reloaded.oauth_integrations[0].is_token_expired() is True
        assert reloaded.get_valid_credentials() == []
        assert reloaded.get_valid_oauth_integrations() == []


# -- absent expiry: valid only if everything else is valid --

def test_absent_expiry_with_otherwise_valid_fixtures(clock):
    assert _credential().is_expired() is False
    assert _credential().is_valid() is True
    assert _oauth().is_token_expired() is False
    assert _oauth().is_valid() is True
    assert _person().is_access_expired() is False
    assert Collaboration(collab_id="c", name="C", status="active", start_date=datetime(2000, 1, 1)).is_active() is True


def test_absent_expiry_does_not_validate_an_inactive_or_tokenless_object(clock):
    assert _credential(status=CredentialStatus.REVOKED).is_valid() is False
    assert _oauth(is_active=False).is_valid() is False
    assert _oauth(access_token=None).is_valid() is False
    assert Collaboration(collab_id="c", name="C", status="planning", start_date=datetime(2000, 1, 1)).is_active() is False


# -- exact boundary: the v4.0.0 comparison operators are kept --

def test_exact_boundary_expires_at_equals_now(clock):
    assert _credential(expires_at=T0).is_expired() is False        # now > expires_at
    assert _oauth(expires_at=T0).is_token_expired() is True         # now >= expires_at
    collaborator = Collaborator(person_id="p", name="P", email="p@example.com",
                                external_organization="Org", access_expires=T0)
    assert collaborator.is_access_expired() is False                # now > access_expires
    collaboration = Collaboration(collab_id="c", name="C", status="active",
                                  start_date=datetime(2000, 1, 1), end_date=T0)
    assert collaboration.is_active() is False                       # now < end_date


# -- equivalent aware instants and the declared naive normalization --

@pytest.mark.parametrize("offset", ["Z", "+05:00", "-08:00"])
def test_equivalent_aware_instants_give_the_same_answer(clock, offset):
    instant = T0 + timedelta(minutes=1)
    zone = timezone.utc if offset == "Z" else timezone(timedelta(hours=int(offset[:3])))
    text = instant.astimezone(zone).isoformat().replace("+00:00", "Z")
    assert _credential(expires_at=text).is_expired() is False
    clock.now = T0 + timedelta(minutes=2)
    assert _credential(expires_at=text).is_expired() is True


@pytest.mark.parametrize("delta, expired", [(timedelta(minutes=-1), True), (timedelta(minutes=1), False)])
def test_naive_expiry_is_local_wall_clock_time(clock, delta, expired):
    naive_local = (T0 + delta).astimezone().replace(tzinfo=None)
    assert _credential(expires_at=naive_local).is_expired() is expired


# -- filter selection depends on is_valid (not a consumer gate) --

@pytest.mark.parametrize("model", ["credential", "oauth"])
def test_filter_selection_depends_on_is_valid(clock, monkeypatch, model):
    past = T0 - timedelta(days=1)
    person = _person(credentials=[_credential(expires_at=past)], oauth=[_oauth(expires_at=past)])
    target = Credential if model == "credential" else OAuthIntegration
    select = person.get_valid_credentials if model == "credential" else person.get_valid_oauth_integrations
    assert select() == []

    monkeypatch.setattr(target, "is_valid", lambda self: True)

    assert len(select()) == 1
