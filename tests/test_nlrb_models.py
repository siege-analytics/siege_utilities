"""Tests for NLRB case data models and DataFrame export (SU#618)."""

from __future__ import annotations

from datetime import date

import pytest

try:
    from django.db import models as django_models  # noqa: F401

    _DJANGO_AVAILABLE = True
except Exception:
    _DJANGO_AVAILABLE = False

try:
    import pandas as pd

    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False

from siege_utilities.geo.providers.nlrb_clients import (
    ElectionRecord,
    NLRBCaseRecord,
    NLRBFetchResult,
    ULPRecord,
)


# ---------------------------------------------------------------------------
# Django model tests (skip if Django not available)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="Django not available")
class TestNLRBCaseModel:
    def test_import(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        assert NLRBCase is not None

    def test_has_case_number(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        field = NLRBCase._meta.get_field("case_number")
        assert field is not None
        assert field.unique

    def test_has_case_type(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        field = NLRBCase._meta.get_field("case_type")
        assert field is not None

    def test_has_date_fields(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        assert NLRBCase._meta.get_field("date_filed") is not None
        assert NLRBCase._meta.get_field("date_closed") is not None

    def test_has_region_fk(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        field = NLRBCase._meta.get_field("region")
        assert field.related_model.__name__ == "NLRBRegion"

    def test_has_location_fields(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        assert NLRBCase._meta.get_field("city") is not None
        assert NLRBCase._meta.get_field("state") is not None

    def test_has_naics_code(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        field = NLRBCase._meta.get_field("naics_code")
        assert field is not None

    def test_str_representation(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        case = NLRBCase(case_number="05-RC-123456", case_name="Test Corp")
        assert "05-RC-123456" in str(case)
        assert "Test Corp" in str(case)

    def test_from_record(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        record = NLRBCaseRecord(
            case_number="05-RC-100001",
            case_type="RC",
            case_name="Acme Corp",
            status="Open",
            date_filed=date(2024, 1, 15),
            region=5,
            city="Chicago",
            state="IL",
            source="labordata",
        )
        instance = NLRBCase.from_record(record)
        assert instance.case_number == "05-RC-100001"
        assert instance.region_number == 5
        assert instance.city == "Chicago"

    def test_to_record(self):
        from siege_utilities.geo.django.models.nlrb_cases import NLRBCase

        instance = NLRBCase(
            case_number="05-RC-100001",
            case_type="RC",
            case_name="Acme Corp",
            region_number=5,
            city="Chicago",
            state="IL",
        )
        record = instance.to_record()
        assert record.case_number == "05-RC-100001"
        assert record.region == 5
        assert record.city == "Chicago"


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="Django not available")
class TestElectionResultModel:
    def test_import(self):
        from siege_utilities.geo.django.models.nlrb_cases import ElectionResult

        assert ElectionResult is not None

    def test_has_case_fk(self):
        from siege_utilities.geo.django.models.nlrb_cases import ElectionResult

        field = ElectionResult._meta.get_field("case")
        assert field.related_model.__name__ == "NLRBCase"

    def test_has_tally_fields(self):
        from siege_utilities.geo.django.models.nlrb_cases import ElectionResult

        assert ElectionResult._meta.get_field("tally_date") is not None
        assert ElectionResult._meta.get_field("eligible_voters") is not None
        assert ElectionResult._meta.get_field("votes_for") is not None
        assert ElectionResult._meta.get_field("votes_against") is not None


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="Django not available")
class TestULPChargeModel:
    def test_import(self):
        from siege_utilities.geo.django.models.nlrb_cases import ULPCharge

        assert ULPCharge is not None

    def test_has_case_fk(self):
        from siege_utilities.geo.django.models.nlrb_cases import ULPCharge

        field = ULPCharge._meta.get_field("case")
        assert field.related_model.__name__ == "NLRBCase"

    def test_has_allegation_fields(self):
        from siege_utilities.geo.django.models.nlrb_cases import ULPCharge

        assert ULPCharge._meta.get_field("allegation") is not None
        assert ULPCharge._meta.get_field("section_of_act") is not None


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="Django not available")
class TestBargainingUnitModel:
    def test_import(self):
        from siege_utilities.geo.django.models.nlrb_cases import BargainingUnit

        assert BargainingUnit is not None

    def test_has_case_fk(self):
        from siege_utilities.geo.django.models.nlrb_cases import BargainingUnit

        field = BargainingUnit._meta.get_field("case")
        assert field.related_model.__name__ == "NLRBCase"

    def test_has_naics_soc_fields(self):
        from siege_utilities.geo.django.models.nlrb_cases import BargainingUnit

        assert BargainingUnit._meta.get_field("naics_code") is not None
        assert BargainingUnit._meta.get_field("soc_codes") is not None
        assert BargainingUnit._meta.get_field("employee_count") is not None


# ---------------------------------------------------------------------------
# DataFrame export tests (skip if pandas not available)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _PANDAS_AVAILABLE, reason="pandas not available")
class TestDataFrameExport:
    def test_cases_to_dataframe(self):
        from siege_utilities.geo.providers.nlrb_export import cases_to_dataframe

        cases = [
            NLRBCaseRecord(case_number="05-RC-1", case_type="RC", city="Chicago"),
            NLRBCaseRecord(case_number="01-CA-2", case_type="CA", city="Boston"),
        ]
        df = cases_to_dataframe(cases)
        assert len(df) == 2
        assert "case_number" in df.columns
        assert "city" in df.columns
        assert df.iloc[0]["city"] == "Chicago"

    def test_cases_from_fetch_result(self):
        from siege_utilities.geo.providers.nlrb_export import cases_to_dataframe

        result = NLRBFetchResult(
            cases=[NLRBCaseRecord(case_number="05-RC-1", case_type="RC")]
        )
        df = cases_to_dataframe(result)
        assert len(df) == 1

    def test_elections_to_dataframe(self):
        from siege_utilities.geo.providers.nlrb_export import elections_to_dataframe

        elections = [
            ElectionRecord(
                case_number="05-RC-1",
                tally_date=date(2024, 3, 1),
                votes_for=100,
                votes_against=50,
            ),
        ]
        df = elections_to_dataframe(elections)
        assert len(df) == 1
        assert df.iloc[0]["votes_for"] == 100

    def test_ulp_to_dataframe(self):
        from siege_utilities.geo.providers.nlrb_export import ulp_charges_to_dataframe

        charges = [
            ULPRecord(
                case_number="01-CA-1",
                allegation="8(a)(1)",
                section_of_act="8(a)(1)",
            ),
        ]
        df = ulp_charges_to_dataframe(charges)
        assert len(df) == 1
        assert df.iloc[0]["section_of_act"] == "8(a)(1)"

    def test_empty_returns_empty_dataframe(self):
        from siege_utilities.geo.providers.nlrb_export import cases_to_dataframe

        df = cases_to_dataframe([])
        assert len(df) == 0

    def test_fetch_result_to_dataframes(self):
        from siege_utilities.geo.providers.nlrb_export import fetch_result_to_dataframes

        result = NLRBFetchResult(
            cases=[NLRBCaseRecord(case_number="05-RC-1", case_type="RC")],
            elections=[ElectionRecord(case_number="05-RC-1")],
            ulp_charges=[ULPRecord(case_number="01-CA-1")],
        )
        dfs = fetch_result_to_dataframes(result)
        assert "cases" in dfs
        assert "elections" in dfs
        assert "ulp_charges" in dfs
        assert len(dfs["cases"]) == 1
