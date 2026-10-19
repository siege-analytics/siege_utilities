"""CRM upserts must serialize real DataFrame values before sending HTTP (#1424)."""

import csv
import io
import json
from decimal import Decimal
from unittest.mock import Mock, call

import numpy as np
import pandas as pd
import pytest
import requests

from siege_utilities.connectors._protocol import ConnectorError
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


@pytest.mark.parametrize("provider,object_type", [
    ("salesforce", "Account"), ("hubspot", "contacts"),
    ("zoho", "Contacts"), ("dynamics", "contacts"),
])
def test_encoding_error_keeps_connector_error_contract(provider, object_type, monkeypatch):
    connector = _connector(provider)
    connector._retry_attempts = 3
    connector._retry_backoff = 2
    send = Mock(side_effect=AssertionError("no HTTP expected"))
    sleep = Mock(side_effect=AssertionError("no backoff expected"))
    monkeypatch.setattr(requests.Session, "send", send)
    monkeypatch.setattr("time.sleep", sleep)
    request = Mock(wraps=connector._session.request)
    monkeypatch.setattr(connector._session, "request", request)

    with pytest.raises(ConnectorError, match="JSON") as exc_info:
        connector.create_record(object_type, {"Name": "x", "AnnualRevenue": float("nan")})

    assert isinstance(exc_info.value.__cause__, requests.exceptions.InvalidJSONError)
    assert request.call_count == 1
    send.assert_not_called()
    sleep.assert_not_called()


@pytest.mark.parametrize("provider,object_type", [
    ("salesforce", "Account"), ("hubspot", "contacts"),
    ("zoho", "Contacts"), ("dynamics", "contacts"),
])
def test_transport_errors_keep_three_attempts_and_two_backoffs(provider, object_type, monkeypatch):
    connector = _connector(provider)
    connector._retry_attempts = 3
    connector._retry_backoff = 2
    send = Mock(side_effect=requests.exceptions.ConnectionError("connection failed"))
    sleep = Mock()
    monkeypatch.setattr(requests.Session, "send", send)
    monkeypatch.setattr("time.sleep", sleep)
    request = Mock(wraps=connector._session.request)
    monkeypatch.setattr(connector._session, "request", request)

    with pytest.raises(ConnectorError):
        connector.create_record(object_type, {"name": "test"})

    assert request.call_count == 3
    assert send.call_count == 3
    assert sleep.call_args_list == [call(2), call(4)]


def test_zoho_nested_numpy_boolean_preserves_object(monkeypatch):
    connector = _connector("zoho")
    send = _mock_http(monkeypatch, [_response({"data": [{
        "status": "success", "action": "update", "details": {"id": "test"},
    }]})])
    frame = pd.DataFrame([{
        "Email": "lead@example.test",
        "Last_Name": "Test",
        "Foreign_Languages": ["Korean"],
        "$append_values": {"Foreign_Languages": np.bool_(True)},
    }], dtype=object)

    connector.upsert_records("Leads", frame, "Email")

    send.assert_called_once()
    row = json.loads(send.call_args.args[0].body)["data"][0]
    assert isinstance(row["$append_values"], dict)
    assert row["$append_values"]["Foreign_Languages"] is True


@pytest.mark.parametrize("provider", ["salesforce", "hubspot", "zoho", "dynamics"])
def test_nested_upsert_values_preserve_http_types(provider, monkeypatch):
    connector = _connector(provider)
    if provider == "salesforce":
        response = _response([{"success": True, "id": "test", "created": False}])
    elif provider == "hubspot":
        response = _response({"results": [{"id": "test"}]})
    elif provider == "zoho":
        response = _response({"data": [{
            "status": "success", "action": "update", "details": {"id": "test"},
        }]})
    else:
        response = _response("", content_type="multipart/mixed", status=202)
    send = _mock_http(monkeypatch, [response])
    frame = pd.DataFrame([{
        "external_id": "test",
        "nested": {
            "id": np.int64(7), "amount": Decimal("12.50"),
            "ratio": np.float32(1.5), "active": np.bool_(True),
            "nan": np.nan, "nat": pd.NaT, "na": pd.NA, "none": None,
            "items": [None, np.nan, pd.NaT, pd.NA, {
                "date": pd.Timestamp("2026-01-02T12:34:56Z"),
                "quantity": np.int64(2), "missing": pd.NA,
                "more": [{"flag": np.bool_(False)}, [np.int64(3), np.nan]],
            }],
        },
    }], dtype=object)

    connector.upsert_records("contacts", frame, "external_id")

    send.assert_called_once()
    body = send.call_args.args[0].body
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    if provider == "dynamics":
        rows = [json.loads(line, parse_constant=_reject_non_json_constant)
                for line in body.split("\r\n") if line.startswith("{")]
        assert len(rows) == 1
        row = rows[0]
    else:
        payload = json.loads(body, parse_constant=_reject_non_json_constant)
        if provider == "salesforce":
            row = payload["records"][0]
        elif provider == "hubspot":
            row = payload["inputs"][0]["properties"]
        else:
            row = payload["data"][0]
    nested = row["nested"]
    assert isinstance(nested, dict)
    assert nested == {
        "id": 7, "amount": "12.50", "ratio": 1.5, "active": True,
        "items": [None, None, None, None, {
            "date": "2026-01-02T12:34:56+00:00", "quantity": 2,
            "more": [{"flag": False}, [3, None]],
        }],
    }
    assert type(nested["id"]) is int
    assert type(nested["amount"]) is str
    assert type(nested["ratio"]) is float
    assert nested["active"] is True
    assert isinstance(nested["items"], list)
    assert isinstance(nested["items"][4], dict)
    assert type(nested["items"][4]["quantity"]) is int
    assert nested["items"][4]["more"][0]["flag"] is False


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
