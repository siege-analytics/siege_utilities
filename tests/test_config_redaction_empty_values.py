"""Genuinely empty builtins in a sensitive position are preserved, not redacted.

The fail-closed allowlist preserves a value only when, by EXACT class identity,
it is a sized builtin empty by len, an exact numeric zero, or an exact empty
SecretStr('')/SecretBytes(b''); any subclass (even one that unwraps to empty)
and any non-empty value is redacted. This pins the contract the merge-gate
review flagged: empty builtins come back unchanged (as on develop), an exact
empty SecretStr/SecretBytes is preserved for the default export->import
round-trip, and an empty str subclass or a SecretStr subclass is still redacted.
"""
import math

from pydantic import SecretStr, SecretBytes
import pytest

from siege_utilities.config.models.person import (
    _redact_sensitive_value,
    _strip_sensitive_fields,
)
from tests.hostile_secrets import unwrap_recording_subclass


def test_empty_builtins_in_sensitive_keys_are_preserved_identically():
    original = {"access_token": [], "client_secret": {}, "password": (), "token": None}
    assert _strip_sensitive_fields(dict(original)) == original


@pytest.mark.parametrize("value", ["", b"", [], {}, (), set(), frozenset(), 0, 0.0, -0.0, False])
def test_exact_empty_builtin_is_preserved_with_type_and_sign(value):
    result = _redact_sensitive_value(value)
    assert type(result) is type(value)
    assert result == value
    if type(value) is float:
        assert math.copysign(1.0, result) == math.copysign(1.0, value)


def test_none_is_preserved():
    assert _redact_sensitive_value(None) is None


def test_empty_str_subclass_is_redacted():
    class EmptyStrSub(str):
        pass

    assert _redact_sensitive_value(EmptyStrSub("")) == "***REDACTED***"


def test_exact_empty_secretstr_is_preserved():
    # Amended ruling (Hub FINAL 10:30 CDT): an exact-type empty Pydantic secret
    # carries no secret and is preserved, so the default model round-trip works.
    result = _redact_sensitive_value(SecretStr(""))
    assert type(result) is SecretStr
    assert result.get_secret_value() == ""


def test_exact_empty_secretbytes_is_preserved():
    result = _redact_sensitive_value(SecretBytes(b""))
    assert type(result) is SecretBytes
    assert result.get_secret_value() == b""


def test_non_empty_secret_is_redacted():
    assert _redact_sensitive_value(SecretStr("x")) == "***REDACTED***"
    assert _redact_sensitive_value(SecretBytes(b"x")) == "***REDACTED***"


@pytest.mark.parametrize("base", [SecretStr, SecretBytes], ids=["SecretStr", "SecretBytes"])
def test_empty_secret_subclass_is_redacted_without_being_unwrapped(base):
    # A subclass is always redacted, even unwrapping to empty: exact type only,
    # and its get_secret_value() is never consulted to decide.
    calls: list[bool] = []
    hostile = unwrap_recording_subclass(base, calls)

    assert _redact_sensitive_value(hostile("" if base is SecretStr else b"")) == "***REDACTED***"
    assert calls == []


@pytest.mark.parametrize("value", ["abc", b"abc", [1], {"k": "v"}, (1,), 1, 1.0, True])
def test_non_empty_builtin_is_redacted(value):
    assert _redact_sensitive_value(value) == "***REDACTED***"
