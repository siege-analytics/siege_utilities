"""The shipped comprehensive mapping example runs, and the text and map section
helpers accept page breaks (#1927)."""

from pathlib import Path

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pandas")
PdfReader = pytest.importorskip("PyPDF2").PdfReader
PILImage = pytest.importorskip("PIL.Image")

from siege_utilities.reporting.examples import comprehensive_mapping_example as example
from siege_utilities.reporting.report_generator import ReportGenerator

MAP_KEYS = ("bivariate_map", "marker_map", "elevation_map", "heatmap", "cluster_map", "flow_map")


@pytest.fixture
def maps_dict(tmp_path):
    """Six tiny map images, standing in for demonstrate_comprehensive_mapping()."""
    maps = {}
    for index, key in enumerate(MAP_KEYS):
        path = tmp_path / f"{key}.png"
        PILImage.new("RGB", (24, 16), (40 * index, 90, 160)).save(path)
        maps[key] = path
    return maps


def test_comprehensive_pdf_report_runs(maps_dict, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    output = Path(example.create_comprehensive_pdf_report(maps_dict))

    assert output.is_file()
    assert output.stat().st_size > 0
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
    for heading in ("Executive Summary", "Migration Flow Patterns", "Raw Data Tables"):
        assert heading in text


def test_comprehensive_powerpoint_runs(maps_dict, tmp_path, monkeypatch):
    pptx = pytest.importorskip("pptx")
    monkeypatch.chdir(tmp_path)

    output = Path(example.create_comprehensive_powerpoint(maps_dict))

    assert output.is_file()
    assert output.stat().st_size > 0
    deck_text = "\n".join(
        shape.text_frame.text
        for slide in pptx.Presentation(str(output)).slides
        for shape in slide.shapes if shape.has_text_frame
    )
    # The comparison slide shows both column headings and their items.
    for expected in ("Static Maps", "Interactive Maps", "Choropleth", "Cluster Maps"):
        assert expected in deck_text


@pytest.fixture
def generator(tmp_path):
    return ReportGenerator("Page breaks", output_dir=tmp_path)


def _pages(generator, report, path):
    generator.generate_pdf_report(report, str(path))
    return [page.extract_text() for page in PdfReader(path).pages]


@pytest.mark.parametrize("helper", ["text", "map"])
def test_page_break_parameters_default_to_false(generator, maps_dict, helper):
    report = {"sections": []}
    if helper == "text":
        generator.add_text_section(report, "Only", "Body")
    else:
        generator.add_map_section(report, "Only", [maps_dict["marker_map"]])
    section = report["sections"][0]
    assert section["page_break_before"] is False
    assert section["page_break_after"] is False


@pytest.mark.parametrize("helper", ["text", "map"])
@pytest.mark.parametrize("flag", ["page_break_before", "page_break_after", None])
def test_page_break_parameters_insert_a_page_break(generator, maps_dict, tmp_path, helper, flag):
    report = {"sections": []}
    generator.add_text_section(report, "First section", "First body")
    kwargs = {flag: True} if flag else {}
    if helper == "text":
        generator.add_text_section(report, "Middle section", "Middle body", **kwargs)
    else:
        generator.add_map_section(
            report, "Middle section", [maps_dict["marker_map"]], description="Middle body", **kwargs,
        )
    generator.add_text_section(report, "Last section", "Last body")

    pages = _pages(generator, report, tmp_path / f"{helper}-{flag}.pdf")

    def page_of(title):
        return next(index for index, text in enumerate(pages) if title in text)

    first, middle, last = page_of("First section"), page_of("Middle section"), page_of("Last section")
    if flag is None:
        assert first == middle == last == 0
    elif flag == "page_break_before":
        assert (first, middle, last) == (0, 1, 1)
    else:
        assert (first, middle, last) == (0, 0, 1)
