"""NLRB data source clients for case, election, and ULP data.

Three backends:

- **data.gov** — XML dumps of C-Cases (ULP) and R-Cases (representation).
- **labordata GitHub** — cleaned CSV/Parquet exports from labordata/nlrb-data.
- **NxGen Advanced Search** — HTML scraping of the NLRB case search
  (fragile; marked as best-effort).

A unified :class:`NLRBDataClient` facade reconciles records across sources.
"""

from __future__ import annotations

import csv
import io
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)

try:
    import requests
    _RequestException = requests.exceptions.RequestException
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]
    _RequestException = OSError  # type: ignore[assignment, misc]


def _requests():
    import requests
    return requests


# ---------------------------------------------------------------------------
# Enums & records
# ---------------------------------------------------------------------------


class CaseType(str, Enum):
    """NLRB case type prefix codes."""

    R = "R"       # Representation
    C = "C"       # Unfair Labor Practice (charged against employer)
    CB = "CB"     # ULP charged against union
    CD = "CD"     # ULP charged against union (duty of fair representation)
    CE = "CE"     # ULP charged against union (excessive fees)
    CA = "CA"     # ULP charged against employer (alias for C in older data)
    AC = "AC"     # Amendment of Certification
    UC = "UC"     # Unit Clarification
    UD = "UD"     # Unit De-authorization
    WH = "WH"     # Wage-Hour (historical)
    RM = "RM"     # Employer-filed representation
    RD = "RD"     # Decertification
    RC = "RC"     # Certification (union-filed)


class CaseStatus(str, Enum):
    """High-level case statuses."""

    OPEN = "Open"
    CLOSED = "Closed"
    PENDING = "Pending"
    UNKNOWN = "Unknown"


@dataclass
class NLRBCaseRecord:
    """A single NLRB case record from any data source."""

    case_number: str
    case_type: str
    case_name: str = ""
    status: str = CaseStatus.UNKNOWN.value
    date_filed: Optional[date] = None
    date_closed: Optional[date] = None
    region: Optional[int] = None
    city: str = ""
    state: str = ""
    union_name: str = ""
    unit_description: str = ""
    naics_code: str = ""
    employee_count: Optional[int] = None
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ElectionRecord:
    """Election tally result linked to a case."""

    case_number: str
    tally_date: Optional[date] = None
    eligible_voters: Optional[int] = None
    votes_for: Optional[int] = None
    votes_against: Optional[int] = None
    void_ballots: Optional[int] = None
    union_name: str = ""
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ULPRecord:
    """Unfair labor practice charge."""

    case_number: str
    allegation: str = ""
    charging_party: str = ""
    charged_party: str = ""
    section_of_act: str = ""
    date_filed: Optional[date] = None
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NLRBFetchResult:
    """Result from a client fetch operation."""

    cases: list[NLRBCaseRecord] = field(default_factory=list)
    elections: list[ElectionRecord] = field(default_factory=list)
    ulp_charges: list[ULPRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    source: str = ""

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_records(self) -> int:
        return len(self.cases) + len(self.elections) + len(self.ulp_charges)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%dT%H:%M:%S")


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value or not value.strip():
        return None
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def _extract_region(case_number: str) -> Optional[int]:
    """Extract the region number from a case number like '05-RC-123456'."""
    if not case_number:
        return None
    parts = case_number.split("-")
    if parts:
        try:
            return int(parts[0])
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# data.gov XML client
# ---------------------------------------------------------------------------

DATAGOV_CASES_URL = (
    "https://data.nlrb.gov/data/cases"
)


class NLRBDatagovClient:
    """Download and parse NLRB case data from data.gov XML exports.

    The NLRB publishes case data through its open data portal. This client
    fetches the XML feed and parses it into structured records.

    Args:
        timeout: HTTP request timeout in seconds.
        base_url: Override the default data.gov endpoint.
    """

    def __init__(
        self,
        timeout: int = 60,
        base_url: Optional[str] = None,
        session: Optional[object] = None,
    ):
        self._timeout = timeout
        self._base_url = base_url or DATAGOV_CASES_URL
        self._session = session

    def _get_session(self):
        if self._session is None:
            self._session = _requests().Session()
            self._session.headers.update({"Accept": "application/xml"})
        return self._session

    def fetch_cases(self, params: Optional[dict] = None) -> NLRBFetchResult:
        """Fetch case records from the data.gov XML endpoint.

        Args:
            params: Optional query parameters for filtering.

        Returns:
            NLRBFetchResult with parsed case records.
        """
        result = NLRBFetchResult(source="datagov")
        try:
            resp = self._get_session().get(
                self._base_url,
                params=params,
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except (_RequestException, OSError) as exc:
            result.errors.append(f"HTTP error fetching data.gov: {exc}")
            return result

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            result.errors.append(f"XML parse error: {exc}")
            return result

        for case_el in root.iter("case"):
            record = self._parse_case_element(case_el)
            if record:
                result.cases.append(record)

        log.info("data.gov: parsed %d cases", len(result.cases))
        return result

    def _parse_case_element(self, el: ET.Element) -> Optional[NLRBCaseRecord]:
        case_number = (el.findtext("caseNumber") or el.findtext("case_number") or "").strip()
        if not case_number:
            return None

        return NLRBCaseRecord(
            case_number=case_number,
            case_type=el.findtext("caseType") or el.findtext("case_type") or "",
            case_name=el.findtext("caseName") or el.findtext("case_name") or "",
            status=el.findtext("status") or CaseStatus.UNKNOWN.value,
            date_filed=_parse_date(el.findtext("dateFiled") or el.findtext("date_filed")),
            date_closed=_parse_date(el.findtext("dateClosed") or el.findtext("date_closed")),
            region=_extract_region(case_number),
            city=el.findtext("city") or "",
            state=el.findtext("state") or "",
            union_name=el.findtext("unionName") or el.findtext("labor_union") or "",
            unit_description=el.findtext("unitDescription") or "",
            naics_code=el.findtext("naicsCode") or el.findtext("naics") or "",
            employee_count=_safe_int(el.findtext("employeeCount") or el.findtext("num_employees")),
            source="datagov",
        )


# ---------------------------------------------------------------------------
# labordata GitHub CSV/Parquet client
# ---------------------------------------------------------------------------

LABORDATA_BASE_URL = (
    "https://raw.githubusercontent.com/labordata/nlrb-data/main"
)

LABORDATA_FILES = {
    "cases": "/data/cases.csv",
    "elections": "/data/elections.csv",
    "ulp_charges": "/data/charges.csv",
}


class NLRBLabordataClient:
    """Download and parse NLRB data from the labordata/nlrb-data GitHub repo.

    The labordata project maintains cleaned CSV exports of NLRB data. This
    client downloads the CSV files and parses them into structured records.

    Args:
        timeout: HTTP request timeout in seconds.
        base_url: Override the default GitHub raw content URL.
    """

    def __init__(
        self,
        timeout: int = 120,
        base_url: Optional[str] = None,
        session: Optional[object] = None,
    ):
        self._timeout = timeout
        self._base_url = base_url or LABORDATA_BASE_URL
        self._session = session

    def _get_session(self):
        if self._session is None:
            self._session = _requests().Session()
        return self._session

    def fetch_cases(self) -> NLRBFetchResult:
        """Fetch all available data from the labordata repository.

        Downloads cases, elections, and ULP charges CSVs.
        """
        result = NLRBFetchResult(source="labordata")
        _RequestException = _requests().exceptions.RequestException

        try:
            cases_csv = self._download_csv("cases")
            for row in cases_csv:
                record = self._parse_case_row(row)
                if record:
                    result.cases.append(record)
        except (_RequestException, OSError) as exc:
            result.errors.append(f"cases: {exc}")

        try:
            elections_csv = self._download_csv("elections")
            for row in elections_csv:
                record = self._parse_election_row(row)
                if record:
                    result.elections.append(record)
        except (_RequestException, OSError) as exc:
            result.errors.append(f"elections: {exc}")

        try:
            charges_csv = self._download_csv("ulp_charges")
            for row in charges_csv:
                record = self._parse_ulp_row(row)
                if record:
                    result.ulp_charges.append(record)
        except (_RequestException, OSError) as exc:
            result.errors.append(f"ulp_charges: {exc}")

        log.info(
            "labordata: %d cases, %d elections, %d charges",
            len(result.cases),
            len(result.elections),
            len(result.ulp_charges),
        )
        return result

    def _download_csv(self, dataset: str) -> list[dict]:
        path = LABORDATA_FILES.get(dataset)
        if not path:
            raise ValueError(f"Unknown labordata dataset: {dataset!r}")
        url = self._base_url + path
        resp = self._get_session().get(url, timeout=self._timeout)
        resp.raise_for_status()

        reader = csv.DictReader(io.StringIO(resp.text))
        return list(reader)

    def _parse_case_row(self, row: dict) -> Optional[NLRBCaseRecord]:
        case_number = row.get("case_number", "").strip()
        if not case_number:
            return None

        return NLRBCaseRecord(
            case_number=case_number,
            case_type=row.get("case_type", ""),
            case_name=row.get("case_name", ""),
            status=row.get("status", CaseStatus.UNKNOWN.value),
            date_filed=_parse_date(row.get("date_filed")),
            date_closed=_parse_date(row.get("date_closed")),
            region=_extract_region(case_number),
            city=row.get("city", ""),
            state=row.get("state", ""),
            union_name=row.get("union_name", row.get("labor_union", "")),
            unit_description=row.get("unit_description", row.get("bargaining_unit", "")),
            naics_code=row.get("naics_code", row.get("naics", "")),
            employee_count=_safe_int(row.get("employee_count", row.get("num_employees"))),
            source="labordata",
        )

    def _parse_election_row(self, row: dict) -> Optional[ElectionRecord]:
        case_number = row.get("case_number", "").strip()
        if not case_number:
            return None

        return ElectionRecord(
            case_number=case_number,
            tally_date=_parse_date(row.get("tally_date")),
            eligible_voters=_safe_int(row.get("eligible_voters")),
            votes_for=_safe_int(row.get("votes_for", row.get("votes_cast_for"))),
            votes_against=_safe_int(row.get("votes_against", row.get("votes_cast_against"))),
            void_ballots=_safe_int(row.get("void_ballots")),
            union_name=row.get("union_name", row.get("labor_union", "")),
            source="labordata",
        )

    def _parse_ulp_row(self, row: dict) -> Optional[ULPRecord]:
        case_number = row.get("case_number", "").strip()
        if not case_number:
            return None

        return ULPRecord(
            case_number=case_number,
            allegation=row.get("allegation", ""),
            charging_party=row.get("charging_party", ""),
            charged_party=row.get("charged_party", row.get("employer", "")),
            section_of_act=row.get("section_of_act", row.get("nlra_section", "")),
            date_filed=_parse_date(row.get("date_filed")),
            source="labordata",
        )


# ---------------------------------------------------------------------------
# NxGen Advanced Search client (fragile — web scraping)
# ---------------------------------------------------------------------------

NXGEN_SEARCH_URL = "https://www.nlrb.gov/search/case"


class NLRBNxGenClient:
    """Scrape NLRB case data from the NxGen Advanced Search page.

    .. warning::
        This client relies on HTML structure that may change without notice.
        Use it as a fallback when data.gov or labordata sources are
        insufficient. Prefer the other clients for bulk data.

    Args:
        timeout: HTTP request timeout in seconds.
        base_url: Override the default NxGen search URL.
    """

    def __init__(
        self,
        timeout: int = 30,
        base_url: Optional[str] = None,
        session: Optional[object] = None,
    ):
        self._timeout = timeout
        self._base_url = base_url or NXGEN_SEARCH_URL
        self._session = session

    def _get_session(self):
        if self._session is None:
            self._session = _requests().Session()
            self._session.headers.update({
                "User-Agent": "siege_utilities NLRB research client",
            })
        return self._session

    def fetch_case(self, case_number: str) -> NLRBFetchResult:
        """Fetch a single case by number from the NxGen search.

        Args:
            case_number: NLRB case number (e.g., '05-RC-123456').
        """
        result = NLRBFetchResult(source="nxgen")
        url = f"{self._base_url}?f%5B0%5D=case_number%3A{case_number}"

        try:
            resp = self._get_session().get(url, timeout=self._timeout)
            resp.raise_for_status()
        except (_RequestException, OSError) as exc:
            result.errors.append(f"NxGen HTTP error: {exc}")
            return result

        records = self._parse_search_results(resp.text)
        result.cases.extend(records)
        return result

    def _parse_search_results(self, html: str) -> list[NLRBCaseRecord]:
        """Best-effort HTML parsing — returns empty list on failure."""
        records: list[NLRBCaseRecord] = []
        try:
            from html.parser import HTMLParser

            class _CaseExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._in_row = False
                    self._current_field = ""
                    self._fields: dict = {}
                    self._rows: list[dict] = []

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "tr":
                        self._in_row = True
                        self._fields = {}
                    elif tag == "td" and self._in_row:
                        cls = attrs_dict.get("class", "")
                        if "case-number" in cls:
                            self._current_field = "case_number"
                        elif "case-name" in cls:
                            self._current_field = "case_name"
                        elif "date-filed" in cls:
                            self._current_field = "date_filed"
                        elif "status" in cls:
                            self._current_field = "status"
                        elif "city" in cls:
                            self._current_field = "city"
                        elif "state" in cls:
                            self._current_field = "state"

                def handle_data(self, data):
                    if self._current_field:
                        self._fields[self._current_field] = data.strip()
                        self._current_field = ""

                def handle_endtag(self, tag):
                    if tag == "tr" and self._in_row and self._fields.get("case_number"):
                        self._rows.append(dict(self._fields))
                        self._in_row = False
                        self._fields = {}

            parser = _CaseExtractor()
            parser.feed(html)

            for row_data in parser._rows:
                case_num = row_data.get("case_number", "")
                if case_num:
                    records.append(NLRBCaseRecord(
                        case_number=case_num,
                        case_type=case_num.split("-")[1] if "-" in case_num else "",
                        case_name=row_data.get("case_name", ""),
                        status=row_data.get("status", CaseStatus.UNKNOWN.value),
                        date_filed=_parse_date(row_data.get("date_filed")),
                        city=row_data.get("city", ""),
                        state=row_data.get("state", ""),
                        region=_extract_region(case_num),
                        source="nxgen",
                    ))
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            log.warning("NxGen parse failed (expected — page structure may have changed): %s", exc)

        return records


# ---------------------------------------------------------------------------
# Unified facade
# ---------------------------------------------------------------------------


class NLRBDataClient:
    """Unified NLRB data client that reconciles across multiple sources.

    Fetches from available backends and deduplicates by case number. When
    the same case appears in multiple sources, labordata is preferred
    (cleaned data), then data.gov, then NxGen.

    Args:
        datagov_client: Optional pre-configured data.gov client.
        labordata_client: Optional pre-configured labordata client.
        nxgen_client: Optional pre-configured NxGen client.
        use_nxgen: Whether to include the fragile NxGen source. Default False.
    """

    SOURCE_PRIORITY = ("labordata", "datagov", "nxgen")

    def __init__(
        self,
        datagov_client: Optional[NLRBDatagovClient] = None,
        labordata_client: Optional[NLRBLabordataClient] = None,
        nxgen_client: Optional[NLRBNxGenClient] = None,
        use_nxgen: bool = False,
    ):
        self._datagov = datagov_client or NLRBDatagovClient()
        self._labordata = labordata_client or NLRBLabordataClient()
        self._nxgen = nxgen_client or NLRBNxGenClient() if use_nxgen else None

    def fetch_all(self, datagov_params: Optional[dict] = None) -> NLRBFetchResult:
        """Fetch from all configured sources and reconcile.

        Args:
            datagov_params: Optional query parameters for the data.gov source.

        Returns:
            Merged NLRBFetchResult with deduplicated records.
        """
        results: list[NLRBFetchResult] = []

        labordata_result = self._labordata.fetch_cases()
        results.append(labordata_result)

        datagov_result = self._datagov.fetch_cases(params=datagov_params)
        results.append(datagov_result)

        if self._nxgen:
            nxgen_result = self._nxgen.fetch_case("")
            results.append(nxgen_result)

        return self._reconcile(results)

    def _reconcile(self, results: list[NLRBFetchResult]) -> NLRBFetchResult:
        """Merge results, preferring higher-priority sources."""
        merged = NLRBFetchResult(source="unified")

        case_map: dict[str, NLRBCaseRecord] = {}
        election_map: dict[str, ElectionRecord] = {}
        ulp_map: dict[str, ULPRecord] = {}

        for source_name in self.SOURCE_PRIORITY:
            for result in results:
                if result.source != source_name:
                    continue
                for case in result.cases:
                    if case.case_number not in case_map:
                        case_map[case.case_number] = case
                for election in result.elections:
                    key = f"{election.case_number}:{election.tally_date}"
                    if key not in election_map:
                        election_map[key] = election
                for ulp in result.ulp_charges:
                    key = f"{ulp.case_number}:{ulp.allegation[:50]}"
                    if key not in ulp_map:
                        ulp_map[key] = ulp
                merged.errors.extend(result.errors)

        merged.cases = list(case_map.values())
        merged.elections = list(election_map.values())
        merged.ulp_charges = list(ulp_map.values())

        log.info(
            "unified: %d cases, %d elections, %d charges (%d errors)",
            len(merged.cases),
            len(merged.elections),
            len(merged.ulp_charges),
            len(merged.errors),
        )
        return merged
