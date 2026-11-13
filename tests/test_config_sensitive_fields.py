"""Guard the sensitivity declarations on every config model field."""

import importlib
import inspect
import pkgutil
import re

from pydantic import BaseModel, create_model
import pytest

import siege_utilities.config.models as models
from siege_utilities.config.models import actor_types
from siege_utilities.config.models._sensitivity import field_has_sensitive_name
from tests.sensitive_field_cases import PUBLIC_NAMES, SECRET_NAMES


_NON_SECRET_FIELDS = frozenset({
    ("User", "source_credentials"),  # Container of secret-store references.
    ("Collaborator", "restricted_credentials"),  # Credential names.
    ("Collaboration", "shared_credentials"),  # Credential names.
    ("DataSource", "auth_required"),  # Boolean setting.
    ("DatabaseConnection", "connection_timeout"),  # Timeout in seconds.
    ("Person", "credentials"),  # Container; nested credential fields are walked.
    ("OnePasswordCredential", "credential_name"),  # Secret-store reference.
    ("SourceCredential", "credential_ref"),  # Secret-store reference.
    ("Person", "onepassword_credentials"),  # References, not stored credentials.
    ("GoogleAccount", "token_file"),  # Path to a token file, not its contents.
    ("OAuthIntegration", "token_type"),  # Authentication scheme, e.g. Bearer.
})


def _assert_config_secret_fields_marked() -> None:
    missing = []
    for module_info in pkgutil.iter_modules(models.__path__):
        module = importlib.import_module(f"{models.__name__}.{module_info.name}")
        for _, model in inspect.getmembers(module, inspect.isclass):
            if not issubclass(model, BaseModel) or model.__module__ != module.__name__:
                continue
            for name, field in model.model_fields.items():
                if not field_has_sensitive_name(name, field):
                    continue
                metadata = field.json_schema_extra
                marked = isinstance(metadata, dict) and metadata.get("sensitive") is True
                allowlisted = (
                    isinstance(metadata, dict) and metadata.get("sensitive") is False
                    and any((base.__name__, name) in _NON_SECRET_FIELDS for base in model.__mro__)
                )
                if not marked and not allowlisted:
                    missing.append(f"{model.__name__}.{name}")
    assert not missing, "Secret-like fields need sensitivity markers: " + ", ".join(sorted(missing))


def test_config_secret_fields_marked() -> None:
    """New modules/classes are discovered automatically, with no model list."""
    _assert_config_secret_fields_marked()


@pytest.mark.parametrize("name", SECRET_NAMES)
def test_field_marker_guard_raises_for_unmarked_secret(
    monkeypatch: pytest.MonkeyPatch, name: str,
) -> None:
    injected = create_model(
        "InjectedUser", __base__=actor_types.User, __module__=actor_types.__name__,
        **{name: (str, "sentinel-secret")},
    )
    monkeypatch.setattr(actor_types, "InjectedUser", injected, raising=False)
    with pytest.raises(AssertionError, match=re.escape(f"InjectedUser.{name}")):
        _assert_config_secret_fields_marked()


@pytest.mark.parametrize("name", PUBLIC_NAMES)
def test_field_marker_guard_accepts_public_fields(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    injected = create_model(
        "InjectedUser", __base__=actor_types.User, __module__=actor_types.__name__,
        **{name: (str, "public-value")},
    )
    monkeypatch.setattr(actor_types, "InjectedUser", injected, raising=False)
    _assert_config_secret_fields_marked()
