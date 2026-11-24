"""Weight column dtypes and small effective samples in build_chain (#1478).

Decimal (from a database NUMERIC column), object-dtype floats, float32,
nullable Float64, int64 and bool weight columns are valid inputs and must give
the same table as float64 weights. A missing weight (NaN, None, pd.NA in a
nullable column), an infinite weight or a non-numeric column raises
CrosstabInputError instead of a raw NumPy or pandas error.
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
