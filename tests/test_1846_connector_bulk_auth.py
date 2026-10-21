"""R2 B3: raw CRM transfers share the bounded OAuth replay contract."""

from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.connectors._protocol import ConnectorAuthError, ConnectorError, ConnectorRateLimitError
from tests.test_1417_crm_retry_idempotency import batch_response, connector, response


def renewable(provider):
    c = connector(provider)
    c._client_secret = "client-secret"
    c._refresh_token = "refresh-token"

    def refresh():
        c._access_token = "renewed-token"
        c._session.headers["Authorization"] = "Bearer renewed-token"

    c.refresh_access_token = Mock(side_effect=refresh)
    return c


@pytest.mark.parametrize("persistent", [False, True])
def test_connector_dynamics_public_upsert_401(persistent):
    c = renewable("dynamics")
    c._session.post = Mock(side_effect=[
        response(401), response(401) if persistent else batch_response([(1, 204, {})]),
    ])
    if persistent:
        with pytest.raises(ConnectorAuthError):
            c.upsert_records("contacts", pd.DataFrame({"key": ["a"]}), "key")
    else:
        result = c.upsert_records("contacts", pd.DataFrame({"key": ["a"]}), "key")
        assert result.ok and result.updated_ids == ["a"]
    c.refresh_access_token.assert_called_once()
    assert c._session.post.call_count == 2
    first, second = c._session.post.call_args_list
    assert first.kwargs["data"] == second.kwargs["data"]
    assert second.kwargs["headers"]["Authorization"] == "Bearer renewed-token"


@pytest.mark.parametrize("persistent", [False, True])
def test_connector_salesforce_bulk_upload_401(persistent):
    c = renewable("salesforce")
    c._session.put = Mock(side_effect=[response(401), response(401 if persistent else 201)])
    if persistent:
        with pytest.raises(ConnectorAuthError):
            c._bulk_upload_data("job", "Id\n1\n")
    else:
        c._bulk_upload_data("job", "Id\n1\n")
    c.refresh_access_token.assert_called_once()
    assert c._session.put.call_count == 2
    first, second = c._session.put.call_args_list
    assert first.kwargs["data"] == second.kwargs["data"] == b"Id\n1\n"
    assert second.kwargs["headers"]["Authorization"] == "Bearer renewed-token"


@pytest.mark.parametrize("operation", ["upload", "download"])
@pytest.mark.parametrize("hint", ["30", "901", "1e300"])
def test_connector_salesforce_bulk_429_cap(operation, hint, monkeypatch):
    c = renewable("salesforce")
    sleep = Mock()
    monkeypatch.setattr("time.sleep", sleep)
    send = Mock(side_effect=[response(429, headers={"Retry-After": hint}), response()])
    if operation == "upload":
        c._session.put = send

        def invoke():
            return c._bulk_upload_data("job", "Id\n1\n")
    else:
        c._session.get = send

        def invoke():
            return c._bulk_get_csv_results("/results")
    if hint == "30":
        invoke()
        sleep.assert_called_once_with(30)
        assert send.call_count == 2
    else:
        with pytest.raises(ConnectorRateLimitError) as caught:
            invoke()
        assert caught.value.retry_after == float(hint)
        sleep.assert_not_called()
        send.assert_called_once()


@pytest.mark.parametrize("kind", ["success", "failure"])
@pytest.mark.parametrize("persistent", [False, True])
def test_connector_salesforce_result_download_401_never_silent(kind, persistent):
    c = renewable("salesforce")
    csv_response = response()
    csv_response._content = (b"sf__Id,sf__Created\n001,true\n" if kind == "success" else
                             b"sf__Error\ninvalid field\n")
    c._session.get = Mock(side_effect=[response(401), response(401) if persistent else csv_response])
    info = {"state": "JobComplete", "numberRecordsProcessed": 1,
            "numberRecordsFailed": int(kind == "failure")}
    if persistent:
        with pytest.raises(ConnectorAuthError):
            c._bulk_collect_results("job", info)
    else:
        result = c._bulk_collect_results("job", info)
        if kind == "success":
            assert result.ok and result.created_ids == ["001"]
        else:
            assert not result.ok and result.errors[0].message == "invalid field"
    c.refresh_access_token.assert_called_once()
    assert c._session.get.call_count == 2
    assert c._session.get.call_args.kwargs["headers"]["Authorization"] == "Bearer renewed-token"


@pytest.mark.parametrize("persistent", [False, True])
def test_connector_dynamics_inner_401_refreshes(persistent):
    c = renewable("dynamics")
    rejected = batch_response([(1, 401, {})])
    c._session.post = Mock(side_effect=[rejected, rejected if persistent else batch_response([(1, 204, {})])])
    if persistent:
        with pytest.raises(ConnectorAuthError):
            c.upsert_records("contacts", pd.DataFrame({"key": ["a"]}), "key")
    else:
        assert c.upsert_records("contacts", pd.DataFrame({"key": ["a"]}), "key").ok
    c.refresh_access_token.assert_called_once()
    assert c._session.post.call_count == 2


@pytest.mark.parametrize("failure", ["empty", "missing_id", "transport", "forbidden", "throttle"])
def test_connector_salesforce_results_cannot_report_success_without_ids(failure, monkeypatch):
    c = renewable("salesforce")
    c._retry_attempts = 1
    monkeypatch.setattr("time.sleep", Mock())
    resp = response({"forbidden": 403, "throttle": 429}.get(failure, 200))
    resp._content = b"sf__Id,sf__Created\n" if failure == "empty" else b"sf__Id,sf__Created\n,true\n"
    c._session.get = Mock(return_value=resp)
    if failure == "transport":
        c._session.get.side_effect = requests.Timeout("lost result")
    expected = {"forbidden": ConnectorAuthError, "throttle": ConnectorRateLimitError}.get(failure, ConnectorError)
    with pytest.raises(expected):
        c._bulk_collect_results("job", {"state": "JobComplete", "numberRecordsProcessed": 1})
    c.refresh_access_token.assert_not_called()
