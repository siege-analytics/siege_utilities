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
from datetime import datetime, timedelta
from typing import Any, Mapping

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

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
    UpsertResult,
)

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 2.0
BATCH_SIZE = 1000

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
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            return False
        return True

    def refresh_access_token(self) -> None:
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

        Args:
            object_type: Dataverse entity set name (``"contacts"``, etc.).
            fields: Columns ($select). ``None`` for defaults.
            filters: Key-value pairs translated to OData $filter.
            limit: Maximum records ($top).
        """
        entity_set = STANDARD_ENTITIES.get(object_type, object_type)
        columns = fields or DEFAULT_COLUMNS.get(entity_set, [])

        params: dict[str, Any] = {}
        if columns:
            params["$select"] = ",".join(columns)
        if filters:
            params["$filter"] = self._build_odata_filter(filters)
        if limit:
            params["$top"] = limit

        return self._query_all_odata(entity_set, params, columns)

    def fetch_xml(self, entity: str, fetch_xml: str) -> pd.DataFrame:
        """Execute a FetchXML query (power-user escape hatch)."""
        import urllib.parse

        self._ensure_connected()
        encoded = urllib.parse.quote(fetch_xml)
        path = f"/api/data/v9.2/{entity}?fetchXml={encoded}"
        data = self.request("GET", path)
        records = data.get("value", [])
        if not records:
            log.warning("FetchXML query returned 0 records")
            return pd.DataFrame()
        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # CRM model mapping helpers
    # ------------------------------------------------------------------

    def to_crm_contacts(self, df: pd.DataFrame) -> list:
        from siege_utilities.connectors._models import CRMAddress, CRMContact

        results: list[CRMContact] = []
        for _, row in df.iterrows():
            r = row.to_dict()
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
        from siege_utilities.connectors._models import CRMAccount, CRMAddress
        from decimal import Decimal

        results: list[CRMAccount] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            address = CRMAddress(
                street=r.get("address1_line1"),
                city=r.get("address1_city"),
                state=r.get("address1_stateorprovince"),
                postal_code=r.get("address1_postalcode"),
                country=r.get("address1_country"),
            )
            revenue = r.get("revenue")
            employees = r.get("numberofemployees")
            extra_keys = set(r.keys()) - {
                "accountid", "name", "industrycode", "websiteurl",
                "revenue", "numberofemployees", "address1_line1",
                "address1_city", "address1_stateorprovince",
                "address1_postalcode", "address1_country",
            }
            results.append(CRMAccount(
                id=str(r.get("accountid", "")),
                name=r.get("name", ""),
                industry=str(r.get("industrycode")) if r.get("industrycode") else None,
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
        from siege_utilities.connectors._models import CRMOpportunity
        from datetime import date as date_type
        from decimal import Decimal

        results: list[CRMOpportunity] = []
        for _, row in df.iterrows():
            r = row.to_dict()
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
                name=r.get("name", ""),
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
        entity_set = STANDARD_ENTITIES.get(object_type, object_type)
        path = f"/api/data/v9.2/{entity_set}"
        resp = self.request("POST", path, json_body=data)
        record_id = resp.get(f"{object_type.rstrip('s')}id", "")
        if not record_id:
            odata_id = resp.get("@odata.editLink", "")
            if "(" in odata_id:
                record_id = odata_id.split("(")[-1].rstrip(")")
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
        record_dicts = records.to_dict(orient="records")
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

        self._ensure_connected()
        batch_id = str(uuid.uuid4())
        changeset_id = str(uuid.uuid4())
        boundary = f"batch_{batch_id}"
        changeset_boundary = f"changeset_{changeset_id}"

        body_parts = [f"--{boundary}", f"Content-Type: multipart/mixed;boundary={changeset_boundary}", ""]

        for i, rec in enumerate(records):
            match_val = rec.get(match_field, "")
            uri = f"{self._environment_url}/api/data/v9.2/{entity_set}({match_field}='{match_val}')"
            import json as _json
            rec_body = _json.dumps(rec)

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

        if resp.status_code in (200, 202):
            for i, rec in enumerate(records):
                success_count += 1
                updated.append(rec.get(match_field, f"record-{base_index + i}"))
        else:
            for i, rec in enumerate(records):
                failure_count += 1
                errors.append(UpsertError(
                    record_index=base_index + i,
                    message=f"Batch failed with status {resp.status_code}: {resp.text[:200]}",
                ))

        return UpsertResult(
            success_count=success_count,
            failure_count=failure_count,
            created_ids=created,
            updated_ids=updated,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # OData query helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_odata_filter(filters: dict[str, Any]) -> str:
        """Translate Python dict to OData $filter expression."""
        parts: list[str] = []
        for key, value in filters.items():
            if value is None:
                parts.append(f"{key} eq null")
            elif isinstance(value, bool):
                parts.append(f"{key} eq {'true' if value else 'false'}")
            elif isinstance(value, (int, float)):
                parts.append(f"{key} eq {value}")
            elif isinstance(value, list):
                or_parts = [f"{key} eq '{v}'" for v in value]
                parts.append(f"({' or '.join(or_parts)})")
            else:
                escaped = str(value).replace("'", "''")
                parts.append(f"{key} eq '{escaped}'")
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
        self._token_expires_at = datetime.now() + timedelta(seconds=int(expires_in))

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._authenticated:
            raise ConnectorAuthError("Not authenticated. Call authenticate() first.")
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            log.info("Token expired, re-authenticating...")
            self.authenticate()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the Dataverse Web API."""
        self._ensure_connected()
        url = f"{self._environment_url}{path}" if not path.startswith("http") else path
        last_exc: BaseException | None = None

        for attempt in range(1, self._retry_attempts + 1):
            try:
                resp = self._session.request(
                    method, url,
                    params=dict(params) if params else None,
                    json=json_body,
                    timeout=self._timeout,
                )
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                log.warning(
                    "Dynamics %s %s attempt %d/%d failed: %s",
                    method, path, attempt, self._retry_attempts, exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code in (401, 403):
                error_msg = self._extract_error(resp)
                raise ConnectorAuthError(f"Dynamics {resp.status_code}: {error_msg}")

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise ConnectorRateLimitError(
                    f"Dynamics rate limit hit on {method} {path}.",
                    retry_after=float(retry_after) if retry_after else None,
                )

            if resp.status_code == 404:
                raise ConnectorNotFoundError(f"Dynamics resource not found: {path}")

            if 500 <= resp.status_code < 600:
                last_exc = ConnectorError(f"Dynamics {resp.status_code} on {method} {path}.")
                log.warning(
                    "Dynamics %s %s 5xx %d attempt %d/%d",
                    method, path, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code == 204:
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
            f"Dynamics {method} {path} failed after {self._retry_attempts} "
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
