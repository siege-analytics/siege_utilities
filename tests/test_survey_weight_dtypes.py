"""Weight column dtypes and small effective samples in build_chain (#1478).

Decimal (from a database NUMERIC column), object-dtype floats, float32,
nullable Float64, int64 and bool weight columns are valid inputs and must give
the same table as float64 weights. A missing weight (NaN, None, pd.NA in a
nullable column), an infinite weight or a non-numeric column raises
CrosstabInputError instead of a raw NumPy or pandas error.

The conversion to float64 must not change anything else: a frame with integer
column labels (as read with header=None) keeps working with a weight column,
as in 6.0.0, and datetime, timedelta and complex weight columns raise
CrosstabInputError instead of being converted to numbers.
"""
import decimal

import numpy as np
import pandas as pd
import pytest

from siege_utilities.reporting.pages.page_models import TableType
from siege_utilities.survey.crosstab import CrosstabInputError, build_chain
from siege_utilities.survey.significance import chi_square_flag, column_proportion_test


def _frame(weights):
    return pd.DataFrame({
        "answer": ["yes", "no", "yes", "no", "yes", "no"],
        "grp": ["A", "A", "A", "B", "B", "B"],
    }).assign(w=weights)


def _cells(chain):
    return {
        key: {v.metric: (round(v.count, 6), round(v.pct, 6)) for v in views}
        for key, views in chain.views.items()
    }


FLOAT = [1.0, 2.0, 1.0, 1.0, 1.0, 3.0]


@pytest.mark.parametrize("weights", [
    pytest.param([decimal.Decimal(str(w)) for w in FLOAT], id="decimal-object"),
    pytest.param(pd.Series(FLOAT, dtype=object), id="float-object"),
    pytest.param(np.array(FLOAT, dtype="float32"), id="float32"),
    pytest.param(pd.array(FLOAT, dtype="Float64"), id="nullable-Float64"),
    pytest.param([1, 2, 1, 1, 1, 3], id="int64"),
])
def test_numeric_weight_dtypes_match_float64(weights):
    expected = build_chain(_frame(FLOAT), "answer", ["grp"], weight_var="w")
    actual = build_chain(_frame(weights), "answer", ["grp"], weight_var="w")
    assert _cells(actual) == _cells(expected)
    for key, views in expected.views.items():
        assert actual.views[key][0].effective_n == pytest.approx(views[0].effective_n)
    column_proportion_test(actual)
    chi_square_flag(actual)


def test_bool_weights_act_as_zero_one_weights():
    flags = [True, True, False, True, True, True]
    expected = build_chain(_frame([float(f) for f in flags]), "answer", ["grp"], weight_var="w")
    actual = build_chain(_frame(flags), "answer", ["grp"], weight_var="w")
    assert _cells(actual) == _cells(expected)


@pytest.mark.parametrize("weights", [
    pytest.param([1.0, 2.0, np.nan, 1.0, 1.0, 3.0], id="float-nan"),
    pytest.param(pd.array([1.0, 2.0, pd.NA, 1.0, 1.0, 3.0], dtype="Float64"), id="Float64-NA"),
    pytest.param(pd.array([1, 2, pd.NA, 1, 1, 3], dtype="Int64"), id="Int64-NA"),
    pytest.param([1.0, 2.0, None, 1.0, 1.0, 3.0], id="object-None"),
    pytest.param([1.0, 2.0, np.inf, 1.0, 1.0, 3.0], id="inf"),
    pytest.param(["a", "b", "c", "d", "e", "f"], id="text"),
])
def test_missing_or_non_numeric_weights_raise_crosstab_input_error(weights):
    with pytest.raises(CrosstabInputError):
        build_chain(_frame(weights), "answer", ["grp"], weight_var="w")


@pytest.mark.parametrize("scores, weights", [
    pytest.param([1.0, 5.0], [100.0, 1.0], id="dominant-weight"),
    pytest.param([3.0, 3.0], [1.0, 1e-9], id="near-zero-weight"),
])
def test_mean_scale_ci_is_not_reported_below_two_effective_respondents(scores, weights):
    df = pd.DataFrame({"question": "a", "grp": "A", "score": scores, "weight": weights})
    cell = build_chain(df, "question", ["grp"], metric="score", weight_var="weight",
                       table_type=TableType.MEAN_SCALE).views["grp=A"][0]
    assert 1 < cell.effective_n < 2
    assert cell.ci is None


def _cells_by_level(chain):
    # Cell keys are "<label>=<level>"; drop the label so frames that differ
    # only in their column labels can be compared.
    return {key.split("=", 1)[1]: cells for key, cells in _cells(chain).items()}


def test_integer_column_labels_work_with_a_weight_column():
    named = _frame(FLOAT)
    unnamed = named.set_axis([1, 2, 3], axis=1)  # as read with header=None
    expected = build_chain(named, "answer", ["grp"], weight_var="w")
    actual = build_chain(unnamed, 1, [2], weight_var=3)
    assert _cells_by_level(actual) == _cells_by_level(expected)


def test_integer_column_labels_work_for_a_weighted_mean_scale():
    named = pd.DataFrame({"q": "a", "grp": "A", "score": [1.0, 5.0, 9.0], "w": [1.0, 0.5, 0.5]})
    unnamed = named.set_axis([1, 2, 3, 4], axis=1)
    expected = build_chain(named, "q", ["grp"], metric="score", weight_var="w",
                           table_type=TableType.MEAN_SCALE).views["grp=A"][0]
    actual = build_chain(unnamed, 1, [2], metric=3, weight_var=4,
                         table_type=TableType.MEAN_SCALE).views["2=A"][0]
    assert actual.count == pytest.approx(expected.count)
    assert actual.ci == pytest.approx(expected.ci)


@pytest.mark.parametrize("weights", [
    pytest.param(pd.to_datetime([f"2024-01-0{d}" for d in range(1, 7)]), id="datetime64"),
    pytest.param(pd.to_timedelta([1, 2, 1, 1, 1, 3], unit="D"), id="timedelta64"),
    pytest.param([complex(w, 1) for w in FLOAT], id="complex"),
])
def test_datetime_timedelta_and_complex_weights_raise_crosstab_input_error(weights):
    with pytest.raises(CrosstabInputError, match="must be numeric"):
        build_chain(_frame(weights), "answer", ["grp"], weight_var="w")


def test_build_chain_leaves_the_callers_weight_column_unchanged():
    df = _frame([decimal.Decimal(str(w)) for w in FLOAT])
    before = df.copy(deep=True)
    build_chain(df, "answer", ["grp"], weight_var="w")
    assert df.equals(before)
    assert isinstance(df["w"].iloc[0], decimal.Decimal)
