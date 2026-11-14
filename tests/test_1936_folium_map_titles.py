"""Folium-based maps accept a title and the marker map's default tile style
works with real folium (#1936). Nothing here mocks folium."""

import pytest

pytest.importorskip("folium")
pytest.importorskip("reportlab")
pytest.importorskip("matplotlib")
pd = pytest.importorskip("pandas")

from siege_utilities.reporting.chart_generator import ChartGenerator

TITLE = "Regional <b>view</b> & more"
ESCAPED_TITLE = "Regional &lt;b&gt;view&lt;/b&gt; &amp; more"

POINTS = pd.DataFrame({
    "lat": [40.71, 34.05, 41.88],
    "lon": [-74.01, -118.24, -87.63],
    "value": [8.3, 3.9, 2.7],
    "label": ["New York", "Los Angeles", "Chicago"],
})
FLOWS = pd.DataFrame({
    "lat": [40.71, 34.05], "lon": [-74.01, -118.24],
    "dest_lat": [34.05, 41.88], "dest_lon": [-118.24, -87.63],
    "flow": [1500, 800],
})


def _make_map(chart_gen, kind, **kwargs):
    if kind == "marker":
        return chart_gen.create_marker_map(POINTS, "lat", "lon", value_column="value", label_column="label", **kwargs)
    if kind == "heatmap":
        return chart_gen.create_heatmap_map(POINTS, "lat", "lon", value_column="value", **kwargs)
    if kind == "cluster":
        return chart_gen.create_cluster_map(POINTS, "lat", "lon", label_column="label", **kwargs)
    return chart_gen.create_flow_map(FLOWS, "lat", "lon", "dest_lat", "dest_lon", flow_value_column="flow", **kwargs)


SAVED_AS = {
    "marker": "temp_marker_map.html",
    "heatmap": "temp_heatmap.html",
    "cluster": "temp_cluster_map.html",
    "flow": "temp_flow_map.html",
}


@pytest.mark.parametrize("kind", list(SAVED_AS))
def test_titled_folium_map_saves_its_escaped_title(tmp_path, kind):
    chart_gen = ChartGenerator(output_dir=tmp_path)

    _make_map(chart_gen, kind, title=TITLE)

    html = (tmp_path / SAVED_AS[kind]).read_text()
    assert ESCAPED_TITLE in html
    assert "<b>view</b>" not in html


@pytest.mark.parametrize("kind", list(SAVED_AS))
def test_folium_map_without_title_adds_no_title(tmp_path, kind):
    chart_gen = ChartGenerator(output_dir=tmp_path)

    _make_map(chart_gen, kind)

    html = (tmp_path / SAVED_AS[kind]).read_text()
    assert "siege-map-title" not in html


def _saved_heading(html):
    """Return the title heading's text as a browser shows it."""
    import html as html_lib
    import re

    match = re.search(r'<h3 class="siege-map-title"[^>]*>(.*?)</h3>', html, re.DOTALL)
    assert match, "no title heading in the saved map"
    return html_lib.unescape(match.group(1))


@pytest.mark.parametrize("title", [
    "Total {{ 7 * 191 }}",                 # an expression
    "Region {% if true %}A{% endif %} map",  # a statement
    "Region {# note #} map",               # a comment
    "Region {{ undefined_name }} map",     # an undefined name
    "Broken {{ map",                       # a malformed delimiter
    "Ratio {7} and 50% }}",                # stray braces and percent
])
@pytest.mark.parametrize("kind", list(SAVED_AS))
def test_title_is_shown_as_text_not_run_as_a_template(tmp_path, kind, title):
    chart_gen = ChartGenerator(output_dir=tmp_path)

    _make_map(chart_gen, kind, title=title)

    html = (tmp_path / SAVED_AS[kind]).read_text()
    assert _saved_heading(html) == title
    assert "1337" not in html


def test_title_with_quotes_is_escaped(tmp_path):
    title = 'He said "hi" & \'bye\''
    chart_gen = ChartGenerator(output_dir=tmp_path)

    _make_map(chart_gen, "marker", title=title)

    html = (tmp_path / SAVED_AS["marker"]).read_text()
    assert _saved_heading(html) == title
    assert '"hi"' not in html.split('class="siege-map-title"', 1)[1].split("</h3>", 1)[0]


def test_marker_map_accepts_a_tile_provider_object(tmp_path):
    xyzservices = pytest.importorskip("xyzservices")
    chart_gen = ChartGenerator(output_dir=tmp_path)

    chart_gen.create_marker_map(POINTS, "lat", "lon", map_style=xyzservices.providers.CartoDB.Positron)

    assert "basemaps.cartocdn.com" in (tmp_path / SAVED_AS["marker"]).read_text()


def test_marker_map_default_style_uses_openstreetmap_tiles(tmp_path):
    chart_gen = ChartGenerator(output_dir=tmp_path)

    chart_gen.create_marker_map(POINTS, "lat", "lon", label_column="label")

    html = (tmp_path / SAVED_AS["marker"]).read_text()
    assert "tile.openstreetmap.org" in html


@pytest.mark.parametrize("map_style, tile_host", [
    ("open-street-map", "tile.openstreetmap.org"),
    ("cartodb-positron", "basemaps.cartocdn.com"),
    ("CartoDB positron", "basemaps.cartocdn.com"),
])
def test_marker_map_accepts_documented_style_names(tmp_path, map_style, tile_host):
    chart_gen = ChartGenerator(output_dir=tmp_path)

    chart_gen.create_marker_map(POINTS, "lat", "lon", map_style=map_style)

    assert tile_host in (tmp_path / SAVED_AS["marker"]).read_text()


def test_marker_map_with_an_unknown_style_raises(tmp_path):
    chart_gen = ChartGenerator(output_dir=tmp_path)

    with pytest.raises(RuntimeError, match="Marker Map Error"):
        chart_gen.create_marker_map(POINTS, "lat", "lon", map_style="no-such-style")
