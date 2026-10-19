"""Offline CRM success-path coverage (#1453).

The HTTP adapter exercises request serialization and response parsing without
live credentials or network calls. See docs/crm_1453_coverage_baseline.md for
results from the same tests against v4.0.0 and the fixed branch.
"""

from collections import deque
import csv
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid5

import pandas as pd
from pydantic import ValidationError
import pytest
import requests

from siege_utilities.connectors import dynamics
from siege_utilities.connectors._adapters import (
    geographic_adapter, pipeline_adapter, tabular_adapter, timeseries_adapter,
)
from siege_utilities.connectors._dedup import CRM_NAMESPACE, crm_dedup_pipeline
from siege_utilities.connectors._models import (
    CRMAccount, CRMActivity, CRMAddress, CRMContact, CRMOpportunity,
)
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import API_VERSION, SOQLQuery, SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector


SF = f"/services/data/{API_VERSION}"
PROVIDERS = ["salesforce", "hubspot", "zoho", "dynamics"]


class ScriptedHTTPAdapter(requests.adapters.BaseAdapter):
    """Check real prepared requests against a finite sequence of responses."""

    def __init__(self):
        super().__init__()
        self.pending = deque()
        self.sent = []

    def add(self, method, path, payload, *, status=200, content_type="application/json"):
        self.pending.append((method, path, payload, status, content_type))

    def send(self, request, **kwargs):
        self.sent.append(request)
        assert self.pending, f"Unexpected HTTP request: {request.method} {request.url}"
        method, path, payload, status, content_type = self.pending.popleft()
        assert request.method == method
        assert urlparse(request.url).path == path
        if callable(payload):
            payload = payload(request)
        response = requests.Response()
        response.status_code = status
        response.headers["Content-Type"] = content_type
        response.encoding = "utf-8"
        response.request = request
        response.url = request.url
        response._content = (payload if isinstance(payload, str) else json.dumps(payload)).encode()
        return response

    def done(self):
        assert not self.pending, f"Missing {len(self.pending)} expected HTTP requests"

    def close(self):
        pass


@pytest.fixture
def offline(monkeypatch):
    def reject_network(*args, **kwargs):
        pytest.fail("Live HTTP transport is forbidden in CRM coverage tests")

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", reject_network)
    monkeypatch.setattr(dynamics, "MSAL_AVAILABLE", True)
    monkeypatch.setattr(dynamics, "msal", SimpleNamespace(
        ConfidentialClientApplication=Mock(), PublicClientApplication=Mock(),
    ), raising=False)
    connectors = []

    def make(provider):
        if provider == "salesforce":
            connector = SalesforceConnector(client_id="id", client_secret="secret", retry_attempts=1)
            connector._instance_url = "https://salesforce.example.test"
        elif provider == "hubspot":
            connector = HubSpotConnector(access_token="offline-token", retry_attempts=1)
        elif provider == "zoho":
            connector = ZohoConnector(client_id="id", client_secret="secret", retry_attempts=1)
        else:
            connector = dynamics.DynamicsConnector(
                environment_url="https://dynamics.example.test", tenant_id="tenant",
                client_id="id", client_secret="secret", retry_attempts=1,
            )
        connector._authenticated = True
        connector._access_token = "offline-token"
        connector._token_expires_at = None
        adapter = ScriptedHTTPAdapter()
        connector._session.mount("https://", adapter)
        connector._session.mount("http://", adapter)
        connectors.append(connector)
        return connector, adapter

    yield make
    for connector in connectors:
        connector.close()


def query(request):
    return parse_qs(urlparse(request.url).query)


def body(request):
    return json.loads(request.body)


@pytest.mark.parametrize("limit", [None, 1, 2, 3])
def test_salesforce_next_records_url_and_server_limit(offline, limit):
    connector, http = offline("salesforce")
    count = 3 if limit is None else limit
    first = {"records": [{"Id": "1", "Account": {"Name": "Acme"}}], "totalSize": count}
    if count > 1:
        first["nextRecordsUrl"] = f"{SF}/query/cursor-1"
    http.add("GET", f"{SF}/query", first)
    if count > 1:
        http.add("GET", f"{SF}/query/cursor-1", {
            "records": [{"Id": str(i), "Account": None} for i in range(2, count + 1)], "done": True,
        })
    frame = connector.get_objects("Contact", fields=["Id", "Account.Name"], limit=limit)
    assert frame.Id.tolist() == [str(i) for i in range(1, count + 1)]
    assert frame["Account.Name"].tolist() == ["Acme"] + [None] * (count - 1)
    expected = "SELECT Id, Account.Name FROM Contact" + (f" LIMIT {limit}" if limit is not None else "")
    assert query(http.sent[0]) == {"q": [expected]}
    if count > 1:
        assert not query(http.sent[1])
    http.done()


@pytest.mark.parametrize("limit", [None, 1, 2, 3])
def test_hubspot_after_cursor_and_limit_boundary(offline, limit):
    connector, http = offline("hubspot")
    http.add("GET", "/crm/v3/objects/contacts", {
        "results": [{"id": "1", "properties": {"firstname": "Ada"}},
                    {"id": "2", "properties": {"firstname": None}}],
        "paging": {"next": {"after": "opaque-2"}},
    })
    if limit is None or limit > 2:
        http.add("GET", "/crm/v3/objects/contacts", {
            "results": [{"id": "3", "properties": {"firstname": "Grace"}}],
        })
    frame = connector.get_objects("contacts", fields=["firstname"], limit=limit)
    count = 3 if limit is None else limit
    assert frame.id.tolist() == [str(i) for i in range(1, count + 1)]
    assert frame.firstname.tolist() == ["Ada", None, "Grace"][:count]
    assert query(http.sent[0]) == {"limit": [str(min(limit, 100) if limit else 100)], "properties": ["firstname"]}
    if count > 2:
        assert query(http.sent[1])["after"] == ["opaque-2"]
    assert len(http.sent) == (2 if count > 2 else 1)
    http.done()


@pytest.mark.parametrize("limit", [None, 1, 2, 3])
def test_zoho_page_number_and_limit_boundary(offline, limit):
    connector, http = offline("zoho")
    http.add("GET", "/crm/v6/Contacts", {
        "data": [{"id": "1", "Account_Name": {"id": "a", "name": "Acme"}},
                 {"id": "2", "Account_Name": None}], "info": {"more_records": True},
    })
    if limit is None or limit > 2:
        http.add("GET", "/crm/v6/Contacts", {
            "data": [{"id": "3", "Account_Name": None}], "info": {"more_records": False},
        })
    frame = connector.get_objects("Contacts", fields=["id", "Account_Name"], limit=limit)
    count = 3 if limit is None else limit
    assert frame.id.tolist() == [str(i) for i in range(1, count + 1)]
    assert frame.iloc[0].Account_Name == "Acme"
    assert frame.iloc[0].Account_Name_id == "a"
    assert query(http.sent[0]) == {"page": ["1"], "per_page": [str(min(limit, 200) if limit else 200)],
                                  "fields": ["id,Account_Name"]}
    if count > 2:
        assert query(http.sent[1])["page"] == ["2"]
    assert len(http.sent) == (2 if count > 2 else 1)
    http.done()


@pytest.mark.parametrize("limit", [None, 1, 2, 3])
def test_zoho_coql_offset_and_limit_boundary(offline, limit):
    connector, http = offline("zoho")
    # An oversized page verifies the client cap even when more_records is true.
    http.add("POST", "/crm/v6/coql", {
        "data": [{"id": "1"}, {"id": "2"}], "info": {"more_records": True},
    })
    if limit is None or limit > 2:
        http.add("POST", "/crm/v6/coql", {"data": [{"id": "3"}], "info": {"more_records": False}})
    frame = connector.get_objects("Contacts", fields=["id"], filters={"Last_Name": "Lee"}, limit=limit)
    count = 3 if limit is None else limit
    assert frame.id.tolist() == [str(i) for i in range(1, count + 1)]
    prefix = "select id from Contacts where Last_Name = 'Lee' limit "
    assert body(http.sent[0]) == {"select_query": prefix + f"0, {limit if limit else 200}"}
    if count > 2:
        assert body(http.sent[1]) == {"select_query": prefix + f"2, {1 if limit else 200}"}
    assert len(http.sent) == (2 if count > 2 else 1)
    http.done()


@pytest.mark.parametrize("limit", [None, 1, 2, 3])
def test_dynamics_next_link_and_server_limit(offline, limit):
    connector, http = offline("dynamics")
    count = 3 if limit is None else limit
    first = {"value": [{"contactid": "1", "firstname": "Ada"}]}
    if count > 1:
        first["@odata.nextLink"] = "https://dynamics.example.test/api/data/v9.2/contacts?$skiptoken=opaque%2Bcursor"
    http.add("GET", "/api/data/v9.2/contacts", first)
    if count > 1:
        http.add("GET", "/api/data/v9.2/contacts", {
            "value": [{"contactid": str(i), "firstname": None} for i in range(2, count + 1)],
        })
    frame = connector.get_objects("contacts", fields=["contactid", "firstname"], limit=limit)
    assert frame.contactid.tolist() == [str(i) for i in range(1, count + 1)]
    assert frame.firstname.tolist() == ["Ada"] + [None] * (count - 1)
    expected = {"$select": ["contactid,firstname"]}
    if limit is not None:
        expected["$top"] = [str(limit)]
    assert query(http.sent[0]) == expected
    if count > 1:
        assert query(http.sent[1]) == {"$skiptoken": ["opaque+cursor"]}
    http.done()


@pytest.mark.parametrize("provider,object_type,fields,columns", [
    ("hubspot", "contacts", ["firstname"], ["id", "firstname"]),
    ("zoho", "Contacts", ["id", "First_Name"], ["id", "First_Name"]),
    ("dynamics", "contacts", ["contactid", "firstname"], ["contactid", "firstname"]),
])
def test_zero_limit_never_sends_http(offline, provider, object_type, fields, columns):
    connector, http = offline(provider)
    frame = connector.get_objects(object_type, fields=fields, limit=0)
    assert frame.empty
    assert frame.columns.tolist() == columns
    assert http.sent == []


@pytest.mark.parametrize("partial", [False, True])
def test_salesforce_composite_upsert_results_and_payload(offline, partial):
    connector, http = offline("salesforce")
    # Three rows across two batches also exercise global failure positions.
    connector.COMPOSITE_BATCH_SIZE = 2
    http.add("PATCH", f"{SF}/composite/sobjects/Contact/ExternalId__c", [
        {"success": True, "created": True, "id": "created"},
        {"success": True, "created": False, "id": "updated"},
    ])
    last = {"success": False, "errors": [{
        "statusCode": "INVALID_EMAIL_ADDRESS", "message": "Bad email", "fields": ["Email"],
    }]} if partial else {"success": True, "created": True, "id": "third"}
    http.add("PATCH", f"{SF}/composite/sobjects/Contact/ExternalId__c", [last])
    frame = pd.DataFrame({"ExternalId__c": ["a", "b", "c"], "Email": ["a@example.test", None, "bad"]})
    result = connector.upsert_records("Contact", frame, "ExternalId__c")
    assert (result.success_count, result.failure_count) == ((2, 1) if partial else (3, 0))
    assert result.created_ids == (["created"] if partial else ["created", "third"])
    assert result.updated_ids == ["updated"]
    assert [asdict(error) for error in result.errors] == ([{
        "record_index": 2, "message": "Bad email", "field": "Email", "code": "INVALID_EMAIL_ADDRESS",
    }] if partial else [])
    assert body(http.sent[0]) == {"allOrNone": False, "records": [
        {"ExternalId__c": "a", "Email": "a@example.test", "attributes": {"type": "Contact"}},
        {"ExternalId__c": "b", "attributes": {"type": "Contact"}},
    ]}
    assert body(http.sent[1])["records"][0]["ExternalId__c"] == "c"
    http.done()


@pytest.mark.parametrize("partial", [False, True])
def test_salesforce_bulk_v2_lifecycle_and_csv_results(offline, partial):
    connector, http = offline("salesforce")
    job = f"{SF}/jobs/ingest/job-1"
    http.add("POST", f"{SF}/jobs/ingest", {"id": "job-1"})
    http.add("PUT", f"{job}/batches", "", status=201, content_type="text/plain")
    http.add("PATCH", job, {"state": "UploadComplete"})
    http.add("GET", job, {"state": "JobComplete", "numberRecordsProcessed": 3,
                          "numberRecordsFailed": int(partial)})
    successes = "sf__Id,sf__Created\ncreated,true\nupdated,false\n" + ("" if partial else "third,true\n")
    http.add("GET", f"{job}/successfulResults", successes, content_type="text/csv")
    if partial:
        http.add("GET", f"{job}/failedResults",
                 "sf__Id,sf__Error,ExternalId__c,Email\n,INVALID_EMAIL_ADDRESS: Bad email,c,bad\n",
                 content_type="text/csv")
    frame = pd.DataFrame({"ExternalId__c": ["a", "b", "c"], "Email": ["a@example.test", pd.NA, "bad"]},
                         index=["row-a", "row-b", "row-c"])
    progress = Mock()
    result = connector.upsert_records("Contact", frame, "ExternalId__c", force_bulk=True, progress_callback=progress)
    assert (result.success_count, result.failure_count) == ((2, 1) if partial else (3, 0))
    assert result.created_ids == (["created"] if partial else ["created", "third"])
    assert result.updated_ids == ["updated"]
    assert [asdict(error) for error in result.errors] == ([{
        "record_index": "row-c", "message": "INVALID_EMAIL_ADDRESS: Bad email",
        "code": "INVALID_EMAIL_ADDRESS", "field": None,
    }] if partial else [])
    assert body(http.sent[0]) == {"object": "Contact", "operation": "upsert", "contentType": "CSV",
                                 "lineEnding": "LF", "externalIdFieldName": "ExternalId__c"}
    assert http.sent[1].headers["Content-Type"] == "text/csv"
    uploaded = list(csv.DictReader(io.StringIO(http.sent[1].body.decode())))
    assert uploaded == [{"ExternalId__c": "a", "Email": "a@example.test"},
                        {"ExternalId__c": "b", "Email": ""}, {"ExternalId__c": "c", "Email": "bad"}]
    assert body(http.sent[2]) == {"state": "UploadComplete"}
    assert [call.args for call in progress.call_args_list] == [
        ("uploading", 0, 3), ("processing", 0, 3), ("JobComplete", 3, 3),
    ]
    http.done()


@pytest.mark.parametrize("partial", [False, True])
def test_hubspot_batch_upsert_results_and_error_identity(offline, partial):
    connector, http = offline("hubspot")
    response = {"results": [{"id": "updated", "new": False}, {"id": "created", "new": True}]}
    if partial:
        response["errors"] = [{"message": "Bad email", "category": "VALIDATION_ERROR",
                               "context": {"objectWriteTraceId": ["2"]}}]
    else:
        response["results"].append({"id": "third", "new": True})
    http.add("POST", "/crm/v3/objects/contacts/batch/upsert", response, status=207 if partial else 200)
    frame = pd.DataFrame({"email": ["a@example.test", "b@example.test", "bad"], "phone": [None, "123", None]},
                         index=["row-a", "row-b", "row-c"])
    result = connector.upsert_records("contacts", frame, "email")
    assert (result.success_count, result.failure_count) == ((2, 1) if partial else (3, 0))
    assert result.created_ids == (["created"] if partial else ["created", "third"])
    assert result.updated_ids == ["updated"]
    assert [asdict(error) for error in result.errors] == ([{
        "record_index": "row-c", "message": "Bad email", "code": "VALIDATION_ERROR", "field": None,
    }] if partial else [])
    inputs = body(http.sent[0])["inputs"]
    assert inputs == [
        {"id": "a@example.test", "idProperty": "email", "objectWriteTraceId": "0",
         "properties": {"email": "a@example.test"}},
        {"id": "b@example.test", "idProperty": "email", "objectWriteTraceId": "1",
         "properties": {"email": "b@example.test", "phone": "123"}},
        {"id": "bad", "idProperty": "email", "objectWriteTraceId": "2", "properties": {"email": "bad"}},
    ]
    http.done()


@pytest.mark.parametrize("partial", [False, True])
def test_zoho_upsert_results_and_payload(offline, partial):
    connector, http = offline("zoho")
    outcomes = [{"status": "success", "action": "insert", "details": {"id": "created"}},
                {"status": "success", "action": "update", "details": {"id": "updated"}}]
    outcomes.append({"status": "error", "message": "Bad email", "code": "INVALID_DATA"} if partial else
                    {"status": "success", "action": "insert", "details": {"id": "third"}})
    http.add("POST", "/crm/v6/Contacts/upsert", {"data": outcomes})
    result = connector.upsert_records("Contacts", pd.DataFrame({
        "Email": ["a@example.test", "b@example.test", "bad"], "Phone": [None, "123", None],
    }), "Email")
    assert (result.success_count, result.failure_count) == ((2, 1) if partial else (3, 0))
    assert result.created_ids == (["created"] if partial else ["created", "third"])
    assert result.updated_ids == ["updated"]
    assert [asdict(error) for error in result.errors] == ([{
        "record_index": 2, "message": "Bad email", "code": "INVALID_DATA", "field": None,
    }] if partial else [])
    assert body(http.sent[0]) == {"duplicate_check_fields": ["Email"], "data": [
        {"Email": "a@example.test"}, {"Email": "b@example.test", "Phone": "123"}, {"Email": "bad"},
    ]}
    http.done()


def dynamics_multipart(parts):
    lines = ["--batch_response", "Content-Type: multipart/mixed; boundary=changeset_response", ""]
    for content_id, status, payload in parts:
        lines.extend([
            "--changeset_response", "Content-Type: application/http", "Content-Transfer-Encoding: binary",
            f"Content-ID: {content_id}", "", f"HTTP/1.1 {status} Response",
            "Content-Type: application/json", "", json.dumps(payload),
        ])
    lines.extend(["--changeset_response--", "--batch_response--", ""])
    return "\r\n".join(lines)


@pytest.mark.parametrize("partial", [False, True])
def test_dynamics_batch_success_and_atomic_partial_failure(offline, monkeypatch, partial):
    connector, http = offline("dynamics")
    monkeypatch.setattr(dynamics, "BATCH_SIZE", 2)
    # Out-of-order Content-IDs must still classify each input correctly.
    successes = [(2, 204, {}), (1, 201, {})]
    http.add("POST", "/api/data/v9.2/$batch", dynamics_multipart(successes),
             content_type="multipart/mixed; boundary=batch_response")
    second = [(2, 400, {"error": {"code": "0xBAD", "message": "Invalid value"}})] if partial else successes
    http.add("POST", "/api/data/v9.2/$batch", dynamics_multipart(second),
             content_type="multipart/mixed; boundary=batch_response")
    result = connector.upsert_records("contacts", pd.DataFrame({
        "emailaddress1": ["a@example.test", "b@example.test", "c@example.test", "d@example.test"],
        "telephone1": [None, "123", None, None],
    }), "emailaddress1")
    assert (result.success_count, result.failure_count) == ((2, 2) if partial else (4, 0))
    assert result.created_ids == (["a@example.test"] if partial else ["a@example.test", "c@example.test"])
    assert result.updated_ids == (["b@example.test"] if partial else ["b@example.test", "d@example.test"])
    assert [asdict(error) for error in result.errors] == ([{
        "record_index": index, "message": "Changeset failed or rolled back: Invalid value",
        "code": "0xBAD", "field": None,
    } for index in [2, 3]] if partial else [])
    request_body = http.sent[0].body
    if isinstance(request_body, bytes):
        request_body = request_body.decode()
    assert request_body.count("PATCH https://dynamics.example.test/api/data/v9.2/contacts(") == 2
    assert "emailaddress1=%27a%40example.test%27" in request_body
    assert '"emailaddress1": "a@example.test"}' in request_body
    assert '"telephone1": "123"' in request_body
    assert '"telephone1": null' not in request_body
    http.done()


MAPPING_FIELDS = {
    "salesforce": {
        "contacts": ("Id", "FirstName", "Email", "MailingStreet"),
        "accounts": ("Id", "Name", "AnnualRevenue", "NumberOfEmployees", "BillingStreet"),
        "opportunities": ("Id", "Name", "Amount", "Probability", "CloseDate"),
    },
    "hubspot": {
        "contacts": ("id", "firstname", "email", "address"),
        "accounts": ("id", "name", "annualrevenue", "numberofemployees", "address"),
        "opportunities": ("id", "dealname", "amount", "hs_deal_stage_probability", "closedate"),
    },
    "zoho": {
        "contacts": ("id", "First_Name", "Email", "Mailing_Street"),
        "accounts": ("id", "Account_Name", "Annual_Revenue", "Employees", "Billing_Street"),
        "opportunities": ("id", "Deal_Name", "Amount", "Probability", "Closing_Date"),
    },
    "dynamics": {
        "contacts": ("contactid", "firstname", "emailaddress1", "address1_line1"),
        "accounts": ("accountid", "name", "revenue", "numberofemployees", "address1_line1"),
        "opportunities": ("opportunityid", "name", "estimatedvalue", "closeprobability", "estimatedclosedate"),
    },
}


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("kind", ["contacts", "accounts", "opportunities"])
def test_canonical_mapping_mixed_null_frame(offline, provider, kind):
    connector, http = offline(provider)
    fields = MAPPING_FIELDS[provider][kind]
    values = {
        "contacts": ("valid", "Ada", "ada@example.test", "1 Main St"),
        "accounts": ("valid", "Acme", 0, 0, "1 Main St"),
        "opportunities": ("valid", "Renewal", 0, 0.8 if provider == "hubspot" else 80, "2026-10-19"),
    }[kind]
    rows = [{**dict(zip(fields, values)), "custom_score": 0}]
    for index, missing in enumerate([None, float("nan"), pd.NA, pd.NaT]):
        rows.append({**dict.fromkeys(fields, missing), fields[0]: f"missing-{index}", "custom_score": missing})
    frame = pd.DataFrame(rows, dtype=object)
    original = frame.copy(deep=True)
    models = getattr(connector, f"to_crm_{kind}")(frame)
    assert [model.id for model in models] == ["valid", "missing-0", "missing-1", "missing-2", "missing-3"]
    assert [model.source_id for model in models] == [model.id for model in models]
    assert {model.source_system for model in models} == {"dynamics365" if provider == "dynamics" else provider}
    assert models[0].metadata["custom_score"] == 0
    for model in models[1:]:
        assert "custom_score" not in model.metadata
        if kind == "contacts":
            assert (model.first_name, model.email, model.address.street) == (None, None, None)
        elif kind == "accounts":
            assert (model.name, model.revenue, model.employee_count, model.address.street) == ("", None, None, None)
        else:
            assert (model.name, model.amount, model.probability, model.close_date) == ("", None, None, None)
    valid = models[0]
    if kind == "contacts":
        assert (valid.first_name, valid.email, valid.address.street) == ("Ada", "ada@example.test", "1 Main St")
    elif kind == "accounts":
        assert (valid.name, valid.revenue, valid.employee_count, valid.address.street) == ("Acme", Decimal("0"), 0, "1 Main St")
    else:
        assert (valid.name, valid.amount, valid.probability, valid.close_date) == ("Renewal", Decimal("0"), 80, date(2026, 10, 19))
    assert type(valid).to_dataframe(models).id.tolist() == [model.id for model in models]
    pd.testing.assert_frame_equal(frame, original)
    assert http.sent == []


@pytest.mark.parametrize("kwargs,expected", [
    ({"eq": "O'Reilly"}, "Field = 'O\\'Reilly'"),
    ({"ne": None}, "Field != null"),
    ({"gt": 1, "gte": 2, "lt": 10, "lte": 9}, "Field > 1 AND Field >= 2 AND Field < 10 AND Field <= 9"),
    ({"eq": True}, "Field = true"),
    ({"in_": ["A", "B"]}, "Field IN ('A', 'B')"),
    ({"not_in": [1, 2]}, "Field NOT IN (1, 2)"),
    ({"like": "A%"}, "Field LIKE 'A%'"),
    ({"is_null": True}, "Field = null"),
    ({"is_null": False}, "Field != null"),
    ({"eq": date(2026, 10, 19)}, "Field = 2026-10-19"),
    ({"eq": datetime(2026, 10, 19, 12, tzinfo=timezone.utc)}, "Field = 2026-10-19T12:00:00Z"),
])
def test_soql_where_rendering(kwargs, expected):
    query_builder = SOQLQuery().select("Id").from_("Contact").where("Field", **kwargs)
    assert query_builder.build() == f"SELECT Id FROM Contact WHERE {expected}"
    assert str(query_builder) == query_builder.build()


def test_soql_full_query_and_http_execution(offline):
    query_builder = (SOQLQuery().select("Id").select("Name", "Account.Name").from_("Contact")
                     .where("IsDeleted", eq=False).where_raw("(Email != null OR Phone != null)")
                     .order_by("Name").order_by("Id", desc=True).limit(20).offset(0))
    expected = ("SELECT Id, Name, Account.Name FROM Contact WHERE IsDeleted = false AND "
                "(Email != null OR Phone != null) ORDER BY Name ASC, Id DESC LIMIT 20 OFFSET 0")
    assert query_builder.build() == expected
    connector, http = offline("salesforce")
    http.add("GET", f"{SF}/query", {"records": [{"Id": "1", "Name": "Ada", "attributes": {"type": "Contact"}}]})
    frame = connector.soql(query_builder)
    assert frame.to_dict("records") == [{"Id": "1", "Name": "Ada"}]
    assert query(http.sent[0]) == {"q": [expected]}
    http.done()


def test_pipeline_counts_rows_and_averages_known_amounts():
    frame = pd.DataFrame({"stage": ["Won", "Won", "Lost"], "amount": [20, None, 5]})
    original = frame.copy(deep=True)
    assert pipeline_adapter(frame).to_dict("records") == [
        {"stage": "Won", "count": 2, "total_value": 20, "avg_value": 20},
        {"stage": "Lost", "count": 1, "total_value": 5, "avg_value": 5},
    ]
    pd.testing.assert_frame_equal(frame, original)


def test_pipeline_preserves_unstaged_deals_and_ordered_zero_rows():
    result = pipeline_adapter(pd.DataFrame({"stage": ["Won", "Lost", None], "amount": [10, 20, 999]}),
                              stage_order=["Prospect", "Won"])
    assert result.to_dict("records") == [
        {"stage": "Prospect", "count": 0, "total_value": 0, "avg_value": 0},
        {"stage": "Won", "count": 1, "total_value": 10, "avg_value": 10},
        {"stage": "Lost", "count": 1, "total_value": 20, "avg_value": 20},
        {"stage": "(none)", "count": 1, "total_value": 999, "avg_value": 999},
    ]


def test_timeseries_utc_aggregation_fills_empty_periods():
    frame = pd.DataFrame({"when": ["2026-03-07T12:00:00-05:00", "2026-03-09T12:00:00-04:00", "invalid"],
                          "amount": [10, 30, 999]})
    result = timeseries_adapter(frame, timestamp_column="when", value_column="amount", agg="sum")
    assert result.date.tolist() == list(pd.date_range("2026-03-07", periods=3, tz="UTC"))
    assert result.value.tolist() == [10, 0, 30]


@pytest.mark.parametrize("frame", [pd.DataFrame(), pd.DataFrame({"timestamp": [None, "invalid"]})])
def test_timeseries_empty_or_invalid_input_schema(frame):
    result = timeseries_adapter(frame)
    assert result.empty
    assert result.columns.tolist() == ["date", "value"]


def test_geographic_address_selection_preserves_index():
    frame = pd.DataFrame({"town": ["Chicago", None, None], "zip": ["60601", "00001", None],
                          "ignored": [1, 2, 3]}, index=[10, 20, 30])
    original = frame.copy(deep=True)
    result = geographic_adapter(frame, city_column="town", postal_code_column="zip")
    assert result.index.tolist() == [10, 20]
    assert result.columns.tolist() == ["street", "city", "state", "postal_code", "country"]
    assert result.city.tolist() == ["Chicago", None]
    assert result.postal_code.tolist() == ["60601", "00001"]
    assert result[["street", "state", "country"]].isna().all().all()
    pd.testing.assert_frame_equal(frame, original)


def test_tabular_selection_rename_sort_and_limit():
    frame = pd.DataFrame({"name": ["Ada", "Grace", "Linus"], "amount": [1, 3, 2], "hidden": [9, 9, 9]},
                         index=[10, 20, 30])
    original = frame.copy(deep=True)
    result = tabular_adapter(frame, columns=["name", "amount", "missing"], rename={"amount": "Total"},
                             sort_by="Total", ascending=False, limit=2)
    assert result.to_dict("records") == [{"name": "Grace", "Total": 3}, {"name": "Linus", "Total": 2}]
    assert result.index.tolist() == [0, 1]
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("adapter,columns", [
    (pipeline_adapter, ["stage", "count", "total_value", "avg_value"]),
    (geographic_adapter, ["street", "city", "state", "postal_code", "country"]),
    (tabular_adapter, []),
])
def test_empty_adapters(adapter, columns):
    result = adapter(pd.DataFrame())
    assert result.empty
    assert result.columns.tolist() == columns


MODEL_CASES = [
    (CRMAddress, {"city": "Chicago"}),
    (CRMContact, {"id": "1", "source_system": "crm", "source_id": "a"}),
    (CRMAccount, {"id": "1", "name": "Acme", "source_system": "crm", "source_id": "a"}),
    (CRMOpportunity, {"id": "1", "name": "Renewal", "source_system": "crm", "source_id": "a"}),
    (CRMActivity, {"id": "1", "type": "call", "source_system": "crm", "source_id": "a"}),
]


@pytest.mark.parametrize("model,values", MODEL_CASES)
def test_models_reject_unknown_fields(model, values):
    assert model(**values).model_dump().items() >= values.items()
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model(**values, typo="value")


@pytest.mark.parametrize("model,values", MODEL_CASES[1:])
def test_model_empty_frames_and_independent_metadata(model, values):
    first, second = model(**values), model(**values)
    first.metadata["custom"] = "only-first"
    assert second.metadata == {}
    assert model.to_dataframe([]).empty
    frame = model.to_dataframe([first, second])
    assert frame.source_id.tolist() == ["a", "a"]
    assert frame.loc[0, "custom"] == "only-first"
    assert pd.isna(frame.loc[1, "custom"])
    assert "metadata" not in frame.columns


def test_model_dataframes_flatten_addresses_numbers_and_dates():
    identity = {"id": "1", "source_system": "crm", "source_id": "source-1"}
    address = CRMAddress(street="1 Main St", city="Chicago", postal_code="00123")
    contact = CRMContact(**identity, first_name="Ada", address=address, metadata={"segment": "A"})
    account = CRMAccount(**identity, name="Acme", revenue=Decimal("12.50"), address=address)
    opportunity = CRMOpportunity(**identity, name="Renewal", amount=Decimal("25.50"), close_date=date(2026, 10, 19))
    activity = CRMActivity(**identity, type="call", timestamp=datetime(2026, 10, 19, 12, tzinfo=timezone.utc),
                           due_date=date(2026, 10, 20))
    contact_frame = CRMContact.to_dataframe([contact])
    assert contact_frame.loc[0, "address_postal_code"] == "00123"
    assert contact_frame.loc[0, "segment"] == "A"
    assert "address" not in contact_frame.columns
    account_frame = CRMAccount.to_dataframe([account])
    assert account_frame.loc[0, "address_city"] == "Chicago"
    assert account_frame.loc[0, "revenue"] == 12.5
    assert account_frame.revenue.dtype.kind == "f"
    opportunity_frame = CRMOpportunity.to_dataframe([opportunity])
    assert opportunity_frame.loc[0, "amount"] == 25.5
    assert opportunity_frame.loc[0, "close_date"] == "2026-10-19"
    activity_frame = CRMActivity.to_dataframe([activity])
    assert activity_frame.loc[0, "timestamp"] == "2026-10-19 12:00:00+00:00"
    assert activity_frame.loc[0, "due_date"] == "2026-10-20"


def test_dedup_cross_crm_names_have_stable_ids_and_preserve_sources():
    frames = [pd.DataFrame({"first_name": [" José ", "Grace"], "last_name": ["GARCÍA", "Hopper"],
                            "source_system": ["zoho", "zoho"], "source_id": ["z1", "z2"]}),
              pd.DataFrame({"first_name": ["jose"], "last_name": ["garcia"],
                            "source_system": ["salesforce"], "source_id": ["s1"]})]
    originals = [frame.copy(deep=True) for frame in frames]
    result = crm_dedup_pipeline(frames)
    jose = result[result.normalized_name == "jose garcia"]
    assert jose.canonical_id.tolist() == [str(uuid5(CRM_NAMESPACE, "jose garcia"))] * 2
    assert jose.source_system.tolist() == ["salesforce", "zoho"]
    assert jose.source_id.tolist() == ["s1", "z1"]
    assert result.canonical_id.nunique() == 2
    assert result.match_confidence.tolist() == [1.0, 1.0, 1.0]
    pd.testing.assert_frame_equal(result, crm_dedup_pipeline(list(reversed(frames))))
    for frame, original in zip(frames, originals):
        pd.testing.assert_frame_equal(frame, original)


def test_dedup_custom_columns_normalizer_namespace_and_blank_names():
    frame = pd.DataFrame({"display": ["Ada", "ADA", " ", None, "Skip"], "vendor": ["crm"] * 5,
                          "record": ["1", "2", "3", "4", "5"]})
    namespace = UUID("12345678-1234-5678-1234-567812345678")
    result = crm_dedup_pipeline([pd.DataFrame(), frame], name_columns=["display"],
                               source_system_column="vendor", source_id_column="record",
                               normalizer=lambda name: "" if name == "Skip" else name.lower(), namespace=namespace)
    assert result.to_dict("records") == [
        {"canonical_id": str(uuid5(namespace, "ada")), "normalized_name": "ada", "vendor": "crm",
         "record": record, "match_confidence": 1.0} for record in ["1", "2"]
    ]
    assert str(uuid5(namespace, "ada")) != str(uuid5(CRM_NAMESPACE, "ada"))


@pytest.mark.parametrize("frames", [[], [pd.DataFrame()], [pd.DataFrame({
    "first_name": [None], "last_name": [" "], "source_system": ["crm"], "source_id": ["1"],
})]])
def test_dedup_empty_output_schema(frames):
    result = crm_dedup_pipeline(frames)
    assert result.empty
    assert result.columns.tolist() == ["canonical_id", "normalized_name", "source_system", "source_id", "match_confidence"]
