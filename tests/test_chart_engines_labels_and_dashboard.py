"""Chart data/artist regressions for #1556; no rendering or image comparisons."""

from copy import deepcopy
from html import unescape
from types import SimpleNamespace

import pandas as pd
import pytest

from siege_utilities.reporting.engines import bar_engine, composite_engine, stats_engine


class ChartHarness(bar_engine.BarChartMixin, composite_engine.CompositeChartMixin):
    """Return constructed figures before the ReportLab/rendering boundary."""

    default_dpi = 72
    default_colors = {'primary': '#0077cc'}
    color_palette = ['#0077cc', '#ff6633', '#33aa55']

    def _matplotlib_to_reportlab_image(self, fig, width, height):
        return fig

    def _create_placeholder_chart(self, width, height, message):
        fig, ax = bar_engine.plt.subplots(figsize=(width, height))
        ax.text(0.5, 0.5, message)
        return fig


@pytest.fixture
def charts(monkeypatch):
    # Text heatmap tests still run without matplotlib; only artist tests skip.
    figure_module = pytest.importorskip('matplotlib.figure')
    figures = []

    def subplots(rows=1, cols=1, **kwargs):
        fig = figure_module.Figure(**kwargs)
        figures.append(fig)
        return fig, fig.subplots(rows, cols)

    plotting = SimpleNamespace(subplots=subplots, tight_layout=lambda: None,
                               close=lambda fig: fig.clear())
    for module in (bar_engine, composite_engine):
        monkeypatch.setattr(module, 'plt', plotting)
        monkeypatch.setattr(module, 'MATPLOTLIB_AVAILABLE', True)
    yield ChartHarness()
    for fig in figures:
        fig.clear()


def legend_text(ax):
    legend = ax.get_legend()
    assert legend is not None
    return [text.get_text() for text in legend.get_texts()]


@pytest.mark.parametrize('values', [[10, 20], [-10, 20]])
def test_horizontal_labels_show_values_at_bar_ends(charts, values):
    fig = charts.create_bar_chart({'name': ['A', 'B'], 'value': values},
                                  'name', 'value', chart_type='horizontal')
    ax = fig.axes[0]
    assert [text.get_text() for text in ax.texts] == [str(value) for value in values]
    for bar, text in zip(ax.patches, ax.texts):
        assert text.get_position() == pytest.approx(
            (bar.get_x() + bar.get_width(), bar.get_y() + bar.get_height() / 2))


@pytest.mark.parametrize('values', [[0.48, 0.52], [12.4, 20.6], [0.00012, 0.00058]])
def test_vertical_labels_preserve_fractional_values(charts, values):
    fig = charts.create_bar_chart({'name': ['A', 'B'], 'value': values}, 'name', 'value')
    ax = fig.axes[0]
    assert [float(text.get_text()) for text in ax.texts] == pytest.approx(values)
    for bar, text in zip(ax.patches, ax.texts):
        assert text.get_position() == pytest.approx(
            (bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height()))


def test_caller_can_format_shares_as_percentages(charts):
    fig = charts.create_bar_chart({'name': ['A', 'B'], 'value': [0.48, 0.52]},
                                  'name', 'value', value_format='.1%')
    assert [text.get_text() for text in fig.axes[0].texts] == ['48.0%', '52.0%']


@pytest.mark.parametrize('orientation', ['bar', 'horizontal'])
def test_grouped_bars_sum_repeated_pairs_and_omit_missing_pairs(charts, orientation):
    data = pd.DataFrame({'name': ['A', 'A', 'A', 'B'],
                         'group': ['First', 'Second', 'First', 'First'],
                         'value': [10, 20, 5, 30]})
    fig = charts.create_bar_chart(data, 'name', 'value', group_by='group',
                                  chart_type=orientation)
    ax = fig.axes[0]
    assert legend_text(ax) == ['First', 'Second']
    assert len(ax.containers) == 2
    assert [text.get_text() for text in ax.texts] == ['15', '30', '20']
    first, second = ax.containers[0][0], ax.containers[1][0]
    if orientation == 'horizontal':
        assert first.get_y() + first.get_height() == pytest.approx(second.get_y())
        assert [text.get_text() for text in ax.get_yticklabels()] == ['A', 'B']
    else:
        assert first.get_x() + first.get_width() == pytest.approx(second.get_x())
        assert [text.get_text() for text in ax.get_xticklabels()] == ['A', 'B']


def chart_config(kind, *, datasets=None, title='Chart'):
    return {'type': kind, 'title': title, 'data': {
        'labels': ['A', 'B'],
        'datasets': datasets if datasets is not None else [{'data': [10, 20]}],
    }}


def test_dashboard_pie_consumes_the_shared_datasets_schema(charts):
    config = chart_config('pie')
    original = deepcopy(config)
    fig = charts.create_dashboard([config], layout='1x1')
    ax = fig.axes[0]
    assert len(ax.patches) == 2
    assert [wedge.theta2 - wedge.theta1 for wedge in ax.patches] == pytest.approx([120, 240])
    assert legend_text(ax) == ['Dataset 1: A', 'Dataset 1: B']
    assert config == original


@pytest.mark.parametrize('kind', ['bar', 'line', 'pie', 'scatter'])
def test_dashboard_plots_every_dataset_and_labels_the_legend(charts, kind):
    datasets = [{'label': 'First', 'data': [10, 20]},
                {'label': 'Second', 'data': [30, 40]}]
    fig = charts.create_dashboard([chart_config(kind, datasets=datasets)], layout='1x1')
    ax = fig.axes[0]
    if kind == 'pie':
        assert len(ax.patches) == 4
        assert legend_text(ax) == ['First: A', 'First: B', 'Second: A', 'Second: B']
        assert ax.patches[0].r > ax.patches[2].r
    else:
        assert legend_text(ax) == ['First', 'Second']
        if kind == 'bar':
            assert len(ax.containers) == 2
            assert [bar.get_height() for bar in ax.patches] == [10, 20, 30, 40]
            assert ax.containers[0][0].get_x() != ax.containers[1][0].get_x()
        elif kind == 'line':
            assert [list(line.get_ydata()) for line in ax.lines] == [[10, 20], [30, 40]]
        else:
            assert [list(series.get_offsets()[:, 1]) for series in ax.collections] == [
                [10, 20], [30, 40]]


def test_dashboard_overflow_names_every_chart_that_would_be_dropped(charts):
    configs = [chart_config('bar', title=name) for name in ['Kept', 'Lost one', 'Lost two']]
    with pytest.raises(RuntimeError, match='overflow.*Lost one.*Lost two'):
        charts.create_dashboard(configs, layout='1x1')


def test_dashboard_unknown_type_names_the_chart(charts):
    with pytest.raises(RuntimeError, match='Unknown chart type.*radar.*Traffic'):
        charts.create_dashboard([chart_config('radar', title='Traffic')], layout='1x1')


@pytest.mark.parametrize('kind', ['bar', 'line', 'pie', 'scatter'])
def test_dashboard_invalid_dataset_raises_instead_of_returning_partial_chart(charts, kind):
    datasets = [{'label': 'Valid', 'data': [10, 20]}, {'label': 'Incomplete', 'data': [30]}]
    with pytest.raises(RuntimeError, match='Incomplete'):
        charts.create_dashboard([chart_config(kind, datasets=datasets)], layout='1x1')


def heatmap_lines(data):
    return unescape(stats_engine.StatsChartMixin().create_heatmap_text_chart(
        pd.DataFrame(data, columns=['row', 'column', 'value']), 'column', 'row', 'value',
    )).split('<br/>')


def test_text_heatmap_missing_cell_differs_from_zero_and_headers_align():
    lines = heatmap_lines([('r1', 'Monday', 0), ('r1', 'Tuesday', 5), ('r2', 'Monday', 10)])
    header = lines[3]
    rows = [line for line in lines if line.startswith(('r1 ', 'r2 '))]
    start = header.index('Mo')
    assert header.index('Tu') == start + 2
    assert rows[1][start:start + 2] == '██'
    zero = rows[0][start:start + 2]
    missing = rows[1][start + 2:start + 4]
    assert missing != zero
    assert missing == '··'
    assert 'Monday, Tuesday' in '\n'.join(lines)


def test_text_heatmap_missing_cells_do_not_lower_the_scale():
    lines = heatmap_lines([('r1', 'A', 10), ('r1', 'B', 15), ('r2', 'A', 20)])
    row = next(line for line in lines if line.startswith('r1 '))
    assert row[11:15] == '  ▒▒'


def test_text_heatmap_retains_entirely_missing_rows_and_columns():
    lines = heatmap_lines([('r1', 'A', 0), ('r2', 'B', float('nan'))])
    row = next(line for line in lines if line.startswith('r2 '))
    assert row[11:] == '····'


@pytest.mark.parametrize('values,expected', [([0, 0], '0.0%'), ([1, float('nan')], 'n/a')])
def test_pie_legend_handles_zero_and_nan_totals(charts, values, expected):
    fig = charts.create_pie_chart({'label': ['A', 'B'], 'value': values}, 'label', 'value')
    ax = fig.axes[0]
    assert len(ax.tables) == 1
    table = ax.tables[0]
    assert [table[(row, 3)].get_text().get_text() for row in [1, 2]] == [expected, expected]
    assert ax.texts  # An explicit notice explains why there are no wedges.


# --- default value labels: fixed-point, never exponent notation ---------------

def _texts(fig):
    return [text.get_text() for text in fig.axes[0].texts]


@pytest.mark.parametrize('values,expected', [
    ([1234567.89, 2345678.12], ['1,234,567.89', '2,345,678.12']),
    ([1000000, 0.5], ['1,000,000.0', '0.5']),
    ([12345678.9, 3.0], ['12,345,678.9', '3.0']),
    ([1500000.0, 2500000.0], ['1,500,000', '2,500,000']),
])
def test_million_scale_vertical_labels_stay_fixed_point(charts, values, expected):
    fig = charts.create_bar_chart({'name': ['A', 'B'], 'value': values}, 'name', 'value')
    assert _texts(fig) == expected


def test_million_scale_horizontal_labels_stay_fixed_point(charts):
    fig = charts.create_bar_chart({'name': ['A', 'B'], 'value': [1234567.89, 2345678.12]},
                                  'name', 'value', chart_type='horizontal')
    assert _texts(fig) == ['1,234,567.89', '2,345,678.12']


def test_million_scale_grouped_labels_stay_fixed_point(charts):
    data = pd.DataFrame({'name': ['A', 'A', 'B', 'B'], 'group': ['x', 'y', 'x', 'y'],
                         'value': [1234567.89, 2345678.12, 3456789.5, 4567890.25]})
    fig = charts.create_bar_chart(data, 'name', 'value', group_by='group')
    assert _texts(fig) == ['1,234,567.89', '3,456,789.50', '2,345,678.12', '4,567,890.25']


def test_million_scale_facade_bar_labels_stay_fixed_point():
    """The report facades call create_bar_chart with no value_format."""
    pytest.importorskip('matplotlib')
    from siege_utilities import ChartGenerator
    from siege_utilities.reporting._facade_content import _chart_images

    generator = ChartGenerator()
    figures = []

    def keep(fig, width, height):
        figures.append(fig)
        return 'IMG'

    generator._matplotlib_to_reportlab_image = keep
    config = {'type': 'bar', 'title': 'Revenue by channel',
              'data': {'labels': ['Organic', 'Paid'],
                       'datasets': [{'label': 'Revenue', 'data': [1234567.89, 2345678.12]}]}}
    assert _chart_images(config, SimpleNamespace(chart_generator=generator)) == ['IMG']
    assert _texts(figures[0]) == ['1,234,567.89', '2,345,678.12']


@pytest.mark.parametrize('values,expected', [
    ([1500, 2500], ',.0f'),
    ([12.4, 20.6], ',.1f'),
    ([100 / 3, 200 / 3], ',.2f'),
    ([0.00012, 0.00058], ',.5f'),
    ([1.0, float('nan')], ',.0f'),
])
def test_default_label_format_uses_the_fewest_decimals(values, expected):
    assert bar_engine.BarChartMixin._default_value_format(values) == expected


@pytest.mark.parametrize('values,expected', [
    # More than two decimals only when the smallest non-zero value is below 0.1.
    ([0.05, 1 / 3], ',.3f'),
    ([0.012345], ',.3f'),
    ([0.4832, 0.5168], ',.2f'),
    # Up to two significant digits of the smallest value, not more.
    ([0.000123456], ',.5f'),
    # Float artefacts within the tolerance do not add decimals.
    ([0.1 + 0.2, 0.3], ',.1f'),
    # Relative tolerance of one billionth: cents vanish at fifty million, and
    # values below 1e-9 are shown as 0.
    ([50000000.04, 2.0], ',.0f'),
    ([2e-10, 5e-10], ',.0f'),
    # The most decimals the rule produces is nine.
    ([5e-9], ',.9f'),
])
def test_default_label_format_follows_the_documented_limits(values, expected):
    assert bar_engine.BarChartMixin._default_value_format(values) == expected


# --- text heatmap with pandas nullable dtypes ---------------------------------

@pytest.mark.parametrize('dtype', ['Int64', 'Float64'])
def test_text_heatmap_accepts_nullable_dtypes(dtype):
    frame = pd.DataFrame([('r1', 'A', 1), ('r1', 'B', 5), ('r2', 'A', 10)],
                         columns=['row', 'column', 'value']).astype({'value': dtype})
    lines = unescape(stats_engine.StatsChartMixin().create_heatmap_text_chart(
        frame, 'column', 'row', 'value')).split('<br/>')
    row = next(line for line in lines if line.startswith('r2 '))
    assert row[11:13] == '██'
    assert next(line for line in lines if line.startswith('r2 '))[13:15] == '··'


# --- dashboard layouts, refusals and figure lifetime --------------------------

@pytest.mark.parametrize('layout', ['4', '2X2', (2, 2)])
def test_dashboard_layout_without_lowercase_x_is_a_2x2_grid(charts, layout):
    fig = charts.create_dashboard([chart_config('bar')], layout=layout)
    assert len(fig.axes) == 4
    assert [ax.get_visible() for ax in fig.axes] == [True, False, False, False]


def test_dashboard_layout_is_columns_by_rows(charts):
    fig = charts.create_dashboard([chart_config('bar')] * 3, layout='3x1')
    boxes = [ax.get_position() for ax in fig.axes]
    assert len(boxes) == 3
    assert len({round(box.y0, 6) for box in boxes}) == 1  # one row
    assert len({round(box.x0, 6) for box in boxes}) == 3  # three columns


def test_dashboard_error_names_the_untitled_chart_by_position(charts):
    def untitled(data):
        return {'type': 'bar', 'data': {'labels': ['A', 'B'], 'datasets': [{'data': data}]}}

    with pytest.raises(RuntimeError, match="'Chart 3'"):
        charts.create_dashboard([untitled([1, 2]), untitled([1, 2]), untitled([1]),
                                 untitled([1, 2])], layout='2x2')


@pytest.mark.parametrize('bad', [None, float('nan'), float('inf')])
def test_dashboard_refuses_non_finite_values(charts, bad):
    datasets = [{'label': 'Sessions', 'data': [10, bad]}]
    with pytest.raises(RuntimeError, match="Sessions.*finite"):
        charts.create_dashboard([chart_config('bar', datasets=datasets)], layout='1x1')


def test_dashboard_closes_its_figure_when_it_fails():
    plt = pytest.importorskip('matplotlib.pyplot')
    from siege_utilities import ChartGenerator

    before = set(plt.get_fignums())
    datasets = [{'label': 'Incomplete', 'data': [30]}]
    with pytest.raises(RuntimeError):
        ChartGenerator().create_dashboard([chart_config('bar', datasets=datasets)],
                                          layout='1x1')
    assert set(plt.get_fignums()) == before


def test_bar_chart_closes_its_figure_when_it_fails():
    plt = pytest.importorskip('matplotlib.pyplot')
    from siege_utilities import ChartGenerator

    before = set(plt.get_fignums())
    empty = pd.DataFrame({'name': [], 'group': [], 'value': []})
    with pytest.raises(RuntimeError):
        ChartGenerator().create_bar_chart(empty, x_column='name', y_column='value',
                                          group_by='group')
    assert set(plt.get_fignums()) == before
