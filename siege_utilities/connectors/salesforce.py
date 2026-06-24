"""
Salesforce CRM connector — OAuth, connection management, and read operations.

Provides OAuth 2.0 authentication (Web Server Flow and Username-Password
Flow), an authenticated HTTP client, and read operations for standard
Salesforce objects (Contact, Account, Opportunity, Lead, Case).

Records are returned as DataFrames. Known object types can be mapped to
canonical :mod:`connectors._models` shapes via ``to_crm_contacts()``,
``to_crm_accounts()``, ``to_crm_opportunities()``.

Two auth flows:
- **Web Server Flow** (production): interactive OAuth with redirect.
- **Username-Password Flow** (dev/CI): direct token grant.

Instance URL is discovered from the token response — callers never
hard-code ``na1.salesforce.com`` or similar.
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

PRODUCTION_LOGIN_URL = "https://login.salesforce.com"
SANDBOX_LOGIN_URL = "https://test.salesforce.com"
API_VERSION = "v60.0"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 2.0

STANDARD_OBJECTS = [
    "Account",
    "Campaign",
    "Case",
    "Contact",
    "Lead",
    "Opportunity",
    "Task",
    "Event",
]

DEFAULT_FIELDS: dict[str, list[str]] = {
    "Contact": [
        "Id", "FirstName", "LastName", "Email", "Phone", "Title",
        "AccountId", "Department", "MailingStreet", "MailingCity",
        "MailingState", "MailingPostalCode", "MailingCountry",
        "CreatedDate", "LastModifiedDate",
    ],
    "Account": [
        "Id", "Name", "Industry", "Website", "AnnualRevenue",
        "NumberOfEmployees", "BillingStreet", "BillingCity",
        "BillingState", "BillingPostalCode", "BillingCountry",
        "Phone", "Type", "CreatedDate", "LastModifiedDate",
    ],
    "Opportunity": [
        "Id", "Name", "AccountId", "StageName", "Amount", "CloseDate",
        "Probability", "OwnerId", "Type", "LeadSource",
        "CreatedDate", "LastModifiedDate",
    ],
    "Lead": [
        "Id", "FirstName", "LastName", "Email", "Phone", "Company",
        "Title", "Status", "LeadSource", "Industry",
        "Street", "City", "State", "PostalCode", "Country",
        "CreatedDate", "LastModifiedDate",
    ],
    "Case": [
        "Id", "CaseNumber", "Subject", "Description", "Status",
        "Priority", "Type", "ContactId", "AccountId",
        "CreatedDate", "LastModifiedDate", "ClosedDate",
    ],
    "Campaign": [
        "Id", "Name", "Type", "Status", "StartDate", "EndDate",
        "BudgetedCost", "ActualCost", "NumberOfLeads", "NumberOfContacts",
        "CreatedDate", "LastModifiedDate",
    ],
    "Task": [
        "Id", "Subject", "Description", "Status", "Priority",
        "ActivityDate", "WhoId", "WhatId", "OwnerId",
        "CreatedDate", "LastModifiedDate",
    ],
    "Event": [
        "Id", "Subject", "Description", "StartDateTime", "EndDateTime",
        "WhoId", "WhatId", "OwnerId",
        "CreatedDate", "LastModifiedDate",
    ],
}

__all__ = ["SalesforceConnector", "SOQLQuery"]

_UNSET = object()


class SOQLQuery:
    """Fluent SOQL query builder.

    Usage::

        q = (SOQLQuery()
             .select("FirstName", "LastName", "Email")
             .from_("Contact")
             .where("Status", eq="Active")
             .where("Department", eq="Sales")
             .order_by("LastName")
             .limit(100))
        print(q.build())
        # SELECT FirstName, LastName, Email FROM Contact
        # WHERE Status = 'Active' AND Department = 'Sales'
        # ORDER BY LastName ASC LIMIT 100
    """

    def __init__(self) -> None:
        self._fields: list[str] = []
        self._object_type: str | None = None
        self._conditions: list[str] = []
        self._order_clauses: list[str] = []
        self._limit_val: int | None = None
        self._offset_val: int | None = None

    def select(self, *fields: str) -> SOQLQuery:
        """Add fields to the SELECT clause."""
        self._fields.extend(fields)
        return self

    def from_(self, object_type: str) -> SOQLQuery:
        """Set the FROM object type."""
        self._object_type = object_type
        return self

    def where(
        self,
        field: str,
        *,
        eq: Any = _UNSET,
        ne: Any = _UNSET,
        gt: Any = _UNSET,
        gte: Any = _UNSET,
        lt: Any = _UNSET,
        lte: Any = _UNSET,
        in_: list | None = None,
        not_in: list | None = None,
        like: str | None = None,
        is_null: bool | None = None,
    ) -> SOQLQuery:
        """Add a WHERE condition.

        Supports equality, comparison, IN, NOT IN, LIKE, and null checks.
        Multiple calls are joined with AND.
        """
        if eq is not _UNSET:
            self._conditions.append(f"{field} = {_soql_literal(eq)}")
        if ne is not _UNSET:
            self._conditions.append(f"{field} != {_soql_literal(ne)}")
        if gt is not _UNSET:
            self._conditions.append(f"{field} > {_soql_literal(gt)}")
        if gte is not _UNSET:
            self._conditions.append(f"{field} >= {_soql_literal(gte)}")
        if lt is not _UNSET:
            self._conditions.append(f"{field} < {_soql_literal(lt)}")
        if lte is not _UNSET:
            self._conditions.append(f"{field} <= {_soql_literal(lte)}")
        if in_ is not None:
            vals = ", ".join(_soql_literal(v) for v in in_)
            self._conditions.append(f"{field} IN ({vals})")
        if not_in is not None:
            vals = ", ".join(_soql_literal(v) for v in not_in)
            self._conditions.append(f"{field} NOT IN ({vals})")
        if like is not None:
            self._conditions.append(f"{field} LIKE {_soql_literal(like)}")
        if is_null is True:
            self._conditions.append(f"{field} = null")
        elif is_null is False:
            self._conditions.append(f"{field} != null")
        return self

    def where_raw(self, condition: str) -> SOQLQuery:
        """Add a raw SOQL WHERE condition string."""
        self._conditions.append(condition)
        return self

    def order_by(self, field: str, *, desc: bool = False) -> SOQLQuery:
        """Add an ORDER BY clause."""
        direction = "DESC" if desc else "ASC"
        self._order_clauses.append(f"{field} {direction}")
        return self

    def limit(self, n: int) -> SOQLQuery:
        """Set the LIMIT value."""
        self._limit_val = int(n)
        return self

    def offset(self, n: int) -> SOQLQuery:
        """Set the OFFSET value."""
        self._offset_val = int(n)
        return self

    def build(self) -> str:
        """Build the SOQL query string.

        Raises:
            ValueError: If no object type or fields are set.
        """
        if not self._object_type:
            raise ValueError("SOQLQuery requires from_() to set the object type.")
        if not self._fields:
            raise ValueError("SOQLQuery requires at least one field via select().")

        parts = [f"SELECT {', '.join(self._fields)} FROM {self._object_type}"]

        if self._conditions:
            parts.append("WHERE " + " AND ".join(self._conditions))

        if self._order_clauses:
            parts.append("ORDER BY " + ", ".join(self._order_clauses))

        if self._limit_val is not None:
            parts.append(f"LIMIT {self._limit_val}")

        if self._offset_val is not None:
            parts.append(f"OFFSET {self._offset_val}")

        return " ".join(parts)

    def __str__(self) -> str:
        return self.build()


def _soql_literal(value: Any) -> str:
    """Convert a Python value to a SOQL literal."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


class SalesforceConnector:
    """Salesforce CRM connector implementing ConnectorProtocol.

    Usage (Username-Password Flow)::

        from siege_utilities.connectors.salesforce import SalesforceConnector

        sf = SalesforceConnector(
            client_id=os.environ["SF_CLIENT_ID"],
            client_secret=os.environ["SF_CLIENT_SECRET"],
            username=os.environ["SF_USERNAME"],
            password=os.environ["SF_PASSWORD"],
            security_token=os.environ["SF_SECURITY_TOKEN"],
        )
        sf.authenticate()
        print(sf.instance_url)

    Usage (Web Server Flow)::

        sf = SalesforceConnector(
            client_id=os.environ["SF_CLIENT_ID"],
            client_secret=os.environ["SF_CLIENT_SECRET"],
        )
        auth_url = sf.get_authorization_url(redirect_uri="https://myapp/callback")
        # User visits auth_url, gets redirected with ?code=...
        sf.authenticate_with_code(code="...", redirect_uri="https://myapp/callback")
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        username: str | None = None,
        password: str | None = None,
        security_token: str | None = None,
        login_url: str | None = None,
        sandbox: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "SalesforceConnector requires `requests`. "
                "Install via `pip install siege-utilities`."
            )
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required.")

        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password
        self._security_token = security_token or ""
        self._login_url = login_url or (SANDBOX_LOGIN_URL if sandbox else PRODUCTION_LOGIN_URL)
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._instance_url: str | None = None
        self._token_expires_at: datetime | None = None
        self._authenticated = False

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "siege_utilities/SalesforceConnector",
        })
        log.info("SalesforceConnector initialised (login: %s)", self._login_url)

    def close(self) -> None:
        """Close the underlying HTTP session."""
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
        return "salesforce"

    @property
    def instance_url(self) -> str | None:
        """The Salesforce instance URL discovered during authentication."""
        return self._instance_url

    def authenticate(self) -> None:
        """Authenticate using the best available flow.

        If ``username`` and ``password`` were provided, uses the
        Username-Password Flow. Otherwise raises with guidance to use
        ``authenticate_with_code()`` for the Web Server Flow.
        """
        if self._username and self._password:
            self._authenticate_password()
        else:
            raise ConnectorAuthError(
                "No username/password provided. For the Web Server Flow, "
                "call get_authorization_url() then authenticate_with_code(). "
                "For the Username-Password Flow, provide username, password, "
                "and security_token to the constructor."
            )

    def authenticate_with_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> None:
        """Complete the OAuth 2.0 Web Server Flow with an authorization code."""
        token_url = f"{self._login_url}/services/oauth2/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": redirect_uri,
        }
        self._exchange_token(token_url, payload)
        log.info("Authenticated via Web Server Flow (instance: %s)", self._instance_url)

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str | None = None,
    ) -> str:
        """Generate the OAuth 2.0 authorization URL for the Web Server Flow."""
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
        }
        if state:
            params["state"] = state
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self._login_url}/services/oauth2/authorize?{query}"

    def is_connected(self) -> bool:
        """Whether the connector has an active, authenticated session."""
        if not self._authenticated or not self._access_token:
            return False
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            return False
        return True

    def refresh_access_token(self) -> None:
        """Refresh the access token using the stored refresh token."""
        if not self._refresh_token:
            raise ConnectorAuthError(
                "No refresh token available. Re-authenticate using "
                "authenticate() or authenticate_with_code()."
            )
        token_url = f"{self._login_url}/services/oauth2/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        self._exchange_token(token_url, payload)
        log.info("Access token refreshed (instance: %s)", self._instance_url)

    # ------------------------------------------------------------------
    # ConnectorProtocol — read operations
    # ------------------------------------------------------------------

    def list_object_types(self) -> list[str]:
        """Available Salesforce standard object types."""
        self._ensure_connected()
        path = f"/services/data/{API_VERSION}/sobjects"
        data = self.request("GET", path)
        names = sorted(obj["name"] for obj in data.get("sobjects", []) if obj.get("queryable"))
        log.info("Discovered %d queryable object types", len(names))
        return names

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
            object_type: Salesforce object API name (``"Contact"``, etc.).
            fields: Columns to return. ``None`` uses the default set for
                known objects, or ``["Id"]`` for unknown objects.
            filters: Key-value criteria translated to a SOQL WHERE clause.
                Values may be str, int, float, bool, None, or a list
                (translated to ``IN``).
            limit: Maximum records. ``None`` for all (paginated automatically).

        Returns:
            DataFrame with one row per record, columns matching *fields*.
            Empty DataFrame (with correct columns) when no records match.
        """
        soql = self._build_soql(object_type, fields=fields, filters=filters, limit=limit)
        records = self._query_all(soql)
        selected_fields = fields or DEFAULT_FIELDS.get(object_type, ["Id"])
        if not records:
            log.warning("get_objects(%s): query returned 0 records", object_type)
            return pd.DataFrame(columns=selected_fields)

        cleaned = self._clean_records(records, selected_fields)
        df = pd.DataFrame(cleaned)
        log.info("get_objects(%s): returned %d records, %d fields", object_type, len(df), len(df.columns))
        return df

    def soql(self, query: str | SOQLQuery) -> pd.DataFrame:
        """Execute a raw SOQL string or :class:`SOQLQuery` and return a DataFrame.

        This is the escape hatch for queries that ``get_objects()`` can't
        express (subqueries, aggregate functions, relationship traversals).
        """
        soql_str = query.build() if isinstance(query, SOQLQuery) else query
        records = self._query_all(soql_str)
        if not records:
            log.warning("soql(): query returned 0 records")
            return pd.DataFrame()
        keys = [k for k in records[0].keys() if k != "attributes"]
        cleaned = [{k: rec.get(k) for k in keys} for rec in records]
        return pd.DataFrame(cleaned)

    # ------------------------------------------------------------------
    # CRM model mapping helpers
    # ------------------------------------------------------------------

    def to_crm_contacts(self, df: pd.DataFrame) -> list:
        """Map a Contact DataFrame to a list of :class:`CRMContact`."""
        from siege_utilities.connectors._models import CRMAddress, CRMContact

        results: list[CRMContact] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            address = CRMAddress(
                street=r.get("MailingStreet"),
                city=r.get("MailingCity"),
                state=r.get("MailingState"),
                postal_code=r.get("MailingPostalCode"),
                country=r.get("MailingCountry"),
            )
            extra_keys = set(r.keys()) - {
                "Id", "FirstName", "LastName", "Email", "Phone",
                "Title", "AccountId", "MailingStreet", "MailingCity",
                "MailingState", "MailingPostalCode", "MailingCountry",
            }
            results.append(CRMContact(
                id=r["Id"],
                first_name=r.get("FirstName"),
                last_name=r.get("LastName"),
                email=r.get("Email"),
                phone=r.get("Phone"),
                title=r.get("Title"),
                account_id=r.get("AccountId"),
                address=address,
                source_system="salesforce",
                source_id=r["Id"],
                metadata={k: r[k] for k in extra_keys if r.get(k) is not None},
            ))
        return results

    def to_crm_accounts(self, df: pd.DataFrame) -> list:
        """Map an Account DataFrame to a list of :class:`CRMAccount`."""
        from siege_utilities.connectors._models import CRMAccount, CRMAddress
        from decimal import Decimal

        results: list[CRMAccount] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            address = CRMAddress(
                street=r.get("BillingStreet"),
                city=r.get("BillingCity"),
                state=r.get("BillingState"),
                postal_code=r.get("BillingPostalCode"),
                country=r.get("BillingCountry"),
            )
            revenue = r.get("AnnualRevenue")
            extra_keys = set(r.keys()) - {
                "Id", "Name", "Industry", "Website", "AnnualRevenue",
                "NumberOfEmployees", "BillingStreet", "BillingCity",
                "BillingState", "BillingPostalCode", "BillingCountry",
            }
            results.append(CRMAccount(
                id=r["Id"],
                name=r["Name"],
                industry=r.get("Industry"),
                website=r.get("Website"),
                revenue=Decimal(str(revenue)) if revenue is not None else None,
                employee_count=int(r["NumberOfEmployees"]) if r.get("NumberOfEmployees") is not None else None,
                address=address,
                source_system="salesforce",
                source_id=r["Id"],
                metadata={k: r[k] for k in extra_keys if r.get(k) is not None},
            ))
        return results

    def to_crm_opportunities(self, df: pd.DataFrame) -> list:
        """Map an Opportunity DataFrame to a list of :class:`CRMOpportunity`."""
        from siege_utilities.connectors._models import CRMOpportunity
        from datetime import date as date_type
        from decimal import Decimal

        results: list[CRMOpportunity] = []
        for _, row in df.iterrows():
            r = row.to_dict()
            amount = r.get("Amount")
            close_date_raw = r.get("CloseDate")
            close_date = None
            if close_date_raw:
                if isinstance(close_date_raw, str):
                    close_date = date_type.fromisoformat(close_date_raw)
                elif isinstance(close_date_raw, date_type):
                    close_date = close_date_raw

            extra_keys = set(r.keys()) - {
                "Id", "Name", "AccountId", "StageName", "Amount",
                "CloseDate", "Probability", "OwnerId",
            }
            results.append(CRMOpportunity(
                id=r["Id"],
                name=r["Name"],
                account_id=r.get("AccountId"),
                stage=r.get("StageName"),
                amount=Decimal(str(amount)) if amount is not None else None,
                close_date=close_date,
                probability=float(r["Probability"]) if r.get("Probability") is not None else None,
                owner_id=r.get("OwnerId"),
                source_system="salesforce",
                source_id=r["Id"],
                metadata={k: r[k] for k in extra_keys if r.get(k) is not None},
            ))
        return results

    # ------------------------------------------------------------------
    # ConnectorProtocol — write stubs (follow-up tickets)
    # ------------------------------------------------------------------

    def create_record(
        self, object_type: str, data: dict[str, Any]
    ) -> str:
        """Create a single record. Implemented in #1018."""
        raise NotImplementedError("create_record() — see #1018")

    def update_record(
        self, object_type: str, record_id: str, data: dict[str, Any]
    ) -> bool:
        """Update a single record. Implemented in #1018."""
        raise NotImplementedError("update_record() — see #1018")

    def upsert_records(
        self,
        object_type: str,
        records: pd.DataFrame,
        match_field: str,
    ) -> UpsertResult:
        """Bulk upsert from DataFrame. Implemented in #1018/#1019."""
        raise NotImplementedError("upsert_records() — see #1018/#1019")

    # ------------------------------------------------------------------
    # SOQL query building
    # ------------------------------------------------------------------

    def _build_soql(
        self,
        object_type: str,
        *,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> str:
        """Build a SOQL SELECT query from Python arguments."""
        selected = fields or DEFAULT_FIELDS.get(object_type, ["Id"])
        field_clause = ", ".join(selected)
        query = f"SELECT {field_clause} FROM {object_type}"

        if filters:
            where_parts: list[str] = []
            for key, value in filters.items():
                where_parts.append(self._soql_condition(key, value))
            query += " WHERE " + " AND ".join(where_parts)

        if limit is not None:
            query += f" LIMIT {int(limit)}"

        return query

    @staticmethod
    def _soql_condition(field: str, value: Any) -> str:
        """Translate a single key-value filter into a SOQL condition."""
        if value is None:
            return f"{field} = null"
        if isinstance(value, bool):
            return f"{field} = {'true' if value else 'false'}"
        if isinstance(value, (int, float)):
            return f"{field} = {value}"
        if isinstance(value, list):
            if not value:
                return f"{field} = null"
            escaped = [SalesforceConnector._soql_escape(str(v)) for v in value]
            in_clause = ", ".join(f"'{e}'" for e in escaped)
            return f"{field} IN ({in_clause})"
        escaped_str = SalesforceConnector._soql_escape(str(value))
        return f"{field} = '{escaped_str}'"

    @staticmethod
    def _soql_escape(value: str) -> str:
        """Escape single quotes for SOQL string literals."""
        return value.replace("\\", "\\\\").replace("'", "\\'")

    # ------------------------------------------------------------------
    # Query execution with pagination
    # ------------------------------------------------------------------

    def _query_all(self, soql: str) -> list[dict[str, Any]]:
        """Execute a SOQL query and follow pagination to completion."""
        self._ensure_connected()
        path = f"/services/data/{API_VERSION}/query"
        data = self.request("GET", path, params={"q": soql})
        all_records: list[dict[str, Any]] = data.get("records", [])
        total = data.get("totalSize", len(all_records))
        log.info("SOQL query returned %d total records (first page: %d)", total, len(all_records))

        while data.get("nextRecordsUrl"):
            next_path = data["nextRecordsUrl"]
            data = self.request("GET", next_path)
            page_records = data.get("records", [])
            all_records.extend(page_records)
            log.info("Fetched page: %d records (total so far: %d)", len(page_records), len(all_records))

        return all_records

    @staticmethod
    def _clean_records(
        records: list[dict[str, Any]],
        fields: list[str],
    ) -> list[dict[str, Any]]:
        """Strip Salesforce metadata (``attributes``) and normalize columns."""
        cleaned: list[dict[str, Any]] = []
        for rec in records:
            row = {f: rec.get(f) for f in fields}
            cleaned.append(row)
        return cleaned

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

    def _authenticate_password(self) -> None:
        """Username-Password Flow."""
        token_url = f"{self._login_url}/services/oauth2/token"
        payload = {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._username,
            "password": f"{self._password}{self._security_token}",
        }
        self._exchange_token(token_url, payload)
        log.info(
            "Authenticated via Username-Password Flow as %s (instance: %s)",
            self._username, self._instance_url,
        )

    def _exchange_token(self, token_url: str, payload: dict[str, str]) -> None:
        """Exchange credentials for an access token."""
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
                error = body.get("error_description", body.get("error", resp.text[:200]))
            except ValueError:
                error = resp.text[:200]
            raise ConnectorAuthError(
                f"Salesforce auth failed ({resp.status_code}): {error}"
            )

        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        self._instance_url = data["instance_url"]
        self._session.headers["Authorization"] = f"Bearer {self._access_token}"
        self._authenticated = True

        issued_at = data.get("issued_at")
        if issued_at:
            try:
                issued = datetime.fromtimestamp(int(issued_at) / 1000)
                self._token_expires_at = issued + timedelta(hours=2)
            except (ValueError, OSError):
                self._token_expires_at = datetime.now() + timedelta(hours=2)
        else:
            self._token_expires_at = datetime.now() + timedelta(hours=2)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the Salesforce REST API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            path: API path relative to instance URL
                (e.g., ``/services/data/v60.0/sobjects/Contact``).
            params: Query parameters.
            json_body: JSON request body.

        Returns:
            Parsed JSON response.
        """
        self._ensure_connected()
        url = f"{self._instance_url}{path}"
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
                    "Salesforce %s %s attempt %d/%d failed: %s",
                    method, path, attempt, self._retry_attempts, exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code in (401, 403):
                error_msg = self._extract_error(resp)
                raise ConnectorAuthError(
                    f"Salesforce {resp.status_code}: {error_msg}"
                )

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise ConnectorRateLimitError(
                    f"Salesforce rate limit hit on {method} {path}.",
                    retry_after=float(retry_after) if retry_after else None,
                )

            if resp.status_code == 404:
                raise ConnectorNotFoundError(
                    f"Salesforce resource not found: {path}"
                )

            if 500 <= resp.status_code < 600:
                last_exc = ConnectorError(
                    f"Salesforce {resp.status_code} on {method} {path}."
                )
                log.warning(
                    "Salesforce %s %s 5xx %d attempt %d/%d",
                    method, path, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code == 204:
                return {}

            if not (200 <= resp.status_code < 300):
                error_msg = self._extract_error(resp)
                raise ConnectorError(
                    f"Salesforce {resp.status_code}: {error_msg}"
                )

            try:
                return resp.json()
            except ValueError as exc:
                raise ConnectorError(
                    f"Salesforce returned non-JSON on {method} {path}: "
                    f"{resp.text[:200]!r}"
                ) from exc

        raise ConnectorError(
            f"Salesforce {method} {path} failed after {self._retry_attempts} "
            f"attempts: {last_exc}"
        )

    @staticmethod
    def _extract_error(resp: requests.Response) -> str:
        try:
            body = resp.json()
            if isinstance(body, list) and body:
                return body[0].get("message", str(body))
            if isinstance(body, dict):
                return body.get("message", body.get("error", resp.text[:200]))
            return resp.text[:200]
        except ValueError:
            return resp.text[:200]
