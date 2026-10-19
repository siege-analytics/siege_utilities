"""Regression coverage for quantile classes dropped by ties (#1462)."""

import numpy as np
import pytest

gpd = pytest.importorskip('geopandas')
matplotlib = pytest.importorskip('matplotlib')
matplotlib.use('Agg')
plt = pytest.importorskip('matplotlib.pyplot')
box = pytest.importorskip('shapely.geometry').box
to_rgba = matplotlib.colors.to_rgba

from siege_utilities.geo.choropleth import (  # noqa: E402
    BIVARIATE_COLOR_SCHEMES,
    _compute_bivariate_classes,
    create_bivariate_analysis,
    create_bivariate_choropleth,
    create_bivariate_crosstab,
    verify_bivariate_classification,
)


@pytest.fixture(params=['a', 'b', 'both'])
def tied_gdf(request):
    """Exercise a reduced x axis, y axis, and both axes."""
    tied = [0, 0, 0, 0, 0, 0, 1, 2, 3, 4]
    return gpd.GeoDataFrame(
        {
            'a': tied if request.param in ('a', 'both') else list(range(10)),
            'b': tied if request.param in ('b', 'both') else list(range(10)),
        },
        geometry=[box(i, 0, i + 1, 1) for i in range(10)],
        crs='EPSG:3857',
    )


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close('all')


def test_combined_index_uses_actual_grid_size(tied_gdf):
    classified, x_breaks, y_breaks = _compute_bivariate_classes(
        tied_gdf, 'a', 'b', n_classes=3,
    )
    # The final feature is high on both axes, including the reduced axis.
    assert classified['_bivar_class'].iloc[-1] == (
        (len(x_breaks) - 1) * (len(y_breaks) - 1) - 1
    )


def test_verification_reports_reduced_classes(tied_gdf):
    result = verify_bivariate_classification(tied_gdf, 'a', 'b', n_classes=3)

    assert result['valid'] is False
    assert result['classified_units'] == len(tied_gdf)
    for name in ('a', 'b'):
        if tied_gdf[name].max() == 4:
            assert any(
                f"Variable '{name}' has 2 quantile classes; expected 3" in error
                for error in result['errors']
            )


@pytest.mark.parametrize('render', [False, True])
def test_crosstab_uses_actual_class_counts(tied_gdf, render):
    result = create_bivariate_crosstab(
        tied_gdf, 'a', 'b', n_classes=3, render=render,
    )
    ct = result[0] if render else result
    expected_shape = tuple(2 if tied_gdf[name].max() == 4 else 3 for name in ('b', 'a'))
    assert ct.shape == expected_shape
    assert ct.to_numpy().sum() == len(tied_gdf)
    if render:
        _, fig, ax = result
        fig.canvas.draw()
        assert len(ax.get_xticks()) == len(ax.get_xticklabels()) == ct.shape[1]
        assert len(ax.get_yticks()) == len(ax.get_yticklabels()) == ct.shape[0]
        np.testing.assert_allclose(
            ax.patches[-1].get_facecolor(),
            to_rgba(BIVARIATE_COLOR_SCHEMES['purple_blue'][-1]),
        )


def test_map_high_values_and_legend_share_colors(tied_gdf):
    fig, (map_ax, legend_ax) = create_bivariate_choropleth(
        tied_gdf, 'a', 'b', n_classes=3,
    )
    fig.canvas.draw()
    _, x_breaks, y_breaks = _compute_bivariate_classes(tied_gdf, 'a', 'b', 3)
    legend = legend_ax.images[0]
    assert legend.get_array().shape == (len(y_breaks) - 1, len(x_breaks) - 1)
    assert len(legend_ax.get_xticks()) == len(legend_ax.get_xticklabels()) == len(x_breaks)
    assert len(legend_ax.get_yticks()) == len(legend_ax.get_yticklabels()) == len(y_breaks)
    high_color = to_rgba(BIVARIATE_COLOR_SCHEMES['purple_blue'][-1])
    np.testing.assert_allclose(map_ax.collections[0].get_facecolors()[-1], high_color)
    np.testing.assert_allclose(legend.to_rgba(legend.get_array())[-1, -1], high_color)


def test_analysis_renders_all_artifacts_with_ties(tied_gdf):
    # The orchestrator always calls create_bivariate_crosstab(render=True).
    result = create_bivariate_analysis(tied_gdf, 'a', 'b', n_classes=3)

    assert result.verification['valid'] is False
    assert result.crosstab.to_numpy().sum() == len(tied_gdf)
    for fig in (result.bivariate_fig, result.crosstab_fig, result.companion_fig):
        fig.canvas.draw()


@pytest.mark.parametrize('values, count', [([0] * 10, 0), ([0] * 9 + [1], 1)])
@pytest.mark.parametrize('render_artifact', ['map', 'crosstab', 'analysis'])
def test_degenerate_axes_report_clear_errors(values, count, render_artifact):
    gdf = gpd.GeoDataFrame(
        {'a': values, 'b': list(range(10))},
        geometry=[box(i, 0, i + 1, 1) for i in range(10)],
        crs='EPSG:3857',
    )
    verification = verify_bivariate_classification(gdf, 'a', 'b', n_classes=3)
    assert verification['valid'] is False
    assert any(f"'a' has {count} quantile classes" in error
               for error in verification['errors'])
    ct = create_bivariate_crosstab(gdf, 'a', 'b', n_classes=3)
    assert ct.shape == (3, count)

    with pytest.raises(ValueError, match='Cannot render bivariate quantiles'):
        if render_artifact == 'map':
            create_bivariate_choropleth(gdf, 'a', 'b', n_classes=3)
        elif render_artifact == 'crosstab':
            create_bivariate_crosstab(gdf, 'a', 'b', n_classes=3, render=True)
        else:
            create_bivariate_analysis(gdf, 'a', 'b', n_classes=3)
    assert not plt.get_fignums()


def test_verification_reports_unpopulated_bins():
    gdf = gpd.GeoDataFrame({'a': [0, 1], 'b': [0, 1]})
    result = verify_bivariate_classification(gdf, 'a', 'b', n_classes=3)

    assert result['valid'] is False
    assert len(result['var1_breaks']) == len(result['var2_breaks']) == 4
    assert any('2 populated quantile classes; expected 3' in error
               for error in result['errors'])
    ct = create_bivariate_crosstab(gdf, 'a', 'b', n_classes=3)
    assert ct.shape == (3, 3)
    assert ct.iloc[1].sum() == ct.iloc[:, 1].sum() == 0
    assert ct.to_numpy().sum() == 2


def test_requested_single_class_can_render():
    gdf = gpd.GeoDataFrame(
        {'a': [0, 0], 'b': [1, 1]},
        geometry=[box(i, 0, i + 1, 1) for i in range(2)],
        crs='EPSG:3857',
    )
    colors = ['#3b4994']
    fig, axes = create_bivariate_choropleth(
        gdf, 'a', 'b', n_classes=1, color_scheme=colors,
    )
    fig.canvas.draw()
    assert axes[1].images[0].get_array().shape == (1, 1)
    ct, ct_fig, _ = create_bivariate_crosstab(
        gdf, 'a', 'b', n_classes=1, color_scheme=colors, render=True,
    )
    ct_fig.canvas.draw()
    assert ct.shape == (1, 1)
    assert ct.iloc[0, 0] == 2
    assert verify_bivariate_classification(gdf, 'a', 'b', n_classes=1)['valid']
