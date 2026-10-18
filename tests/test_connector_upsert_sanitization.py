"""CRM upserts must serialize real DataFrame values before sending HTTP (#1424)."""

import csv
import io
import json
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector


def _response(body, *, content_type="application/json", status=200):
    response = requests.Response()
    response.status_code = status
    response.headers["Content-Type"] = content_type
    text = json.dumps(body) if content_type == "application/json" else body
    response._content = text.encode("utf-8")
    return response


def _mock_http(monkeypatch, responses):
    # Mock only the transport: Session.request still prepares/encodes the body.
    # Patch all sessions so these tests cannot accidentally reach the network.
    send = Mock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "send", send)
    return send


def _connector(provider):
    if provider == "salesforce":
        connector = SalesforceConnector(
            client_id="test-id", client_secret="test-secret", retry_attempts=1,
        )
        connector._instance_url = "https://salesforce.example.test"
    elif provider == "hubspot":
        connector = HubSpotConnector(access_token="test-token", retry_attempts=1)
    elif provider == "zoho":
        connector = ZohoConnector(
            client_id="test-id", client_secret="test-secret", retry_attempts=1,
        )
    else:
        # Bypass MSAL initialization, which can perform tenant discovery.
        connector = DynamicsConnector.__new__(DynamicsConnector)
        connector._environment_url = "https://dynamics.example.test"
        connector._timeout = 30
        connector._session = requests.Session()
    connector._authenticated = True
    connector._token_expires_at = None
    connector._access_token = "test-token"
    return connector


@pytest.fixture(params=["nan_and_timestamp", "nan", "timestamp", "valid"])
def upsert_rows(request):
    valid = {
        "external_id": "valid",
        "name": 'A "quoted", multiline\nname',
        "amount": 12.5,
        "occurred_at": "2026-10-18T12:34:56+00:00",
        "active": True,
        "count": 3,
        "note": "",
        "date": "2026-10-18",
        "nullable": 0,
    }
    changed = {**valid, "external_id": "changed"}
    expected = changed.copy()
    if request.param in ("nan_and_timestamp", "nan"):
        changed["amount"] = float("nan")
        expected.pop("amount")
    if request.param == "nan_and_timestamp":
        changed.update(note=None, date=pd.NaT, nullable=pd.NA)
        for key in ("note", "date", "nullable"):
            expected.pop(key)
    if request.param in ("nan_and_timestamp", "timestamp"):
        changed["occurred_at"] = pd.Timestamp("2026-10-18T12:34:56.123456-05:00")
        expected["occurred_at"] = "2026-10-18T12:34:56.123456-05:00"
    # Keep the fully valid row's existing ISO string and native types intact.
    frame = pd.DataFrame([changed, valid], dtype=object)
    return frame, [expected, valid]


def _reject_non_json_constant(value):
    raise AssertionError(f"Invalid JSON constant in HTTP body: {value}")


@pytest.mark.parametrize("provider", ["salesforce", "hubspot", "zoho", "dynamics"])
def test_upsert_records_sends_sanitized_json(provider, upsert_rows, monkeypatch):
    frame, expected = upsert_rows
    original = frame.copy(deep=True)
    connector = _connector(provider)
    if provider == "salesforce":
        response = _response([
            {"success": True, "id": value, "created": False}
            for value in ("changed", "valid")
        ])
        object_type = "Contact"
    elif provider == "hubspot":
        response = _response({"results": [{"id": "changed"}, {"id": "valid"}]})
        object_type = "contacts"
    elif provider == "zoho":
        response = _response({"data": [
            {"status": "success", "action": "update", "details": {"id": value}}
            for value in ("changed", "valid")
        ]})
        object_type = "Contacts"
    else:
        response = _response("", content_type="multipart/mixed", status=202)
        object_type = "contacts"
    send = _mock_http(monkeypatch, [response])

    result = connector.upsert_records(object_type, frame, "external_id")

    assert result.success_count == 2
    assert result.failure_count == 0
    assert result.errors == []
    assert result.updated_ids == ["changed", "valid"]
    send.assert_called_once()
    request = send.call_args.args[0]
    body = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
    if provider == "dynamics":
        assert request.method == "POST"
        assert request.url.endswith("/$batch")
        # Each application/http part has one JSON body. Reject NaN explicitly:
        # json.loads accepts that invalid JSON extension unless told otherwise.
        payloads = [
            json.loads(line, parse_constant=_reject_non_json_constant)
            for line in body.split("\r\n") if line.startswith("{")
        ]
    else:
        payload = json.loads(body, parse_constant=_reject_non_json_constant)
        if provider == "salesforce":
            assert request.method == "PATCH"
            assert payload["allOrNone"] is False
            payloads = payload["records"]
            for row in payloads:
                assert row.pop("attributes") == {"type": "Contact"}
        elif provider == "hubspot":
            assert request.method == "POST"
            assert [row["id"] for row in payload["inputs"]] == ["changed", "valid"]
            assert all(row["idProperty"] == "external_id" for row in payload["inputs"])
            payloads = [row["properties"] for row in payload["inputs"]]
        else:
            assert request.method == "POST"
            assert payload["duplicate_check_fields"] == ["external_id"]
            payloads = payload["data"]
    # Exact equality checks omissions, ISO formatting, and the unchanged valid row.
    assert payloads == expected
    pd.testing.assert_frame_equal(frame, original)


def test_salesforce_bulk_upsert_sends_sanitized_csv(upsert_rows, monkeypatch):
    frame, expected = upsert_rows
    original = frame.copy(deep=True)
    connector = _connector("salesforce")
    send = _mock_http(monkeypatch, [
        _response({"id": "job-1"}),
        _response("", content_type="text/csv", status=201),
        _response({"state": "UploadComplete"}),
        _response({
            "state": "JobComplete", "numberRecordsProcessed": 2, "numberRecordsFailed": 0,
        }),
        _response("sf__Id,sf__Created\nchanged,false\nvalid,false\n", content_type="text/csv"),
    ])

    result = connector.upsert_records("Contact", frame, "external_id", force_bulk=True)

    assert result.success_count == 2
    assert result.failure_count == 0
    assert result.errors == []
    assert result.updated_ids == ["changed", "valid"]
    assert send.call_count == 5
    requests_sent = [call.args[0] for call in send.call_args_list]
    upload = requests_sent[1]
    assert upload.method == "PUT"
    assert upload.url.endswith("/job-1/batches")
    assert upload.headers["Content-Type"] == "text/csv"
    rows = list(csv.DictReader(io.StringIO(upload.body.decode("utf-8"))))
    # CSV retains the header and represents omitted fields with empty cells.
    assert rows == [
        {column: str(row[column]) if column in row else "" for column in frame.columns}
        for row in expected
    ]
    pd.testing.assert_frame_equal(frame, original)
