"""B2 value-redaction extras (#1846 hub additions): URL-encoded echoes,
exception-chaining/traceback safety, and the minimum-length guard.

Synthetic values only; every send is intercepted.
"""
import traceback
from typing import Any
from unittest.mock import Mock
from urllib.parse import quote, quote_plus

import pytest

from siege_utilities.connectors._protocol import ConnectorError
from tests.crm_connector_factories import connector, response

SECRET = "REVIEW_SYNTHETIC_SECRET_abcdef12"  # len >= 8, redactable


def _token_rejection(body: dict[str, str]) -> Any:
    c = connector("salesforce")
    c._client_secret = SECRET
    c._session.post = Mock(return_value=response(400, body))
    return c


def test_url_encoded_configured_secret_is_redacted() -> None:
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


def test_traceback_contains_no_secret_in_any_form() -> None:
    encoded = quote(SECRET, safe="")
    c = _token_rejection({"error": SECRET, "error_description": encoded})
    with pytest.raises(ConnectorError) as caught:
        c._exchange_token("https://auth.example.test/token", {"client_secret": SECRET})
    exc = caught.value
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    assert SECRET not in tb
    assert encoded not in tb


def test_short_configured_credential_suppresses_auth_upstream_detail() -> None:
    # #1846 B2 r4 D3 reversal. This test previously asserted the opposite --
    # "A short value must not blank out diagnostics (min-length guard)" with
    # ``assert "abc stays visible" in str(caught.value)``. D3 ("configured
    # cred <8 chars -> diagnostics carry NO upstream detail") supersedes that
    # on the auth/token path: a short credential cannot be removed by value
    # replacement, so an auth-error body that may echo it is dropped in full,
    # leaving only the trusted constant and status. The general request path
    # applies the same rule -- see
    # test_connectors_salesforce_errors.test_short_credential_suppresses_general_path_detail.
    c = connector("salesforce")
    c._client_secret = "abc"  # len 3 < _MIN_SECRET_VALUE_LEN
    c._session.post = Mock(return_value=response(400, {"error": "detail abc stays visible"}))
    with pytest.raises(ConnectorError) as caught:
        c._exchange_token("https://auth.example.test/token", {"client_secret": "abc"})
    text = str(caught.value)
    assert text == "Salesforce auth failed (400)"
    assert "abc stays visible" not in text
    assert "detail" not in text
