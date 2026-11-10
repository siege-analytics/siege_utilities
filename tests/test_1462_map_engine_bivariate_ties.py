"""Tied-data coverage for the reporting map engine's bivariate colours (#1462)."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip('matplotlib')

from siege_utilities.reporting.engines.map_engine import MapChartMixin  # noqa: E402


TIED = [0, 0, 0, 0, 0, 0, 1, 2, 3, 4]


@pytest.fixture
def engine():
    return MapChartMixin()


def _levels(values):
    """Expected matrix level per row: actual qcut bins sampled low to high."""
    codes, edges = pd.qcut(
        pd.Series(values), 3, labels=False, duplicates='drop', retbins=True,
    )
    levels = np.rint(np.linspace(0, 2, len(edges) - 1)).astype(int)
    return levels[codes.to_numpy(dtype=int)]


def _expected(matrix, var1, var2):
    return list(matrix[_levels(var2), _levels(var1)])


@pytest.mark.parametrize('scheme', ['default', 'blue_red', 'green_orange'])
@pytest.mark.parametrize('var1,var2', [
    (TIED, list(range(10))),
    (list(range(10)), TIED),
    (TIED, TIED),
])
def test_tied_data_colours_use_both_palette_ends(engine, scheme, var1, var2):
    matrix = engine._create_bivariate_color_matrix(scheme)
    gdf = pd.DataFrame({'a': var1, 'b': var2})

    result = engine._apply_bivariate_colors(gdf, 'a', 'b', matrix)

    assert list(result['bivariate_color']) == _expected(matrix, var1, var2)
    # The tied axis keeps its lowest and highest palette colours.
    tied_levels = _levels(TIED)
    assert set(tied_levels) == {0, 2}


def test_untied_data_keeps_three_by_three_lookup(engine):
    matrix = engine._create_bivariate_color_matrix('default')
    values = list(range(9))
    gdf = pd.DataFrame({'a': values, 'b': values[::-1]})

    result = engine._apply_bivariate_colors(gdf, 'a', 'b', matrix)

    low_to_high = [0, 0, 0, 1, 1, 1, 2, 2, 2]
    expected = [matrix[b, a] for a, b in zip(low_to_high, low_to_high[::-1])]
    assert list(result['bivariate_color']) == expected


def test_missing_rows_stay_gray_with_tied_data(engine):
    matrix = engine._create_bivariate_color_matrix('default')
    gdf = pd.DataFrame({
        'a': TIED + [np.nan, 1.0],
        'b': list(range(10)) + [3.0, np.nan],
    })

    result = engine._apply_bivariate_colors(gdf, 'a', 'b', matrix)

    assert list(result['bivariate_color'].iloc[-2:]) == ['#cccccc', '#cccccc']
    assert list(result['bivariate_color'].iloc[:10]) == _expected(
        matrix, TIED, list(range(10)),
    )


@pytest.mark.parametrize('constant', ['a', 'b'])
def test_constant_axis_raises_value_error(engine, constant):
    matrix = engine._create_bivariate_color_matrix('default')
    gdf = pd.DataFrame({
        'a': [5.0] * 6 if constant == 'a' else list(range(6)),
        'b': [5.0] * 6 if constant == 'b' else list(range(6)),
    })

    with pytest.raises(ValueError, match=f"{constant}.*at least 2 classes"):
        engine._apply_bivariate_colors(gdf, 'a', 'b', matrix)


@pytest.mark.parametrize('single', ['a', 'b'])
def test_single_class_axis_raises_value_error(engine, single):
    # Ties that leave exactly one class are below the 2-class minimum too;
    # the all-constant case above leaves zero.
    matrix = engine._create_bivariate_color_matrix('default')
    gdf = pd.DataFrame({
        'a': [0] * 9 + [1] if single == 'a' else list(range(10)),
        'b': [0] * 9 + [1] if single == 'b' else list(range(10)),
    })

    with pytest.raises(ValueError, match=f"'{single}': ties leave 1 of 3 requested classes"):
        engine._apply_bivariate_colors(gdf, 'a', 'b', matrix)


def _tied_geodataframe(var1):
    gpd = pytest.importorskip('geopandas')
    pytest.importorskip('reportlab')
    box = pytest.importorskip('shapely.geometry').box
    return gpd.GeoDataFrame(
        {'id': list(range(10)), 'a': var1, 'b': list(range(10))},
        geometry=[box(i, 0, i + 1, 1) for i in range(10)],
    )


def test_matplotlib_bivariate_map_renders_tied_data():
    from reportlab.platypus import Image
    from siege_utilities.reporting.chart_generator import ChartGenerator

    gdf = _tied_geodataframe(TIED)

    image = ChartGenerator().create_bivariate_choropleth_matplotlib(
        gdf, gdf, 'id', 'a', 'b',
    )

    assert isinstance(image, Image)


def test_matplotlib_bivariate_map_reports_constant_axis():
    from siege_utilities.reporting.chart_generator import ChartGenerator

    gdf = _tied_geodataframe([7] * 10)

    with pytest.raises(RuntimeError, match="'a'.*at least 2 classes") as exc:
        ChartGenerator().create_bivariate_choropleth_matplotlib(
            gdf, gdf, 'id', 'a', 'b',
        )
    assert isinstance(exc.value.__cause__, ValueError)
