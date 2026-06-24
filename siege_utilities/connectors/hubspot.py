"""
HubSpot CRM connector — OAuth, connection management, and CRUD.

Provides OAuth 2.0 authorization code flow and private app access token
auth for the HubSpot CRM v3 API. Implements the full
:class:`ConnectorProtocol` contract: auth, read (with search and
associations), and write-back (with batch and association management).

Rate limits:
- OAuth apps: 100 requests / 10 seconds
- Private apps: 200 requests / 10 seconds

Records are returned as DataFrames. Known object types can be mapped to
canonical :mod:`connectors._models` shapes via ``to_crm_contacts()``,
``to_crm_accounts()``, ``to_crm_opportunities()``.
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

HUBSPOT_API_BASE = "https://api.hubapi.com"
HUBSPOT_AUTH_BASE = "https://app.hubspot.com"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 2.0
BATCH_SIZE = 100

STANDARD_OBJECTS = [
    "contacts",
    "companies",
    "deals",
    "tickets",
    "line_items",
    "products",
]

DEFAULT_PROPERTIES: dict[str, list[str]] = {
    "contacts": [
        "firstname", "lastname", "email", "phone", "jobtitle",
        "company", "lifecyclestage", "hs_lead_status",
        "address", "city", "state", "zip", "country",
        "createdate", "lastmodifieddate",
    ],
    "companies": [
        "name", "domain", "industry", "website", "annualrevenue",
        "numberofemployees", "phone", "type",
        "address", "city", "state", "zip", "country",
        "createdate", "lastmodifieddate",
    ],
    "deals": [
        "dealname", "dealstage", "amount", "closedate",
        "hs_deal_stage_probability", "hubspot_owner_id",
        "pipeline", "dealtype",
        "createdate", "lastmodifieddate",
    ],
    "tickets": [
        "subject", "content", "hs_ticket_priority",
        "hs_pipeline_stage", "hs_pipeline",
        "createdate", "lastmodifieddate", "closed_date",
    ],
}

__all__ = ["HubSpotConnector"]


class HubSpotConnector:
    """HubSpot CRM connector implementing ConnectorProtocol.

    Usage (Private App)::

        hs = HubSpotConnector(access_token=os.environ["HUBSPOT_TOKEN"])
        hs.authenticate()
        contacts = hs.get_objects("contacts")

    Usage (OAuth 2.0)::

        hs = HubSpotConnector(
            client_id=os.environ["HUBSPOT_CLIENT_ID"],
            client_secret=os.environ["HUBSPOT_CLIENT_SECRET"],
        )
        auth_url = hs.get_authorization_url(
            redirect_uri="https://myapp/callback",
            scopes=["crm.objects.contacts.read"],
        )
        # User visits auth_url, gets redirected with ?code=...
        hs.authenticate_with_code(code="...", redirect_uri="https://myapp/callback")
    """

    def __init__(
        self,
        *,
        access_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "HubSpotConnector requires `requests`. "
                "Install via `pip install siege-utilities`."
            )
        if not access_token and not (client_id and client_secret):
            raise ValueError(
                "Provide either access_token (private app) or "
                "client_id + client_secret (OAuth)."
            )

        self._access_token = access_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff
        self._authenticated = False
        self._is_private_app = access_token is not None

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "siege_utilities/HubSpotConnector",
        })
        log.info("HubSpotConnector initialised (mode: %s)",
                 "private_app" if self._is_private_app else "oauth")

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
        return "hubspot"

    def authenticate(self) -> None:
        """Authenticate using the best available method.

        Private app tokens are validated immediately. OAuth requires
        calling ``authenticate_with_code()`` first.
        """
        if self._is_private_app:
            self._validate_token()
        else:
            raise ConnectorAuthError(
                "OAuth flow requires calling get_authorization_url() "
                "then authenticate_with_code(). For private app auth, "
                "provide access_token to the constructor."
            )

    def authenticate_with_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> None:
        """Complete the OAuth 2.0 authorization code flow."""
        token_url = f"{HUBSPOT_AUTH_BASE}/oauth/v1/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": redirect_uri,
        }
        self._exchange_token(token_url, payload)
        log.info("Authenticated via OAuth authorization code flow")

    def get_authorization_url(
        self,
        redirect_uri: str,
        scopes: list[str] | None = None,
        state: str | None = None,
    ) -> str:
        """Generate the OAuth 2.0 authorization URL."""
        scope_str = " ".join(scopes) if scopes else "crm.objects.contacts.read"
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": scope_str,
        }
        if state:
            params["state"] = state
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{HUBSPOT_AUTH_BASE}/oauth/authorize?{query}"

    def is_connected(self) -> bool:
        if not self._authenticated or not self._access_token:
            return False
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            return False
        return True

    def refresh_access_token(self) -> None:
        if not self._refresh_token:
            raise ConnectorAuthError(
                "No refresh token available. Re-authenticate."
            )
        token_url = f"{HUBSPOT_AUTH_BASE}/oauth/v1/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        self._exchange_token(token_url, payload)
        log.info("Access token refreshed")

    # ------------------------------------------------------------------
    # ConnectorProtocol — read operations
    # ------------------------------------------------------------------

    def list_object_types(self) -> list[str]:
        """Available HubSpot object types."""
        return list(STANDARD_OBJECTS)

    def get_objects(
        self,
        object_type: str,
        *,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch records of *object_type* as a DataFrame.

        Args:
            object_type: HubSpot object type (``"contacts"``, etc.).
            fields: Properties to return. ``None`` uses defaults.
            filters: Key-value criteria for the Search API.
            limit: Maximum records. ``None`` for all.
        """
        properties = fields or DEFAULT_PROPERTIES.get(object_type, [])

        if filters:
            return self._search_objects(object_type, properties, filters, limit)

        return self._list_objects(object_type, properties, limit)

    def get_associations(
        self,
        from_type: str,
        record_id: str,
        to_type: str,
    ) -> list[str]:
        """Get associated record IDs."""
        self._ensure_connected()
        path = f"/crm/v3/objects/{from_type}/{record_id}/associations/{to_type}"
        data = self.request("GET", path)
        return [r["id"] for r in data.get("results", [])]

    # ------------------------------------------------------------------
    # CRM model mapping helpers
    # ------------------------------------------------------------------

    def to_crm_contacts(self, df: pd.DataFrame) -> list:
        from siege_utilities.connectors._models import CRMAddress, CRMContact

        results: list[CRMContact] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            props = r.get("properties", r)
            address = CRMAddress(
                street=props.get("address"),
                city=props.get("city"),
                state=props.get("state"),
                postal_code=props.get("zip"),
                country=props.get("country"),
            )
            extra_keys = set(props.keys()) - {
                "hs_object_id", "firstname", "lastname", "email", "phone",
                "jobtitle", "company", "address", "city", "state", "zip",
                "country",
            }
            results.append(CRMContact(
                id=str(r.get("id", props.get("hs_object_id", ""))),
                first_name=props.get("firstname"),
                last_name=props.get("lastname"),
                email=props.get("email"),
                phone=props.get("phone"),
                title=props.get("jobtitle"),
                account_id=None,
                address=address,
                source_system="hubspot",
                source_id=str(r.get("id", props.get("hs_object_id", ""))),
                metadata={k: props[k] for k in extra_keys if props.get(k) is not None},
            ))
        return results

    def to_crm_accounts(self, df: pd.DataFrame) -> list:
        from siege_utilities.connectors._models import CRMAccount, CRMAddress
        from decimal import Decimal

        results: list[CRMAccount] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            props = r.get("properties", r)
            address = CRMAddress(
                street=props.get("address"),
                city=props.get("city"),
                state=props.get("state"),
                postal_code=props.get("zip"),
                country=props.get("country"),
            )
            revenue = props.get("annualrevenue")
            employees = props.get("numberofemployees")
            extra_keys = set(props.keys()) - {
                "hs_object_id", "name", "industry", "website", "annualrevenue",
                "numberofemployees", "address", "city", "state", "zip", "country",
            }
            results.append(CRMAccount(
                id=str(r.get("id", props.get("hs_object_id", ""))),
                name=props.get("name", ""),
                industry=props.get("industry"),
                website=props.get("website"),
                revenue=Decimal(str(revenue)) if revenue is not None else None,
                employee_count=int(employees) if employees is not None else None,
                address=address,
                source_system="hubspot",
                source_id=str(r.get("id", props.get("hs_object_id", ""))),
                metadata={k: props[k] for k in extra_keys if props.get(k) is not None},
            ))
        return results

    def to_crm_opportunities(self, df: pd.DataFrame) -> list:
        from siege_utilities.connectors._models import CRMOpportunity
        from datetime import date as date_type
        from decimal import Decimal

        results: list[CRMOpportunity] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            props = r.get("properties", r)
            amount = props.get("amount")
            close_date_raw = props.get("closedate")
            close_date = None
            if close_date_raw:
                if isinstance(close_date_raw, str):
                    close_date = date_type.fromisoformat(close_date_raw[:10])
                elif isinstance(close_date_raw, date_type):
                    close_date = close_date_raw

            probability = props.get("hs_deal_stage_probability")
            extra_keys = set(props.keys()) - {
                "hs_object_id", "dealname", "dealstage", "amount",
                "closedate", "hs_deal_stage_probability", "hubspot_owner_id",
            }
            results.append(CRMOpportunity(
                id=str(r.get("id", props.get("hs_object_id", ""))),
                name=props.get("dealname", ""),
                account_id=None,
                stage=props.get("dealstage"),
                amount=Decimal(str(amount)) if amount is not None else None,
                close_date=close_date,
                probability=float(probability) if probability is not None else None,
                owner_id=props.get("hubspot_owner_id"),
                source_system="hubspot",
                source_id=str(r.get("id", props.get("hs_object_id", ""))),
                metadata={k: props[k] for k in extra_keys if props.get(k) is not None},
            ))
        return results

    # ------------------------------------------------------------------
    # ConnectorProtocol — write operations
    # ------------------------------------------------------------------

    def create_record(
        self, object_type: str, data: dict[str, Any]
    ) -> str:
        path = f"/crm/v3/objects/{object_type}"
        resp = self.request("POST", path, json_body={"properties": data})
        record_id = resp.get("id", "")
        if not record_id:
            raise ConnectorError(f"HubSpot create {object_type} returned no ID")
        log.info("Created %s record: %s", object_type, record_id)
        return record_id

    def update_record(
        self, object_type: str, record_id: str, data: dict[str, Any]
    ) -> bool:
        path = f"/crm/v3/objects/{object_type}/{record_id}"
        self.request("PATCH", path, json_body={"properties": data})
        log.info("Updated %s record: %s", object_type, record_id)
        return True

    def upsert_records(
        self,
        object_type: str,
        records: pd.DataFrame,
        match_field: str,
    ) -> UpsertResult:
        """Batch upsert via HubSpot Batch API (100 records per request)."""
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
            inputs = []
            for rec in batch:
                match_val = rec.get(match_field)
                entry: dict[str, Any] = {"properties": rec, "idProperty": match_field}
                if match_val is not None:
                    entry["id"] = str(match_val)
                inputs.append(entry)

            path = f"/crm/v3/objects/{object_type}/batch/upsert"
            try:
                resp = self.request("POST", path, json_body={"inputs": inputs})
            except ConnectorError as exc:
                for i, _ in enumerate(batch):
                    all_errors.append(UpsertError(
                        record_index=batch_idx * BATCH_SIZE + i,
                        message=str(exc),
                    ))
                total_failure += len(batch)
                continue

            results = resp.get("results", [])
            total_success += len(results)
            for result in results:
                rec_id = result.get("id", "")
                if result.get("new"):
                    all_created.append(rec_id)
                else:
                    all_updated.append(rec_id)

            errors_resp = resp.get("errors", [])
            for err in errors_resp:
                total_failure += 1
                all_errors.append(UpsertError(
                    record_index=batch_idx * BATCH_SIZE,
                    message=err.get("message", "Unknown error"),
                    code=err.get("category"),
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
    # Association management
    # ------------------------------------------------------------------

    def create_association(
        self,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        association_type: str | None = None,
    ) -> None:
        """Create an association between two records."""
        path = f"/crm/v3/objects/{from_type}/{from_id}/associations/{to_type}/{to_id}"
        body: list[dict[str, Any]] = []
        if association_type:
            body.append({
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": association_type,
            })
        self.request("PUT", path, json_body=body)
        log.info("Associated %s/%s → %s/%s", from_type, from_id, to_type, to_id)

    def remove_association(
        self,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
    ) -> None:
        """Remove an association between two records."""
        path = f"/crm/v3/objects/{from_type}/{from_id}/associations/{to_type}/{to_id}"
        self.request("DELETE", path)
        log.info("Removed association %s/%s → %s/%s", from_type, from_id, to_type, to_id)

    def merge_contacts(self, primary_id: str, secondary_id: str) -> None:
        """Merge two contacts, keeping the primary."""
        path = "/crm/v3/objects/contacts/merge"
        self.request("POST", path, json_body={
            "primaryObjectId": primary_id,
            "objectIdToMerge": secondary_id,
        })
        log.info("Merged contact %s into %s", secondary_id, primary_id)

    # ------------------------------------------------------------------
    # Internal — list and search
    # ------------------------------------------------------------------

    def _list_objects(
        self,
        object_type: str,
        properties: list[str],
        limit: int | None,
    ) -> pd.DataFrame:
        """List objects via the CRM v3 list endpoint with cursor pagination."""
        all_records: list[dict[str, Any]] = []
        after: str | None = None
        page_limit = min(limit or 100, 100)

        while True:
            params: dict[str, Any] = {"limit": page_limit}
            if properties:
                params["properties"] = ",".join(properties)
            if after:
                params["after"] = after

            path = f"/crm/v3/objects/{object_type}"
            data = self.request("GET", path, params=params)
            results = data.get("results", [])
            all_records.extend(results)

            log.info("Listed %s: %d records (total so far: %d)",
                     object_type, len(results), len(all_records))

            if limit and len(all_records) >= limit:
                all_records = all_records[:limit]
                break

            paging = data.get("paging", {})
            next_page = paging.get("next", {})
            after = next_page.get("after")
            if not after:
                break

        return self._records_to_dataframe(all_records, properties)

    def _search_objects(
        self,
        object_type: str,
        properties: list[str],
        filters: dict[str, Any],
        limit: int | None,
    ) -> pd.DataFrame:
        """Search objects via the CRM v3 Search API."""
        filter_groups = []
        search_filters = []
        for key, value in filters.items():
            if isinstance(value, list):
                search_filters.append({
                    "propertyName": key,
                    "operator": "IN",
                    "values": [str(v) for v in value],
                })
            elif value is None:
                search_filters.append({
                    "propertyName": key,
                    "operator": "NOT_HAS_PROPERTY",
                })
            else:
                search_filters.append({
                    "propertyName": key,
                    "operator": "EQ",
                    "value": str(value),
                })
        filter_groups.append({"filters": search_filters})

        all_records: list[dict[str, Any]] = []
        after: int = 0
        page_limit = min(limit or 100, 100)

        while True:
            body: dict[str, Any] = {
                "filterGroups": filter_groups,
                "properties": properties,
                "limit": page_limit,
                "after": after,
            }
            path = f"/crm/v3/objects/{object_type}/search"
            data = self.request("POST", path, json_body=body)
            results = data.get("results", [])
            all_records.extend(results)

            log.info("Searched %s: %d results (total so far: %d)",
                     object_type, len(results), len(all_records))

            if limit and len(all_records) >= limit:
                all_records = all_records[:limit]
                break

            paging = data.get("paging", {})
            next_page = paging.get("next", {})
            next_after = next_page.get("after")
            if not next_after:
                break
            after = int(next_after)

        return self._records_to_dataframe(all_records, properties)

    @staticmethod
    def _records_to_dataframe(
        records: list[dict[str, Any]],
        properties: list[str],
    ) -> pd.DataFrame:
        """Convert HubSpot API records to a DataFrame."""
        if not records:
            columns = ["id"] + properties
            return pd.DataFrame(columns=columns)

        rows: list[dict[str, Any]] = []
        for rec in records:
            row: dict[str, Any] = {"id": rec.get("id")}
            props = rec.get("properties", {})
            for p in properties:
                row[p] = props.get(p)
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
                self.refresh_access_token()
            else:
                raise ConnectorAuthError("Access token expired. Re-authenticate.")

    def _validate_token(self) -> None:
        """Validate a private app token by making a test API call."""
        self._session.headers["Authorization"] = f"Bearer {self._access_token}"
        self._authenticated = True
        try:
            self.request("GET", "/crm/v3/objects/contacts", params={"limit": 1})
        except ConnectorAuthError:
            self._authenticated = False
            raise
        except ConnectorError:
            pass
        log.info("Private app token validated")

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
                error = body.get("message", resp.text[:200])
            except ValueError:
                error = resp.text[:200]
            raise ConnectorAuthError(
                f"HubSpot auth failed ({resp.status_code}): {error}"
            )

        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        self._session.headers["Authorization"] = f"Bearer {self._access_token}"
        self._authenticated = True

        expires_in = data.get("expires_in")
        if expires_in:
            self._token_expires_at = datetime.now() + timedelta(seconds=int(expires_in))
        else:
            self._token_expires_at = datetime.now() + timedelta(hours=6)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the HubSpot API."""
        self._ensure_connected()
        url = f"{HUBSPOT_API_BASE}{path}"
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
                    "HubSpot %s %s attempt %d/%d failed: %s",
                    method, path, attempt, self._retry_attempts, exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code in (401, 403):
                error_msg = self._extract_error(resp)
                raise ConnectorAuthError(f"HubSpot {resp.status_code}: {error_msg}")

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise ConnectorRateLimitError(
                    f"HubSpot rate limit hit on {method} {path}.",
                    retry_after=float(retry_after) if retry_after else None,
                )

            if resp.status_code == 404:
                raise ConnectorNotFoundError(f"HubSpot resource not found: {path}")

            if 500 <= resp.status_code < 600:
                last_exc = ConnectorError(
                    f"HubSpot {resp.status_code} on {method} {path}."
                )
                log.warning(
                    "HubSpot %s %s 5xx %d attempt %d/%d",
                    method, path, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code == 204:
                return {}

            if not (200 <= resp.status_code < 300):
                error_msg = self._extract_error(resp)
                raise ConnectorError(f"HubSpot {resp.status_code}: {error_msg}")

            try:
                return resp.json()
            except ValueError as exc:
                raise ConnectorError(
                    f"HubSpot returned non-JSON on {method} {path}: "
                    f"{resp.text[:200]!r}"
                ) from exc

        raise ConnectorError(
            f"HubSpot {method} {path} failed after {self._retry_attempts} "
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
