"""R2 B2: secret absence across CRM diagnostic surfaces and error paths."""

import json
import logging
import traceback
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.connectors._protocol import ConnectorError, UpsertError, UpsertResult
from tests.test_1417_crm_retry_idempotency import batch_response, connector, response


SENTINEL = "crm-r2-secret-7e8b41"
SURFACES = {
    "url": f"https://example.test/records?access_token={SENTINEL}&client_id=visible",
    "header": f"Authorization: Bearer {SENTINEL}\nX-Api-Key: {SENTINEL}",
    "form": f"client_secret={SENTINEL}&refresh_token={SENTINEL}&client_id=visible",
    "json": json.dumps({"client_secret": SENTINEL, "normal": "visible"}),
}
PROVIDERS = ["salesforce", "hubspot", "zoho", "dynamics"]
TARGETS = ["str", "repr", "traceback", "logs", "upsert_repr"]


@pytest.fixture(autouse=True)
def enabled_connector_logs(monkeypatch, caplog):
    # Full-suite Django setup can disable loggers created during collection.
    for provider in PROVIDERS:
        logger = logging.getLogger(f"siege_utilities.connectors.{provider}")
        monkeypatch.setattr(logger, "disabled", False)
        caplog.set_level(logging.DEBUG, logger=logger.name)


def diagnostic(surface):
    return "\n".join(SURFACES.values()) if surface == "all" else SURFACES[surface]


def assert_absent(target, exc, caplog, text):
    values = {
        "str": str(exc),
        "repr": repr(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        "logs": "\n".join(record.getMessage() + logging.Formatter().format(record)
                          for record in caplog.records) + caplog.text,
        "upsert_repr": repr(UpsertResult(0, 1, errors=[UpsertError(0, text)])),
    }
    assert SENTINEL not in values[target]


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("surface", [*SURFACES, "all"])
@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("failure", ["transport", "invalid_json", "non_json", "http", "server"])
def test_connector_secret_absence(provider, surface, target, failure, caplog, monkeypatch):
    c = connector(provider)
    c._retry_attempts = 1
    c._client_secret = None
    c._username = c._password = None
    c._session.headers.update({"Authorization": f"Bearer {SENTINEL}", "X-Api-Key": SENTINEL})
    text = diagnostic(surface)
    prepared = requests.Request(
        "POST", SURFACES["url"], headers=dict(c._session.headers),
        data=SURFACES["form"],
    ).prepare()
    resp = response({"http": 400, "server": 503}.get(failure, 200), body={
        "message": text, "error": {"message": text},
    })
    resp.request = prepared
    if failure in {"transport", "invalid_json"}:
        cls = requests.Timeout if failure == "transport" else requests.exceptions.InvalidJSONError
        c._session.request = Mock(side_effect=cls(text, request=prepared, response=resp))
    else:
        if failure == "non_json":
            resp._content = ("invalid JSON response: " + text).encode()
        c._session.request = Mock(return_value=resp)
    monkeypatch.setattr("time.sleep", Mock())
    caplog.set_level(logging.DEBUG)
    with pytest.raises(ConnectorError) as caught:
        c.request("POST", f"/records?access_token={SENTINEL}",
                  params={"access_token": SENTINEL},
                  json_body={"client_secret": SENTINEL, "form": SURFACES["form"]})
    if failure == "transport":
        assert any("attempt 1/1 failed" in record.getMessage() for record in caplog.records)
    if failure == "server":
        assert any("5xx" in record.getMessage() for record in caplog.records)
    assert_absent(target, caught.value, caplog, text)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("surface", [*SURFACES, "all"])
def test_connector_upsert_response_repr(provider, surface, caplog):
    c = connector(provider)
    text = diagnostic(surface)
    error = {"message": text, "code": text, "category": text, "statusCode": text, "fields": [text]}
    if provider == "dynamics":
        c._session.post = Mock(return_value=batch_response([(1, 400, {"error": error})]))
    else:
        body = {
            "salesforce": [{"success": False, "errors": [error]}],
            "hubspot": {"results": [], "errors": [error]},
            "zoho": {"data": [{"status": "error", **error}]},
        }[provider]
        c._session.request = Mock(return_value=response(body=body))
    caplog.set_level(logging.DEBUG)
    result = c.upsert_records("contacts", pd.DataFrame({"key": ["a"]}), "key")
    assert not result.ok
    assert SENTINEL not in repr(result)
    assert SENTINEL not in repr(result.errors)
    assert SENTINEL not in caplog.text


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("failure", ["transport", "rejection"])
def test_connector_token_exchange_diagnostics(provider, failure, caplog):
    c = connector(provider)
    text = diagnostic("all")
    caplog.set_level(logging.DEBUG)
    if provider == "dynamics":
        c._msal_app = Mock()
        c._scope = ["scope"]
        send = c._msal_app.acquire_token_for_client
        invoke = c._auth_client_credentials
    else:
        send = Mock()
        c._session.post = send

        def invoke():
            return c._exchange_token(SURFACES["url"], {"client_secret": SENTINEL})
    if failure == "transport":
        send.side_effect = requests.ConnectionError(text)
    else:
        payload = {"error": text, "error_description": text, "message": text}
        send.return_value = payload if provider == "dynamics" else response(400, payload)
    with pytest.raises(ConnectorError) as caught:
        invoke()
    for target in TARGETS:
        assert_absent(target, caught.value, caplog, text)


@pytest.mark.parametrize("key", [
    "authorization", "proxy-authorization", "x-api-key", "api-key", "apikey",
    "x-auth-token", "cookie", "set-cookie",
])
@pytest.mark.parametrize("delimiter", [": ", "="])
def test_connector_redact_secrets_headers(key, delimiter):
    from siege_utilities.core._http import redact_secrets

    text = f"{key.upper()}{delimiter}{SENTINEL}\nclient_id=visible"
    result = redact_secrets(text)
    assert SENTINEL not in result
    assert "client_id=visible" in result


@pytest.mark.parametrize("key", [
    "client_secret", "refresh_token", "access_token", "token", "password",
    "assertion", "client_assertion", "code", "secret", "private_key",
])
def test_connector_redact_secrets_form_and_json(key):
    from siege_utilities.core._http import redact_secrets

    text = f'{key.upper()}={SENTINEL}&client_id=visible\n{{"{key}": "{SENTINEL}", "normal": "visible"}}'
    result = redact_secrets(text, replacement="<hidden>")
    assert SENTINEL not in result
    assert "<hidden>" in result
    assert '"normal": "visible"' in result
    assert "client_id=visible" in result


def test_connector_redact_secrets_preserves_url_coverage_and_bare_bearer():
    from siege_utilities.core._http import redact_secrets

    result = redact_secrets(diagnostic("all") + f"\nBearer {SENTINEL}")
    assert SENTINEL not in result
    assert "visible" in result
