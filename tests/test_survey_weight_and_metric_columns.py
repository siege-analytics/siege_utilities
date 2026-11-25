"""Weight and metric column dtypes and labels in build_chain (#1478).

Arrow-backed bool and Fraction weights, Decimal metric columns, complex values
in object weight columns, a weight column that is also a break or row
variable, and falsy weight-column labels. Each test compares against the
table built from plain float64 columns, or expects CrosstabInputError.
"""
import decimal
import fractions

import numpy as np
import pandas as pd
import pytest

from siege_utilities.reporting.pages.page_models import TableType
from siege_utilities.survey.crosstab import CrosstabInputError, build_chain

ANSWER = ["yes", "no", "yes", "no", "yes", "no"]
GRP = ["A", "A", "A", "B", "B", "B"]
FLOAT = [1.0, 2.0, 1.0, 1.0, 1.0, 3.0]
VALUES = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
FLAGS = [True, False, True, True, True, False]


def _frame(weights, **extra):
    df = pd.DataFrame({"answer": ANSWER, "grp": GRP})
    for name, column in extra.items():
        df[name] = column
    df["w"] = weights
    return df


def _cells(chain):
    return {
        key: [
            (v.metric, round(v.count, 6), None if v.pct is None else round(v.pct, 6),
             round(v.base, 6), None if v.effective_n is None else round(v.effective_n, 6))
            for v in views
        ]
        for key, views in chain.views.items()
    }


def _by_level(chain):
    return {key.split("=", 1)[1]: cells for key, cells in _cells(chain).items()}


def _decimals(values):
    return pd.Series([decimal.Decimal(str(v)) for v in values], dtype=object)


# --- bool weights stored in an Arrow-backed column ---------------------------

def test_arrow_bool_weights_match_numpy_bool_weights():
    pytest.importorskip("pyarrow")
    expected = build_chain(_frame(FLAGS), "answer", ["grp"], weight_var="w")
    actual = build_chain(_frame(pd.array(FLAGS, dtype="bool[pyarrow]")),
                         "answer", ["grp"], weight_var="w")
    assert _cells(actual) == _cells(expected)


def test_categorical_bool_weights_still_raise():
    weights = pd.Categorical(FLAGS)
    with pytest.raises(CrosstabInputError, match="must be numeric"):
        build_chain(_frame(weights), "answer", ["grp"], weight_var="w")


# --- complex values in an object column --------------------------------------

@pytest.mark.parametrize("weights", [
    pytest.param(pd.Series([complex(w, 1) for w in FLOAT], dtype=object), id="all-complex"),
    pytest.param(pd.Series([complex(1, 5)] + FLOAT[1:], dtype=object), id="one-complex"),
    pytest.param(pd.Series([np.complex64(w + 1j) for w in FLOAT], dtype=object),
                 id="numpy-complex-scalars"),
])
def test_complex_values_in_an_object_weight_column_raise(weights):
    with pytest.raises(CrosstabInputError, match="must be numeric"):
        build_chain(_frame(weights), "answer", ["grp"], weight_var="w")


# --- Decimal metric column with weights --------------------------------------

@pytest.mark.parametrize("weights", [
    pytest.param(_decimals(FLOAT), id="decimal-weights"),
    pytest.param([1, 2, 1, 1, 1, 3], id="int-weights"),
    pytest.param(pd.array([1, 2, 1, 1, 1, 3], dtype="Int64"), id="Int64-weights"),
])
@pytest.mark.parametrize("table_type", [
    TableType.CROSS_TAB, TableType.SINGLE_RESPONSE, TableType.MULTIPLE_RESPONSE,
    TableType.LONGITUDINAL, TableType.RANKING, TableType.BANNER,
])
def test_decimal_metric_with_weights_matches_float_metric(weights, table_type):
    expected = build_chain(_frame(FLOAT, value=VALUES), "answer", ["grp"],
                           metric="value", weight_var="w", table_type=table_type)
    actual = build_chain(_frame(weights, value=_decimals(VALUES)), "answer", ["grp"],
                         metric="value", weight_var="w", table_type=table_type)
    assert _cells(actual) == _cells(expected)


def test_decimal_respondent_indicator_keeps_respondent_counts():
    expected = build_chain(_frame(FLOAT, value=[1.0] * 6), "answer", ["grp"],
                           metric="value", weight_var="w")
    actual = build_chain(_frame(_decimals(FLOAT), value=_decimals([1] * 6)), "answer", ["grp"],
                         metric="value", weight_var="w")
    assert _cells(actual) == _cells(expected)
    for key, views in expected.views.items():
        assert [v.respondent_count for v in actual.views[key]] == \
            [v.respondent_count for v in views]


def test_build_chain_leaves_a_decimal_metric_column_unchanged():
    df = _frame(_decimals(FLOAT), value=_decimals(VALUES))
    before = df.copy(deep=True)
    build_chain(df, "answer", ["grp"], metric="value", weight_var="w")
    assert df.equals(before)
    assert list(df.columns) == list(before.columns)
    assert isinstance(df["value"].iloc[0], decimal.Decimal)


# --- fractions.Fraction weights ----------------------------------------------

def test_fraction_weights_match_float_weights():
    weights = pd.Series([fractions.Fraction(w) for w in FLOAT], dtype=object)
    expected = build_chain(_frame(FLOAT), "answer", ["grp"], weight_var="w")
    actual = build_chain(_frame(weights), "answer", ["grp"], weight_var="w")
    assert _cells(actual) == _cells(expected)


def test_fraction_weights_do_not_let_timedelta_values_through():
    weights = pd.Series([np.timedelta64(5, "ns")] + [fractions.Fraction(w) for w in FLOAT[1:]],
                        dtype=object)
    with pytest.raises(CrosstabInputError, match="must be numeric"):
        build_chain(_frame(weights), "answer", ["grp"], weight_var="w")


def test_timestamp_objects_in_an_object_weight_column_still_raise():
    weights = pd.Series([pd.Timestamp("2024-01-01")] * 6, dtype=object)
    with pytest.raises(CrosstabInputError, match="must be numeric"):
        build_chain(_frame(weights), "answer", ["grp"], weight_var="w")


# --- the weight column is also a break or row variable -----------------------

@pytest.mark.parametrize("weights, keys", [
    pytest.param([1, 2, 1, 1, 1, 3], {"w=1", "w=2", "w=3"}, id="int"),
    pytest.param(FLAGS, {"w=True", "w=False"}, id="bool"),
    pytest.param(_decimals([1, 2, 1, 1, 1, 3]), {"w=1", "w=2", "w=3"}, id="decimal"),
])
def test_weight_column_used_as_break_keeps_its_labels(weights, keys):
    chain = build_chain(_frame(weights), "answer", ["w"], weight_var="w")
    assert set(chain.views) == keys


def test_weight_column_used_as_row_keeps_its_labels():
    chain = build_chain(_frame([1, 2, 1, 1, 1, 3]), "w", ["grp"], weight_var="w")
    assert [v.metric for v in chain.views["grp=A"]] == ["1", "2"]


def test_decimal_metric_used_as_break_keeps_its_labels():
    df = _frame(_decimals(FLOAT), value=_decimals([10, 20, 10, 20, 10, 20]))
    chain = build_chain(df, "answer", ["value"], metric="value", weight_var="w")
    assert set(chain.views) == {"value=10", "value=20"}


def test_frame_that_already_has_the_private_weight_column_name():
    df = _frame(FLOAT)
    df["__build_chain_weight__"] = ["x", "x", "y", "y", "x", "y"]
    chain = build_chain(df, "answer", ["__build_chain_weight__"], weight_var="w")
    assert set(chain.views) == {"__build_chain_weight__=x", "__build_chain_weight__=y"}
    assert chain.views["__build_chain_weight__=x"][0].base == pytest.approx(4.0)


# --- a frame read without a header, weight in column 0 -----------------------

def test_weight_in_column_label_zero_is_applied():
    named = pd.DataFrame({"w": FLOAT, "answer": ANSWER, "grp": GRP})
    unnamed = named.set_axis([0, 1, 2], axis=1)  # as read with header=None
    expected = build_chain(named, "answer", ["grp"], weight_var="w")
    actual = build_chain(unnamed, 1, [2], weight_var=0)
    assert _by_level(actual) == _by_level(expected)


def test_weight_in_column_label_zero_is_applied_to_a_mean_scale_base():
    named = pd.DataFrame({"w": [2.0, 1.0, 1.0], "q": "a", "grp": "A", "score": [1.0, 5.0, 9.0]})
    unnamed = named.set_axis([0, 1, 2, 3], axis=1)
    expected = build_chain(named, "q", ["grp"], metric="score", weight_var="w",
                           table_type=TableType.MEAN_SCALE).views["grp=A"][0]
    actual = build_chain(unnamed, 1, [2], metric=3, weight_var=0,
                         table_type=TableType.MEAN_SCALE).views["2=A"][0]
    assert actual.count == pytest.approx(expected.count)
    assert actual.base == pytest.approx(expected.base)
    assert actual.ci == pytest.approx(expected.ci)


# --- an integer too large for float64 ----------------------------------------

def test_weight_too_large_for_float64_raises_crosstab_input_error():
    weights = pd.Series([10 ** 400] + FLOAT[1:], dtype=object)
    with pytest.raises(CrosstabInputError):
        build_chain(_frame(weights), "answer", ["grp"], weight_var="w")
