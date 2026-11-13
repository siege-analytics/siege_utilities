"""Upsert results pickle without the connector, and boundary fallbacks keep text.

An ``UpsertResult`` keeps the connector's redactor only to render its own
repr. Pickling must drop it: the redactor is a bound connector method, so
keeping it either fails (the connector's logger adapter holds a local lambda)
or, with cloudpickle/dill, serializes the whole connector and its
credentials into the pickled result.

When a public connector call raises an exception class that cannot be rebuilt
from one message (pydantic ``ValidationError``, ``json.JSONDecodeError``), the
public boundary falls back to ``ConnectorError``. That fallback keeps the
sanitized message and records ``original_type``, so the caller still sees
which field or position failed.
"""
from __future__ import annotations

import copy
import pickle
from typing import Any
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.connectors._protocol import ConnectorError
from tests.crm_connector_factories import batch_response, connector, response

SENTINEL = "dummy-configured-token-pickle-1846"
PROVIDERS = ["salesforce", "hubspot", "zoho", "dynamics"]


def failed_upsert(provider: str) -> Any:
    """A real public upsert whose one record fails, from a configured connector."""
    c = connector(provider)
    c._access_token = SENTINEL
    c._session.headers["Authorization"] = f"Bearer {SENTINEL}"
    c._refresh_token = None
    c._retry_attempts = 1
    error = {"message": "rejected", "code": "bad", "statusCode": "bad", "category": "bad"}
    if provider == "dynamics":
        c._session.post = Mock(return_value=batch_response([(1, 400, {"error": error})]))
    else:
        body = {
            "salesforce": [{"success": False, "errors": [error]}],
            "hubspot": {"results": [], "errors": [error]},
            "zoho": {"data": [{"status": "error", **error}]},
        }[provider]
        c._session.request = Mock(return_value=response(body=body))
    result = c.upsert_records("contacts", pd.DataFrame([{"key": "business-key"}]), "key")
    assert not result.ok
    return result


# -- S2-1: pickling --------------------------------------------------------------


@pytest.mark.parametrize("provider", PROVIDERS)
def test_upsert_result_pickles_without_the_connector(provider: str) -> None:
    result = failed_upsert(provider)

    data = pickle.dumps(result)

    assert SENTINEL.encode() not in data
    clone = pickle.loads(data)
    assert clone == result
    assert clone.failure_count == result.failure_count
    assert clone.errors == result.errors
    # The redactor is not restored; repr falls back to key-based redaction.
    assert clone._redact is None
    assert "UpsertResult(" in repr(clone)


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_result_with_ids_round_trips_on_every_protocol(protocol: int) -> None:
    from siege_utilities.connectors._protocol import UpsertResult, UpsertError

    c = connector("hubspot")
    c._access_token = SENTINEL
    result = UpsertResult(
        success_count=2, failure_count=1,
        created_ids=["rec-created-1"], updated_ids=["rec-updated-2"],
        errors=[UpsertError(record_index=2, message="rejected", field="email", code="BAD")],
        redact=c._redact_field,
    )

    data = pickle.dumps(result, protocol=protocol)

    assert SENTINEL.encode() not in data
    clone = pickle.loads(data)
    assert clone == result
    assert (clone.created_ids, clone.updated_ids) == (["rec-created-1"], ["rec-updated-2"])
    assert (clone.total, clone.ok) == (3, False)
    assert clone._redact is None
    # The fallback key-based redactor renders the ids.
    assert "rec-created-1" in repr(clone) and "rec-updated-2" in repr(clone)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_copies_keep_the_redactor_and_pickling_leaves_the_original_intact(provider: str) -> None:
    result = failed_upsert(provider)
    redactor = result._redact

    pickle.dumps(result)

    assert result._redact is redactor
    assert copy.copy(result)._redact is redactor
    assert copy.deepcopy(result)._redact is redactor


def test_upsert_result_cloudpickle_carries_no_credential() -> None:
    cloudpickle = pytest.importorskip("cloudpickle")
    result = failed_upsert("hubspot")

    data = cloudpickle.dumps(result)

    assert SENTINEL.encode() not in data
    assert cloudpickle.loads(data) == result


# -- S2-2: boundary fallback keeps the sanitized message ------------------------


def test_validation_error_from_a_public_method_keeps_field_detail() -> None:
    c = connector("dynamics")

    with pytest.raises(ConnectorError) as caught:
        c.to_crm_contacts(pd.DataFrame([{"contactid": "c-1", "firstname": 123}]))

    assert caught.value.original_type == "ValidationError"
    text = str(caught.value)
    assert text.startswith("ValidationError: ")
    assert "first_name" in text


def test_json_decode_error_from_a_public_method_keeps_position_detail() -> None:
    c = connector("salesforce")
    resp = requests.Response()
    resp.status_code = 200
    resp._content = b"<html>not json</html>"
    c._session.post = Mock(return_value=resp)

    with pytest.raises(ConnectorError) as caught:
        c.authenticate_with_code("dummy-oauth-code-pickle-1846", "https://app.example.test/cb")

    assert caught.value.original_type == "JSONDecodeError"
    text = str(caught.value)
    assert text.startswith("JSONDecodeError: ")
    assert "Expecting value" in text


class TwoPartError(Exception):
    """An exception that cannot be rebuilt from a single message."""

    def __init__(self, field: str, detail: str) -> None:
        super().__init__(f"{field}: {detail}")
        self.field = field


def test_unrebuildable_exception_keeps_the_redacted_message_and_original_type() -> None:
    c = connector("dynamics")
    c._session.request = Mock(side_effect=TwoPartError("lastname", f"bad value near {SENTINEL}"))
    c._access_token = SENTINEL

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x")

    error = caught.value
    assert type(error) is ConnectorError
    assert error.original_type == "TwoPartError"
    assert str(error).startswith("TwoPartError: ")
    assert "lastname: bad value near" in str(error)
    assert SENTINEL not in str(error) and SENTINEL not in repr(error)
    # Other attributes are not copied onto the rebuilt error.
    assert not hasattr(error, "field")


def test_unrebuildable_exception_under_a_short_credential_stays_constant_only() -> None:
    c = connector("dynamics")
    c._access_token = "dummy7c"
    c._session.request = Mock(side_effect=TwoPartError("lastname", "bad value near dummy7c"))

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x")

    assert caught.value.original_type == "TwoPartError"
    assert str(caught.value) == "TwoPartError"
    assert "dummy7c" not in repr(caught.value)
