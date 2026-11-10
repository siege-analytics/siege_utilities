"""Shared offline factories for the CRM connector test suites.

Builds pre-authenticated Salesforce, HubSpot, Zoho and Dynamics connectors and
canned ``requests.Response`` objects (plain JSON and Dynamics OData multipart
batch bodies). Nothing here touches the network or patches anything on import;
suites opt in to ``record_test_thread_sleeps`` where they assert on sleeps.
"""
from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterable, Mapping
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector


def connector(provider: str) -> Any:
    """Return an authenticated *provider* connector with synthetic credentials.

    Dynamics is built without ``__init__`` so no MSAL application is created.
    """
    c: Any
    if provider == "salesforce":
        c = SalesforceConnector(client_id="id", client_secret="dummy-client-secret-1417")
        c._instance_url = "https://salesforce.example.test"
    elif provider == "hubspot":
        c = HubSpotConnector(access_token="dummy-access-token-1417")
    elif provider == "zoho":
        c = ZohoConnector(client_id="id", client_secret="dummy-client-secret-1417")
    elif provider == "dynamics":
        c = DynamicsConnector.__new__(DynamicsConnector)
        c._environment_url = "https://dynamics.example.test"
        c._session = requests.Session()
        c._timeout = 30
    else:
        raise ValueError(f"unknown CRM provider {provider!r}")
    c._authenticated = True
    c._token_expires_at = None
    c._access_token = "dummy-access-token-1417"
    c._retry_attempts = 3
    c._retry_backoff = 0
    return c


def record_test_thread_sleeps(monkeypatch: pytest.MonkeyPatch, side_effect: Any = None) -> Mock:
    """Patch ``time.sleep``; record (and skip) only the calling thread's sleeps.

    A bare ``Mock`` on ``time.sleep`` also records sleeps from unrelated
    background threads in the test process, so exact sleep assertions were
    flaky in CI (363 recorded calls for a single retry wait). Other threads
    keep sleeping for real and are never recorded.
    """
    recorder = Mock(side_effect=side_effect)
    real_sleep = time.sleep
    test_thread = threading.get_ident()

    def sleep(seconds: float) -> Any:
        if threading.get_ident() == test_thread:
            return recorder(seconds)
        return real_sleep(seconds)

    monkeypatch.setattr("time.sleep", sleep)
    return recorder


def response(
    status: int = 200,
    body: Any = None,
    headers: Mapping[str, str] | None = None,
) -> requests.Response:
    """Return a ``requests.Response`` with *status*, a JSON *body* and *headers*."""
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(body or {}).encode()
    resp.headers.update(headers or {})
    return resp


def batch_response(
    parts: Iterable[tuple[Any, int, Any]],
    *,
    nested: bool = True,
) -> requests.Response:
    """Return a Dynamics ``$batch`` multipart response.

    Each part is ``(content_id, status, payload)``. With *nested* (the
    default), the parts sit inside one changeset, as Dynamics returns them for
    a transactional batch.
    """
    body = ["--batch_response"]
    if nested:
        body += ["Content-Type: multipart/mixed; boundary=changeset_response", ""]
    for i, (content_id, status, payload) in enumerate(parts):
        if nested:
            body.append("--changeset_response")
        elif i:
            body.append("--batch_response")
        body += ["Content-Type: application/http", "Content-Transfer-Encoding: binary"]
        if content_id is not None:
            body.append(f"Content-ID: {content_id}")
        body += ["", f"HTTP/1.1 {status} Result", "Content-Type: application/json", "", json.dumps(payload)]
    if nested:
        body.append("--changeset_response--")
    body.append("--batch_response--")
    resp = response(headers={"Content-Type": "multipart/mixed; boundary=batch_response"})
    resp._content = "\r\n".join(body).encode()
    return resp
