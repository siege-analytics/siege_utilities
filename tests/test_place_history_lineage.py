"""Regression coverage for place history lineage defects in #1434."""

import math

import pytest

from siege_utilities.geo.place_history import (
    DictCrosswalkProvider,
    Lineage,
    LineageStep,
    _build_lineage,
    place_history,
)


@pytest.mark.parametrize("ancestor_weight", [0.005, 0.05])
def test_reverse_without_shares_retains_ancestors_but_omits_weights(ancestor_weight):
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", weight=ancestor_weight)
    provider.add(2000, 2010, "B00", "M10", weight=1.0)
    provider.add(2010, 2020, "M10", "T20", weight=0.1)

    lineage = _build_lineage("T20", 2020, 2000, provider, min_weight=0.01)

    assert lineage.terminal_geoids == ["A00", "B00"]
    assert [step.target_geoid for step in lineage.steps] == ["M10", "A00", "B00"]
    assert [step.weight for step in lineage.steps] == [0.1, ancestor_weight, 1.0]
    assert lineage.terminal_weights == {}


@pytest.mark.parametrize("from_year,to_year", [(2020, 2000), (2025, 2005)])
def test_reverse_step_years_match_geoid_vintages(from_year, to_year):
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10")
    provider.add(2010, 2020, "M10", "T20")

    result = place_history("T20", from_year, to_year, provider=provider)

    assert result.errors == []
    assert result.lineage.steps == [
        LineageStep("T20", "M10", source_year=2020, target_year=2010),
        LineageStep("M10", "A00", source_year=2010, target_year=2000),
    ]


@pytest.mark.parametrize(
    "origin,from_year,to_year,terminal,total_weight",
    [("A00", 2000, 2020, "T20", 0.4), ("T20", 2020, 2000, "A00", 1.0)],
)
def test_terminal_weights_sum_diamond_paths(
    origin, from_year, to_year, terminal, total_weight
):
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", weight=0.6, reverse_weight=1.0)
    provider.add(2000, 2010, "A00", "N10", weight=0.4, reverse_weight=1.0)
    provider.add(2010, 2020, "M10", "T20", weight=0.5, reverse_weight=0.75)
    provider.add(2010, 2020, "N10", "T20", weight=0.25, reverse_weight=0.25)

    result = place_history(origin, from_year, to_year, provider=provider)

    assert result.errors == []
    # Preserve the existing list while providing one summed weight per GEOID.
    assert result.lineage.terminal_geoids == [terminal, terminal]
    assert result.lineage.terminal_weights == pytest.approx({terminal: total_weight})


def test_forward_step_years_terminals_and_pruning_are_preserved():
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", weight=0.6, relationship="SPLIT")
    provider.add(2000, 2010, "A00", "N10", weight=0.395, relationship="SPLIT")
    provider.add(2000, 2010, "A00", "SMALL10", weight=0.005, relationship="SPLIT")
    provider.add(2010, 2020, "M10", "T20", weight=0.5, relationship="PARTIAL")
    provider.add(2010, 2020, "M10", "SMALL20", weight=0.01, relationship="PARTIAL")
    provider.add(2010, 2020, "N10", "T20", weight=0.8, relationship="PARTIAL")

    result = place_history("A00", 2005, 2025, provider=provider)

    assert result.errors == []
    assert result.lineage.direction == "forward"
    assert result.lineage.steps == [
        LineageStep("A00", "M10", 2000, 2010, 0.6, "SPLIT"),
        LineageStep("A00", "N10", 2000, 2010, 0.395, "SPLIT"),
        LineageStep("M10", "T20", 2010, 2020, 0.5, "PARTIAL"),
        LineageStep("N10", "T20", 2010, 2020, 0.8, "PARTIAL"),
    ]
    assert result.lineage.terminal_geoids == ["T20", "T20"]
    assert result.lineage.terminal_weights == pytest.approx({"T20": 0.616})


@pytest.mark.parametrize("weight", [0.0, -0.1, float("nan"), float("inf"), -float("inf")])
def test_reverse_skips_degenerate_records_without_pruning_small_ancestors(weight):
    provider = DictCrosswalkProvider()
    provider.add(2010, 2020, "INVALID10", "T20", weight=weight)
    provider.add(2010, 2020, "SMALL10", "T20", weight=0.005)

    lineage = _build_lineage("T20", 2020, 2010, provider)

    assert lineage.terminal_geoids == ["SMALL10"]
    assert [step.target_geoid for step in lineage.steps] == ["SMALL10"]
    assert lineage.terminal_weights == {}


@pytest.mark.parametrize(
    "from_year,to_year", [(2010, 2010), (2012, 2018), (2018, 2012), (2000, 2020)]
)
def test_terminal_weight_is_one_without_mappings(from_year, to_year):
    result = place_history("A", from_year, to_year, provider=DictCrosswalkProvider())

    assert result.errors == []
    assert result.lineage.steps == []
    assert result.lineage.terminal_geoids == ["A"]
    assert result.lineage.terminal_weights == {"A": 1.0}


def test_lineage_terminal_weights_default_is_independent_and_direction_stays_positional():
    first = Lineage("A", 2020, [], [], "reverse")
    second = Lineage("B", 2000)

    assert first.direction == "reverse"
    assert first.terminal_weights == {}
    first.terminal_weights["A"] = 1.0
    assert second.terminal_weights == {}


def test_reverse_step_weights_and_pruning_use_cumulative_reverse_shares():
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", weight=0.005, reverse_weight=0.9)
    provider.add(2000, 2010, "SMALL00", "M10", weight=1.0, reverse_weight=0.05)
    provider.add(2010, 2020, "M10", "T20", weight=0.005, reverse_weight=0.1)

    lineage = _build_lineage("T20", 2020, 2000, provider, min_weight=0.01)

    assert lineage.steps == [
        LineageStep("T20", "M10", 2020, 2010, 0.1),
        LineageStep("M10", "A00", 2010, 2000, 0.9),
    ]
    assert lineage.terminal_geoids == ["A00"]
    assert lineage.terminal_weights == pytest.approx({"A00": 0.09})


@pytest.mark.parametrize("missing_year", [2000, 2010])
def test_reverse_missing_share_omits_all_totals_including_known_paths(missing_year):
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", reverse_weight=1.0)
    provider.add(2010, 2020, "M10", "T20", reverse_weight=0.5)
    provider.add(
        2000, 2010, "A00", "N10", weight=0.005,
        reverse_weight=None if missing_year == 2000 else 0.02,
    )
    provider.add(
        2010, 2020, "N10", "T20", weight=0.005,
        reverse_weight=None if missing_year == 2010 else 0.5,
    )

    lineage = _build_lineage("T20", 2020, 2000, provider, min_weight=0.01)

    assert lineage.terminal_geoids == ["A00", "A00"]
    assert len(lineage.steps) == 4
    assert lineage.terminal_weights == {}


@pytest.mark.parametrize("weight", [0.0, -0.1, float("nan"), float("inf"), -float("inf")])
def test_reverse_skips_invalid_reverse_shares_without_using_forward_weights(weight):
    provider = DictCrosswalkProvider()
    provider.add(2010, 2020, "INVALID10", "T20", weight=1.0, reverse_weight=weight)
    provider.add(2010, 2020, "A10", "T20", weight=0.005, reverse_weight=0.7)

    lineage = _build_lineage("T20", 2020, 2010, provider, min_weight=0)

    assert lineage.steps == [LineageStep("T20", "A10", 2020, 2010, 0.7)]
    assert lineage.terminal_geoids == ["A10"]
    assert lineage.terminal_weights == {"A10": 0.7}


def test_forward_skips_zero_weight_with_zero_min_weight():
    provider = DictCrosswalkProvider()
    provider.add(2010, 2020, "A", "ZERO", weight=0)
    provider.add(2010, 2020, "A", "B", weight=1)

    lineage = _build_lineage("A", 2010, 2020, provider, min_weight=0)

    assert lineage.terminal_geoids == ["B"]
    assert lineage.terminal_weights == {"B": 1}


@pytest.mark.parametrize("weight", [1e308, 1e-200])
def test_forward_skips_cumulative_overflow_and_underflow(weight):
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", weight=weight)
    provider.add(2010, 2020, "M10", "T20", weight=weight)
    provider.add(2000, 2010, "A00", "N10", weight=1.0)
    provider.add(2010, 2020, "N10", "U20", weight=1.0)

    lineage = _build_lineage("A00", 2000, 2020, provider, min_weight=0)

    assert lineage.terminal_geoids == ["U20"]
    assert lineage.terminal_weights == {"U20": 1.0}


def test_forward_does_not_publish_overflowing_terminal_sum():
    provider = DictCrosswalkProvider()
    provider.add(2010, 2020, "A", "OVERFLOW", weight=1e308)
    provider.add(2010, 2020, "A", "OVERFLOW", weight=1e308)
    provider.add(2010, 2020, "A", "B", weight=1.0)

    lineage = _build_lineage("A", 2010, 2020, provider)

    assert lineage.terminal_weights == {"B": 1.0}


def test_reverse_uses_target_share_and_min_weight_applies_to_it():
    # T20 is 89.9% former A10 (a small slice of a big tract), 10% B10, 0.1% D10.
    p = DictCrosswalkProvider()
    p.add(2010, 2020, "A10", "T20", weight=0.005, reverse_weight=0.899)
    p.add(2010, 2020, "A10", "U20", weight=0.995, reverse_weight=1.0)
    p.add(2010, 2020, "B10", "T20", weight=1.0, reverse_weight=0.1)
    p.add(2010, 2020, "D10", "T20", weight=0.9, reverse_weight=0.001)
    lin = _build_lineage("T20", 2020, 2010, p, min_weight=0.01)
    assert lin.terminal_weights == pytest.approx({"A10": 0.899, "B10": 0.1})


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.5])
def test_forward_skips_degenerate_weights(bad):
    p = DictCrosswalkProvider()
    p.add(2010, 2020, "A", "B", weight=bad)
    p.add(2010, 2020, "A", "C", weight=1.0)
    lin = _build_lineage("A", 2010, 2020, p)
    assert all(math.isfinite(w) and w > 0 for w in lin.terminal_weights.values())
    assert set(lin.terminal_weights) == {"C"}
