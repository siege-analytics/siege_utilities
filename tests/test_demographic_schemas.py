"""Tests for demographic Pydantic schemas (no geopandas required)."""

import pytest
from pydantic import ValidationError

from siege_utilities.geo.schemas.demographics import (
    DemographicVariableSchema,
    DemographicSnapshotSchema,
    DemographicTimeSeriesSchema,
)


class TestDemographicVariableSchema:
    def test_basic_creation(self):
        v = DemographicVariableSchema(
            code="B01001_001E", label="Total Population", dataset="acs5"
        )
        assert v.code == "B01001_001E"
        assert v.label == "Total Population"
        assert v.dataset == "acs5"
        assert v.concept == ""
        assert v.group == ""

    def test_is_estimate(self):
        v = DemographicVariableSchema(
            code="B01001_001E", label="Pop Estimate", dataset="acs5"
        )
        assert v.is_estimate is True
        assert v.is_moe is False

    def test_is_moe(self):
        v = DemographicVariableSchema(
            code="B01001_001M", label="Pop MOE", dataset="acs5"
        )
        assert v.is_moe is True
        assert v.is_estimate is False

    def test_base_code(self):
        est = DemographicVariableSchema(
            code="B01001_001E", label="X", dataset="acs5"
        )
        moe = DemographicVariableSchema(
            code="B01001_001M", label="X", dataset="acs5"
        )
        plain = DemographicVariableSchema(
            code="P1_001N", label="X", dataset="dec"
        )
        assert est.base_code == "B01001_001"
        assert moe.base_code == "B01001_001"
        assert plain.base_code == "P1_001N"

    def test_round_trip(self):
        v = DemographicVariableSchema(
            code="B19013_001E", label="Median Income", dataset="acs5",
            concept="Income", group="B19013", universe="Households",
        )
        dumped = v.model_dump()
        v2 = DemographicVariableSchema(**dumped)
        assert v.code == v2.code
        assert v.concept == v2.concept


class TestDemographicSnapshotSchema:
    def test_basic_creation(self):
        s = DemographicSnapshotSchema(
            boundary_type="tract", boundary_id="06037101100",
            year=2022, dataset="acs5",
        )
        assert s.boundary_type == "tract"
        assert s.year == 2022
        assert s.values == {}

    def test_auto_populate_summaries(self):
        s = DemographicSnapshotSchema(
            boundary_type="tract", boundary_id="06037101100",
            year=2022, dataset="acs5",
            values={
                "B01001_001E": 4521,
                "B19013_001E": 75000,
                "B01002_001E": 35.5,
            },
        )
        assert s.total_population == 4521
        assert s.median_household_income == 75000
        assert s.median_age == 35.5

    def test_auto_populate_does_not_overwrite_explicit(self):
        s = DemographicSnapshotSchema(
            boundary_type="county", boundary_id="06037",
            year=2022, dataset="acs5",
            values={"B01001_001E": 4521},
            total_population=9999,
        )
        assert s.total_population == 9999

    def test_get_value(self):
        s = DemographicSnapshotSchema(
            boundary_type="state", boundary_id="06",
            year=2022, dataset="acs5",
            values={"B01001_001E": 39000000},
        )
        assert s.get_value("B01001_001E") == 39000000
        assert s.get_value("MISSING", default=-1) == -1

    def test_get_moe(self):
        s = DemographicSnapshotSchema(
            boundary_type="tract", boundary_id="06037101100",
            year=2022, dataset="acs5",
            moe_values={"B01001_001M": 150},
        )
        assert s.get_moe("B01001_001E") == 150
        assert s.get_moe("B01001_001M") == 150
        assert s.get_moe("MISSING") is None

    def test_year_validation(self):
        with pytest.raises(ValidationError):
            DemographicSnapshotSchema(
                boundary_type="tract", boundary_id="X",
                year=1900, dataset="acs5",
            )

    def test_round_trip(self):
        s = DemographicSnapshotSchema(
            boundary_type="tract", boundary_id="06037101100",
            year=2022, dataset="acs5",
            values={"B01001_001E": 4521},
            moe_values={"B01001_001M": 150},
        )
        dumped = s.model_dump()
        s2 = DemographicSnapshotSchema(**dumped)
        assert s.boundary_id == s2.boundary_id
        assert s.values == s2.values


class TestDemographicTimeSeriesSchema:
    def test_basic_creation(self):
        ts = DemographicTimeSeriesSchema(
            boundary_type="tract", boundary_id="06037101100",
            variable_code="B01001_001E", dataset="acs5",
            start_year=2015, end_year=2022,
            years=[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022],
            values=[4000, 4100, 4200, 4300, 4400, 4500, 4600, 4700],
        )
        assert ts.start_year == 2015
        assert ts.end_year == 2022
        assert len(ts.years) == 8
        assert ts.moe_values == []
        assert ts.trend_direction == ""

    def test_with_statistics(self):
        ts = DemographicTimeSeriesSchema(
            boundary_type="county", boundary_id="06037",
            variable_code="B01001_001E", dataset="acs5",
            start_year=2015, end_year=2020,
            years=[2015, 2016, 2017, 2018, 2019, 2020],
            values=[10000, 10200, 10400, 10600, 10800, 11000],
            mean_value=10500.0, std_dev=316.23,
            cagr=0.0192, trend_direction="increasing",
        )
        assert ts.mean_value == 10500.0
        assert ts.trend_direction == "increasing"

    def test_round_trip(self):
        ts = DemographicTimeSeriesSchema(
            boundary_type="tract", boundary_id="06037101100",
            variable_code="B01001_001E", dataset="acs5",
            start_year=2015, end_year=2020,
            years=[2015, 2020], values=[4000, 4500],
            moe_values=[100, 120],
        )
        dumped = ts.model_dump()
        ts2 = DemographicTimeSeriesSchema(**dumped)
        assert ts.years == ts2.years
        assert ts.values == ts2.values
