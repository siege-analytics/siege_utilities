"""Tests for NLRB data source clients (SU#617)."""

from __future__ import annotations

import csv
import io
import textwrap
import xml.etree.ElementTree as ET
from datetime import date
from unittest.mock import MagicMock


from siege_utilities.geo.providers.nlrb_clients import (
    CaseStatus,
    CaseType,
    ElectionRecord,
    NLRBCaseRecord,
    NLRBDataClient,
    NLRBDatagovClient,
    NLRBFetchResult,
    NLRBLabordataClient,
    NLRBNxGenClient,
    ULPRecord,
    _extract_region,
    _parse_date,
    _safe_int,
)


def _mock_session():
    return MagicMock()


# ---------------------------------------------------------------------------
# Record dataclass tests
# ---------------------------------------------------------------------------


class TestNLRBCaseRecord:
    def test_minimal_construction(self):
        rec = NLRBCaseRecord(case_number="05-RC-123456", case_type="RC")
        assert rec.case_number == "05-RC-123456"
        assert rec.case_type == "RC"
        assert rec.status == CaseStatus.UNKNOWN.value

    def test_full_construction(self):
        rec = NLRBCaseRecord(
            case_number="05-RC-123456",
            case_type="RC",
            case_name="ACME Corp",
            status="Open",
            date_filed=date(2024, 1, 15),
            date_closed=None,
            region=5,
            city="Chicago",
            state="IL",
            union_name="SEIU",
            unit_description="Warehouse workers",
            naics_code="493110",
            employee_count=150,
            source="labordata",
        )
        assert rec.city == "Chicago"
        assert rec.employee_count == 150

    def test_to_dict(self):
        rec = NLRBCaseRecord(case_number="01-CA-999", case_type="CA")
        d = rec.to_dict()
        assert isinstance(d, dict)
        assert d["case_number"] == "01-CA-999"
        assert "source" in d


class TestElectionRecord:
    def test_construction_and_dict(self):
        rec = ElectionRecord(
            case_number="05-RC-123456",
            tally_date=date(2024, 3, 1),
            eligible_voters=200,
            votes_for=120,
            votes_against=75,
            union_name="UAW",
        )
        assert rec.votes_for == 120
        d = rec.to_dict()
        assert d["eligible_voters"] == 200


class TestULPRecord:
    def test_construction_and_dict(self):
        rec = ULPRecord(
            case_number="01-CA-888",
            allegation="8(a)(1) interference",
            charging_party="Local 123",
            charged_party="ACME Corp",
            section_of_act="8(a)(1)",
        )
        assert rec.section_of_act == "8(a)(1)"
        d = rec.to_dict()
        assert d["charging_party"] == "Local 123"


class TestNLRBFetchResult:
    def test_empty_is_success(self):
        r = NLRBFetchResult()
        assert r.success
        assert r.total_records == 0

    def test_with_errors(self):
        r = NLRBFetchResult(errors=["something failed"])
        assert not r.success

    def test_total_records(self):
        r = NLRBFetchResult(
            cases=[NLRBCaseRecord(case_number="1", case_type="RC")],
            elections=[ElectionRecord(case_number="1")],
            ulp_charges=[ULPRecord(case_number="2"), ULPRecord(case_number="3")],
        )
        assert r.total_records == 4


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestCaseType:
    def test_representation(self):
        assert CaseType.R.value == "R"
        assert CaseType.RC.value == "RC"

    def test_ulp_types(self):
        assert CaseType.C.value == "C"
        assert CaseType.CA.value == "CA"
        assert CaseType.CB.value == "CB"


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_iso_format(self):
        assert _parse_date("2024-01-15") == date(2024, 1, 15)

    def test_us_format(self):
        assert _parse_date("01/15/2024") == date(2024, 1, 15)

    def test_us_dash_format(self):
        assert _parse_date("01-15-2024") == date(2024, 1, 15)

    def test_iso_datetime(self):
        assert _parse_date("2024-01-15T10:30:00") == date(2024, 1, 15)

    def test_none_input(self):
        assert _parse_date(None) is None

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_whitespace(self):
        assert _parse_date("  ") is None

    def test_invalid_format(self):
        assert _parse_date("not-a-date") is None


class TestSafeInt:
    def test_int(self):
        assert _safe_int(42) == 42

    def test_string_int(self):
        assert _safe_int("42") == 42

    def test_float_string(self):
        assert _safe_int("42.7") == 42

    def test_none(self):
        assert _safe_int(None) is None

    def test_invalid(self):
        assert _safe_int("abc") is None

    def test_empty(self):
        assert _safe_int("") is None


class TestExtractRegion:
    def test_standard_format(self):
        assert _extract_region("05-RC-123456") == 5

    def test_two_digit_region(self):
        assert _extract_region("28-CA-999999") == 28

    def test_empty(self):
        assert _extract_region("") is None

    def test_none(self):
        assert _extract_region(None) is None

    def test_no_dash(self):
        assert _extract_region("ABC") is None


# ---------------------------------------------------------------------------
# data.gov client tests
# ---------------------------------------------------------------------------


class TestNLRBDatagovClient:
    def _make_xml(self, cases: list[dict]) -> str:
        root = ET.Element("cases")
        for c in cases:
            el = ET.SubElement(root, "case")
            for k, v in c.items():
                child = ET.SubElement(el, k)
                child.text = str(v)
        return ET.tostring(root, encoding="unicode")

    def test_parse_single_case(self):
        xml = self._make_xml([{
            "caseNumber": "05-RC-100001",
            "caseType": "RC",
            "caseName": "Acme Corp",
            "status": "Closed",
            "dateFiled": "2024-01-10",
            "dateClosed": "2024-06-15",
            "city": "Chicago",
            "state": "IL",
        }])
        session = _mock_session()
        session.get.return_value.text = xml
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBDatagovClient(session=session)

        result = client.fetch_cases()

        assert result.success
        assert len(result.cases) == 1
        case = result.cases[0]
        assert case.case_number == "05-RC-100001"
        assert case.region == 5
        assert case.date_filed == date(2024, 1, 10)
        assert case.source == "datagov"

    def test_empty_xml(self):
        xml = "<cases></cases>"
        session = _mock_session()
        session.get.return_value.text = xml
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBDatagovClient(session=session)

        result = client.fetch_cases()

        assert result.success
        assert len(result.cases) == 0

    def test_http_error(self):
        session = _mock_session()
        session.get.side_effect = ConnectionError("timeout")
        client = NLRBDatagovClient(session=session)

        result = client.fetch_cases()

        assert not result.success
        assert "HTTP error" in result.errors[0]

    def test_malformed_xml(self):
        session = _mock_session()
        session.get.return_value.text = "not xml at all <<<"
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBDatagovClient(session=session)

        result = client.fetch_cases()

        assert not result.success
        assert "XML parse error" in result.errors[0]

    def test_skips_case_without_number(self):
        xml = self._make_xml([{"caseType": "RC", "status": "Open"}])
        session = _mock_session()
        session.get.return_value.text = xml
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBDatagovClient(session=session)

        result = client.fetch_cases()

        assert result.success
        assert len(result.cases) == 0

    def test_alternate_field_names(self):
        xml = self._make_xml([{
            "case_number": "12-CA-555555",
            "case_type": "CA",
            "case_name": "Test Co",
            "date_filed": "03/15/2024",
            "labor_union": "IBEW",
            "naics": "238210",
            "num_employees": "45",
        }])
        session = _mock_session()
        session.get.return_value.text = xml
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBDatagovClient(session=session)

        result = client.fetch_cases()

        assert len(result.cases) == 1
        case = result.cases[0]
        assert case.union_name == "IBEW"
        assert case.naics_code == "238210"
        assert case.employee_count == 45

    def test_multiple_cases(self):
        xml = self._make_xml([
            {"caseNumber": "05-RC-100001", "caseType": "RC"},
            {"caseNumber": "05-RC-100002", "caseType": "RC"},
            {"caseNumber": "01-CA-200001", "caseType": "CA"},
        ])
        session = _mock_session()
        session.get.return_value.text = xml
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBDatagovClient(session=session)

        result = client.fetch_cases()
        assert len(result.cases) == 3


# ---------------------------------------------------------------------------
# labordata client tests
# ---------------------------------------------------------------------------


class TestNLRBLabordataClient:
    def _make_csv(self, rows: list[dict]) -> str:
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    def _make_session(self, file_contents: dict[str, str]):
        """Create a mock session that returns different content per URL."""
        session = _mock_session()

        def side_effect(url, timeout=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.text = ""
            for key, content in file_contents.items():
                if key in url:
                    resp.text = content
                    break
            return resp

        session.get.side_effect = side_effect
        return session

    def test_parse_cases(self):
        csv_text = self._make_csv([{
            "case_number": "05-RC-200001",
            "case_type": "RC",
            "case_name": "Test Corp",
            "status": "Open",
            "date_filed": "2024-02-01",
            "city": "Austin",
            "state": "TX",
        }])
        session = self._make_session({"cases.csv": csv_text})
        client = NLRBLabordataClient(session=session)

        result = client.fetch_cases()

        assert result.success
        assert len(result.cases) == 1
        assert result.cases[0].city == "Austin"
        assert result.source == "labordata"

    def test_parse_elections(self):
        cases_csv = self._make_csv([{
            "case_number": "05-RC-200001",
            "case_type": "RC",
            "case_name": "Test",
            "status": "Closed",
        }])
        elections_csv = self._make_csv([{
            "case_number": "05-RC-200001",
            "tally_date": "2024-04-01",
            "eligible_voters": "100",
            "votes_for": "60",
            "votes_against": "35",
            "union_name": "SEIU",
        }])
        session = self._make_session({
            "cases.csv": cases_csv,
            "elections.csv": elections_csv,
        })
        client = NLRBLabordataClient(session=session)

        result = client.fetch_cases()

        assert len(result.elections) == 1
        assert result.elections[0].votes_for == 60
        assert result.elections[0].eligible_voters == 100

    def test_parse_ulp_charges(self):
        charges_csv = self._make_csv([{
            "case_number": "01-CA-300001",
            "allegation": "8(a)(1) interference",
            "charging_party": "Local 999",
            "employer": "Bad Corp",
            "nlra_section": "8(a)(1)",
            "date_filed": "2024-05-01",
        }])
        session = self._make_session({"charges.csv": charges_csv})
        client = NLRBLabordataClient(session=session)

        result = client.fetch_cases()

        assert len(result.ulp_charges) == 1
        assert result.ulp_charges[0].charged_party == "Bad Corp"
        assert result.ulp_charges[0].section_of_act == "8(a)(1)"

    def test_handles_download_failure(self):
        session = _mock_session()
        session.get.side_effect = ConnectionError("network down")
        client = NLRBLabordataClient(session=session)

        result = client.fetch_cases()

        assert not result.success

    def test_skips_empty_case_number(self):
        csv_text = self._make_csv([{
            "case_number": "",
            "case_type": "RC",
        }])
        session = self._make_session({"cases.csv": csv_text})
        client = NLRBLabordataClient(session=session)

        result = client.fetch_cases()

        assert len(result.cases) == 0

    def test_alternate_field_names(self):
        csv_text = self._make_csv([{
            "case_number": "07-RC-400001",
            "case_type": "RC",
            "labor_union": "UFCW",
            "bargaining_unit": "Grocery workers",
            "naics": "445110",
            "num_employees": "85",
        }])
        session = self._make_session({"cases.csv": csv_text})
        client = NLRBLabordataClient(session=session)

        result = client.fetch_cases()

        assert len(result.cases) == 1
        case = result.cases[0]
        assert case.union_name == "UFCW"
        assert case.unit_description == "Grocery workers"
        assert case.naics_code == "445110"
        assert case.employee_count == 85


# ---------------------------------------------------------------------------
# NxGen client tests
# ---------------------------------------------------------------------------


class TestNLRBNxGenClient:
    def test_http_error(self):
        session = _mock_session()
        session.get.side_effect = ConnectionError("blocked")
        client = NLRBNxGenClient(session=session)

        result = client.fetch_case("05-RC-000001")

        assert not result.success
        assert "NxGen HTTP error" in result.errors[0]

    def test_empty_html_returns_empty(self):
        session = _mock_session()
        session.get.return_value.text = "<html><body>No results</body></html>"
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBNxGenClient(session=session)

        result = client.fetch_case("05-RC-000001")

        assert result.success
        assert len(result.cases) == 0

    def test_parses_table_rows(self):
        html = textwrap.dedent("""\
            <html><body><table>
            <tr>
                <td class="case-number">05-RC-111111</td>
                <td class="case-name">Test Corp</td>
                <td class="date-filed">2024-01-01</td>
                <td class="status">Open</td>
                <td class="city">Dallas</td>
                <td class="state">TX</td>
            </tr>
            </table></body></html>
        """)
        session = _mock_session()
        session.get.return_value.text = html
        session.get.return_value.raise_for_status = MagicMock()
        client = NLRBNxGenClient(session=session)

        result = client.fetch_case("05-RC-111111")

        assert len(result.cases) == 1
        assert result.cases[0].case_number == "05-RC-111111"
        assert result.cases[0].city == "Dallas"
        assert result.cases[0].source == "nxgen"


# ---------------------------------------------------------------------------
# Unified facade tests
# ---------------------------------------------------------------------------


class TestNLRBDataClient:
    def _mock_labordata_result(self):
        return NLRBFetchResult(
            source="labordata",
            cases=[
                NLRBCaseRecord(
                    case_number="05-RC-100001",
                    case_type="RC",
                    city="Chicago",
                    state="IL",
                    source="labordata",
                ),
                NLRBCaseRecord(
                    case_number="01-CA-200001",
                    case_type="CA",
                    source="labordata",
                ),
            ],
            elections=[
                ElectionRecord(
                    case_number="05-RC-100001",
                    tally_date=date(2024, 3, 1),
                    votes_for=100,
                    source="labordata",
                ),
            ],
        )

    def _mock_datagov_result(self):
        return NLRBFetchResult(
            source="datagov",
            cases=[
                NLRBCaseRecord(
                    case_number="05-RC-100001",
                    case_type="RC",
                    city="Chicago",
                    state="IL",
                    source="datagov",
                ),
                NLRBCaseRecord(
                    case_number="12-RC-300001",
                    case_type="RC",
                    source="datagov",
                ),
            ],
        )

    def test_deduplicates_by_case_number(self):
        datagov = MagicMock(spec=NLRBDatagovClient)
        labordata = MagicMock(spec=NLRBLabordataClient)

        labordata.fetch_cases.return_value = self._mock_labordata_result()
        datagov.fetch_cases.return_value = self._mock_datagov_result()

        client = NLRBDataClient(
            datagov_client=datagov,
            labordata_client=labordata,
        )
        result = client.fetch_all()

        assert len(result.cases) == 3
        case_numbers = {c.case_number for c in result.cases}
        assert case_numbers == {"05-RC-100001", "01-CA-200001", "12-RC-300001"}

    def test_prefers_labordata(self):
        datagov = MagicMock(spec=NLRBDatagovClient)
        labordata = MagicMock(spec=NLRBLabordataClient)

        labordata.fetch_cases.return_value = self._mock_labordata_result()
        datagov.fetch_cases.return_value = self._mock_datagov_result()

        client = NLRBDataClient(
            datagov_client=datagov,
            labordata_client=labordata,
        )
        result = client.fetch_all()

        shared_case = next(c for c in result.cases if c.case_number == "05-RC-100001")
        assert shared_case.source == "labordata"

    def test_merges_elections(self):
        datagov = MagicMock(spec=NLRBDatagovClient)
        labordata = MagicMock(spec=NLRBLabordataClient)

        labordata.fetch_cases.return_value = self._mock_labordata_result()
        datagov.fetch_cases.return_value = self._mock_datagov_result()

        client = NLRBDataClient(
            datagov_client=datagov,
            labordata_client=labordata,
        )
        result = client.fetch_all()
        assert len(result.elections) == 1

    def test_collects_errors(self):
        datagov = MagicMock(spec=NLRBDatagovClient)
        labordata = MagicMock(spec=NLRBLabordataClient)

        labordata.fetch_cases.return_value = NLRBFetchResult(
            source="labordata", errors=["lab error"]
        )
        datagov.fetch_cases.return_value = NLRBFetchResult(
            source="datagov", errors=["gov error"]
        )

        client = NLRBDataClient(
            datagov_client=datagov,
            labordata_client=labordata,
        )
        result = client.fetch_all()
        assert len(result.errors) == 2

    def test_nxgen_disabled_by_default(self):
        datagov = MagicMock(spec=NLRBDatagovClient)
        labordata = MagicMock(spec=NLRBLabordataClient)
        client = NLRBDataClient(
            datagov_client=datagov,
            labordata_client=labordata,
        )
        assert client._nxgen is None

    def test_nxgen_enabled(self):
        datagov = MagicMock(spec=NLRBDatagovClient)
        labordata = MagicMock(spec=NLRBLabordataClient)
        nxgen = MagicMock(spec=NLRBNxGenClient)
        client = NLRBDataClient(
            datagov_client=datagov,
            labordata_client=labordata,
            nxgen_client=nxgen,
            use_nxgen=True,
        )
        assert client._nxgen is not None

    def test_source_priority_order(self):
        assert NLRBDataClient.SOURCE_PRIORITY == ("labordata", "datagov", "nxgen")
