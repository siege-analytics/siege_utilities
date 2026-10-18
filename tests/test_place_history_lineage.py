"""Regression coverage for place history lineage defects in #1434."""

import pytest

from siege_utilities.geo.place_history import (
    DictCrosswalkProvider,
    Lineage,
    LineageStep,
    _build_lineage,
    place_history,
)


@pytest.mark.parametrize("ancestor_weight", [0.005, 0.05])
def test_reverse_retains_ancestors_below_cumulative_min_weight(ancestor_weight):
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", weight=ancestor_weight)
    provider.add(2000, 2010, "B00", "M10", weight=1.0)
    provider.add(2010, 2020, "M10", "T20", weight=0.1)

    lineage = _build_lineage("T20", 2020, 2000, provider, min_weight=0.01)

    assert lineage.terminal_geoids == ["A00", "B00"]
    assert [step.target_geoid for step in lineage.steps] == ["M10", "A00", "B00"]
    assert [step.weight for step in lineage.steps] == [0.1, ancestor_weight, 1.0]
    assert lineage.terminal_weights == pytest.approx(
        {"A00": ancestor_weight * 0.1, "B00": 0.1}
    )


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
    "origin,from_year,to_year,terminal",
    [("A00", 2000, 2020, "T20"), ("T20", 2020, 2000, "A00")],
)
def test_terminal_weights_sum_diamond_paths(origin, from_year, to_year, terminal):
    provider = DictCrosswalkProvider()
    provider.add(2000, 2010, "A00", "M10", weight=0.6)
    provider.add(2000, 2010, "A00", "N10", weight=0.4)
    provider.add(2010, 2020, "M10", "T20", weight=0.5)
    provider.add(2010, 2020, "N10", "T20", weight=0.25)

    result = place_history(origin, from_year, to_year, provider=provider)

    assert result.errors == []
    # Preserve the existing list while providing one summed weight per GEOID.
    assert result.lineage.terminal_geoids == [terminal, terminal]
    assert result.lineage.terminal_weights == pytest.approx({terminal: 0.4})


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
    assert lineage.terminal_weights == {"SMALL10": 0.005}


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
