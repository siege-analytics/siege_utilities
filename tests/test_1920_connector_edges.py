"""CRM connector edges from #1920 item 3.

3a: a request that is sent once (POST, PATCH, the Dynamics ``$batch`` POST and
any single-attempt raw transfer) and gets HTTP 429 waits at most once before it
raises ``ConnectorRateLimitError``.

3c: the Salesforce Bulk API CSV upload is a PUT but is not safe to resend after
an uncertain failure. A transport failure or a 5xx raises ``ConnectorError``
without a second upload. The single 401 refresh replay and the resend after a
429 wait still apply, because both responses prove nothing was processed.

3d: ``dataclasses.replace`` cannot carry an ``UpsertResult`` redactor; the copy
uses key-based redaction unless the caller passes ``redact=`` again.

Item 4: Salesforce ``is_connected()`` stays True after a rejected request; the
CHANGELOG correction states this, and the test pins it.
"""
from __future__ import annotations

import copy
import dataclasses
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.connectors._http import request_raw
from siege_utilities.connectors._protocol import (
    ConnectorAuthError, ConnectorError, ConnectorRateLimitError, UpsertResult,
)
from tests.crm_connector_factories import batch_response, connector, record_test_thread_sleeps, response

PROVIDERS = ["dynamics", "hubspot", "salesforce", "zoho"]


def raw_connector(attempts: int = 3) -> SimpleNamespace:
    return SimpleNamespace(_retry_attempts=attempts, _retry_backoff=0, _max_retry_wait=900.0)


# -- 3a: a single-attempt 429 waits at most once -------------------------------

@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("provider", PROVIDERS)
def test_single_attempt_request_429_waits_once(monkeypatch, provider: str, method: str) -> None:
    sleeps = record_test_thread_sleeps(monkeypatch)
    c = connector(provider)
    c._session.request = Mock(return_value=response(429, {}, {"Retry-After": "2"}))

    with pytest.raises(ConnectorRateLimitError):
        c.request(method, "/x", json_body={"a": 1})

    assert c._session.request.call_count == 1
    assert [call.args for call in sleeps.call_args_list] == [(2.0,)]


def test_single_attempt_raw_transfer_429_waits_once(monkeypatch) -> None:
    sleeps = record_test_thread_sleeps(monkeypatch)
    send = Mock(return_value=response(429, {}, {"Retry-After": "2"}))

    with pytest.raises(ConnectorRateLimitError):
        request_raw(raw_connector(), "POST", send, None)

    assert send.call_count == 1
    assert [call.args for call in sleeps.call_args_list] == [(2.0,)]


@pytest.mark.parametrize("batch_reply", [
    response(429, {}, {"Retry-After": "2"}),
    batch_response([(1, 429, {})]),
], ids=["outer-429", "changeset-part-429"])
def test_dynamics_batch_429_waits_once(monkeypatch, batch_reply: requests.Response) -> None:
    sleeps = record_test_thread_sleeps(monkeypatch)
    c = connector("dynamics")
    c._session.post = Mock(return_value=batch_reply)

    with pytest.raises(ConnectorRateLimitError):
        c.upsert_records("contacts", pd.DataFrame([{"key": "a"}]), "key")

    assert c._session.post.call_count == 1
    assert sleeps.call_count == 1


# -- 3c: the Salesforce bulk upload is sent once --------------------------------

@pytest.mark.parametrize("failure", [
    requests.exceptions.ConnectionError("connection reset"),
    response(503, {}),
], ids=["transport-error", "server-error"])
def test_salesforce_bulk_upload_is_not_resent_after_an_uncertain_failure(monkeypatch, failure) -> None:
    sleeps = record_test_thread_sleeps(monkeypatch)
    c = connector("salesforce")
    c._session.put = Mock(side_effect=[failure, response(201, {})])

    with pytest.raises(ConnectorError, match="after 1 attempts"):
        c._bulk_upload_data("750000000000001", "key\na\n")

    assert c._session.put.call_count == 1
    assert sleeps.call_count == 0


def test_salesforce_bulk_job_stops_before_closing_when_the_upload_fails(monkeypatch) -> None:
    record_test_thread_sleeps(monkeypatch)
    c = connector("salesforce")
    # Only the job-creation POST is answered; a close or poll request would
    # exhaust the mock and fail the test instead of polling forever.
    c._session.request = Mock(side_effect=[response(200, {"id": "750000000000001"})])
    c._session.put = Mock(side_effect=[requests.exceptions.ConnectionError("reset"), response(201, {})])

    with pytest.raises(ConnectorError, match="after 1 attempts"):
        c._bulk_upsert("Contact", pd.DataFrame([{"Ext__c": "a"}]), "Ext__c")

    assert c._session.put.call_count == 1
    assert [call.args[0] for call in c._session.request.call_args_list] == ["POST"]


def test_salesforce_bulk_upload_still_replays_once_after_a_token_refresh(monkeypatch) -> None:
    record_test_thread_sleeps(monkeypatch)
    c = connector("salesforce")
    c._refresh_token = "dummy-refresh-token-1920"
    c.refresh_access_token = Mock()
    c._session.put = Mock(side_effect=[response(401, {}), response(201, {})])

    c._bulk_upload_data("750000000000001", "key\na\n")

    assert c._session.put.call_count == 2
    c.refresh_access_token.assert_called_once_with()


def test_raw_put_resends_a_5xx_unless_uncertain_retries_are_off(monkeypatch) -> None:
    record_test_thread_sleeps(monkeypatch)
    default_send = Mock(side_effect=[response(503, {}), response(503, {}), response(200, {})])
    certain_send = Mock(side_effect=[response(503, {}), response(200, {})])

    assert request_raw(raw_connector(), "PUT", default_send, None).status_code == 200
    with pytest.raises(ConnectorError, match="after 1 attempts: HTTP 503"):
        request_raw(raw_connector(), "PUT", certain_send, None, retry_uncertain=False)

    assert (default_send.call_count, certain_send.call_count) == (3, 1)


def test_raw_put_still_resends_after_a_429_when_uncertain_retries_are_off(monkeypatch) -> None:
    sleeps = record_test_thread_sleeps(monkeypatch)
    send = Mock(side_effect=[response(429, {}, {"Retry-After": "2"}), response(201, {})])

    assert request_raw(raw_connector(), "PUT", send, None, retry_uncertain=False).status_code == 201

    assert send.call_count == 2
    assert [call.args for call in sleeps.call_args_list] == [(2.0,)]


# -- 3d: dataclasses.replace and the redactor ----------------------------------

def test_replace_drops_the_redactor_unless_it_is_passed_again() -> None:
    redactor = connector("hubspot")._redact_field
    result = UpsertResult(success_count=1, failure_count=0, created_ids=["a"], redact=redactor)

    assert dataclasses.replace(result, success_count=2)._redact is None
    assert dataclasses.replace(result, success_count=2, redact=result._redact)._redact == redactor
    assert copy.copy(result)._redact == redactor


def test_replaced_copy_repr_uses_key_based_redaction_only() -> None:
    c = connector("hubspot")
    secret_id = c._access_token
    result = UpsertResult(success_count=1, failure_count=0, created_ids=[secret_id], redact=c._redact_field)

    assert secret_id not in repr(result)
    assert secret_id in repr(dataclasses.replace(result, success_count=2))
    assert secret_id not in repr(dataclasses.replace(result, success_count=2, redact=result._redact))


def test_upsert_result_documents_how_replace_treats_the_redactor() -> None:
    doc = UpsertResult.__doc__ or ""

    assert "dataclasses.replace" in doc
    assert "redact=" in doc


# -- item 4: Salesforce is_connected() after a rejected request ----------------

@pytest.mark.parametrize("status", [401, 403])
def test_salesforce_is_connected_stays_true_after_a_rejected_request(status: int) -> None:
    c = connector("salesforce")
    c._refresh_token = None
    c._session.request = Mock(return_value=response(status, [{"message": "Session expired or invalid"}]))
    assert c.is_connected() is True

    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/services/data/v59.0/sobjects")

    assert c.is_connected() is True
