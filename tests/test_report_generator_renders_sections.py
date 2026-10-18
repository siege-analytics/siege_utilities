"""PDF regressions for the section builders and canvas pagination (#1485)."""

import re

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pandas")
PdfReader = pytest.importorskip("PyPDF2").PdfReader
PILImage = pytest.importorskip("PIL.Image")

from reportlab.pdfgen.canvas import Canvas

from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.templates.content_page_template import ContentPageTemplate


def image_count(reader):
    # Inspect embedded image objects; PyPDF2.images omits some ReportLab filters.
    return sum(
        image.get_object().get("/Subtype") == "/Image"
        for page in reader.pages if "/XObject" in page["/Resources"]
        for image in page["/Resources"]["/XObject"].values()
    )


@pytest.fixture
def generator(tmp_path):
    return ReportGenerator("PDF regression", output_dir=tmp_path)


@pytest.fixture
def chart_path(tmp_path):
    image_path = tmp_path / "chart.png"
    PILImage.new("RGB", (32, 24), "navy").save(image_path)
    return image_path


@pytest.mark.parametrize("with_chart", [True, False])
def test_analytics_pdf_renders_sections(generator, chart_path, tmp_path, with_chart):
    report = generator.create_analytics_report(
        "Q3", charts=[chart_path] if with_chart else [],
        insights=["X1"], recommendations=["R1"],
        executive_summary="Summary evidence", methodology="Method evidence",
        data_summary="Data evidence",
    )
    output = tmp_path / "analytics.pdf"
    generator.generate_pdf_report(report, str(output))

    assert output.is_file()
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() for page in reader.pages)
    for expected in ("X1", "R1", "Q3", "Summary evidence", "Method evidence", "Data evidence"):
        assert expected in text
    assert image_count(reader) == (1 if with_chart else 0)


def test_comprehensive_pdf_title_toc_and_appendices(generator, tmp_path):
    report = generator.create_comprehensive_report(
        "Quarterly <Review>", author="A & B", client="Client <North>",
        sections=[
            {"type": "text", "title": "Findings & scope", "content": "Body evidence"},
            {"type": "text", "title": "Details", "content": "Detail evidence",
             "level": 2, "page_break_before": True},
        ],
        appendices=[{"type": "appendix", "title": "Source notes", "content": "Appendix evidence"}],
    )
    # A metadata title must not duplicate the explicit title_page section.
    report["metadata"]["title"] = report["title"]
    output = tmp_path / "comprehensive.pdf"
    generator.generate_pdf_report(report, str(output))
    pages = [page.extract_text() for page in PdfReader(output).pages]

    for expected in ("Quarterly <Review>", "Analysis Report", "A & B", "Client <North>",
                     report["sections"][0]["date"]):
        assert expected in pages[0]
    assert sum(page.count("Quarterly <Review>") for page in pages) == 1
    assert "Table of Contents" in pages[1]
    assert "Placeholder for table of contents" not in pages[1]
    for title in ("Findings & scope", "Details", "Appendices", "Source notes"):
        actual_page = next(i for i, text in enumerate(pages[2:], 3) if title in text)
        # ReportLab paints the right-aligned page number before the entry text.
        assert re.search(r"\b" + str(actual_page) + r"\s*" + re.escape(title), pages[1])
    assert "Body evidence" in pages[2]
    assert any("Appendix evidence" in page for page in pages[2:])


@pytest.mark.parametrize("kind", ["paragraph", "table"])
def test_content_page_overflow_preserves_every_item(tmp_path, kind):
    output = tmp_path / f"overflow-{kind}.pdf"
    canvas = Canvas(str(output))
    template = ContentPageTemplate(canvas)
    template.start_page("Overflow", 7, "Regression section")
    tokens = [f"item{i:04d}" for i in range(600 if kind == "paragraph" else 90)]
    if kind == "paragraph":
        template.add_paragraph(" ".join(tokens), text_color="#123456")
    else:
        template.add_table([[token, "Value"] for token in tokens], headers=["Item", "Value"])
    template.finish_page()
    canvas.save()

    pages = [page.extract_text() for page in PdfReader(output).pages]
    text = "\n".join(pages)
    assert len(pages) > 1
    assert re.findall(r"item\d{4}", text) == tokens
    for number, page in enumerate(pages, 7):
        assert "Regression section" in page
        assert f"Page {number}" in page
        if kind == "table":
            assert "Item" in page  # Repeat column headers after every page break.


@pytest.mark.parametrize("section", [
    {"type": "unknown", "content": ["lost"]},
    {"type": "text", "content": ["lost"]},
    {"type": "text", "content": {}},
    {"type": "insights", "content": "lost"},
    {"type": "recommendations", "content": [{"unexpected": "lost"}]},
    {"type": "charts", "content": "lost"},
    {"type": "charts", "content": {"charts": "lost"}},
    {"type": "table", "content": []},
    {"type": "maps", "content": ["lost"]},
])
def test_invalid_section_raises_without_publishing_pdf(generator, tmp_path, section):
    output = tmp_path / "invalid.pdf"
    with pytest.raises(ValueError, match="section"):
        generator.generate_pdf_report({"sections": [{"title": "Bad", **section}]}, str(output))
    assert not output.exists()
    assert not list(tmp_path.glob(".*.part"))


def test_missing_chart_warns(generator, tmp_path, caplog):
    report = generator.create_analytics_report("Missing", charts=[tmp_path / "missing.png"])
    generator.generate_pdf_report(report, str(tmp_path / "missing.pdf"))
    assert "chart" in caplog.text.lower()
    assert "missing.png" in caplog.text


def test_paragraph_too_tall_for_empty_page_raises(tmp_path):
    template = ContentPageTemplate(Canvas(str(tmp_path / "too-tall.pdf")))
    template.start_page("Too tall", 1)
    with pytest.raises(ValueError, match="fit"):
        template.add_paragraph("Oversized", font_size=1000)


@pytest.mark.parametrize("kind", ["chart", "charts", "maps"])
def test_image_mapping_sections_still_render(generator, chart_path, tmp_path, kind):
    content = {"description": "Caption <one> & two"}
    content.update({"image_path": chart_path} if kind == "chart" else {kind: [chart_path]})
    output = tmp_path / f"{kind}.pdf"
    generator.generate_pdf_report({"sections": [{"type": kind, "title": kind, "content": content}]}, str(output))
    reader = PdfReader(output)
    assert "Caption <one> & two" in reader.pages[0].extract_text()
    assert image_count(reader) == 1


def test_table_cell_text_wraps_without_truncation(tmp_path):
    output = tmp_path / "wrapped-cell.pdf"
    canvas = Canvas(str(output))
    template = ContentPageTemplate(canvas)
    template.start_page("Wrapped cells", 1)
    tokens = [f"cell{i:03d}" for i in range(80)]
    template.add_table([[" ".join(tokens), "Other"]], headers=["Description", "Value"])
    template.finish_page()
    canvas.save()
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
    assert re.findall(r"cell\d{3}", text) == tokens


def test_table_row_too_tall_for_empty_page_raises(tmp_path):
    template = ContentPageTemplate(Canvas(str(tmp_path / "tall-row.pdf")))
    template.start_page("Tall row", 1)
    with pytest.raises(ValueError, match="fit"):
        template.add_table([["Long cell " * 1000]], headers=["Description"])


@pytest.mark.parametrize("headers", [None, ["Metric", "Value"]])
def test_table_record_rows_render_values(generator, tmp_path, headers):
    report = generator.create_comprehensive_report("Record table")
    generator.add_table_section(
        report, "Metrics",
        [{"Metric": "Signups", "Value": 1820}, {"Value": 640, "Metric": "RSVPs"}],
        headers=headers,
    )
    output = tmp_path / "records.pdf"
    generator.generate_pdf_report(report, str(output))
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
    for expected in ("Metric", "Value", "Signups", "1820", "RSVPs", "640"):
        assert expected in text
