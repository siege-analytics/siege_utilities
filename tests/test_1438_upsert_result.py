"""Preserve input identity, committed writes, and Bulk job outcomes (#1438)."""

from datetime import datetime, timezone
from unittest.mock import Mock, call

import pandas as pd
import pytest
import requests

from siege_utilities.connectors._protocol import (
    ConnectorAuthError, ConnectorError, ConnectorRateLimitError,
)
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import API_VERSION, SalesforceConnector


def salesforce():
    return SalesforceConnector(client_id="id", client_secret="secret")


@pytest.mark.parametrize("index", [None, [10, 20, 30], ["first", "second", "third"]])
def test_hubspot_ticket_error_context_maps_to_input_index(index):
    connector = HubSpotConnector(access_token="token")
    frame = pd.DataFrame({"email": ["a@b.com", "b@c.com", "c@d.com"]}, index=index)
    connector.request = Mock(return_value={
        "results": [{"id": "saved", "new": True}],
        "errors": [{"category": "VALIDATION_ERROR", "message": "Invalid email",
                    "context": {"ids": ["c@d.com"]}}],
    })

    result = connector.upsert_records("contacts", frame, "email")

    assert result.errors[0].record_index == frame.index[2]
    assert result.failure_count == 1
    assert result.created_ids == ["saved"]


@pytest.fixture
def bulk_connector():
    connector = salesforce()
    connector._ensure_connected = Mock()
    connector._bulk_create_job = Mock(return_value="job-1")
    connector._bulk_upload_data = Mock()
    connector._bulk_close_job = Mock()
    connector._bulk_poll_job = Mock(return_value={
        "state": "JobComplete", "numberRecordsProcessed": 3, "numberRecordsFailed": 1,
    })
    connector._bulk_get_csv_results = Mock(side_effect=[
        [{"sf__Id": "created-1", "sf__Created": "true"},
         {"sf__Id": "updated-2", "sf__Created": "false"}],
        [{"sf__Id": "", "sf__Error": "INVALID_EMAIL_ADDRESS: Email is invalid: Email",
          "ExternalId__c": "c", "Email": "invalid"}],
    ])
    return connector


def bulk_frame(index=None):
    return pd.DataFrame({"ExternalId__c": ["a", "b", "c"],
                         "Email": ["a@b.com", "b@c.com", "invalid"]}, index=index)


@pytest.mark.parametrize("index", [None, [10, 20, 30], ["first", "second", "third"]])
@pytest.mark.parametrize("operation", ["insert", "upsert"])
def test_bulk_failed_csv_maps_to_input_index(bulk_connector, index, operation):
    frame = bulk_frame(index)
    if operation == "insert":
        result = bulk_connector.bulk_insert("Contact", frame)
    else:
        result = bulk_connector.upsert_records("Contact", frame, "ExternalId__c", force_bulk=True)
    assert result.errors[0].record_index == frame.index[2]
    assert result.created_ids == ["created-1"]
    assert result.updated_ids == ["updated-2"]
    assert result.success_count == 2
    assert result.failure_count == 1


def test_bulk_failure_code_is_separate_from_message(bulk_connector):
    result = bulk_connector.bulk_insert("Contact", bulk_frame())
    error = result.errors[0]
    assert error.code == "INVALID_EMAIL_ADDRESS"
    assert error.code != error.message
    assert error.message == "INVALID_EMAIL_ADDRESS: Email is invalid: Email"


def test_bulk_success_results_retrieval_failure_is_surfaced(bulk_connector):
    bulk_connector._bulk_poll_job.return_value["numberRecordsFailed"] = 0
    bulk_connector._bulk_get_csv_results.side_effect = ConnectorError("results unavailable")
    with pytest.raises(ConnectorError, match="results unavailable"):
        bulk_connector.bulk_insert("Contact", bulk_frame())


@pytest.mark.parametrize("error_type", [ConnectorError, ConnectorAuthError, ConnectorRateLimitError])
def test_composite_later_error_keeps_committed_results(error_type):
    connector = salesforce()
    error = error_type("batch two failed")
    connector.request = Mock(side_effect=[
        [{"success": True, "created": i < 20, "id": f"saved-{i}"} for i in range(24)]
        + [{"success": False, "errors": [{"statusCode": "INVALID_FIELD", "message": "bad"}]}],
        error,
    ])
    frame = pd.DataFrame({"ExternalId__c": range(51)})

    with pytest.raises(error_type) as caught:
        connector.upsert_records("Contact", frame, "ExternalId__c")

    assert caught.value is error
    partial = caught.value.partial_result
    assert partial.created_ids == [f"saved-{i}" for i in range(20)]
    assert partial.updated_ids == [f"saved-{i}" for i in range(20, 24)]
    assert partial.success_count == 24
    assert partial.failure_count == 1
    assert partial.errors[0].record_index == 24
    assert connector.request.call_count == 2


def test_bulk_timeout_aborts_job_before_raising(monkeypatch):
    connector = salesforce()
    connector.request = Mock(return_value={"state": "InProgress"})
    monkeypatch.setattr("siege_utilities.connectors.salesforce.time.monotonic", Mock(side_effect=[0, 601]))
    with pytest.raises(ConnectorError, match="timed out"):
        connector._bulk_poll_job("job-1", 3)
    connector.request.assert_called_once_with(
        "PATCH", f"/services/data/{API_VERSION}/jobs/ingest/job-1", json_body={"state": "Aborted"},
    )


def test_bulk_timeout_is_configurable(monkeypatch):
    connector = SalesforceConnector(client_id="id", client_secret="secret", bulk_timeout=1200)
    connector.request = Mock(return_value={"state": "JobComplete"})
    monkeypatch.setattr("siege_utilities.connectors.salesforce.time.monotonic", Mock(side_effect=[0, 601]))
    assert connector._bulk_poll_job("job-1", 3)["state"] == "JobComplete"
    assert connector.request.call_args.args[0] == "GET"


def test_hubspot_grouped_errors_in_second_batch_count_rows_once():
    connector = HubSpotConnector(access_token="token")
    frame = pd.DataFrame({"key": range(103)}, index=range(1000, 1103))
    connector.request = Mock(side_effect=[
        {"results": [{"id": f"saved-{i}"} for i in range(100)]},
        {"results": [{"id": "saved-101"}], "errors": [
            {"message": "invalid", "context": {"ids": ["102", "100"]}},
            {"message": "also invalid", "context": {"ids": ["102"]}},
        ]},
    ])
    result = connector.upsert_records("contacts", frame, "key")
    assert [error.record_index for error in result.errors] == [1100, 1102, 1102]
    assert result.failure_count == 2
    assert result.success_count == 101


@pytest.mark.parametrize("nested", [False, True])
def test_hubspot_write_trace_identifies_duplicate_match_values(nested):
    connector = HubSpotConnector(access_token="token")
    frame = pd.DataFrame({"email": ["same@example.com"] * 3}, index=["a", "b", "c"])

    def respond(method, path, *, json_body):
        traces = [entry["objectWriteTraceId"] for entry in json_body["inputs"]]
        assert len(set(traces)) == 3
        context = {"objectWriteTraceId": [traces[2]]}
        error = {"message": "invalid"}
        error.update({"errors": [{"context": context}]} if nested else {"context": context})
        return {"errors": [error]}

    connector.request = Mock(side_effect=respond)
    result = connector.upsert_records("contacts", frame, "email")
    assert result.failure_count == 1
    assert result.errors[0].record_index == "c"


@pytest.mark.parametrize("context", [{}, {"ids": ["unknown"]}])
def test_hubspot_unmapped_error_raises_with_known_writes(context):
    connector = HubSpotConnector(access_token="token")
    connector.request = Mock(return_value={
        "results": [{"id": "saved", "new": True}],
        "errors": [{"message": "invalid", "context": context}],
    })
    with pytest.raises(ConnectorError, match="context") as caught:
        connector.upsert_records("contacts", pd.DataFrame({"key": ["a", "b"]}), "key")
    assert caught.value.partial_result.created_ids == ["saved"]


def test_hubspot_duplicate_ids_require_trace_context():
    connector = HubSpotConnector(access_token="token")
    connector.request = Mock(return_value={
        "errors": [{"message": "invalid", "context": {"ids": ["same"]}}],
    })
    with pytest.raises(ConnectorError, match="unique input row"):
        connector.upsert_records("contacts", pd.DataFrame({"key": ["same", "same"]}), "key")


def test_bulk_reordered_errors_match_serialized_rows_with_duplicate_keys(bulk_connector):
    frame = pd.DataFrame({
        "ExternalId__c": ["same"] * 3,
        "Name": ["good", "O'Brien, Inc.", "two\nlines"],
        "When__c": [datetime(2024, 1, 1, tzinfo=timezone.utc)] * 3,
        "Optional__c": [None] * 3,
    }, index=[7, 11, 15])
    bulk_connector._bulk_poll_job.return_value["numberRecordsFailed"] = 2
    bulk_connector._bulk_get_csv_results.side_effect = [
        [{"sf__Id": "saved", "sf__Created": "true"}],
        [{"ExternalId__c": "same", "Name": name, "When__c": "2024-01-01T00:00:00+00:00",
          "Optional__c": "", "sf__Error": "INVALID_FIELD: bad value"}
         for name in ["two\nlines", "O'Brien, Inc."]],
    ]
    result = bulk_connector.upsert_records("Contact", frame, "ExternalId__c", force_bulk=True)
    assert [error.record_index for error in result.errors] == [15, 11]


@pytest.mark.parametrize("key_field,response_key", [("ExternalId__c", "ExternalId__c"), ("Id", "sf__Id")])
def test_bulk_unique_identifier_maps_sparse_failure(bulk_connector, key_field, response_key):
    frame = bulk_frame().rename(columns={"ExternalId__c": key_field})
    bulk_connector._bulk_get_csv_results.side_effect = [
        [{"sf__Id": "saved-1", "sf__Created": "true"},
         {"sf__Id": "saved-2", "sf__Created": "false"}],
        [{response_key: "c", "sf__Error": "INVALID_FIELD: bad"}],
    ]
    result = bulk_connector.upsert_records("Contact", frame, key_field, force_bulk=True)
    assert result.errors[0].record_index == 2


@pytest.mark.parametrize("failure", ["unmatched", "duplicate"])
def test_bulk_ambiguous_results_raise_with_known_writes(bulk_connector, failure):
    frame = bulk_frame()
    if failure == "duplicate":
        frame.iloc[1] = frame.iloc[2]
    failed_row = {"ExternalId__c": "missing" if failure == "unmatched" else "c",
                  "Email": "invalid", "sf__Error": "INVALID_FIELD: bad"}
    bulk_connector._bulk_get_csv_results.side_effect = [
        [{"sf__Id": "saved-1", "sf__Created": "true"},
         {"sf__Id": "saved-2", "sf__Created": "false"}], [failed_row],
    ]
    with pytest.raises(ConnectorError, match="unique input row") as caught:
        bulk_connector.bulk_insert("Contact", frame)
    assert caught.value.partial_result.created_ids == ["saved-1"]
    assert caught.value.partial_result.updated_ids == ["saved-2"]


@pytest.mark.parametrize("rows", [[], [{"sf__Id": "", "sf__Created": "true"}],
                                   [{"sf__Id": "saved", "sf__Created": None}]])
def test_bulk_empty_or_invalid_success_csv_cannot_report_ok(bulk_connector, rows):
    bulk_connector._bulk_poll_job.return_value["numberRecordsFailed"] = 0
    bulk_connector._bulk_get_csv_results.side_effect = [rows]
    with pytest.raises(ConnectorError, match="successfulResults"):
        bulk_connector.bulk_insert("Contact", bulk_frame())


@pytest.mark.parametrize("failure", [ConnectorError("results unavailable"), []])
def test_bulk_missing_failure_results_keep_success_ids(bulk_connector, failure):
    bulk_connector._bulk_get_csv_results.side_effect = [
        [{"sf__Id": "saved-1", "sf__Created": "true"},
         {"sf__Id": "saved-2", "sf__Created": "false"}], failure,
    ]
    with pytest.raises(ConnectorError) as caught:
        bulk_connector.bulk_insert("Contact", bulk_frame())
    partial = caught.value.partial_result
    assert partial.created_ids == ["saved-1"]
    assert partial.updated_ids == ["saved-2"]
    assert not partial.ok


@pytest.mark.parametrize("failure", ["http", "transport", "malformed", "truncated"])
def test_bulk_result_download_failures_raise(bulk_connector, failure):
    bulk_connector._instance_url = "https://example.salesforce.test"
    # Exercise the real downloader so HTTP, transport, and CSV failures use
    # the same error path as result validation.
    del bulk_connector._bulk_get_csv_results
    response = Mock(status_code=200, text='sf__Id,sf__Created\n"unfinished')
    if failure == "http":
        response.status_code = 503
    elif failure == "truncated":
        response.text = 'sf__Id,sf__Created\nsaved\n'
    bulk_connector._session.get = Mock(return_value=response)
    if failure == "transport":
        bulk_connector._session.get.side_effect = requests.Timeout("download timed out")
    with pytest.raises(ConnectorError) as caught:
        bulk_connector.bulk_insert("Contact", bulk_frame())
    assert caught.value.partial_result.success_count == 2


def test_composite_first_batch_failure_has_empty_partial_result():
    connector = salesforce()
    connector.request = Mock(side_effect=ConnectorError("first batch failed"))
    with pytest.raises(ConnectorError) as caught:
        connector.upsert_records("Contact", bulk_frame(), "ExternalId__c")
    assert caught.value.partial_result.total == 0
    assert caught.value.partial_result.created_ids == []


def test_bulk_short_timeout_limits_sleep_and_aborts(monkeypatch):
    connector = SalesforceConnector(client_id="id", client_secret="secret", bulk_timeout=2)
    connector.request = Mock(return_value={"state": "InProgress"})
    monkeypatch.setattr("siege_utilities.connectors.salesforce.time.monotonic", Mock(side_effect=[0, 0, 1, 2]))
    sleep = Mock()
    monkeypatch.setattr("siege_utilities.connectors.salesforce.time.sleep", sleep)
    with pytest.raises(ConnectorError, match="timed out after 2s"):
        connector._bulk_poll_job("job-1", 3)
    sleep.assert_called_once_with(1)
    path = f"/services/data/{API_VERSION}/jobs/ingest/job-1"
    assert connector.request.call_args_list == [
        call("GET", path), call("PATCH", path, json_body={"state": "Aborted"}),
    ]


def test_bulk_timeout_surfaces_abort_failure(monkeypatch):
    connector = salesforce()
    abort_error = ConnectorError("abort refused")
    connector.request = Mock(side_effect=abort_error)
    monkeypatch.setattr("siege_utilities.connectors.salesforce.time.monotonic", Mock(side_effect=[0, 601]))
    with pytest.raises(ConnectorError, match="timed out.*abort failed: abort refused") as caught:
        connector._bulk_poll_job("job-1", 3)
    assert caught.value.__cause__ is abort_error
    assert connector.request.call_args.kwargs["json_body"] == {"state": "Aborted"}


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_bulk_timeout_must_be_positive_and_finite(timeout):
    with pytest.raises(ValueError, match="bulk_timeout.*positive finite"):
        SalesforceConnector(client_id="id", client_secret="secret", bulk_timeout=timeout)
