"""Regression probes for survey weighting and inference (#1478)."""

from math import exp, sqrt
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from siege_utilities.reporting.pages.page_models import TableType
from siege_utilities.survey import crosstab
from siege_utilities.survey.crosstab import build_chain
from siege_utilities.survey.models import Chain, View, Wave, WaveSet
from siege_utilities.survey.significance import (
    SignificanceError,
    chi_square_flag,
    column_proportion_test,
)


def _flags(chain):
    return {
        key: [(v.metric, v.sig_flag) for v in views]
        for key, views in chain.views.items()
        if key != chain.delta_column
    }


def test_issue_1_population_weight_scaling_preserves_empty_flags():
    df = pd.DataFrame({
        "answer": ["no"] * 25 + ["yes"] * 25 + ["no"] * 23 + ["yes"] * 27,
        "grp": ["A"] * 50 + ["B"] * 50,
    })
    chains = [
        column_proportion_test(build_chain(
            df.assign(weight=scale), "answer", ["grp"], weight_var="weight"
        ))
        for scale in (1.0, 10000.0)
    ]
    expected = {key: [("no", None), ("yes", None)] for key in ("grp=A", "grp=B")}
    assert _flags(chains[0]) == _flags(chains[1]) == expected
    assert chains[0].views["grp=A"][0].base == 50.0
    assert chains[1].views["grp=A"][0].base == 500000.0
    assert chains[1].views["grp=A"][0].effective_n == 50.0


def test_issue_2_longitudinal_delta_is_not_a_comparison_column():
    df = pd.DataFrame({
        "answer": (["no"] * 25 + ["yes"] * 25) * 2,
        "year": [2022] * 50 + [2024] * 50,
    })
    chain = build_chain(df, "answer", ["year"], table_type=TableType.LONGITUDINAL)
    column_proportion_test(chain)
    assert _flags(chain) == {
        year: [("no", None), ("yes", None)] for year in ("2022", "2024")
    }
    assert all(v.sig_flag is None for v in chain.views[chain.delta_column])


def test_issue_3_top_n_uses_full_category_denominator():
    df = pd.DataFrame({"party": ["D"] * 40 + ["R"] * 35 + ["I"] * 25, "grp": "A"})
    chain = build_chain(df, "party", ["grp"], top_n=2)
    assert {v.metric: v.pct for v in chain.views["grp=A"]} == {"D": 0.40, "R": 0.35}
    assert all(v.base == 100.0 for v in chain.views["grp=A"])


def test_issue_4_mean_scale_uses_weighted_mean_and_se(monkeypatch):
    # Isolate the mean/SE from optional scipy; the t and refusal paths are below.
    monkeypatch.setattr(crosstab, "_critical_value", lambda n: 2.0)
    df = pd.DataFrame({
        "question": "a", "grp": "A", "score": [1, 1, 5, 5],
        "weight": [10, 10, 0.1, 0.1],
    })
    cells = []
    for scale in (1.0, 10000.0):
        chain = build_chain(
            df.assign(weight=df.weight * scale), "question", ["grp"],
            metric="score", weight_var="weight", table_type=TableType.MEAN_SCALE,
        )
        cells.append(chain.views["grp=A"][0])
    # Exact reliability-weight variance: 3200/10401; Kish n: 20402/10001.
    expected_ci = 2 * sqrt((3200 / 10401) / (20402 / 10001))
    for cell in cells:
        assert cell.count == pytest.approx(105 / 101)
        assert cell.ci == pytest.approx(expected_ci)
        assert cell.effective_n == pytest.approx(20402 / 10001)
    assert cells[0].base == pytest.approx(20.2)
    assert cells[1].base == pytest.approx(202000)


def _association_frame():
    rows = []
    for group, counts in (("A", (30, 20, 10)), ("B", (10, 20, 30))):
        for answer, count in zip(("x", "y", "z"), counts):
            rows.extend([{"answer": answer, "grp": group}] * count)
    return pd.DataFrame(rows)


def test_issue_5_chi_square_refuses_sums_and_uses_respondent_counts(monkeypatch):
    expected = pd.DataFrame({"grp=A": [30, 20, 10], "grp=B": [10, 20, 30]},
                            index=pd.Index(["x", "y", "z"], name="answer"))
    calls = []

    def checked_chi_square(table):
        pd.testing.assert_frame_equal(table, expected, check_dtype=False)
        calls.append(table)
        return SimpleNamespace(statistic=20.0, p_value=exp(-10))

    monkeypatch.setattr(
        "siege_utilities.data.statistics.cross_tabulation.chi_square_test",
        checked_chi_square,
    )
    df = _association_frame()
    metric_chain = build_chain(df.assign(dollars=10000), "answer", ["grp"], metric="dollars")
    with pytest.raises(SignificanceError, match="respondent counts"):
        chi_square_flag(metric_chain)
    aggregate_chain = Chain("answer", ["grp"], {
        "grp=A": [View("x", 400000, 300000), View("y", 400000, 100000)],
        "grp=B": [View("x", 400000, 100000), View("y", 400000, 300000)],
    }, TableType.CROSS_TAB)
    with pytest.raises(SignificanceError, match="respondent counts"):
        chi_square_flag(aggregate_chain)
    assert calls == []
    for weights in (None, 10000.0):
        chain = build_chain(df.assign(weight=weights), "answer", ["grp"],
                            weight_var="weight" if weights else None)
        chi_square_flag(chain)
        assert chain.chi_square_significant is True
        assert chain.chi_square_p == pytest.approx(exp(-10))
    assert len(calls) == 2


def test_small_mean_sample_without_scipy_refuses(monkeypatch):
    monkeypatch.setattr(crosstab, "_SCIPY_T_AVAILABLE", False)
    df = pd.DataFrame({"question": "a", "grp": "A", "score": [1.0, 5.0]})
    with pytest.raises(SignificanceError, match="requires scipy"):
        build_chain(df, "question", ["grp"], metric="score", table_type=TableType.MEAN_SCALE)


def test_small_mean_sample_uses_student_t():
    scipy_stats = pytest.importorskip("scipy.stats")
    df = pd.DataFrame({"question": "a", "grp": "A", "score": [1.0, 5.0]})
    chain = build_chain(df, "question", ["grp"], metric="score", table_type=TableType.MEAN_SCALE)
    assert chain.views["grp=A"][0].ci == pytest.approx(2 * scipy_stats.t.ppf(0.975, df=1))


def test_chi_square_real_respondent_statistic(monkeypatch):
    pytest.importorskip("scipy.stats")
    from siege_utilities.data.statistics.cross_tabulation import chi_square_test

    results = []

    def capture_result(table):
        result = chi_square_test(table)
        results.append(result)
        return result

    monkeypatch.setattr(
        "siege_utilities.data.statistics.cross_tabulation.chi_square_test", capture_result
    )
    chain = build_chain(_association_frame().assign(weight=10000), "answer", ["grp"],
                        weight_var="weight")
    chi_square_flag(chain)
    assert results[0].statistic == pytest.approx(20.0)
    assert results[0].dof == 2
    assert chain.chi_square_p == pytest.approx(exp(-10), abs=1e-6)


@pytest.mark.parametrize("table_type", [
    TableType.SINGLE_RESPONSE, TableType.BANNER, TableType.LONGITUDINAL, TableType.RANKING,
])
def test_top_n_denominator_in_all_count_builders(table_type):
    df = pd.DataFrame({"party": ["D"] * 40 + ["R"] * 35 + ["I"] * 25, "grp": "A"})
    chain = build_chain(df.assign(weight=10000), "party", ["grp"], top_n=2,
                        weight_var="weight", table_type=table_type)
    cells = next(iter(chain.views.values()))
    assert {v.metric: v.pct for v in cells} == {"D": 0.40, "R": 0.35}
    assert [v.respondent_count for v in cells] == [40, 35]
    assert all(v.effective_n == 100 for v in cells)


def test_compare_waves_preserves_metadata_and_skips_delta():
    df = pd.DataFrame({"answer": ["no"] * 25 + ["yes"] * 25, "weight": 10000})
    waves = WaveSet("tracker", [Wave(str(year), date(year, 1, 1), df) for year in (2022, 2024)])
    chain = waves.compare_chain("answer", weight_var="weight")
    column_proportion_test(chain)
    assert _flags(chain) == {year: [("no", None), ("yes", None)] for year in ("2022", "2024")}
    assert chain.views["2022"][0].effective_n == 50
    assert all(v.sig_flag is None for v in chain.views[chain.delta_column])


def test_kish_n_excludes_missing_answers_and_is_scale_invariant():
    df = pd.DataFrame({"answer": ["yes", "no", None], "grp": "A", "weight": [1, 3, 100]})
    for scale in (1, 10000):
        chain = build_chain(df.assign(weight=df.weight * scale), "answer", ["grp"], weight_var="weight")
        cells = chain.views["grp=A"]
        assert all(v.effective_n == pytest.approx(1.6) for v in cells)
        assert all(v.base == 104 * scale for v in cells)


def test_proportion_test_refuses_unknown_sample_sizes():
    chain = Chain("answer", ["grp"], {
        "A": [View("yes", 1000000, 600000, pct=0.6)],
        "B": [View("yes", 1000000, 500000, pct=0.5)],
    }, TableType.CROSS_TAB)
    with pytest.raises(SignificanceError, match="effective_n"):
        column_proportion_test(chain)


def test_mean_omits_missing_values_and_zero_weights(monkeypatch):
    monkeypatch.setattr(crosstab, "_critical_value", lambda n: 2.0)
    df = pd.DataFrame({
        "question": "a", "grp": "A", "score": [1, 5, None, 100], "weight": [1, 1, 100, 0],
    })
    cell = build_chain(df, "question", ["grp"], metric="score", weight_var="weight",
                       table_type=TableType.MEAN_SCALE).views["grp=A"][0]
    assert cell.count == 3
    assert cell.ci == pytest.approx(4)
    assert cell.effective_n == 2
    assert cell.base == 102


def test_weighted_small_effective_sample_without_scipy_refuses(monkeypatch):
    monkeypatch.setattr(crosstab, "_SCIPY_T_AVAILABLE", False)
    df = pd.DataFrame({"question": "a", "grp": "A", "score": range(100),
                       "weight": [10000] + [0.1] * 99})
    with pytest.raises(SignificanceError, match="requires scipy"):
        build_chain(df, "question", ["grp"], metric="score", weight_var="weight",
                    table_type=TableType.MEAN_SCALE)


def test_large_mean_sample_without_scipy_uses_normal_critical_value(monkeypatch):
    monkeypatch.setattr(crosstab, "_SCIPY_T_AVAILABLE", False)
    df = pd.DataFrame({"question": "a", "grp": "A", "score": [1, 5] * 20})
    cell = build_chain(df, "question", ["grp"], metric="score",
                       table_type=TableType.MEAN_SCALE).views["grp=A"][0]
    assert cell.count == 3
    assert cell.ci == pytest.approx(1.96 * sqrt(4 / 39))


@pytest.mark.parametrize("weight", [-1, float("nan"), float("inf")])
def test_invalid_survey_weights_raise(weight):
    df = pd.DataFrame({"answer": ["yes", "no"], "grp": "A", "weight": [1, weight]})
    with pytest.raises(crosstab.CrosstabInputError, match="finite and nonnegative"):
        build_chain(df, "answer", ["grp"], weight_var="weight")


def test_multiple_response_metric_sum_refuses_proportion_test():
    """MULTIPLE_RESPONSE must gate effective_n like the other count builders,
    so a metric-sum table refuses the proportion test instead of lettering
    dollar sums (sibling-path fix for #1478)."""
    df = pd.DataFrame({"item": ["x", "y"] * 50, "grp": ["A"] * 50 + ["B"] * 50,
                       "dollars": [10000.0] * 100})
    chain = build_chain(df, "item", ["grp"], metric="dollars",
                        table_type=TableType.MULTIPLE_RESPONSE)
    assert all(v.effective_n is None for vs in chain.views.values() for v in vs)
    with pytest.raises(SignificanceError, match="effective_n"):
        column_proportion_test(chain)


def test_zero_weight_rows_are_not_chi_square_respondents():
    """Zero-weight rows are excluded from the weighted display, so they must
    also be excluded from the chi-square respondent base (sibling-path fix
    for #1478)."""
    df = pd.DataFrame({"ans": ["x"] * 30 + ["y"] * 60, "grp": ["A"] * 30 + ["B"] * 30 + ["A"] * 30,
                       "w": [1.0] * 60 + [0.0] * 30})
    cells = {v.metric: v for v in build_chain(df, "ans", ["grp"], weight_var="w").views["grp=A"]}
    assert cells["y"].count == 0.0
    assert cells["y"].respondent_count == 0
