"""Regression probes for #1477: preserve ACS MOEs through time and boundaries."""

import logging
import math
from types import SimpleNamespace

import pandas as pd
import pytest

from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
from siege_utilities.geo.temporal.services import (
    TemporalDemographicService,
    TemporalTimeseriesBuilder,
)
from siege_utilities.geo.timeseries.longitudinal_data import (
    LongitudinalAligner,
    get_longitudinal_data,
)


@pytest.fixture(autouse=True)
def enable_moe_warnings(monkeypatch, caplog):
    # Django test settings disable existing loggers during collection.
    for name in (
        "siege_utilities.geo.crosswalk.crosswalk_processor",
        "siege_utilities.geo.timeseries.longitudinal_data",
    ):
        logger = logging.getLogger(name)
        monkeypatch.setattr(logger, "disabled", False)
        monkeypatch.setattr(logger, "propagate", True)
        caplog.set_level(logging.WARNING, logger=name)


def test_builder_probe_preserves_api_moe_keys():
    service = TemporalDemographicService()
    rows = []
    for year, (estimate, moe) in {
        2018: (100, 10), 2019: (110, 11), 2020: (120, 12),
    }.items():
        snapshot = service.build_snapshots(pd.DataFrame({
            "GEOID": ["48201000100"],
            "B01001_001E": [estimate],
            "B01001_001M": [moe],
        }), "tract", year)[0]
        assert snapshot.moe_values == {"B01001_001M": moe}
        rows.append({
            "boundary_id": snapshot.boundary_id,
            "year": year,
            "values": snapshot.values,
            "moe_values": snapshot.moe_values,
        })

    result = TemporalTimeseriesBuilder().build(
        ["B01001_001E"], [2018, 2019, 2020], "tract",
        snapshots_df=pd.DataFrame(rows),
    )[0]

    assert result.success
    assert result.series[0].moe_values == [10, 11, 12]
    assert result.series[0].values == [100, 110, 120]


@pytest.fixture
def merge_crosswalk():
    return pd.DataFrame({
        "source_geoid": ["48201000100", "48201000200"],
        "target_geoid": ["48201000300", "48201000300"],
        "area_weight": [1.0, 1.0],
    })


@pytest.fixture
def source_data():
    return pd.DataFrame({
        "GEOID": ["48201000100", "48201000200"],
        "NAME": ["Tract 1", "Tract 2"],
        "B01001_001E": [100, 200],
        "B01001_001M": [3, 4],
        "count": [20, 30],
    })


def test_crosswalk_merge_uses_root_sum_of_squares(merge_crosswalk, source_data):
    processor = CrosswalkProcessor(merge_crosswalk, 2010, 2020, "tract")
    result = processor.transform(source_data).iloc[0]

    assert result["B01001_001M"] == pytest.approx(math.hypot(3, 4))
    assert result["B01001_001E"] == 300
    assert result["count"] == 50


def test_crosswalk_split_scales_moe_by_share(source_data):
    crosswalk = pd.DataFrame({
        "source_geoid": ["48201000100", "48201000100"],
        "target_geoid": ["48201000300", "48201000400"],
        "area_weight": [0.25, 0.75],
    })
    result = CrosswalkProcessor(crosswalk, 2010, 2020, "tract").transform(
        source_data.iloc[:1],
    ).set_index("GEOID")

    assert result["B01001_001M"].tolist() == pytest.approx([0.75, 2.25])
    assert result["B01001_001E"].tolist() == [25, 75]


def test_crosswalk_split_then_merge_combines_weighted_moes(source_data):
    crosswalk = pd.DataFrame({
        "source_geoid": ["48201000100", "48201000100", "48201000200"],
        "target_geoid": ["48201000300", "48201000400", "48201000300"],
        "area_weight": [0.25, 0.75, 1.0],
    })
    result = CrosswalkProcessor(crosswalk, 2010, 2020, "tract").transform(
        source_data,
    ).set_index("GEOID")

    assert result.loc["48201000300", "B01001_001M"] == pytest.approx(math.hypot(0.75, 4))
    assert result.loc["48201000400", "B01001_001M"] == pytest.approx(2.25)
    assert result["B01001_001E"].tolist() == [225, 75]


def test_longitudinal_normalization_publishes_rss_moe(monkeypatch, merge_crosswalk, source_data):
    def fetch_data(self, **kwargs):
        assert kwargs["include_moe"] is True
        if kwargs["year"] == 2019:
            return source_data.copy()
        return pd.DataFrame({
            "GEOID": ["48201000300"], "NAME": ["Merged tract"],
            "B01001_001E": [320], "B01001_001M": [6],
        })

    monkeypatch.setattr(
        "siege_utilities.geo.census_api_client.CensusAPIClient.fetch_data", fetch_data,
    )
    monkeypatch.setattr(
        "siege_utilities.geo.crosswalk.crosswalk_processor.get_crosswalk",
        lambda **kwargs: merge_crosswalk,
    )

    result = get_longitudinal_data(
        "B01001_001E", [2019, 2020], "tract", target_year=2020,
        include_moe=True, normalize_boundaries=True,
    ).iloc[0]

    assert result["B01001_001M_2019"] == pytest.approx(5)
    assert result["B01001_001E_2019"] == 300
    assert result["B01001_001M_2020"] == 6


@pytest.mark.parametrize("options", [
    {"aggregation_func": "mean"},
    {"aggregation_func": "weighted_mean"},
    {"aggregation_func": max},
    {"intensive_variables": ["B01001_001E"]},
    {"intensive_variables": ["B01001_001M"]},
])
def test_unsupported_moe_aggregation_excludes_with_warning(
    merge_crosswalk, source_data, options, caplog,
):
    merge_crosswalk["overlap_area"] = [1.0, 1.0]
    result = CrosswalkProcessor(merge_crosswalk, 2010, 2020, "tract").transform(
        source_data, **options,
    )

    assert "B01001_001M" not in result.columns
    assert "B01001_001M" in caplog.text
    assert "MOE" in caplog.text
    assert "B01001_001E" in result.columns


@pytest.mark.parametrize("moes", [[3, None], [None, None]])
def test_missing_contributing_moe_stays_unknown(merge_crosswalk, source_data, moes):
    source_data["B01001_001M"] = pd.Series(moes, dtype="Float64")
    result = CrosswalkProcessor(merge_crosswalk, 2010, 2020, "tract").transform(source_data)

    assert pd.isna(result.iloc[0]["B01001_001M"])


def test_unpaired_and_non_acs_columns_keep_existing_aggregation(merge_crosswalk, source_data):
    source_data["B01002_001M"] = [3, 4]  # No matching estimate column.
    source_data["ITEM"] = [10, 20]
    source_data["ITEE"] = [30, 40]
    result = CrosswalkProcessor(merge_crosswalk, 2010, 2020, "tract").transform(source_data)

    assert result.iloc[0]["B01002_001M"] == 7
    assert result.iloc[0]["ITEM"] == 30
    assert result.iloc[0]["ITEE"] == 70


def test_selected_moe_detects_estimate_elsewhere_in_frame(merge_crosswalk, source_data):
    result = CrosswalkProcessor(merge_crosswalk, 2010, 2020, "tract").transform(
        source_data, value_columns=["B01001_001M"],
    )

    assert result.iloc[0]["B01001_001M"] == pytest.approx(5)
    assert "B01001_001E" not in result.columns


@pytest.mark.parametrize("estimate", ["B01001A_001E", "DP05_0001E", "S0101_C01_001E"])
def test_acs_table_variants_use_paired_moes(merge_crosswalk, source_data, estimate):
    moe = estimate[:-1] + "M"
    source_data = source_data.rename(columns={"B01001_001E": estimate, "B01001_001M": moe})
    result = CrosswalkProcessor(merge_crosswalk, 2010, 2020, "tract").transform(source_data)

    assert result.iloc[0][moe] == pytest.approx(5)


def test_one_to_one_and_unmatched_moes_are_preserved(merge_crosswalk, source_data):
    result = CrosswalkProcessor(merge_crosswalk.iloc[:1], 2010, 2020, "tract").transform(
        source_data,
    ).set_index("GEOID")

    assert result.loc["48201000300", "B01001_001M"] == 3
    assert result.loc["48201000200", "B01001_001M"] == 4


def test_zero_share_does_not_contribute_missing_moe(merge_crosswalk, source_data):
    merge_crosswalk["area_weight"] = [1.0, 0.0]
    source_data["B01001_001M"] = [3.0, float("nan")]
    result = CrosswalkProcessor(merge_crosswalk, 2010, 2020, "tract").transform(source_data)

    assert result.iloc[0]["B01001_001M"] == 3


def test_areal_fallback_excludes_moes_with_warning(monkeypatch, source_data, caplog):
    def unavailable_crosswalk(*args, **kwargs):
        raise ValueError("Crosswalk unavailable")

    monkeypatch.setattr(LongitudinalAligner, "_apply_crosswalk_step", unavailable_crosswalk)
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.get_census_boundaries",
        lambda **kwargs: pd.DataFrame({"GEOID": source_data["GEOID"]}),
    )

    def interpolate(**kwargs):
        assert "B01001_001M" not in kwargs["extensive_variables"]
        assert "B01001_001M" not in (kwargs["intensive_variables"] or [])
        return SimpleNamespace(data=source_data.copy())

    monkeypatch.setattr("siege_utilities.geo.interpolation.areal.interpolate_areal", interpolate)
    result = LongitudinalAligner(target_vintage=2020).align(source_data, source_vintage=2010)

    assert result.method == "areal"
    assert "B01001_001M" not in result.data.columns
    assert "Excluding ACS MOE" in caplog.text
    assert "B01001_001M" in caplog.text
