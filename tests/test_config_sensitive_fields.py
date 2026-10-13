"""Guard the sensitivity declarations on every config model field."""

import importlib
import inspect
import pkgutil

from pydantic import BaseModel, create_model
import pytest

import siege_utilities.config.models as models
from siege_utilities.config.models import actor_types
from siege_utilities.config.models._sensitivity import SECRET_FIELD_NAME


_NON_SECRET_FIELDS = frozenset({
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
                if not SECRET_FIELD_NAME.search(name):
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


@pytest.mark.parametrize("name", [
    "webhook_secret", "bot_token", "signing_key", "api_keys",
    "connection_string", "connectionString", "passphrase", "apikey", "apiKey",
    "privateKey", "passwd", "pwd", "dsn",
])
def test_field_marker_guard_raises_for_unmarked_secret(
    monkeypatch: pytest.MonkeyPatch, name: str,
) -> None:
    injected = create_model(
        "InjectedUser", __base__=actor_types.User, __module__=actor_types.__name__,
        **{name: (str, "sentinel-secret")},
    )
    monkeypatch.setattr(actor_types, "InjectedUser", injected, raising=False)
    with pytest.raises(AssertionError, match=rf"InjectedUser\.{name}"):
        _assert_config_secret_fields_marked()
