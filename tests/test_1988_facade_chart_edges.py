"""Facade chart and sample-table edges found after #1734 (refs #1988).

- A DataFrame with repeated column labels must give sample-table rows with
  exactly as many cells as headers; label-based column selection repeated
  every column with that label.
- A NumPy complex value is not a real number and must raise the named
  non-numeric ``ValueError``; ``float()`` dropped its imaginary part.
- A ``Decimal`` written without a fractional part (``Decimal("88")``) reaches
  the pie legend as ``88``; ``Decimal("88.0")`` keeps its written fraction.
- The ``ValueError`` and ``OverflowError`` arms of the numeric conversion
  raise the named non-numeric ``ValueError``.
"""

import math
import numbers
import time
from decimal import Decimal
from fractions import Fraction
from unittest.mock import Mock

import pytest

pytest.importorskip("reportlab")
pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")
matplotlib_axes = pytest.importorskip("matplotlib.axes")
matplotlib_patches = pytest.importorskip("matplotlib.patches")

from siege_utilities.reporting._facade_content import _chart_images
from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator
from siege_utilities.reporting.report_generator import ReportGenerator


@pytest.fixture
def generator(tmp_path):
    return ReportGenerator("Acme", output_dir=tmp_path)


def _chart_config(kind, labels, values, title="Edge"):
    if kind == "pie":
        return {"type": kind, "title": title, "data": {"labels": labels, "data": values}}
    return {"type": kind, "title": title,
            "data": {"labels": labels, "datasets": [{"label": "Series", "data": values}]}}


def _sample_tables(tmp_path, df):
    payload = AnalyticsReportGenerator("Acme", output_dir=tmp_path)._process_dataframe_data(df, {})
    return [section for section in payload["sections"]
            if section["type"] == "table" and section["title"].startswith("Sample Data")]


def test_repeated_column_labels_give_rows_as_wide_as_the_headers(tmp_path):
    df = pd.DataFrame([["a", "b"], ["c", "d"]], columns=["name", "name"])

    (table,) = _sample_tables(tmp_path, df)

    assert table["headers"] == ["name", "name"]
    assert table["data"] == [["a", "b"], ["c", "d"]]


def test_repeated_labels_across_wide_column_groups_keep_their_positions(tmp_path):
    columns = ["name"] + [f"c{i}" for i in range(12)] + ["name"]
    df = pd.DataFrame([[f"r0-{i}" for i in range(14)], [f"r1-{i}" for i in range(14)]],
                      columns=columns)

    first, second = _sample_tables(tmp_path, df)

    assert first["headers"] == columns[:12]
    assert first["data"] == [[f"r{r}-{i}" for i in range(12)] for r in range(2)]
    assert second["headers"] == columns[12:]
    assert second["data"] == [[f"r{r}-{i}" for i in range(12, 14)] for r in range(2)]


@pytest.mark.parametrize("kind", ["bar", "line", "pie"])
@pytest.mark.parametrize("value", [np.complex64(1 + 2j), np.complex128(1 + 2j)],
                         ids=["complex64", "complex128"])
def test_numpy_complex_value_raises_the_named_non_numeric_error(generator, kind, value):
    config = _chart_config(kind, ["a", "b"], [value, 3], title="Complex")
    with pytest.raises(ValueError, match=rf"Facade {kind} chart 'Complex.*' has a non-numeric value"):
        _chart_images(config, generator)


def _pie_legend_values(monkeypatch, generator, values):
    tables = []
    real_table = matplotlib_axes.Axes.table

    def record(self, *args, **kwargs):
        tables.append(kwargs["cellText"])
        return real_table(self, *args, **kwargs)

    monkeypatch.setattr(matplotlib_axes.Axes, "table", record)
    labels = [f"l{i}" for i in range(len(values))]
    _chart_images(_chart_config("pie", labels, values, title="Legend"), generator)
    assert len(tables) == 1
    return [row[2] for row in tables[0]]


def test_pie_legend_prints_a_decimal_written_without_a_fraction_as_an_integer(generator, monkeypatch):
    # The legend formats the pie's value column, so one float in the series
    # makes every cell a float; this series is integral throughout.
    legend = _pie_legend_values(monkeypatch, generator, [Decimal("88"), Decimal("1E+3"), 7])

    assert legend == ["88", "1,000", "7"]


def test_pie_legend_keeps_the_written_fraction_of_a_decimal(generator, monkeypatch):
    # Decimal("88.0") is written with a fractional digit, so it stays a float.
    legend = _pie_legend_values(monkeypatch, generator, [Decimal("88.0")])

    assert legend == ["88.0"]


def _spy(generator, method):
    real = getattr(generator.chart_generator, method)
    spy = Mock(wraps=real)
    setattr(generator.chart_generator, method, spy)
    return spy


@pytest.mark.parametrize("value, expected_type", [
    (Decimal(2 ** 63 - 1), int),
    (Decimal(2 ** 63), float),
    (Decimal(-(2 ** 63)), int),
    (Decimal(-(2 ** 63) - 1), float),
], ids=["2**63-1", "2**63", "-2**63", "-2**63-1"])
def test_whole_number_decimal_is_an_int_only_within_the_64_bit_range(generator, value, expected_type):
    # The companion value is 0 so the series total equals the value itself.
    spy = _spy(generator, "create_bar_chart")

    images = _chart_images(_chart_config("bar", ["a", "b"], [value, 0], title="Big"), generator)

    assert len(images) == 1
    drawn = spy.call_args.args[0]["Value"][0]
    assert type(drawn) is expected_type
    assert drawn == float(value) if expected_type is float else drawn == int(value)


@pytest.mark.parametrize("kind", ["bar", "line", "pie"])
@pytest.mark.parametrize("value", [Decimal(2 ** 63 - 1), Decimal(2 ** 63), Decimal(2 ** 64)],
                         ids=["2**63-1", "2**63", "2**64"])
def test_large_whole_number_decimals_draw(generator, kind, value):
    config = _chart_config(kind, ["a", "b"], [value, 3], title="Big")

    assert len(_chart_images(config, generator)) == 1


def test_huge_decimal_exponent_draws_quickly(generator):
    spy = _spy(generator, "create_bar_chart")
    started = time.perf_counter()

    images = _chart_images(_chart_config("bar", ["a", "b"], [Decimal("1E+1000000"), 3], title="Huge"),
                           generator)

    assert time.perf_counter() - started < 5
    assert len(images) == 1
    assert spy.call_args.args[0]["Value"][0] == math.inf


def test_infinite_decimal_reaches_the_engine_as_a_float(generator):
    # is_finite() keeps Decimal("Infinity") off the int path, as before #1988.
    spy = _spy(generator, "create_bar_chart")

    _chart_images(_chart_config("bar", ["a", "b"], [Decimal("Infinity"), 3], title="Inf"), generator)

    drawn = spy.call_args.args[0]["Value"][0]
    assert type(drawn) is float and drawn == math.inf


def _capture_pie(monkeypatch):
    """Record the drawn wedge fractions and the legend's value and percent cells."""
    seen = {}
    real_pie = matplotlib_axes.Axes.pie
    real_table = matplotlib_axes.Axes.table

    def pie(self, x, *args, **kwargs):
        result = real_pie(self, x, *args, **kwargs)
        wedges = [p for p in self.patches if isinstance(p, matplotlib_patches.Wedge)]
        seen["fractions"] = [float(w.theta2 - w.theta1) / 360.0 for w in wedges]
        return result

    def table(self, *args, **kwargs):
        rows = kwargs["cellText"]
        seen["values"] = [row[2] for row in rows]
        seen["percent"] = [row[3] for row in rows]
        return real_table(self, *args, **kwargs)

    monkeypatch.setattr(matplotlib_axes.Axes, "pie", pie)
    monkeypatch.setattr(matplotlib_axes.Axes, "table", table)
    return seen


def _percent(fraction):
    return f"{fraction * 100:.1f}%"


@pytest.mark.parametrize("values, expected", [
    ([Decimal(6 * 10**18), Decimal(4 * 10**18)], [0.6, 0.4]),
    ([Decimal(9 * 10**18)] * 3, [1 / 3, 1 / 3, 1 / 3]),
    ([Decimal(5 * 10**18), Decimal(3 * 10**18)], [0.625, 0.375]),
    ([6 * 10**18, 4 * 10**18], [0.6, 0.4]),
], ids=["decimal-total-over-2**63", "three-decimals-over-2**63", "decimal-total-fits", "int-total-over-2**63"])
def test_pie_wedges_match_the_legend_percentages(generator, monkeypatch, values, expected):
    seen = _capture_pie(monkeypatch)
    labels = [f"l{i}" for i in range(len(values))]

    assert len(_chart_images(_chart_config("pie", labels, values, title="Big pie"), generator)) == 1

    assert seen["fractions"] == pytest.approx(expected, abs=1e-6)
    assert seen["percent"] == [_percent(fraction) for fraction in expected]


def test_pie_legend_keeps_whole_numbers_while_the_total_fits(generator, monkeypatch):
    seen = _capture_pie(monkeypatch)

    _chart_images(_chart_config("pie", ["a", "b"], [Decimal(5 * 10**18), Decimal(3 * 10**18)],
                                title="Fits"), generator)

    assert seen["values"] == ["5,000,000,000,000,000,000", "3,000,000,000,000,000,000"]


@pytest.mark.parametrize("values", [
    [Decimal("5"), 2**63],
    [Decimal(2**63 - 1), 2**63],
    [Decimal("5"), np.uint64(2**63 + 5)],
    [5, 2**63],
], ids=["D5-int", "Dmax-int", "D5-uint64", "int-int"])
def test_bar_with_an_int_beyond_64_bits_is_drawn_from_floats(generator, values):
    spy = _spy(generator, "create_bar_chart")

    images = _chart_images(_chart_config("bar", ["a", "b"], values, title="Mixed"), generator)

    assert len(images) == 1
    drawn = spy.call_args.args[0]["Value"]
    assert [type(value) for value in drawn] == [float, float]
    assert drawn == [float(value) for value in values]


def test_int_too_large_for_a_float_raises_the_named_error(generator):
    config = _chart_config("bar", ["a", "b"], [10**400, 3], title="Huge int")
    with pytest.raises(ValueError, match="Facade bar chart 'Huge int - Series' has a value too large to draw"):
        _chart_images(config, generator)


def test_zero_decimal_with_a_large_exponent_is_an_int_zero(generator):
    spy = _spy(generator, "create_bar_chart")
    started = time.perf_counter()

    _chart_images(_chart_config("bar", ["a", "b", "c"],
                                [Decimal("0E+18"), Decimal("0E+19"), Decimal("0E+1000000")], title="Zero"),
                  generator)

    assert time.perf_counter() - started < 5
    drawn = spy.call_args.args[0]["Value"]
    assert drawn == [0, 0, 0] and [type(value) for value in drawn] == [int, int, int]


class _RealWithoutFloat:
    """A registered Real whose float conversion fails with ValueError."""

    def __float__(self):
        raise ValueError("no float value")

    def __repr__(self):
        return "RealWithoutFloat()"


numbers.Real.register(_RealWithoutFloat)


@pytest.mark.parametrize("value, cause", [
    (Fraction(10 ** 400, 1), OverflowError),
    (_RealWithoutFloat(), ValueError),
], ids=["overflow", "value-error"])
def test_conversion_failures_raise_the_named_non_numeric_error(generator, value, cause):
    config = _chart_config("bar", ["a", "b"], [value, 3], title="Convert")

    with pytest.raises(ValueError, match="Facade bar chart 'Convert - Series' has a non-numeric value") as raised:
        _chart_images(config, generator)

    assert isinstance(raised.value.__cause__, cause)
