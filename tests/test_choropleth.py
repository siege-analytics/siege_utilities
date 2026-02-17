"""
Unit tests for the choropleth map creation module.

Tests create_choropleth, create_choropleth_comparison, create_classified_comparison,
create_bivariate_choropleth, save_map, and supporting constants.
"""

import pytest
import numpy as np
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
from shapely.geometry import box

from siege_utilities.geo.choropleth import (
    create_choropleth,
    create_choropleth_comparison,
    create_classified_comparison,
    create_bivariate_choropleth,
    save_map,
    BIVARIATE_COLOR_SCHEMES,
    SCHEME_LABELS,
    _resolve_color_scheme,
    HAS_MAPCLASSIFY,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_gdf():
    """Create a minimal GeoDataFrame for testing choropleths."""
    gdf = gpd.GeoDataFrame({
        'name': ['A', 'B', 'C', 'D', 'E', 'F'],
        'population': [100, 200, 300, 400, 500, 600],
        'income': [50000, 60000, 70000, 80000, 90000, 100000],
        'unemployment': [3.0, 5.0, 7.0, 4.0, 6.0, 8.0],
        'geometry': [box(i, 0, i + 1, 1) for i in range(6)],
    }, crs='EPSG:4326')
    return gdf


@pytest.fixture(autouse=True)
def close_figures():
    """Close all matplotlib figures after each test."""
    yield
    plt.close('all')


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestBivariateColorSchemes:
    """Tests for the BIVARIATE_COLOR_SCHEMES constant."""

    def test_has_expected_keys(self):
        expected = {'purple_blue', 'teuling', 'blue_red', 'green_orange'}
        assert expected == set(BIVARIATE_COLOR_SCHEMES.keys())

    def test_each_scheme_has_nine_colors(self):
        for name, colors in BIVARIATE_COLOR_SCHEMES.items():
            assert len(colors) == 9, f"Scheme '{name}' has {len(colors)} colors, expected 9"

    def test_colors_are_hex_strings(self):
        for name, colors in BIVARIATE_COLOR_SCHEMES.items():
            for color in colors:
                assert isinstance(color, str), f"Scheme '{name}' has non-string color"
                assert color.startswith('#'), f"Scheme '{name}' color '{color}' not hex"


class TestSchemeLabels:
    """Tests for the SCHEME_LABELS constant."""

    def test_has_common_schemes(self):
        expected = {'quantiles', 'equal_interval', 'fisher_jenks', 'percentiles'}
        assert expected.issubset(set(SCHEME_LABELS.keys()))

    def test_labels_are_strings(self):
        for key, label in SCHEME_LABELS.items():
            assert isinstance(label, str), f"Label for '{key}' is not a string"


# =============================================================================
# _resolve_color_scheme TESTS
# =============================================================================

class TestResolveColorScheme:
    """Tests for the internal _resolve_color_scheme function."""

    def test_string_lookup(self):
        colors = _resolve_color_scheme('purple_blue', 3)
        assert len(colors) == 9
        assert colors == BIVARIATE_COLOR_SCHEMES['purple_blue']

    def test_list_passthrough(self):
        custom = ['#000'] * 9
        colors = _resolve_color_scheme(custom, 3)
        assert colors == custom

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="Unknown bivariate color scheme"):
            _resolve_color_scheme('nonexistent', 3)

    def test_wrong_count_raises(self):
        with pytest.raises(ValueError, match="4 colors but.*9 required"):
            _resolve_color_scheme(['#000'] * 4, 3)

    def test_four_class_needs_sixteen(self):
        with pytest.raises(ValueError, match="9 colors but.*16 required"):
            _resolve_color_scheme('purple_blue', 4)


# =============================================================================
# create_choropleth TESTS
# =============================================================================

class TestCreateChoropleth:
    """Tests for the create_choropleth function."""

    def test_returns_fig_and_ax(self, sample_gdf):
        fig, ax = create_choropleth(sample_gdf, 'population')
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_title_is_set(self, sample_gdf):
        fig, ax = create_choropleth(sample_gdf, 'population', title='Test Title')
        assert ax.get_title() == 'Test Title'

    def test_accepts_ax_parameter(self, sample_gdf):
        ext_fig, ext_ax = plt.subplots(1, 1)
        fig, ax = create_choropleth(sample_gdf, 'population', ax=ext_ax)
        assert ax is ext_ax
        assert fig is ext_fig

    def test_axes_are_off(self, sample_gdf):
        fig, ax = create_choropleth(sample_gdf, 'population')
        assert not ax.axison

    @pytest.mark.skipif(not HAS_MAPCLASSIFY, reason="mapclassify not installed")
    def test_with_scheme(self, sample_gdf):
        fig, ax = create_choropleth(
            sample_gdf, 'population', scheme='quantiles', k=3
        )
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_no_title_when_empty(self, sample_gdf):
        fig, ax = create_choropleth(sample_gdf, 'population', title='')
        assert ax.get_title() == ''


# =============================================================================
# create_choropleth_comparison TESTS
# =============================================================================

class TestCreateChoroplethComparison:
    """Tests for the create_choropleth_comparison function."""

    def test_returns_fig_and_axes(self, sample_gdf):
        fig, axes = create_choropleth_comparison(
            sample_gdf,
            columns=[
                {'column': 'population', 'title': 'Pop'},
                {'column': 'income', 'title': 'Income'},
            ],
            ncols=2,
        )
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axes, np.ndarray)

    def test_correct_subplot_count(self, sample_gdf):
        fig, axes = create_choropleth_comparison(
            sample_gdf,
            columns=[
                {'column': 'population'},
                {'column': 'income'},
                {'column': 'unemployment'},
            ],
            ncols=3,
        )
        assert axes.size >= 3

    def test_single_column(self, sample_gdf):
        fig, axes = create_choropleth_comparison(
            sample_gdf,
            columns=[{'column': 'population', 'title': 'Pop'}],
            ncols=1,
        )
        assert isinstance(fig, matplotlib.figure.Figure)


# =============================================================================
# create_classified_comparison TESTS
# =============================================================================

class TestCreateClassifiedComparison:
    """Tests for the create_classified_comparison function."""

    @pytest.mark.skipif(not HAS_MAPCLASSIFY, reason="mapclassify not installed")
    def test_returns_fig_and_axes(self, sample_gdf):
        fig, axes = create_classified_comparison(
            sample_gdf,
            column='population',
            schemes=['quantiles', 'equal_interval'],
        )
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axes, np.ndarray)

    @pytest.mark.skipif(not HAS_MAPCLASSIFY, reason="mapclassify not installed")
    def test_custom_titles(self, sample_gdf):
        fig, axes = create_classified_comparison(
            sample_gdf,
            column='population',
            schemes=['quantiles'],
            titles=['Custom Title'],
            ncols=1,
        )
        flat = np.atleast_1d(axes).flat
        assert flat[0].get_title() == 'Custom Title'


# =============================================================================
# create_bivariate_choropleth TESTS
# =============================================================================

class TestCreateBivariateChoropleth:
    """Tests for the create_bivariate_choropleth function."""

    def test_returns_fig_and_axes(self, sample_gdf):
        fig, axes = create_bivariate_choropleth(
            sample_gdf, 'population', 'income'
        )
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axes, np.ndarray)
        assert len(axes) == 2  # map + legend

    def test_named_scheme(self, sample_gdf):
        fig, axes = create_bivariate_choropleth(
            sample_gdf, 'population', 'income',
            color_scheme='blue_red',
        )
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_raw_color_list(self, sample_gdf):
        custom_colors = ['#111111'] * 9
        fig, axes = create_bivariate_choropleth(
            sample_gdf, 'population', 'income',
            color_scheme=custom_colors,
        )
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_invalid_scheme_raises(self, sample_gdf):
        with pytest.raises(ValueError, match="Unknown bivariate color scheme"):
            create_bivariate_choropleth(
                sample_gdf, 'population', 'income',
                color_scheme='nonexistent',
            )

    def test_title_is_set(self, sample_gdf):
        fig, axes = create_bivariate_choropleth(
            sample_gdf, 'population', 'income',
            title='My Bivariate Map',
        )
        assert axes[0].get_title() == 'My Bivariate Map'

    def test_does_not_modify_input(self, sample_gdf):
        original_cols = set(sample_gdf.columns)
        create_bivariate_choropleth(sample_gdf, 'population', 'income')
        assert set(sample_gdf.columns) == original_cols


# =============================================================================
# save_map TESTS
# =============================================================================

class TestSaveMap:
    """Tests for the save_map function."""

    def test_saves_to_path(self, sample_gdf, tmp_path):
        fig, ax = create_choropleth(sample_gdf, 'population')
        output = tmp_path / 'test_map.png'
        result = save_map(fig, output)
        assert result == output
        assert output.exists()

    def test_creates_parent_dirs(self, sample_gdf, tmp_path):
        fig, ax = create_choropleth(sample_gdf, 'population')
        output = tmp_path / 'deep' / 'nested' / 'map.png'
        result = save_map(fig, output)
        assert result == output
        assert output.exists()

    def test_returns_path_object(self, sample_gdf, tmp_path):
        fig, ax = create_choropleth(sample_gdf, 'population')
        result = save_map(fig, str(tmp_path / 'map.png'))
        assert isinstance(result, Path)
