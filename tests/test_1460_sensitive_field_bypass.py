"""Red-first regressions for the two remaining #1460 export bypasses."""

from datetime import datetime

from pydantic import AliasChoices, AliasPath, ConfigDict, Field, create_model
import pytest
import yaml

from siege_utilities.config.models import actor_types
from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.export import export_entities
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from tests.test_config_sensitive_fields import _assert_config_secret_fields_marked


REDACTED = "***REDACTED***"
SENTINEL = "DUMMY-B1460-PAYLOAD"
SURFACES = ("to_dict", "to_yaml", "export_entities")
ALIAS_CASES = [
    pytest.param({"alias": "client_secret"}, True, id="alias"),
    pytest.param({"validation_alias": "client_secret"}, True, id="validation-alias"),
    pytest.param({"serialization_alias": "client_secret"}, True, id="serialization-alias"),
    pytest.param({"validation_alias": AliasChoices("x", "access_token")}, True,
                 id="choices-last"),
    pytest.param({"validation_alias": AliasChoices("access_token", "x")}, True,
                 id="choices-first"),
    pytest.param({"validation_alias": AliasPath("client_secret", 0, "x")}, True,
                 id="path-first"),
    pytest.param({"validation_alias": AliasPath("x", 0, "access_token")}, True,
                 id="path-last"),
    pytest.param({"validation_alias": AliasChoices("x", AliasPath("y", 0, "access_token"))},
                 True, id="choices-path"),
    pytest.param({"alias": "display_name", "validation_alias": "x",
                  "serialization_alias": "client_secret"}, True, id="distinct-aliases"),
    pytest.param({"alias": "display_name"}, False, id="public-alias"),
    pytest.param({"validation_alias": "display_name"}, False, id="public-validation-alias"),
    pytest.param({"serialization_alias": "display_name"}, False, id="public-serialization-alias"),
    pytest.param({"validation_alias": AliasChoices("x", AliasPath("display_name", 0))},
                 False, id="public-choices-path"),
]


class HashableBytearray(bytearray):
    """A bytearray key must be hashable; builtin bytearray cannot enter a dict."""

    def __hash__(self):
        return hash(bytes(self))


class OpaqueKey:
    """An arbitrary key whose string representation looks public."""

    def __str__(self):
        return "display_name"


KEY_CASES = [
    pytest.param(b"access_token", True, id="credential-bytes"),
    pytest.param(b"display_name", False, id="public-bytes"),
    pytest.param(b"\xff", True, id="undecodable-bytes"),
    pytest.param(HashableBytearray(b"access_token"), True, id="credential-bytearray"),
    pytest.param(HashableBytearray(b"display_name"), False, id="public-bytearray"),
    pytest.param(HashableBytearray(b"\xff"), True, id="undecodable-bytearray"),
    pytest.param(1, False, id="int"),
    pytest.param(1.5, False, id="float"),
    pytest.param(True, False, id="bool"),
    pytest.param(None, False, id="none"),
    pytest.param(("display_name", 1), True, id="tuple"),
    pytest.param(frozenset({"display_name"}), True, id="frozenset"),
    pytest.param(OpaqueKey(), True, id="object"),
    pytest.param("display_name", False, id="public-str"),
]


@pytest.fixture
def represent_exotic_keys(monkeypatch):
    """Exercise real YAML exports without changing their supported key types.

    SafeDumper already accepts bytes and tuples, but needs caller-supplied
    representers for frozensets, arbitrary objects and hashable bytearrays.
    These representers preserve the key's kind and never touch its value.
    """
    representers = dict(yaml.SafeDumper.yaml_representers)
    representers[HashableBytearray] = lambda dumper, key: dumper.represent_binary(bytes(key))
    representers[frozenset] = lambda dumper, key: dumper.represent_set(set(key))
    representers[OpaqueKey] = lambda dumper, key: dumper.represent_scalar("!opaque", str(key))
    monkeypatch.setattr(yaml.SafeDumper, "yaml_representers", representers)


def _user(value, placement="nested"):
    nested = {"record": value} if placement == "nested" else [{"record": value}]
    fixed_time = datetime(2026, 10, 18, 12)
    oauth = OAuthIntegration(
        name="public-integration", provider="google", service="analytics",
        client_id="public-client-id", client_secret="DUMMY-OAUTH-SECRET",
        redirect_uri="https://example.com/callback", metadata={"nested": nested},
        created_date=fixed_time,
    )
    return User(
        person_id="bypass-user", name="Public User", email="public@example.com",
        username="public_user", oauth_integrations=[oauth],
        created_date=fixed_time, last_updated=fixed_time,
    )


def _payload_model(field_kwargs, name="payload"):
    model = create_model(
        "MetadataPayload", __config__=ConfigDict(populate_by_name=True),
        **{name: (str, Field(**field_kwargs))},
    )
    # Supply the internal value through validation, independently of which
    # alias form the test asks the export classifier to recognize.
    return model.model_validate({name: SENTINEL})


def _export(user, surface, exclude_sensitive):
    if surface == "export_entities":
        return export_entities(users=[user], exclude_sensitive=exclude_sensitive)
    return getattr(user, surface)(exclude_sensitive=exclude_sensitive)


def _assert_export(user, surface, sensitive, monkeypatch):
    # Freeze the document timestamp so full serialized output is comparable.
    class FixedDatetime:
        @staticmethod
        def now():
            return datetime(2026, 10, 18, 12)

    monkeypatch.setattr("siege_utilities.config.models.export.datetime", FixedDatetime)
    plain = _export(user, surface, False)
    plain_text = yaml.safe_dump(plain, sort_keys=False) if isinstance(plain, dict) else plain
    assert SENTINEL in plain_text
    redacted = _export(user, surface, True)
    redacted_text = yaml.safe_dump(redacted, sort_keys=False) if isinstance(redacted, dict) else redacted
    expected = plain_text.replace("DUMMY-OAUTH-SECRET", REDACTED)
    if sensitive:
        expected = expected.replace(SENTINEL, REDACTED)
    # YAML quotes the placeholder when it replaces an entire scalar value.
    expected = expected.replace(": " + REDACTED + "\n", ": '" + REDACTED + "'\n")
    assert redacted_text == expected
    assert _export(user, surface, False) == plain
    if surface == "to_dict":
        assert user.to_dict() == plain
    return redacted


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("placement", ["nested", "list"])
@pytest.mark.parametrize("field_kwargs,sensitive", ALIAS_CASES)
def test_alias_field_redaction(field_kwargs, sensitive, placement, surface, monkeypatch):
    user = _user(_payload_model(field_kwargs), placement)
    _assert_export(user, surface, sensitive, monkeypatch)


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("placement", ["nested", "list"])
@pytest.mark.parametrize("key,sensitive", KEY_CASES)
def test_non_str_key_redaction(key, sensitive, placement, surface, monkeypatch,
                               represent_exotic_keys):
    user = _user({key: SENTINEL, "label": "public-neighbor"}, placement)
    result = _assert_export(user, surface, sensitive, monkeypatch)
    if surface == "to_dict":
        nested = result["oauth_integrations"][0]["metadata"]["nested"]
        record = nested["record"] if placement == "nested" else nested[0]["record"]
        assert next(iter(record)) is key
        assert record[key] == (REDACTED if sensitive else SENTINEL)


@pytest.mark.parametrize("field_kwargs,sensitive", ALIAS_CASES)
def test_guard_checks_alias_forms(field_kwargs, sensitive, monkeypatch):
    injected = create_model(
        "InjectedAliasUser", __base__=actor_types.User, __module__=actor_types.__name__,
        payload=(str, Field(**field_kwargs)),
    )
    monkeypatch.setattr(actor_types, "InjectedAliasUser", injected, raising=False)
    if sensitive:
        with pytest.raises(AssertionError, match=r"InjectedAliasUser\.payload"):
            _assert_config_secret_fields_marked()
    else:
        _assert_config_secret_fields_marked()


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("policy", [True, False])
def test_alias_keeps_field_marker_policy(surface, policy, monkeypatch):
    user = _user(_payload_model({"alias": "client_secret", "json_schema_extra": {"sensitive": policy}}))
    _assert_export(user, surface, policy, monkeypatch)


@pytest.mark.parametrize("surface", SURFACES)
def test_public_alias_does_not_hide_sensitive_internal_name(surface, monkeypatch):
    user = _user(_payload_model({"alias": "display_name"}, name="client_secret"))
    _assert_export(user, surface, True, monkeypatch)


@pytest.mark.parametrize("key", [1, 1.5, True, None, b"display_name"])
@pytest.mark.parametrize("surface", SURFACES)
def test_public_key_still_traverses_nested_values(key, surface, monkeypatch):
    user = _user({key: [{"access_token": SENTINEL}]})
    _assert_export(user, surface, True, monkeypatch)


@pytest.mark.parametrize("surface", ["to_yaml", "export_entities"])
@pytest.mark.parametrize("key", [frozenset({"display_name"}), OpaqueKey()])
def test_unsupported_yaml_key_behavior_unchanged(key, surface):
    user = _user({key: SENTINEL})
    for exclude_sensitive in (False, True):
        with pytest.raises(yaml.representer.RepresenterError):
            _export(user, surface, exclude_sensitive)
