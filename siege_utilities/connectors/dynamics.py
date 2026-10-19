"""
Microsoft Dynamics 365 CRM connector — MSAL/OAuth + Dataverse Web API.

Supports app-only (client credentials) and delegated (user) auth via
MSAL. Reads/writes Dynamics 365 entities through the Dataverse Web API
with OData query syntax and FetchXML support.

Auth depends on ``msal`` (Microsoft Authentication Library). HTTP
requests use ``requests`` for consistency with other connectors.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import quote

import pandas as pd

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False

try:
    import msal

    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

from siege_utilities.connectors._retry import rate_limit_error, retry_attempts
from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
    UpsertResult,
    sanitize_record,
)
from siege_utilities.connectors._query_utils import _validate_identifier

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 2.0
TOKEN_REFRESH_MARGIN = timedelta(seconds=60)
BATCH_SIZE = 1000
FORMATTED_VALUE_ANNOTATION = "OData.Community.Display.V1.FormattedValue"

STANDARD_ENTITIES: dict[str, str] = {
    "contacts": "contacts",
    "accounts": "accounts",
    "opportunities": "opportunities",
    "leads": "leads",
    "tasks": "tasks",
    "appointments": "appointments",
    "incidents": "incidents",
}

DEFAULT_COLUMNS: dict[str, list[str]] = {
    "contacts": [
        "contactid", "firstname", "lastname", "emailaddress1",
        "telephone1", "jobtitle", "_parentcustomerid_value",
        "address1_line1", "address1_city", "address1_stateorprovince",
        "address1_postalcode", "address1_country",
        "createdon", "modifiedon",
    ],
    "accounts": [
        "accountid", "name", "industrycode", "websiteurl",
        "revenue", "numberofemployees",
        "address1_line1", "address1_city", "address1_stateorprovince",
        "address1_postalcode", "address1_country",
        "telephone1", "createdon", "modifiedon",
    ],
    "opportunities": [
        "opportunityid", "name", "_parentaccountid_value",
        "stepname", "estimatedvalue", "estimatedclosedate",
        "closeprobability", "_ownerid_value",
        "createdon", "modifiedon",
    ],
    "leads": [
        "leadid", "firstname", "lastname", "emailaddress1",
        "telephone1", "companyname", "jobtitle",
        "leadqualitycode", "leadsourcecode",
        "address1_line1", "address1_city", "address1_stateorprovince",
        "address1_postalcode", "address1_country",
        "createdon", "modifiedon",
    ],
}

__all__ = ["DynamicsConnector"]


def _odata_string_literal(value: Any) -> str:
    """Quote an OData v4 string literal, doubling embedded single quotes."""
    return "'" + str(value).replace("'", "''") + "'"


class DynamicsConnector:
    """Microsoft Dynamics 365 connector implementing ConnectorProtocol.

    Usage (App-Only / Client Credentials)::

        d365 = DynamicsConnector(
            environment_url="https://myorg.crm.dynamics.com",
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
        d365.authenticate()
        contacts = d365.get_objects("contacts")

    Usage (Delegated / User Auth)::

        d365 = DynamicsConnector(
            environment_url="https://myorg.crm.dynamics.com",
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            username=os.environ["DYNAMICS_USERNAME"],
            password=os.environ["DYNAMICS_PASSWORD"],
        )
        d365.authenticate()
    """

    def __init__(
        self,
        *,
        environment_url: str,
        tenant_id: str,
        client_id: str,
        client_secret: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError("DynamicsConnector requires `requests`.")
        if not MSAL_AVAILABLE:
            raise ImportError(
                "DynamicsConnector requires `msal`. "
                "Install via `pip install msal`."
            )
        if not environment_url or not tenant_id or not client_id:
            raise ValueError("environment_url, tenant_id, and client_id are required.")

        self._environment_url = environment_url.rstrip("/")
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._authenticated = False

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        if client_secret:
            self._msal_app = msal.ConfidentialClientApplication(
                client_id,
                authority=authority,
                client_credential=client_secret,
            )
        else:
            self._msal_app = msal.PublicClientApplication(
                client_id,
                authority=authority,
            )

        self._scope = [f"{self._environment_url}/.default"]

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Prefer": f'odata.include-annotations="{FORMATTED_VALUE_ANNOTATION}"',
            "User-Agent": "siege_utilities/DynamicsConnector",
        })
        log.info("DynamicsConnector initialised (env: %s)", self._environment_url)

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # ConnectorProtocol — auth contract
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "dynamics365"

    def authenticate(self) -> None:
        """Authenticate via MSAL using the best available method."""
        if self._client_secret:
            self._auth_client_credentials()
        elif self._username and self._password:
            self._auth_username_password()
        else:
            raise ConnectorAuthError(
                "Provide client_secret for app-only auth, or "
                "username + password for delegated auth."
            )

    def is_connected(self) -> bool:
        if not self._authenticated or not self._access_token:
            return False
        if (
            self._token_expires_at is not None
            and datetime.now(timezone.utc) + TOKEN_REFRESH_MARGIN >= self._token_expires_at
        ):
            return False
        return True

    def refresh_access_token(self) -> None:
        # acquire_token_for_client may reuse a cached token rejected by the
        # API. Evict it so renewal obtains a fresh token from the authority.
        if self._client_secret:
            self._msal_app.remove_tokens_for_client()
        self.authenticate()

    # ------------------------------------------------------------------
    # ConnectorProtocol — read operations
    # ------------------------------------------------------------------

    def list_object_types(self) -> list[str]:
        """Available Dynamics 365 entity types."""
        self._ensure_connected()
        data = self.request("GET", "/api/data/v9.2/EntityDefinitions",
                            params={"$select": "LogicalName", "$filter": "IsValidForAdvancedFind eq true"})
        entities = data.get("value", [])
        return sorted(e["LogicalName"] for e in entities)

    def get_objects(
        self,
        object_type: str,
        *,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch records via OData query.

        Requests formatted values and retains their annotation columns,
        including industry labels, on every page.

        Args:
            object_type: Dataverse entity set name (``"contacts"``, etc.).
            fields: Columns ($select). ``None`` for defaults.
            filters: Key-value pairs translated to OData $filter.
            limit: Maximum records ($top). ``None`` for all; zero returns no rows.
        """
        entity_set = STANDARD_ENTITIES.get(object_type, object_type)
        columns = fields or DEFAULT_COLUMNS.get(entity_set, [])
        if limit == 0:
            return pd.DataFrame(columns=columns)

        params: dict[str, Any] = {}
        if columns:
            params["$select"] = ",".join(columns)
        if filters:
            params["$filter"] = self._build_odata_filter(filters)
        if limit is not None:
            params["$top"] = limit

        return self._query_all_odata(entity_set, params, columns)

    def fetch_xml(self, entity: str, fetch_xml: str) -> pd.DataFrame:
        """Execute FetchXML and follow paging cookies until all rows are read.

        Raises ConnectorError if more rows are advertised without a usable
        paging cookie, rather than returning a partial result.
        """
        import urllib.parse
        import xml.etree.ElementTree as ET

        self._ensure_connected()
        root = ET.fromstring(fetch_xml)
        page = int(root.get("page", "1"))
        root.set("page", str(page))
        records = []
        seen_cookies = set()
        annotations = ",".join([
            FORMATTED_VALUE_ANNOTATION,
            "Microsoft.Dynamics.CRM.fetchxmlpagingcookie",
            "Microsoft.Dynamics.CRM.morerecords",
        ])
        while True:
            encoded = urllib.parse.quote(ET.tostring(root, encoding="unicode"))
            path = f"/api/data/v9.2/{entity}?fetchXml={encoded}"
            data = self.request("GET", path, headers={
                "Prefer": f'odata.include-annotations="{annotations}"',
            })
            records.extend(data.get("value", []))
            cookie = data.get("@Microsoft.Dynamics.CRM.fetchxmlpagingcookie")
            if not data.get("@Microsoft.Dynamics.CRM.morerecords", bool(cookie)):
                break
            if not cookie or cookie in seen_cookies:
                raise ConnectorError("Dynamics FetchXML has more records but no new paging cookie.")
            seen_cookies.add(cookie)
            try:
                wrapper = ET.fromstring(cookie)
                next_page = int(wrapper.get("pagenumber", str(page + 1)))
                encoded_cookie = wrapper.get("pagingcookie")
                if encoded_cookie is not None:
                    cookie = urllib.parse.unquote(urllib.parse.unquote(encoded_cookie))
                elif wrapper.get("page") is None:
                    raise ValueError("Missing paging cookie value")
                if ET.fromstring(cookie).tag != "cookie" or next_page <= page:
                    raise ValueError("Invalid cookie or page")
            except (ET.ParseError, ValueError) as exc:
                raise ConnectorError("Dynamics FetchXML returned an invalid paging cookie.") from exc
            root.set("paging-cookie", cookie)
            root.set("page", str(next_page))
            page = next_page
        if not records:
            log.warning("FetchXML query returned 0 records")
            return pd.DataFrame()
        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # CRM model mapping helpers
    # ------------------------------------------------------------------

    def to_crm_contacts(self, df: pd.DataFrame) -> list:
        from siege_utilities.connectors._models import CRMAddress, CRMContact, _normalize_crm_record

        results: list[CRMContact] = []
        for _, row in df.iterrows():
            r = _normalize_crm_record(row.to_dict())
            address = CRMAddress(
                street=r.get("address1_line1"),
                city=r.get("address1_city"),
                state=r.get("address1_stateorprovince"),
                postal_code=r.get("address1_postalcode"),
                country=r.get("address1_country"),
            )
            extra_keys = set(r.keys()) - {
                "contactid", "firstname", "lastname", "emailaddress1",
                "telephone1", "jobtitle", "_parentcustomerid_value",
                "address1_line1", "address1_city", "address1_stateorprovince",
                "address1_postalcode", "address1_country",
            }
            results.append(CRMContact(
                id=str(r.get("contactid", "")),
                first_name=r.get("firstname"),
                last_name=r.get("lastname"),
                email=r.get("emailaddress1"),
                phone=r.get("telephone1"),
                title=r.get("jobtitle"),
                account_id=r.get("_parentcustomerid_value"),
                address=address,
                source_system="dynamics365",
                source_id=str(r.get("contactid", "")),
                metadata={k: r[k] for k in extra_keys if r.get(k) is not None},
            ))
        return results

    def to_crm_accounts(self, df: pd.DataFrame) -> list:
        """Map accounts using the formatted industry label when available.

        Without a label, industry is the option-set code as a string, not a
        label. Missing names use an empty string.
        """
        from siege_utilities.connectors._models import CRMAccount, CRMAddress, _normalize_crm_record
        from decimal import Decimal

        results: list[CRMAccount] = []
        industry_label_field = f"industrycode@{FORMATTED_VALUE_ANNOTATION}"
        for _, row in df.iterrows():
            r = _normalize_crm_record(row.to_dict())
            address = CRMAddress(
                street=r.get("address1_line1"),
                city=r.get("address1_city"),
                state=r.get("address1_stateorprovince"),
                postal_code=r.get("address1_postalcode"),
                country=r.get("address1_country"),
            )
            revenue = r.get("revenue")
            employees = r.get("numberofemployees")
            industry = r.get(industry_label_field)
            if not industry and r.get("industrycode") is not None:
                industry = str(r["industrycode"])
            extra_keys = set(r.keys()) - {
                "accountid", "name", "industrycode", "websiteurl",
                industry_label_field,
                "revenue", "numberofemployees", "address1_line1",
                "address1_city", "address1_stateorprovince",
                "address1_postalcode", "address1_country",
            }
            results.append(CRMAccount(
                id=str(r.get("accountid", "")),
                name=r.get("name") or "",
                industry=industry,
                website=r.get("websiteurl"),
                revenue=Decimal(str(revenue)) if revenue is not None else None,
                employee_count=int(employees) if employees is not None else None,
                address=address,
                source_system="dynamics365",
                source_id=str(r.get("accountid", "")),
                metadata={k: r[k] for k in extra_keys if r.get(k) is not None},
            ))
        return results

    def to_crm_opportunities(self, df: pd.DataFrame) -> list:
        """Map opportunities, retaining Dataverse's 0-100 probability scale.

        Missing names use an empty string.
        """
        from siege_utilities.connectors._models import CRMOpportunity, _normalize_crm_record
        from datetime import date as date_type
        from decimal import Decimal

        results: list[CRMOpportunity] = []
        for _, row in df.iterrows():
            r = _normalize_crm_record(row.to_dict())
            amount = r.get("estimatedvalue")
            close_raw = r.get("estimatedclosedate")
            close_date = None
            if close_raw:
                if isinstance(close_raw, str):
                    close_date = date_type.fromisoformat(close_raw[:10])
                elif isinstance(close_raw, date_type):
                    close_date = close_raw

            probability = r.get("closeprobability")
            extra_keys = set(r.keys()) - {
                "opportunityid", "name", "_parentaccountid_value",
                "stepname", "estimatedvalue", "estimatedclosedate",
                "closeprobability", "_ownerid_value",
            }
            results.append(CRMOpportunity(
                id=str(r.get("opportunityid", "")),
                name=r.get("name") or "",
                account_id=r.get("_parentaccountid_value"),
                stage=r.get("stepname"),
                amount=Decimal(str(amount)) if amount is not None else None,
                close_date=close_date,
                probability=float(probability) if probability is not None else None,
                owner_id=r.get("_ownerid_value"),
                source_system="dynamics365",
                source_id=str(r.get("opportunityid", "")),
                metadata={k: r[k] for k in extra_keys if r.get(k) is not None},
            ))
        return results

    # ------------------------------------------------------------------
    # ConnectorProtocol — write operations
    # ------------------------------------------------------------------

    def create_record(
        self, object_type: str, data: dict[str, Any]
    ) -> str:
        """Create a record from *data* in the *object_type* entity set.

        Return its ID from OData-EntityId, an edit link, or a body attribute.
        Raise ConnectorError if the response does not identify the new record.
        """
        entity_set = STANDARD_ENTITIES.get(object_type, object_type)
        path = f"/api/data/v9.2/{entity_set}"
        resp = self.request("POST", path, json_body=data)
        record_id = ""
        for link_key in ("OData-EntityId", "@odata.editLink"):
            odata_id = resp.get(link_key) or ""
            _, separator, key = odata_id.rpartition("(")
            if separator and key.endswith(")"):
                record_id = key[:-1]
                if record_id:
                    break
        if not record_id:
            id_attribute = {
                "contacts": "contactid",
                "accounts": "accountid",
                "opportunities": "opportunityid",
                "leads": "leadid",
                "tasks": "activityid",
                "appointments": "activityid",
                "incidents": "incidentid",
            }.get(object_type, f"{object_type.removesuffix('s')}id")
            record_id = resp.get(id_attribute, "")
        if not record_id:
            raise ConnectorError(
                f"Dynamics create {entity_set} succeeded but returned no record id."
            )
        log.info("Created %s record: %s", entity_set, record_id)
        return record_id

    def update_record(
        self, object_type: str, record_id: str, data: dict[str, Any]
    ) -> bool:
        entity_set = STANDARD_ENTITIES.get(object_type, object_type)
        path = f"/api/data/v9.2/{entity_set}({record_id})"
        self.request("PATCH", path, json_body=data)
        log.info("Updated %s record: %s", entity_set, record_id)
        return True

    def upsert_records(
        self,
        object_type: str,
        records: pd.DataFrame,
        match_field: str,
    ) -> UpsertResult:
        """Batch upsert via $batch endpoint (up to 1000 per request)."""
        from siege_utilities.connectors._protocol import UpsertError

        if records.empty:
            log.warning("upsert_records(%s): empty DataFrame", object_type)
            return UpsertResult(success_count=0, failure_count=0)

        entity_set = STANDARD_ENTITIES.get(object_type, object_type)
        record_dicts = [sanitize_record(row) for row in records.to_dict(orient="records")]
        batches = [
            record_dicts[i:i + BATCH_SIZE]
            for i in range(0, len(record_dicts), BATCH_SIZE)
        ]

        all_created: list[str] = []
        all_updated: list[str] = []
        all_errors: list[UpsertError] = []
        total_success = 0
        total_failure = 0

        for batch_idx, batch in enumerate(batches):
            log.info(
                "upsert_records(%s): batch %d/%d (%d records)",
                object_type, batch_idx + 1, len(batches), len(batch),
            )
            result = self._batch_upsert(
                entity_set, batch, match_field,
                base_index=batch_idx * BATCH_SIZE,
            )
            total_success += result.success_count
            total_failure += result.failure_count
            all_created.extend(result.created_ids)
            all_updated.extend(result.updated_ids)
            all_errors.extend(result.errors)

        log.info(
            "upsert_records(%s): %d succeeded, %d failed",
            object_type, total_success, total_failure,
        )
        return UpsertResult(
            success_count=total_success,
            failure_count=total_failure,
            created_ids=all_created,
            updated_ids=all_updated,
            errors=all_errors,
        )

    def _batch_upsert(
        self,
        entity_set: str,
        records: list[dict[str, Any]],
        match_field: str,
        *,
        base_index: int = 0,
    ) -> UpsertResult:
        """Execute a $batch request with individual upserts."""
        from siege_utilities.connectors._protocol import UpsertError

        _validate_identifier(entity_set)
        _validate_identifier(match_field)
        self._ensure_connected()
        batch_id = str(uuid.uuid4())
        changeset_id = str(uuid.uuid4())
        boundary = f"batch_{batch_id}"
        changeset_boundary = f"changeset_{changeset_id}"

        body_parts = [f"--{boundary}", f"Content-Type: multipart/mixed;boundary={changeset_boundary}", ""]

        for i, rec in enumerate(records):
            match_val = rec.get(match_field, "")
            # Escape OData syntax before encoding for the inner request URI.
            match_literal = quote(_odata_string_literal(match_val), safe="")
            uri = (
                f"{self._environment_url}/api/data/v9.2/{entity_set}"
                f"({match_field}={match_literal})"
            )
            import json as _json
            rec_body = _json.dumps(rec, allow_nan=False)

            body_parts.extend([
                f"--{changeset_boundary}",
                "Content-Type: application/http",
                "Content-Transfer-Encoding: binary",
                f"Content-ID: {i + 1}",
                "",
                f"PATCH {uri} HTTP/1.1",
                "Content-Type: application/json",
                f"Content-Length: {len(rec_body)}",
                "Prefer: return=representation",
                "",
                rec_body,
            ])

        body_parts.extend([f"--{changeset_boundary}--", f"--{boundary}--"])
        batch_body = "\r\n".join(body_parts)

        url = f"{self._environment_url}/api/data/v9.2/$batch"
        resp = self._session.post(
            url,
            data=batch_body,
            headers={
                "Content-Type": f"multipart/mixed;boundary={boundary}",
                "Authorization": f"Bearer {self._access_token}",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
            },
            timeout=self._timeout * 4,
        )

        created: list[str] = []
        updated: list[str] = []
        errors: list[UpsertError] = []
        success_count = 0
        failure_count = 0

        self._raise_batch_control_error(resp.status_code, resp.headers, resp.text)
        if resp.status_code not in (200, 202):
            for i, rec in enumerate(records):
                failure_count += 1
                errors.append(UpsertError(
                    record_index=base_index + i,
                    message=f"Batch failed with status {resp.status_code}: {resp.text[:200]}",
                ))
        else:
            parts = self._parse_batch_response(resp)
            by_id = {}
            invalid = False
            for position, (content_id, status, headers, body) in enumerate(parts, 1):
                self._raise_batch_control_error(status, headers, body)
                try:
                    index = int(content_id) if content_id is not None else position
                except ValueError:
                    invalid = True
                    continue
                if index in by_id or not 1 <= index <= len(records):
                    invalid = True
                by_id[index] = (status, body)

            # All submitted operations share one atomic changeset. A failed
            # operation rolls back the other records, even if parts are absent
            # or a response includes earlier successful operation statuses.
            failed = next(((status, body) for _, status, _, body in parts
                           if not 200 <= status < 300), None)
            for i, rec in enumerate(records):
                result = by_id.get(i + 1)
                if failed is not None:
                    status, body = result if result and not 200 <= result[0] < 300 else failed
                    message, code = self._batch_error_detail(status, body)
                    errors.append(UpsertError(
                        record_index=base_index + i,
                        message=f"Changeset failed or rolled back: {message}",
                        code=code,
                    ))
                elif invalid or result is None:
                    errors.append(UpsertError(
                        record_index=base_index + i,
                        message="Missing or invalid Dynamics batch response part",
                    ))
                else:
                    success_count += 1
                    target = created if result[0] == 201 else updated
                    target.append(rec.get(match_field, f"record-{base_index + i}"))
            failure_count = len(errors)

        return UpsertResult(
            success_count=success_count,
            failure_count=failure_count,
            created_ids=created,
            updated_ids=updated,
            errors=errors,
        )

    def _raise_batch_control_error(self, status: int, headers: Mapping[str, str], body: str) -> None:
        if status in (401, 403):
            raise ConnectorAuthError(f"Dynamics {status}: {body[:200]}")
        if status == 429:
            raise rate_limit_error(
                headers, "Dynamics rate limit hit on POST $batch.", self._retry_backoff,
            )

    @staticmethod
    def _parse_batch_response(resp: requests.Response) -> list[tuple[str | None, int, Any, str]]:
        """Read nested MIME changesets and the embedded HTTP responses."""
        from email.parser import Parser

        content_type = resp.headers.get("Content-Type", "")
        message = Parser().parsestr(f"Content-Type: {content_type}\n\n{resp.text}")
        parts = []
        for part in message.walk():
            if part.get_content_type() != "application/http":
                continue
            payload = part.get_payload()
            if not isinstance(payload, str):
                continue
            status_line, _, rest = payload.lstrip().partition("\n")
            tokens = status_line.split()
            if len(tokens) < 2 or not tokens[0].startswith("HTTP/") or not tokens[1].isdigit():
                continue
            http = Parser().parsestr(rest)
            parts.append((
                part.get("Content-ID", http.get("Content-ID")),
                int(tokens[1]), http, http.get_payload(),
            ))
        return parts

    @staticmethod
    def _batch_error_detail(status: int, body: str) -> tuple[str, str | None]:
        import json

        try:
            payload = json.loads(body)
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"]), error.get("code")
        except json.JSONDecodeError:
            pass
        return f"HTTP {status}: {body[:200]}", str(status)

    # ------------------------------------------------------------------
    # OData query helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_odata_filter(filters: dict[str, Any]) -> str:
        """Translate Python dict to OData $filter expression."""
        parts: list[str] = []
        for key, value in filters.items():
            _validate_identifier(key)
            if value is None:
                parts.append(f"{key} eq null")
            elif isinstance(value, bool):
                parts.append(f"{key} eq {'true' if value else 'false'}")
            elif isinstance(value, (int, float)):
                parts.append(f"{key} eq {value}")
            elif isinstance(value, list):
                or_parts = [f"{key} eq {_odata_string_literal(v)}" for v in value]
                parts.append(f"({' or '.join(or_parts)})")
            else:
                parts.append(f"{key} eq {_odata_string_literal(value)}")
        return " and ".join(parts)

    def _query_all_odata(
        self,
        entity_set: str,
        params: dict[str, Any],
        columns: list[str],
    ) -> pd.DataFrame:
        """Execute an OData query and follow @odata.nextLink pagination."""
        all_records: list[dict[str, Any]] = []
        path = f"/api/data/v9.2/{entity_set}"
        data = self.request("GET", path, params=params)
        records = data.get("value", [])
        all_records.extend(records)
        log.info("OData query %s: %d records", entity_set, len(records))

        while data.get("@odata.nextLink"):
            next_url = data["@odata.nextLink"]
            rel_path = next_url.replace(self._environment_url, "")
            data = self.request("GET", rel_path)
            page_records = data.get("value", [])
            all_records.extend(page_records)
            log.info("OData page: %d records (total: %d)", len(page_records), len(all_records))

        if not all_records:
            log.warning("get_objects(%s): 0 records", entity_set)
            return pd.DataFrame(columns=columns or [])

        return pd.DataFrame(all_records)

    # ------------------------------------------------------------------
    # MSAL auth
    # ------------------------------------------------------------------

    def _auth_client_credentials(self) -> None:
        """App-only auth via client credentials."""
        result = self._msal_app.acquire_token_for_client(scopes=self._scope)
        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise ConnectorAuthError(f"Dynamics 365 client credentials auth failed: {error}")
        self._set_token(result)
        log.info("Authenticated via client credentials (env: %s)", self._environment_url)

    def _auth_username_password(self) -> None:
        """Delegated auth via username/password (ROPC)."""
        result = self._msal_app.acquire_token_by_username_password(
            username=self._username,
            password=self._password,
            scopes=self._scope,
        )
        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise ConnectorAuthError(f"Dynamics 365 user auth failed: {error}")
        self._set_token(result)
        log.info("Authenticated via username/password (env: %s)", self._environment_url)

    def _set_token(self, result: dict[str, Any]) -> None:
        self._access_token = result["access_token"]
        self._session.headers["Authorization"] = f"Bearer {self._access_token}"
        self._authenticated = True
        expires_in = result.get("expires_in", 3600)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._authenticated:
            raise ConnectorAuthError("Not authenticated. Call authenticate() first.")
        if (
            self._token_expires_at is not None
            and datetime.now(timezone.utc) + TOKEN_REFRESH_MARGIN >= self._token_expires_at
        ):
            log.info("Token expires soon or has expired, re-authenticating...")
            self.refresh_access_token()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the Dataverse Web API."""
        self._ensure_connected()
        url = f"{self._environment_url}{path}" if not path.startswith("http") else path
        last_exc: BaseException | None = None

        auth_refreshed = False
        attempts = retry_attempts(method, self._retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                while True:
                    resp = self._session.request(
                        method, url,
                        params=dict(params) if params else None,
                        json=json_body,
                        timeout=self._timeout,
                        **({"headers": dict(headers)} if headers is not None else {}),
                    )
                    if (
                        resp.status_code != 401
                        or auth_refreshed
                        or not (self._client_secret or (self._username and self._password))
                    ):
                        break
                    # A rejected token permits one replay, including writes.
                    # Keep this separate from transport and server-error retries.
                    auth_refreshed = True
                    self.refresh_access_token()
            except requests.exceptions.InvalidJSONError as exc:
                raise ConnectorError(
                    f"Dynamics JSON encoding failed for {method} {path}: {exc}"
                ) from exc
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                log.warning(
                    "Dynamics %s %s attempt %d/%d failed: %s",
                    method, path, attempt, attempts, exc,
                )
                if attempt < attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code in (401, 403):
                error_msg = self._extract_error(resp)
                raise ConnectorAuthError(f"Dynamics {resp.status_code}: {error_msg}")

            if resp.status_code == 429:
                error = rate_limit_error(
                    resp.headers, f"Dynamics rate limit hit on {method} {path}.",
                    self._retry_backoff ** attempt,
                )
                if attempt < attempts:
                    continue
                raise error

            if resp.status_code == 404:
                raise ConnectorNotFoundError(f"Dynamics resource not found: {path}")

            if 500 <= resp.status_code < 600:
                last_exc = ConnectorError(f"Dynamics {resp.status_code} on {method} {path}.")
                log.warning(
                    "Dynamics %s %s 5xx %d attempt %d/%d",
                    method, path, resp.status_code, attempt, attempts,
                )
                if attempt < attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code == 204:
                entity_id = resp.headers.get("OData-EntityId")
                if entity_id is not None:
                    return {"OData-EntityId": entity_id}
                return {}

            if not (200 <= resp.status_code < 300):
                error_msg = self._extract_error(resp)
                raise ConnectorError(f"Dynamics {resp.status_code}: {error_msg}")

            try:
                return resp.json()
            except ValueError as exc:
                raise ConnectorError(
                    f"Dynamics returned non-JSON on {method} {path}: "
                    f"{resp.text[:200]!r}"
                ) from exc

        raise ConnectorError(
            f"Dynamics {method} {path} failed after {attempts} "
            f"attempts: {last_exc}"
        )

    @staticmethod
    def _extract_error(resp: requests.Response) -> str:
        try:
            body = resp.json()
            if isinstance(body, dict):
                error = body.get("error", {})
                if isinstance(error, dict):
                    return error.get("message", resp.text[:200])
                return str(error) or resp.text[:200]
            return resp.text[:200]
        except ValueError:
            return resp.text[:200]
