"""Key-based redaction treats ``code`` and ``key`` as credentials only in credential contexts.

#1920 item 3b: a JSON or mapping field named ``code`` or ``key`` is often
ordinary data in CRM bodies (error codes such as ``INVALID_DATA``, record
keys), so a plain literal value is no longer redacted by name. Any other value
(URLs, escapes, nested JSON, opaque token-like runs, configured credentials of
any length) is still masked; tests/test_1920_redaction_names_falsifiers.py
holds the credential-context cases. In query strings and form bodies, ``code``
and ``key`` carry OAuth authorization codes and API keys, so they stay
redacted there.

The dangerous direction is a false negative, so most of this file proves that
real credentials in every other context are still redacted.
"""
from __future__ import annotations

import json

import pytest

from siege_utilities.connectors._protocol import UpsertError
from siege_utilities.core._http import redact_secrets

SECRET = "s3cr3t-value-1920-XYZ"
OTHER_SECRET = "0ther-s3cr3t-1920-ABC"


# -- ordinary code/key fields survive ------------------------------------------

@pytest.mark.parametrize("text", [
    '{"code": "INVALID_DATA", "key": "row-7"}',
    "{'code': 'INVALID_DATA', 'key': 'row-7'}",
    '{"data": [{"code": "DUPLICATE_DATA", "details": {"api_name": "Email"}, "status": "error"}]}',
    '{"error": {"code": "0x80040217", "message": "Record not found"}}',
], ids=["json", "python-mapping", "zoho-error-body", "dynamics-error-body"])
def test_ordinary_code_and_key_fields_survive(text: str) -> None:
    assert redact_secrets(text) == text


@pytest.mark.parametrize("value", [
    "INVALID_DATA", "row-7", "0x80040217", "12345", "MANDATORY_NOT_FOUND", "a.b:c-d_e", "x" * 32,
])
@pytest.mark.parametrize("field", ["code", "key"])
def test_plain_literal_code_and_key_values_survive(field: str, value: str) -> None:
    text = json.dumps({field: value})

    assert redact_secrets(text) == text


@pytest.mark.parametrize("value", [
    "AKIAIOSFODNN7EXAMPLE",
    "9f86d081884c7d659a2feaa0c55ad015",
    "550e8400-e29b-41d4-a716-446655440000",
    "ops@example.test",
    "two words",
    "x" * 33,
    "path/segment",
    "50%25off",
], ids=["opaque-token", "hex-digest", "uuid-over-32", "email", "space", "over-32", "slash", "percent"])
@pytest.mark.parametrize("field", ["code", "key"])
def test_non_literal_code_and_key_values_are_masked(field: str, value: str) -> None:
    result = redact_secrets(json.dumps({field: value}))

    assert value not in result
    assert result == json.dumps({field: "[REDACTED]"})


def test_upsert_error_message_keeps_an_error_code_field() -> None:
    message = 'Batch rejected: {"code": "INVALID_DATA", "key": "row-7"}'

    assert UpsertError(record_index=0, message=message).message == message


# -- a configured credential in a code/key field is still redacted -------------

@pytest.mark.parametrize("text", [
    f'{{"code": "{SECRET}", "key": "{OTHER_SECRET}"}}',
    f"{{'code': '{SECRET}', 'key': '{OTHER_SECRET}'}}",
], ids=["json", "python-mapping"])
def test_configured_credential_in_a_code_or_key_field_is_still_redacted(text: str) -> None:
    result = redact_secrets(text, values=(SECRET, OTHER_SECRET))

    assert SECRET not in result
    assert OTHER_SECRET not in result
    assert result.count("[REDACTED]") == 2


# -- real credentials stay redacted in every credential context ----------------

CREDENTIAL_NAMED_FIELDS = [
    "client_secret", "refresh_token", "access_token", "token", "password",
    "assertion", "client_assertion", "secret", "private_key", "api_key",
    "apikey", "api-key", "x-api-key",
]


@pytest.mark.parametrize("quote", ['"', "'"], ids=["json", "python-mapping"])
@pytest.mark.parametrize("name", CREDENTIAL_NAMED_FIELDS)
def test_credential_named_fields_are_still_redacted(name: str, quote: str) -> None:
    text = f"{{{quote}{name}{quote}: {quote}{SECRET}{quote}, {quote}code{quote}: {quote}INVALID_DATA{quote}}}"

    result = redact_secrets(text)

    assert SECRET not in result
    assert "INVALID_DATA" in result


@pytest.mark.parametrize("text", [
    f"Authorization: Bearer {SECRET}",
    f"authorization={SECRET}",
    f"x-api-key: {SECRET}",
    f"Cookie: session={SECRET}",
    f'{{"Authorization": "Bearer {SECRET}"}}',
    f"Bearer {SECRET}",
], ids=["authorization-header", "authorization-equals", "api-key-header", "cookie-header",
        "authorization-json", "bare-bearer"])
def test_auth_headers_and_bearer_tokens_are_still_redacted(text: str) -> None:
    assert SECRET not in redact_secrets(text)


@pytest.mark.parametrize("text", [
    f"https://app.example.test/callback?code={SECRET}&state=visible",
    f"https://app.example.test/callback?state=visible&code={SECRET}",
    f"https://api.example.test/v1/items?key={SECRET}",
    f"https://api.example.test/v1/items?token={SECRET}",
    f"https://api.example.test/v1/items?access_token={SECRET}",
    f"https://api.example.test/v1/items?client_secret={SECRET}",
    f"https://h.example.test/x?next=https%3A%2F%2Fu%3A{SECRET}%40h%2F",
], ids=["query-code-first", "query-code-later", "query-key", "query-token", "query-access-token",
        "query-client-secret", "encoded-nested-userinfo"])
def test_url_credentials_are_still_redacted(text: str) -> None:
    result = redact_secrets(text)

    assert SECRET not in result


@pytest.mark.parametrize("text", [
    f"grant_type=authorization_code&code={SECRET}&client_secret={OTHER_SECRET}&client_id=visible",
    f"key={SECRET}&client_id=visible",
    f"CODE={SECRET}&client_id=visible",
], ids=["oauth-token-request", "form-key", "form-code-uppercase"])
def test_form_body_code_and_key_are_still_redacted(text: str) -> None:
    result = redact_secrets(text)

    assert SECRET not in result
    assert OTHER_SECRET not in result
    assert "client_id=visible" in result
