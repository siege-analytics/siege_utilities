"""Error-path coverage (SU-4b) for siege_utilities.config.models.actor_types.

Forces the custom pydantic field_validator ValueError guards on User, Client,
and Collaborator. Each invalid construction surfaces as pydantic ValidationError
wrapping the validator's ValueError. Only validators reachable past the Field
constraints are exercised (e.g. the role/cross-field/uniqueness checks).
"""

import datetime

import pytest
from pydantic import ValidationError

from siege_utilities.config.models.actor_types import (
    Client,
    Collaborator,
    User,
)

_PERSON = dict(person_id="p1", name="Test Person", email="t@example.com")


# --- User -----------------------------------------------------------------

def test_user_rejects_invalid_role():
    with pytest.raises(ValidationError) as exc_info:
        User(username="ok", role="wizard", **_PERSON)
    assert "Role must be one of" in str(exc_info.value)


def test_user_rejects_duplicate_permissions():
    with pytest.raises(ValidationError) as exc_info:
        User(username="ok", permissions=["read", "read"], **_PERSON)
    assert "Permissions must be unique" in str(exc_info.value)


def test_user_rejects_duplicate_assigned_clients():
    with pytest.raises(ValidationError) as exc_info:
        User(username="ok", assigned_clients=["AAAA", "AAAA"], **_PERSON)
    assert "Assigned clients must be unique" in str(exc_info.value)


def test_user_rejects_primary_client_not_in_assigned():
    with pytest.raises(ValidationError) as exc_info:
        User(username="ok", assigned_clients=["AAAA"], primary_client="BBBB", **_PERSON)
    assert "must be in assigned_clients" in str(exc_info.value)


# --- Client ---------------------------------------------------------------

_CLIENT = dict(industry="tech", project_count=1, client_status="active", **_PERSON)


@pytest.mark.parametrize("bad_code", ["A", "abcd", "TEST"])
def test_client_rejects_invalid_client_code(bad_code):
    # too short / lowercase / reserved -> ValueError in the client_code validator
    with pytest.raises(ValidationError) as exc_info:
        Client(client_code=bad_code, **_CLIENT)
    assert "client_code" in str(exc_info.value).lower()


def test_client_rejects_primary_user_not_in_assigned():
    with pytest.raises(ValidationError) as exc_info:
        Client(client_code="ABCD", assigned_users=["u1"], primary_user="u2", **_CLIENT)
    assert "must be in assigned_users" in str(exc_info.value)


# --- Collaborator ---------------------------------------------------------

def test_collaborator_rejects_empty_external_organization():
    with pytest.raises(ValidationError) as exc_info:
        Collaborator(external_organization="   ", **_PERSON)
    assert "cannot be empty" in str(exc_info.value)


def test_collaborator_rejects_past_access_expiry():
    past = datetime.datetime(2000, 1, 1)
    with pytest.raises(ValidationError) as exc_info:
        Collaborator(external_organization="Org", access_expires=past, **_PERSON)
    assert "future" in str(exc_info.value)
