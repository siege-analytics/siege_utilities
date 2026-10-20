"""B2 value-redaction extras (#1846 hub additions): URL-encoded echoes,
exception-chaining/traceback safety, and the minimum-length guard.

Synthetic values only; every send is intercepted.
"""
import traceback
from unittest.mock import Mock
from urllib.parse import quote, quote_plus

import pytest

from siege_utilities.connectors._protocol import ConnectorError
from tests.test_1417_crm_retry_idempotency import connector, response

SECRET = "REVIEW_SYNTHETIC_SECRET_abcdef12"  # len >= 8, redactable


def _token_rejection(body):
    c = connector("salesforce")
    c._client_secret = SECRET
    c._session.post = Mock(return_value=response(400, body))
    return c


def test_url_encoded_configured_secret_is_redacted():
    # Upstream echoes the configured secret URL-encoded, with no recognised
    # field name. Key-based redaction cannot catch it; value-based must.
    encoded = quote(SECRET, safe="")
    c = _token_rejection({"error": "bad secret " + encoded})
    with pytest.raises(ConnectorError) as caught:
        c._exchange_token("https://auth.example.test/token", {"client_secret": SECRET})
    text = str(caught.value)
    assert SECRET not in text
    assert encoded not in text
    assert quote_plus(SECRET) not in text


def test_traceback_contains_no_secret_in_any_form():
    encoded = quote(SECRET, safe="")
    c = _token_rejection({"error": SECRET, "error_description": encoded})
    try:
        c._exchange_token("https://auth.example.test/token", {"client_secret": SECRET})
    except ConnectorError as exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    assert SECRET not in tb
    assert encoded not in tb


def test_short_configured_value_is_not_redacted():
    # A short value must not blank out diagnostics (min-length guard).
    c = connector("salesforce")
    c._client_secret = "abc"  # len 3 < _MIN_SECRET_VALUE_LEN
    c._session.post = Mock(return_value=response(400, {"error": "detail abc stays visible"}))
    with pytest.raises(ConnectorError) as caught:
        c._exchange_token("https://auth.example.test/token", {"client_secret": "abc"})
    assert "abc stays visible" in str(caught.value)
