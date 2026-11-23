"""Dynamics batch upserts keep completed batches; Dynamics output shapes are pinned.

#1920 item 1: a Dynamics upsert splits records into batches. A later batch that
fails in transport or with a server error is reported as per-record failures,
and the batches before and after it still count, matching HubSpot and Zoho.
Authentication and rate-limit errors still stop the whole upsert (#1417).

#1920 item 2: ``get_objects`` keeps the formatted-value annotation columns that
Dynamics returns for annotated fields, and ``request()`` returns
``{"OData-EntityId": ...}`` (or ``{}``) on a 204. Both are documented
behavior; these tests pin the documented shapes.
"""
from __future__ import annotations

import json
import logging
from unittest.mock import Mock
from urllib.parse import quote, quote_plus

import pandas as pd
import pytest
import requests

import siege_utilities.connectors.dynamics as dynamics_module
from siege_utilities.connectors._protocol import ConnectorAuthError, ConnectorError, ConnectorRateLimitError
from tests.crm_connector_factories import batch_response, connector, record_test_thread_sleeps, response

ANNOTATION = "OData.Community.Display.V1.FormattedValue"


@pytest.fixture
def three_single_record_batches(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(dynamics_module, "BATCH_SIZE", 1)
    record_test_thread_sleeps(monkeypatch)
    c = connector("dynamics")
    frame = pd.DataFrame([{"key": "a"}, {"key": "b"}, {"key": "c"}])
    return c, frame


def created() -> requests.Response:
    return batch_response([(1, 201, {})])


@pytest.mark.parametrize("failure", [
    response(503, {"error": {"message": "service unavailable"}}),
    requests.exceptions.ConnectionError("connection reset"),
], ids=["server-error", "transport-error"])
def test_a_failed_later_batch_becomes_per_record_failures(three_single_record_batches, failure) -> None:
    c, frame = three_single_record_batches
    c._session.post = Mock(side_effect=[created(), failure, created()])

    result = c.upsert_records("contacts", frame, "key")

    assert (result.success_count, result.failure_count) == (2, 1)
    assert result.created_ids == ["a", "c"]
    assert [e.record_index for e in result.errors] == [1]
    assert result.errors[0].message.startswith("Dynamics batch failed: ")
    assert c._session.post.call_count == 3


# -- A caught batch error never returns a configured credential (#1920) -------
# _batch_upsert reaches request_raw without crossing the public redaction
# boundary, so the conversion to UpsertError must redact the exception text
# itself, by configured value, in every encoding, and fail closed.

ECHOED_TOKEN = 'tok/en+1920 "q"&x=y'
ECHO_FORMS = {
    "raw": ECHOED_TOKEN,
    "url-encoded": quote(ECHOED_TOKEN, safe=""),
    "quote-plus": quote_plus(ECHOED_TOKEN),
    "json-escaped": json.dumps(ECHOED_TOKEN)[1:-1],
}


def assert_echo_absent(result, caplog, secrets) -> None:
    """One failure for the middle record, later success kept, no secret form anywhere."""
    assert (result.success_count, result.failure_count) == (2, 1)
    assert result.created_ids == ["a", "c"]
    assert [e.record_index for e in result.errors] == [1]
    rendered = [result.errors[0].message, repr(result.errors[0]), repr(result)]
    rendered += [record.getMessage() for record in caplog.records]
    for text in rendered:
        for secret in secrets:
            assert secret not in text


@pytest.mark.parametrize("form", ECHO_FORMS)
def test_a_failed_batch_does_not_return_an_echoed_credential(three_single_record_batches, caplog, form) -> None:
    c, frame = three_single_record_batches
    c._access_token = ECHOED_TOKEN
    echo = ConnectorError("opaque upstream echo " + ECHO_FORMS[form])
    c._session.post = Mock(side_effect=[created(), echo, created()])
    caplog.set_level(logging.DEBUG)

    result = c.upsert_records("contacts", frame, "key")

    assert_echo_absent(result, caplog, ECHO_FORMS.values())
    assert result.errors[0].message.startswith("Dynamics batch failed: opaque upstream echo ")
    sent = [call.kwargs["headers"]["Authorization"] for call in c._session.post.call_args_list]
    assert sent == [f"Bearer {ECHOED_TOKEN}"] * 3


class OfflineEchoAdapter(requests.adapters.HTTPAdapter):
    """Answers from a script and never calls the network implementation."""

    def __init__(self, replies) -> None:
        super().__init__()
        self.replies = list(replies)
        self.authorization: list[str | None] = []

    def send(self, request, **kwargs):
        self.authorization.append(request.headers.get("Authorization"))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        reply.request = request
        reply.url = request.url
        return reply


def test_a_failed_batch_through_a_real_session_does_not_return_the_credential(
    three_single_record_batches, caplog,
) -> None:
    c, frame = three_single_record_batches
    c._access_token = ECHOED_TOKEN
    adapter = OfflineEchoAdapter([created(), ConnectorError("opaque upstream echo " + ECHOED_TOKEN), created()])
    c._session = requests.Session()
    c._session.mount("https://", adapter)
    caplog.set_level(logging.DEBUG)

    result = c.upsert_records("contacts", frame, "key")

    assert_echo_absent(result, caplog, ECHO_FORMS.values())
    assert adapter.authorization == [f"Bearer {ECHOED_TOKEN}"] * 3
    assert adapter.replies == []


def test_a_failed_batch_message_is_withheld_when_a_credential_is_too_short(three_single_record_batches, caplog) -> None:
    c, frame = three_single_record_batches
    c._access_token = "q7z"
    c._session.post = Mock(side_effect=[created(), ConnectorError("opaque upstream echo q7z"), created()])
    caplog.set_level(logging.DEBUG)

    result = c.upsert_records("contacts", frame, "key")

    assert_echo_absent(result, caplog, ["q7z"])
    assert result.errors[0].message == "Dynamics batch failed: [REDACTED]"


class UnreadableHeaders(dict):
    """A session header mapping whose lookups fail, so secret collection cannot complete."""

    def get(self, key, default=None):
        raise RuntimeError("header lookup failed")


def test_a_failed_batch_message_is_withheld_when_secret_collection_fails(three_single_record_batches, caplog) -> None:
    c, frame = three_single_record_batches
    c._access_token = ECHOED_TOKEN
    c._session.headers = UnreadableHeaders()
    c._session.post = Mock(side_effect=[created(), ConnectorError("opaque upstream echo " + ECHOED_TOKEN), created()])
    caplog.set_level(logging.DEBUG)

    result = c.upsert_records("contacts", frame, "key")

    assert_echo_absent(result, caplog, ECHO_FORMS.values())
    assert result.errors[0].message == "Dynamics batch failed: [REDACTED]"


def test_a_failed_first_batch_keeps_the_later_ones(three_single_record_batches) -> None:
    c, frame = three_single_record_batches
    c._session.post = Mock(side_effect=[response(502, {}), created(), created()])

    result = c.upsert_records("contacts", frame, "key")

    assert (result.success_count, result.failure_count) == (2, 1)
    assert [e.record_index for e in result.errors] == [0]


def test_authentication_failure_still_stops_the_upsert(three_single_record_batches) -> None:
    c, frame = three_single_record_batches
    c._session.post = Mock(side_effect=[created(), response(401, {}), created()])

    with pytest.raises(ConnectorAuthError):
        c.upsert_records("contacts", frame, "key")

    assert c._session.post.call_count == 2


def test_rate_limit_still_stops_the_upsert(three_single_record_batches) -> None:
    c, frame = three_single_record_batches
    c._session.post = Mock(side_effect=[created(), response(429, {}, {"Retry-After": "0"}), created()])

    with pytest.raises(ConnectorRateLimitError):
        c.upsert_records("contacts", frame, "key")

    assert c._session.post.call_count == 2


def test_an_invalid_match_field_still_raises(three_single_record_batches) -> None:
    c, frame = three_single_record_batches
    c._session.post = Mock(side_effect=AssertionError("must not send"))

    with pytest.raises(ValueError, match="Invalid CRM identifier"):
        c.upsert_records("contacts", frame, "key; drop")


def test_get_objects_keeps_formatted_value_annotation_columns() -> None:
    c = connector("dynamics")
    body = {"value": [{"accountid": "1", "industrycode": 3, f"industrycode@{ANNOTATION}": "Retail"}]}
    c._session.request = Mock(return_value=response(200, body))

    frame = c.get_objects("accounts", fields=["accountid", "industrycode"])

    assert list(frame.columns) == ["accountid", "industrycode", f"industrycode@{ANNOTATION}"]
    assert frame.loc[0, f"industrycode@{ANNOTATION}"] == "Retail"


@pytest.mark.parametrize("headers,expected", [
    ({"OData-EntityId": "https://dynamics.example.test/api/data/v9.2/accounts(1)"},
     {"OData-EntityId": "https://dynamics.example.test/api/data/v9.2/accounts(1)"}),
    ({}, {}),
], ids=["entity-id-header", "no-header"])
def test_request_on_204_returns_the_entity_id_mapping_or_empty(headers: dict, expected: dict) -> None:
    c = connector("dynamics")
    c._session.request = Mock(return_value=response(204, {}, headers))

    assert c.request("PATCH", "/api/data/v9.2/accounts(1)", json_body={"name": "x"}) == expected
