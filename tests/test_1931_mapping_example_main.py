"""The comprehensive mapping example runs from its map step through the PDF and
PowerPoint steps, with every map embedded, and main() does not hide failures
(#1931)."""

from pathlib import Path

import pytest

pytest.importorskip("geopandas")
pytest.importorskip("shapely")
pytest.importorskip("matplotlib")
pytest.importorskip("folium")
pytest.importorskip("reportlab")
PILImage = pytest.importorskip("PIL.Image")
PdfReader = pytest.importorskip("PyPDF2").PdfReader
pptx = pytest.importorskip("pptx")

from pptx.enum.shapes import MSO_SHAPE_TYPE

from siege_utilities.reporting.chart_generator import ChartGenerator
from siege_utilities.reporting.examples import comprehensive_mapping_example as example
from siege_utilities.reporting.image_utils import decode_rl_image

# The maps the PDF report embeds, one per map section.
PDF_MAP_KEYS = ("bivariate_map", "marker_map", "elevation_map", "heatmap", "cluster_map", "flow_map")
PPTX_MAP_SLIDES = ("Regional Population vs Income", "City Population Distribution", "3D Elevation Visualization")


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    """Run the example's map, PDF and PowerPoint steps once, in a temporary
    working directory."""
    workdir = tmp_path_factory.mktemp("mapping-example")
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(workdir)
        # The report generator's branding manager reads and creates
        # ~/.siege_utilities; keep it inside the temporary directory too.
        patch.setenv("HOME", str(workdir / "home"))
        maps = example.demonstrate_comprehensive_mapping()
        pdf_path = workdir / example.create_comprehensive_pdf_report(maps)
        pptx_path = workdir / Path(example.create_comprehensive_powerpoint(maps))
    return {"workdir": workdir, "maps": maps, "pdf": pdf_path, "pptx": pptx_path}


def test_region_boundaries_cover_every_sample_region():
    boundaries = example.create_sample_region_boundaries()
    regions = example.create_sample_regional_data()

    assert sorted(boundaries["region"]) == sorted(regions["region"])
    assert boundaries.crs.to_epsg() == 4326
    assert boundaries.geometry.is_valid.all()
    assert not boundaries.geometry.is_empty.any()


@pytest.mark.parametrize("method, kwargs, message", [
    ("create_bivariate_choropleth_matplotlib",
     {"value_column1": "population", "value_column2": "median_income"}, "Bivariate Choropleth Error"),
    ("create_advanced_choropleth",
     {"value_column": "gdp_growth", "classification": "natural_breaks"}, "Advanced Choropleth Error"),
])
def test_choropleth_without_boundaries_raises_runtime_error(tmp_path, method, kwargs, message):
    # The example used to make these calls with geodata=None.
    chart_gen = ChartGenerator(output_dir=tmp_path)

    with pytest.raises(RuntimeError, match=message):
        getattr(chart_gen, method)(
            data=example.create_sample_regional_data(), geodata=None, location_column="region", **kwargs,
        )


def test_every_map_is_an_image(demo):
    # Every map is a ReportLab Image holding a real PNG, not None, a stub, or
    # the engine's 1x1 fallback image.
    import io

    for key in PDF_MAP_KEYS + ("advanced_choropleth",):
        png = decode_rl_image(demo["maps"][key])
        assert png is not None and png.startswith(b"\x89PNG"), key
        width, height = PILImage.open(io.BytesIO(png)).size
        assert width > 1 and height > 1, key


def test_interactive_maps_are_written_under_the_working_directory(demo):
    saved = sorted(path.name for path in (demo["workdir"] / "interactive_maps").glob("*.html"))

    assert saved == ["temp_cluster_map.html", "temp_flow_map.html", "temp_heatmap.html", "temp_marker_map.html"]


def _placed_image_count(reader):
    # Images in each page's resources (as in test_report_generator_renders_sections);
    # PyPDF2's page.images omits some ReportLab filters, and transparency masks
    # are separate image objects that no page places directly.
    return sum(
        image.get_object().get("/Subtype") == "/Image"
        for page in reader.pages if "/XObject" in page["/Resources"]
        for image in page["/Resources"]["/XObject"].values()
    )


def test_pdf_report_embeds_every_map(demo):
    assert demo["pdf"].is_file() and demo["pdf"].stat().st_size > 0
    # One embedded image per map section: none was dropped by the image helper.
    assert _placed_image_count(PdfReader(demo["pdf"])) == len(PDF_MAP_KEYS)


def test_presentation_map_slides_contain_their_maps(demo):
    assert demo["pptx"].is_file() and demo["pptx"].stat().st_size > 0
    pictures_by_title = {
        slide.shapes.title.text: sum(shape.shape_type == MSO_SHAPE_TYPE.PICTURE for shape in slide.shapes)
        for slide in pptx.Presentation(str(demo["pptx"])).slides
        if slide.shapes.title is not None
    }
    for title in PPTX_MAP_SLIDES:
        assert pictures_by_title.get(title) == 1, title


def test_main_names_the_step_and_reraises_a_chart_engine_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    def failing_maps():
        raise RuntimeError("boom")

    monkeypatch.setattr(example, "demonstrate_comprehensive_mapping", failing_maps)

    with pytest.raises(RuntimeError, match="boom"):
        example.main()
    assert "Error while creating the maps: boom" in capsys.readouterr().out


def test_main_names_the_step_and_reraises_a_later_step_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(example, "demonstrate_comprehensive_mapping", lambda: {})

    # The PDF step needs the maps; a missing one must stop the script.
    with pytest.raises(KeyError, match="bivariate_map"):
        example.main()
    assert "Error while creating the PDF report:" in capsys.readouterr().out
