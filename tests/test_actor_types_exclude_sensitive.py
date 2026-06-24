"""Regression tests for the exclude_sensitive serialization path on the
actor_types models (Organization, Collaboration).

Guards against the F821 / NameError where actor_types.py called
``_strip_sensitive_fields`` without importing it from ``.person``. Only
``Organization.to_dict`` and ``Collaboration.to_dict`` reach that path;
the pre-existing exclude_sensitive tests exercise ``User`` (a Person
subclass that uses person.py's own import), so the bug shipped uncaught
and was caught only by flake8, not by a behavior test. See ticket #1064.
"""

from siege_utilities.config.models.actor_types import Organization, Collaboration


def _org() -> Organization:
    return Organization(
        org_id="test-org-1",
        name="Test Org",
        org_type="vendor",
        primary_email="contact@example.com",
    )


def _collab() -> Collaboration:
    return Collaboration(collab_id="test-collab-1", name="Test Collaboration")


def test_organization_to_dict_exclude_sensitive_runs():
    # Pre-fix this raised: NameError: name '_strip_sensitive_fields' is not defined
    data = _org().to_dict(exclude_sensitive=True)
    assert isinstance(data, dict)
    assert data["org_id"] == "test-org-1"
    assert data["name"] == "Test Org"


def test_collaboration_to_dict_exclude_sensitive_runs():
    data = _collab().to_dict(exclude_sensitive=True)
    assert isinstance(data, dict)
    assert data["collab_id"] == "test-collab-1"
    assert data["name"] == "Test Collaboration"


def test_organization_to_yaml_exclude_sensitive_runs():
    # to_yaml() delegates to to_dict(exclude_sensitive=...), the same path.
    text = _org().to_yaml(exclude_sensitive=True)
    assert isinstance(text, str)
    assert "test-org-1" in text


def test_exclude_sensitive_preserves_non_sensitive_fields():
    # Organization carries no credential-class keys, so the strip is a
    # correct no-op on its fields; equality proves _strip_sensitive_fields
    # executed (rather than erroring) and left non-sensitive data intact.
    org = _org()
    assert org.to_dict(exclude_sensitive=True) == org.to_dict(exclude_sensitive=False)
