"""Genuinely empty builtins in a sensitive position are preserved, not redacted.

The fail-closed allowlist preserves only a value whose EXACT builtin type holds
its empty/zero form; a subclass or any non-empty value is redacted. This pins
the MEDIUM contract the merge-gate review flagged:
empty builtins must come back unchanged (they did on develop), while an empty
str subclass or SecretStr must still be redacted.
"""
from pydantic import SecretStr, SecretBytes
import pytest

from siege_utilities.config.models.person import (
    _redact_sensitive_value,
    _strip_sensitive_fields,
)


def test_empty_builtins_in_sensitive_keys_are_preserved_identically():
    original = {"access_token": [], "client_secret": {}, "password": (), "token": None}
    assert _strip_sensitive_fields(dict(original)) == original


@pytest.mark.parametrize("value", ["", b"", [], {}, (), set(), frozenset(), 0, 0.0, False])
def test_genuinely_empty_exact_builtin_is_preserved(value):
    assert _redact_sensitive_value(value) == value
    assert type(_redact_sensitive_value(value)) is type(value)


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


def test_empty_secretstr_subclass_is_redacted():
    # A subclass is always redacted, even unwrapping to empty: exact type only,
    # and its get_secret_value() is never consulted to decide.
    class SneakySecret(SecretStr):
        def get_secret_value(self):  # noqa: D401 - hostile stub
            return ""

    assert _redact_sensitive_value(SneakySecret("")) == "***REDACTED***"


@pytest.mark.parametrize("value", ["abc", b"abc", [1], {"k": "v"}, (1,), 1, 1.0, True])
def test_non_empty_builtin_is_redacted(value):
    assert _redact_sensitive_value(value) == "***REDACTED***"
