"""
Zoho CRM connector — OAuth, connection management, and CRUD.

Supports OAuth 2.0 self-client (server-to-server) and web-based flows
for the Zoho CRM v6 API. Multi-DC support for all five Zoho data centers.

Rate limits vary by Zoho edition; the connector handles 429s with
exponential backoff. Refresh tokens in Zoho have a limited use count
before requiring re-authorization.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Mapping

import pandas as pd

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
    UpsertResult,
)

log = logging.getLogger(__name__)

ZOHO_DATA_CENTERS: dict[str, dict[str, str]] = {
    "us": {
        "accounts_url": "https://accounts.zoho.com",
        "api_url": "https://www.zohoapis.com",
    },
    "eu": {
        "accounts_url": "https://accounts.zoho.eu",
        "api_url": "https://www.zohoapis.eu",
    },
    "in": {
        "accounts_url": "https://accounts.zoho.in",
        "api_url": "https://www.zohoapis.in",
    },
    "au": {
        "accounts_url": "https://accounts.zoho.com.au",
        "api_url": "https://www.zohoapis.com.au",
    },
    "jp": {
        "accounts_url": "https://accounts.zoho.jp",
        "api_url": "https://www.zohoapis.jp",
    },
}

API_VERSION = "v6"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 2.0
BATCH_SIZE = 100

STANDARD_MODULES = [
    "Leads",
    "Contacts",
    "Accounts",
    "Deals",
    "Tasks",
    "Events",
    "Calls",
    "Campaigns",
]

DEFAULT_FIELDS: dict[str, list[str]] = {
    "Contacts": [
        "id", "First_Name", "Last_Name", "Email", "Phone", "Title",
        "Account_Name", "Department", "Mailing_Street", "Mailing_City",
        "Mailing_State", "Mailing_Zip", "Mailing_Country",
        "Created_Time", "Modified_Time",
    ],
    "Leads": [
        "id", "First_Name", "Last_Name", "Email", "Phone", "Company",
        "Title", "Lead_Status", "Lead_Source", "Industry",
        "Street", "City", "State", "Zip_Code", "Country",
        "Created_Time", "Modified_Time",
    ],
    "Accounts": [
        "id", "Account_Name", "Industry", "Website", "Annual_Revenue",
        "Employees", "Billing_Street", "Billing_City",
        "Billing_State", "Billing_Code", "Billing_Country",
        "Phone", "Account_Type", "Created_Time", "Modified_Time",
    ],
    "Deals": [
        "id", "Deal_Name", "Stage", "Amount", "Closing_Date",
        "Probability", "Owner", "Type", "Lead_Source",
        "Account_Name", "Created_Time", "Modified_Time",
    ],
    "Tasks": [
        "id", "Subject", "Description", "Status", "Priority",
        "Due_Date", "Who_Id", "What_Id", "Owner",
        "Created_Time", "Modified_Time",
    ],
    "Events": [
        "id", "Event_Title", "Description", "Start_DateTime", "End_DateTime",
        "Who_Id", "What_Id", "Owner",
        "Created_Time", "Modified_Time",
    ],
}

__all__ = ["ZohoConnector"]


class ZohoConnector:
    """Zoho CRM connector implementing ConnectorProtocol.

    Usage (Self-Client)::

        zoho = ZohoConnector(
            client_id=os.environ["ZOHO_CLIENT_ID"],
            client_secret=os.environ["ZOHO_CLIENT_SECRET"],
            refresh_token=os.environ["ZOHO_REFRESH_TOKEN"],
            data_center="us",
        )
        zoho.authenticate()
        contacts = zoho.get_objects("Contacts")

    Usage (Web Flow)::

        zoho = ZohoConnector(
            client_id=os.environ["ZOHO_CLIENT_ID"],
            client_secret=os.environ["ZOHO_CLIENT_SECRET"],
            data_center="us",
        )
        auth_url = zoho.get_authorization_url(
            redirect_uri="https://myapp/callback",
            scopes=["ZohoCRM.modules.ALL"],
        )
        zoho.authenticate_with_code(code="...", redirect_uri="https://myapp/callback")
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str | None = None,
        data_center: str = "us",
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "ZohoConnector requires `requests`. "
                "Install via `pip install siege-utilities`."
            )
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required.")
        if data_center not in ZOHO_DATA_CENTERS:
            raise ValueError(
                f"Unknown data center '{data_center}'. "
                f"Valid: {', '.join(ZOHO_DATA_CENTERS.keys())}"
            )

        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._dc = ZOHO_DATA_CENTERS[data_center]
        self._data_center = data_center
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._authenticated = False

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "siege_utilities/ZohoConnector",
        })
        log.info("ZohoConnector initialised (dc: %s)", data_center)

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
        return "zoho"

    def authenticate(self) -> None:
        """Authenticate using the refresh token (self-client flow)."""
        if self._refresh_token:
            self._refresh_access()
        else:
            raise ConnectorAuthError(
                "No refresh token. For the web flow, call "
                "get_authorization_url() then authenticate_with_code()."
            )

    def authenticate_with_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> None:
        """Complete the OAuth 2.0 web-based flow."""
        token_url = f"{self._dc['accounts_url']}/oauth/v2/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": redirect_uri,
        }
        self._exchange_token(token_url, payload)
        log.info("Authenticated via web-based OAuth flow (dc: %s)", self._data_center)

    def get_authorization_url(
        self,
        redirect_uri: str,
        scopes: list[str] | None = None,
        state: str | None = None,
        access_type: str = "offline",
    ) -> str:
        """Generate the OAuth 2.0 authorization URL."""
        scope_str = ",".join(scopes) if scopes else "ZohoCRM.modules.ALL"
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": scope_str,
            "response_type": "code",
            "access_type": access_type,
        }
        if state:
            params["state"] = state
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self._dc['accounts_url']}/oauth/v2/auth?{query}"

    def is_connected(self) -> bool:
        if not self._authenticated or not self._access_token:
            return False
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            return False
        return True

    def refresh_access_token(self) -> None:
        self._refresh_access()

    # ------------------------------------------------------------------
    # ConnectorProtocol — read operations
    # ------------------------------------------------------------------

    def list_object_types(self) -> list[str]:
        """Available Zoho CRM modules."""
        self._ensure_connected()
        path = f"/crm/{API_VERSION}/settings/modules"
        data = self.request("GET", path)
        modules = data.get("modules", [])
        return sorted(m["api_name"] for m in modules if m.get("api_supported"))

    def get_objects(
        self,
        object_type: str,
        *,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch records from a Zoho CRM module."""
        selected_fields = fields or DEFAULT_FIELDS.get(object_type, ["id"])

        if filters:
            return self._coql_query(object_type, selected_fields, filters, limit)

        return self._list_records(object_type, selected_fields, limit)

    def get_custom_module_fields(self, module: str) -> list[dict[str, Any]]:
        """Discover fields for a custom module."""
        self._ensure_connected()
        path = f"/crm/{API_VERSION}/settings/fields"
        data = self.request("GET", path, params={"module": module})
        return data.get("fields", [])

    # ------------------------------------------------------------------
    # CRM model mapping helpers
    # ------------------------------------------------------------------

    def to_crm_contacts(self, df: pd.DataFrame) -> list:
        from siege_utilities.connectors._models import CRMAddress, CRMContact

        results: list[CRMContact] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            address = CRMAddress(
                street=r.get("Mailing_Street"),
                city=r.get("Mailing_City"),
                state=r.get("Mailing_State"),
                postal_code=r.get("Mailing_Zip"),
                country=r.get("Mailing_Country"),
            )
            extra_keys = set(r.keys()) - {
                "id", "First_Name", "Last_Name", "Email", "Phone",
                "Title", "Account_Name", "Mailing_Street", "Mailing_City",
                "Mailing_State", "Mailing_Zip", "Mailing_Country",
            }
            account_name = r.get("Account_Name")
            account_id = None
            if isinstance(account_name, dict):
                account_id = account_name.get("id")
            results.append(CRMContact(
                id=str(r["id"]),
                first_name=r.get("First_Name"),
                last_name=r.get("Last_Name"),
                email=r.get("Email"),
                phone=r.get("Phone"),
                title=r.get("Title"),
                account_id=account_id,
                address=address,
                source_system="zoho",
                source_id=str(r["id"]),
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
                street=r.get("Billing_Street"),
                city=r.get("Billing_City"),
                state=r.get("Billing_State"),
                postal_code=r.get("Billing_Code"),
                country=r.get("Billing_Country"),
            )
            revenue = r.get("Annual_Revenue")
            employees = r.get("Employees")
            extra_keys = set(r.keys()) - {
                "id", "Account_Name", "Industry", "Website", "Annual_Revenue",
                "Employees", "Billing_Street", "Billing_City",
                "Billing_State", "Billing_Code", "Billing_Country",
            }
            results.append(CRMAccount(
                id=str(r["id"]),
                name=r.get("Account_Name", ""),
                industry=r.get("Industry"),
                website=r.get("Website"),
                revenue=Decimal(str(revenue)) if revenue is not None else None,
                employee_count=int(employees) if employees is not None else None,
                address=address,
                source_system="zoho",
                source_id=str(r["id"]),
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
            amount = r.get("Amount")
            close_raw = r.get("Closing_Date")
            close_date = None
            if close_raw:
                if isinstance(close_raw, str):
                    close_date = date_type.fromisoformat(close_raw[:10])
                elif isinstance(close_raw, date_type):
                    close_date = close_raw

            probability = r.get("Probability")
            owner = r.get("Owner")
            owner_id = owner.get("id") if isinstance(owner, dict) else str(owner) if owner else None
            account = r.get("Account_Name")
            account_id = account.get("id") if isinstance(account, dict) else None

            extra_keys = set(r.keys()) - {
                "id", "Deal_Name", "Stage", "Amount",
                "Closing_Date", "Probability", "Owner", "Account_Name",
            }
            results.append(CRMOpportunity(
                id=str(r["id"]),
                name=r.get("Deal_Name", ""),
                account_id=account_id,
                stage=r.get("Stage"),
                amount=Decimal(str(amount)) if amount is not None else None,
                close_date=close_date,
                probability=float(probability) if probability is not None else None,
                owner_id=owner_id,
                source_system="zoho",
                source_id=str(r["id"]),
                metadata={k: r[k] for k in extra_keys if r.get(k) is not None},
            ))
        return results

    # ------------------------------------------------------------------
    # ConnectorProtocol — write operations
    # ------------------------------------------------------------------

    def create_record(
        self, object_type: str, data: dict[str, Any]
    ) -> str:
        path = f"/crm/{API_VERSION}/{object_type}"
        resp = self.request("POST", path, json_body={"data": [data]})
        results = resp.get("data", [])
        if not results or results[0].get("status") != "success":
            details = results[0] if results else resp
            msg = details.get("message", str(details))
            raise ConnectorError(f"Failed to create {object_type}: {msg}")
        record_id = results[0]["details"]["id"]
        log.info("Created %s record: %s", object_type, record_id)
        return record_id

    def update_record(
        self, object_type: str, record_id: str, data: dict[str, Any]
    ) -> bool:
        data["id"] = record_id
        path = f"/crm/{API_VERSION}/{object_type}"
        resp = self.request("PUT", path, json_body={"data": [data]})
        results = resp.get("data", [])
        if not results or results[0].get("status") != "success":
            details = results[0] if results else resp
            msg = details.get("message", str(details))
            raise ConnectorError(f"Failed to update {object_type}/{record_id}: {msg}")
        log.info("Updated %s record: %s", object_type, record_id)
        return True

    def upsert_records(
        self,
        object_type: str,
        records: pd.DataFrame,
        match_field: str,
    ) -> UpsertResult:
        """Batch upsert via Zoho record API (100 records per request)."""
        from siege_utilities.connectors._protocol import UpsertError

        if records.empty:
            log.warning("upsert_records(%s): empty DataFrame", object_type)
            return UpsertResult(success_count=0, failure_count=0)

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
            path = f"/crm/{API_VERSION}/{object_type}/upsert"
            try:
                resp = self.request("POST", path, json_body={
                    "data": batch,
                    "duplicate_check_fields": [match_field],
                })
            except ConnectorError as exc:
                for i in range(len(batch)):
                    all_errors.append(UpsertError(
                        record_index=batch_idx * BATCH_SIZE + i,
                        message=str(exc),
                    ))
                total_failure += len(batch)
                continue

            for i, result in enumerate(resp.get("data", [])):
                if result.get("status") == "success":
                    total_success += 1
                    rec_id = result.get("details", {}).get("id", "")
                    action = result.get("action", "")
                    if action == "insert":
                        all_created.append(rec_id)
                    else:
                        all_updated.append(rec_id)
                else:
                    total_failure += 1
                    all_errors.append(UpsertError(
                        record_index=batch_idx * BATCH_SIZE + i,
                        message=result.get("message", "Unknown error"),
                        code=result.get("code"),
                    ))

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

    # ------------------------------------------------------------------
    # Internal — list and COQL
    # ------------------------------------------------------------------

    def _list_records(
        self,
        module: str,
        fields: list[str],
        limit: int | None,
    ) -> pd.DataFrame:
        """List records via the records API with pagination."""
        all_records: list[dict[str, Any]] = []
        page = 1
        per_page = min(limit or 200, 200)

        while True:
            path = f"/crm/{API_VERSION}/{module}"
            params: dict[str, Any] = {
                "fields": ",".join(fields),
                "per_page": per_page,
                "page": page,
            }
            data = self.request("GET", path, params=params)
            records = data.get("data", [])
            if not records:
                break

            all_records.extend(records)
            log.info("Listed %s: page %d, %d records (total: %d)",
                     module, page, len(records), len(all_records))

            if limit and len(all_records) >= limit:
                all_records = all_records[:limit]
                break

            info = data.get("info", {})
            if not info.get("more_records"):
                break
            page += 1

        return self._records_to_dataframe(all_records, fields)

    def _coql_query(
        self,
        module: str,
        fields: list[str],
        filters: dict[str, Any],
        limit: int | None,
    ) -> pd.DataFrame:
        """Execute a COQL query for filtered access."""
        field_clause = ", ".join(fields)
        where_parts: list[str] = []
        for key, value in filters.items():
            if value is None:
                where_parts.append(f"{key} is null")
            elif isinstance(value, bool):
                where_parts.append(f"{key} = {'true' if value else 'false'}")
            elif isinstance(value, (int, float)):
                where_parts.append(f"{key} = {value}")
            elif isinstance(value, list):
                vals = ", ".join(f"'{self._coql_escape(str(v))}'" for v in value)
                where_parts.append(f"{key} in ({vals})")
            else:
                where_parts.append(f"{key} = '{self._coql_escape(str(value))}'")

        query = f"select {field_clause} from {module}"
        if where_parts:
            query += " where " + " and ".join(where_parts)
        if limit:
            query += f" limit {int(limit)}"

        path = f"/crm/{API_VERSION}/coql"
        all_records: list[dict[str, Any]] = []
        offset = 0

        while True:
            paginated_query = query
            if offset > 0:
                paginated_query += f" offset {offset}"
            data = self.request("POST", path, json_body={"select_query": paginated_query})
            records = data.get("data", [])
            if not records:
                break

            all_records.extend(records)
            log.info("COQL query: %d records (total: %d)", len(records), len(all_records))

            if not data.get("info", {}).get("more_records"):
                break
            offset += len(records)

        return self._records_to_dataframe(all_records, fields)

    @staticmethod
    def _coql_escape(value: str) -> str:
        return value.replace("'", "\\'")

    @staticmethod
    def _records_to_dataframe(
        records: list[dict[str, Any]],
        fields: list[str],
    ) -> pd.DataFrame:
        if not records:
            return pd.DataFrame(columns=fields)

        rows: list[dict[str, Any]] = []
        for rec in records:
            row: dict[str, Any] = {}
            for f in fields:
                val = rec.get(f)
                if isinstance(val, dict) and "id" in val:
                    row[f] = val.get("name", val.get("id"))
                    row[f"{f}_id"] = val["id"]
                else:
                    row[f] = val
            rows.append(row)
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._authenticated:
            raise ConnectorAuthError("Not authenticated. Call authenticate() first.")
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            if self._refresh_token:
                log.info("Token expired, refreshing...")
                self._refresh_access()
            else:
                raise ConnectorAuthError("Access token expired. Re-authenticate.")

    def _refresh_access(self) -> None:
        """Refresh the access token via the refresh token grant."""
        if not self._refresh_token:
            raise ConnectorAuthError("No refresh token available.")
        token_url = f"{self._dc['accounts_url']}/oauth/v2/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        self._exchange_token(token_url, payload)
        log.info("Access token refreshed (dc: %s)", self._data_center)

    def _exchange_token(self, token_url: str, payload: dict[str, str]) -> None:
        try:
            resp = self._session.post(
                token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise ConnectorAuthError(f"Token request failed: {exc}") from exc

        if resp.status_code != 200:
            try:
                body = resp.json()
                error = body.get("error", resp.text[:200])
            except ValueError:
                error = resp.text[:200]
            raise ConnectorAuthError(
                f"Zoho auth failed ({resp.status_code}): {error}"
            )

        data = resp.json()
        if "error" in data:
            raise ConnectorAuthError(f"Zoho auth error: {data['error']}")

        self._access_token = data["access_token"]
        if "refresh_token" in data:
            self._refresh_token = data["refresh_token"]
        self._session.headers["Authorization"] = f"Zoho-oauthtoken {self._access_token}"
        self._authenticated = True

        expires_in = data.get("expires_in", 3600)
        self._token_expires_at = datetime.now() + timedelta(seconds=int(expires_in))

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the Zoho CRM API."""
        self._ensure_connected()
        url = f"{self._dc['api_url']}{path}"
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
                    "Zoho %s %s attempt %d/%d failed: %s",
                    method, path, attempt, self._retry_attempts, exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code in (401, 403):
                error_msg = self._extract_error(resp)
                raise ConnectorAuthError(f"Zoho {resp.status_code}: {error_msg}")

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise ConnectorRateLimitError(
                    f"Zoho rate limit hit on {method} {path}.",
                    retry_after=float(retry_after) if retry_after else None,
                )

            if resp.status_code == 404:
                raise ConnectorNotFoundError(f"Zoho resource not found: {path}")

            if 500 <= resp.status_code < 600:
                last_exc = ConnectorError(f"Zoho {resp.status_code} on {method} {path}.")
                log.warning(
                    "Zoho %s %s 5xx %d attempt %d/%d",
                    method, path, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code == 204:
                return {}

            if not (200 <= resp.status_code < 300):
                error_msg = self._extract_error(resp)
                raise ConnectorError(f"Zoho {resp.status_code}: {error_msg}")

            try:
                return resp.json()
            except ValueError as exc:
                raise ConnectorError(
                    f"Zoho returned non-JSON on {method} {path}: "
                    f"{resp.text[:200]!r}"
                ) from exc

        raise ConnectorError(
            f"Zoho {method} {path} failed after {self._retry_attempts} "
            f"attempts: {last_exc}"
        )

    @staticmethod
    def _extract_error(resp: requests.Response) -> str:
        try:
            body = resp.json()
            if isinstance(body, dict):
                return body.get("message", body.get("error", resp.text[:200]))
            return resp.text[:200]
        except ValueError:
            return resp.text[:200]
