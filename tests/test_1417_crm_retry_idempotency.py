"""Regression tests for safe CRM retries and batch outcomes (#1417)."""

import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.connectors._protocol import (
    ConnectorAuthError, ConnectorError, ConnectorRateLimitError,
)
from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector


def connector(provider):
    if provider == "salesforce":
        c = SalesforceConnector(client_id="id", client_secret="secret")
        c._instance_url = "https://salesforce.example.test"
    elif provider == "hubspot":
        c = HubSpotConnector(access_token="token")
    elif provider == "zoho":
        c = ZohoConnector(client_id="id", client_secret="secret")
    else:
        c = DynamicsConnector.__new__(DynamicsConnector)
        c._environment_url = "https://dynamics.example.test"
        c._session = requests.Session()
        c._timeout = 30
    c._authenticated = True
    c._token_expires_at = None
    c._access_token = "token"
    c._retry_attempts = 3
    c._retry_backoff = 0
    return c


def response(status=200, body=None, headers=None):
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(body or {}).encode()
    resp.headers.update(headers or {})
    return resp


@pytest.fixture(autouse=True)
def sleep(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr("time.sleep", sleep)
    return sleep


@pytest.mark.parametrize("provider", ["salesforce", "hubspot", "zoho", "dynamics"])
@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("failure", ["timeout", "server_error"])
def test_non_idempotent_requests_are_sent_once(provider, method, failure):
    c = connector(provider)
    send = (
        Mock(side_effect=requests.Timeout("committed, response lost"))
        if failure == "timeout" else Mock(return_value=response(503))
    )
    c._session.request = send
    with pytest.raises(ConnectorError):
        c.request(method, "/records", json_body={"name": "Acme"})
    assert send.call_count == 1


@pytest.mark.parametrize("provider", ["salesforce", "hubspot", "zoho", "dynamics"])
@pytest.mark.parametrize("method", ["GET", "put", "DELETE"])
def test_idempotent_requests_still_retry(provider, method):
    c = connector(provider)
    c._session.request = Mock(side_effect=[requests.Timeout(), response()])
    assert c.request(method, "/records") == {}
    assert c._session.request.call_count == 2


@pytest.mark.parametrize("provider", ["salesforce", "hubspot", "zoho", "dynamics"])
def test_rate_limit_backs_off_before_safe_retry(provider, sleep):
    c = connector(provider)
    c._session.request = Mock(side_effect=[response(429, headers={"Retry-After": "7"}), response()])
    assert c.request("GET", "/records") == {}
    sleep.assert_called_once_with(7.0)
    assert c._session.request.call_count == 2


@pytest.mark.parametrize("provider", ["hubspot", "zoho"])
@pytest.mark.parametrize("status,error", [
    (401, ConnectorAuthError), (403, ConnectorAuthError), (429, ConnectorRateLimitError),
])
def test_batch_stops_on_auth_or_rate_limit(provider, status, error, sleep):
    c = connector(provider)
    c._session.request = Mock(return_value=response(status, headers={"Retry-After": "7"}))
    with pytest.raises(error):
        c.upsert_records("contacts", pd.DataFrame({"external_id": range(101)}), "external_id")
    assert c._session.request.call_count == 1
    if status == 429:
        sleep.assert_called_once_with(7.0)


@pytest.mark.parametrize("status,error", [(401, ConnectorAuthError), (429, ConnectorRateLimitError), (503, ConnectorError)])
def test_failed_hubspot_validation_leaves_disconnected(status, error):
    c = connector("hubspot")
    c._session.request = Mock(return_value=response(status, headers={"Retry-After": "0"}))
    with pytest.raises(error):
        c.authenticate()
    assert not c.is_connected()


@pytest.mark.parametrize("retry_after", ["invalid", "-1", "nan", "inf", None, "date"])
def test_retry_after_values_remain_typed_rate_limit_errors(retry_after, sleep):
    c = connector("hubspot")
    if retry_after == "date":
        retry_after = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    c._session.request = Mock(return_value=response(429, headers=headers))
    with pytest.raises(ConnectorRateLimitError):
        c.request("POST", "/records")
    assert c._session.request.call_count == 1
    assert sleep.call_count == 1
    assert 0 <= sleep.call_args.args[0] <= 30


def batch_response(parts, *, nested=True):
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


@pytest.mark.parametrize("nested", [True, False])
def test_failed_changeset_marks_all_rolled_back_records_failed(nested):
    c = connector("dynamics")
    c._session.post = Mock(return_value=batch_response([
        (2, 400, {"error": {"code": "bad_key", "message": "Invalid alternate key"}}),
    ], nested=nested))
    result = c._batch_upsert("contacts", [{"key": "a"}, {"key": "b"}], "key", base_index=1000)
    assert not result.ok
    assert result.success_count == 0
    assert result.failure_count == 2
    assert {e.record_index for e in result.errors} == {1000, 1001}
    assert "Invalid alternate key" in result.errors[1].message
    assert result.errors[1].code == "bad_key"
    assert result.updated_ids == []


def test_batch_successes_are_matched_by_content_id():
    c = connector("dynamics")
    c._session.post = Mock(return_value=batch_response([(2, 204, {}), (1, 201, {})]))
    result = c._batch_upsert("contacts", [{"key": "a"}, {"key": "b"}], "key")
    assert result.ok
    assert result.success_count == 2
    assert result.created_ids == ["a"]
    assert result.updated_ids == ["b"]


def test_non_json_batch_failure_preserves_error_details():
    c = connector("dynamics")
    resp = batch_response([(1, 500, {})])
    resp._content = resp.content.replace(b"{}", b"Upstream service unavailable")
    c._session.post = Mock(return_value=resp)
    result = c._batch_upsert("contacts", [{"key": "a"}, {"key": "b"}], "key")
    assert result.success_count == 0
    assert result.failure_count == 2
    assert {error.record_index for error in result.errors} == {0, 1}
    assert all("HTTP 500: Upstream service unavailable" in error.message for error in result.errors)
    assert all(error.code == "500" for error in result.errors)


def test_successful_part_in_failed_atomic_changeset_is_rolled_back():
    c = connector("dynamics")
    c._session.post = Mock(return_value=batch_response([
        (1, 204, {}), (2, 400, {"error": {"message": "Invalid key"}}),
    ]))
    result = c._batch_upsert("contacts", [{"key": "a"}, {"key": "b"}], "key")
    assert result.success_count == 0
    assert result.failure_count == 2
    assert result.updated_ids == []


@pytest.mark.parametrize("parts", [[], [(1, 204, {})], [(1, 204, {}), (1, 204, {})]])
def test_incomplete_batch_response_cannot_report_full_success(parts):
    c = connector("dynamics")
    c._session.post = Mock(return_value=batch_response(parts))
    result = c._batch_upsert("contacts", [{"key": "a"}, {"key": "b"}], "key")
    assert not result.ok
    assert result.failure_count >= 1
    assert result.success_count + result.failure_count == 2


@pytest.mark.parametrize("status,error", [(401, ConnectorAuthError), (429, ConnectorRateLimitError)])
@pytest.mark.parametrize("inner", [False, True])
def test_dynamics_batch_propagates_auth_and_rate_limit(status, error, inner, sleep):
    c = connector("dynamics")
    resp = batch_response([(1, status, {})]) if inner else response(status, headers={"Retry-After": "7"})
    c._session.post = Mock(return_value=resp)
    with pytest.raises(error):
        c._batch_upsert("contacts", [{"key": "a"}], "key")
    c._session.post.assert_called_once()
    if status == 429:
        assert sleep.call_count == 1
