"""PDF regressions for the section builders and canvas pagination (#1485)."""

import logging
import re

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pandas")
PdfReader = pytest.importorskip("PyPDF2").PdfReader
PILImage = pytest.importorskip("PIL.Image")

from reportlab.lib.styles import getSampleStyleSheet
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


TEXT_EXPECTED = "a string or a mapping with a text string"


@pytest.mark.parametrize("section, message", [
    ({"type": "unknown", "content": ["lost"]}, "Unknown report section type: 'unknown'"),
    ({"type": "text", "content": ["lost"]}, f"'text' section: expected {TEXT_EXPECTED}"),
    ({"type": "text", "content": {}}, f"'text' section: expected {TEXT_EXPECTED}"),
    ({"type": "insights", "content": "lost"},
     "'insights' section: expected a list of nonempty strings"),
    ({"type": "recommendations", "content": [{"unexpected": "lost"}]},
     "'recommendations' section: expected a list of nonempty strings"),
    ({"type": "charts", "content": "lost"},
     "'charts' section: expected a chart list or an image mapping"),
    ({"type": "charts", "content": {"charts": "lost"}},
     "'charts' section: expected a list, tuple or None under 'charts'"),
    ({"type": "charts", "content": {"charts": b"lost"}},
     "'charts' section: expected a list, tuple or None under 'charts'"),
    ({"type": "charts", "content": {"charts": {"image_path": "lost"}}},
     "'charts' section: expected a list, tuple or None under 'charts'"),
    ({"type": "table", "content": []}, "'table' section: expected a mapping with table data"),
    ({"type": "maps", "content": ["lost"]}, "'maps' section: expected a maps mapping"),
    ({"type": "map", "content": ["lost"]}, "'map' section: expected a maps mapping"),
    ({"type": "table", "content": {"data": [["a"]], "headers": "a"}},
     "'table' section: expected a list or tuple of column headers"),
    ({"type": "appendix_header", "title": ""},
     "'appendix_header' section: expected an appendix divider title"),
    ({"type": "maps", "content": {"maps": [], "description": 3}},
     "'maps' section: expected a string description"),
])
def test_invalid_section_raises_without_publishing_pdf(generator, tmp_path, section, message):
    output = tmp_path / "invalid.pdf"
    with pytest.raises(ValueError, match=re.escape(message)):
        generator.generate_pdf_report({"sections": [{"title": "Bad", **section}]}, str(output))
    assert not output.exists()
    assert not list(tmp_path.glob(".*.part"))


@pytest.mark.parametrize("section, message", [
    ({"title": "Cover", "content": "unexpected"},
     "title, subtitle, author, client and date strings on the section"),
    ({"title": "Cover", "author": 7},
     "title, subtitle, author, client and date strings on the section"),
    ({"title": "  "}, "a nonempty title"),
    ({}, "a nonempty title"),
])
def test_invalid_title_page_raises(generator, tmp_path, section, message):
    output = tmp_path / "title.pdf"
    with pytest.raises(ValueError, match=re.escape(f"'title_page' section: expected {message}")):
        generator.generate_pdf_report({"sections": [{"type": "title_page", **section}]}, str(output))
    assert not output.exists()


@pytest.mark.parametrize("kind", ["chart", "map"])
def test_none_description_renders_images_as_in_4_0_0(generator, chart_path, tmp_path, kind):
    report = {"sections": []}
    if kind == "chart":
        generator.add_chart_section(report, "Charts", [chart_path], description=None)
    else:
        generator.add_map_section(report, "Maps", [chart_path], description=None)
    output = tmp_path / f"{kind}-none-description.pdf"
    generator.generate_pdf_report(report, str(output))
    reader = PdfReader(output)
    assert image_count(reader) == 1
    assert "None" not in "\n".join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize("kind", ["chart", "map"])
def test_tuple_of_images_renders(generator, chart_path, tmp_path, kind):
    report = {"sections": []}
    # Two distinct images: ReportLab embeds one image object per unique file.
    second_path = tmp_path / "second.png"
    PILImage.new("RGB", (32, 24), "teal").save(second_path)
    images = (chart_path, second_path)
    if kind == "chart":
        generator.add_chart_section(report, "Charts", images)
    else:
        generator.add_map_section(report, "Maps", images)
    output = tmp_path / f"{kind}-tuple.pdf"
    generator.generate_pdf_report(report, str(output))
    assert image_count(PdfReader(output)) == 2


RECORDS = [{"Metric": "Signups", "Value": 1820}, {"Metric": "RSVPs", "Value": 640}]


@pytest.mark.parametrize("headers, missing, present", [
    (["Name", "Count"], ["Name", "Count"], []),
    (["Metric", "Count"], ["Count"], ["Metric"]),
])
def test_record_headers_must_be_record_keys(generator, headers, missing, present):
    # For records, headers select and order record keys, so a header that is
    # not a key would otherwise produce a column of missing values.
    report = {"sections": []}
    try:
        updated = generator.add_table_section(report, "Metrics", RECORDS, headers=headers)
    except ValueError as exc:
        message = str(exc)
    else:
        pytest.fail(f"no error; rows were {updated['sections'][0]['content']['data']}")
    assert "not keys of the table records" in message
    for name in missing:
        assert repr(name) in message
    for name in present:
        assert repr(name) not in message
    assert report["sections"] == []


def test_missing_chart_warns(generator, tmp_path, caplog, monkeypatch):
    # The test settings set the root logger to CRITICAL and disable existing
    # loggers; capture this logger's warnings regardless of test order.
    logger_name = "siege_utilities.reporting.report_generator"
    monkeypatch.setattr(logging.getLogger(logger_name), "disabled", False)
    caplog.set_level(logging.WARNING, logger=logger_name)
    report = generator.create_analytics_report("Missing", charts=[tmp_path / "missing.png"])
    generator.generate_pdf_report(report, str(tmp_path / "missing.pdf"))
    assert "chart" in caplog.text.lower()
    assert "missing.png" in caplog.text


def test_chart_mapping_warning_logs_keys_not_values(generator, tmp_path, caplog, monkeypatch):
    logger_name = "siege_utilities.reporting.report_generator"
    monkeypatch.setattr(logging.getLogger(logger_name), "disabled", False)
    caplog.set_level(logging.WARNING, logger=logger_name)
    secret = "private-value-0451"
    report = {"sections": [{"type": "charts", "title": "Charts", "content": {
        "charts": [{"image_path": str(tmp_path / f"{secret}.png"), "note": secret}],
    }}]}
    generator.generate_pdf_report(report, str(tmp_path / "mapping.pdf"))
    assert "image_path" in caplog.text and "note" in caplog.text
    assert secret not in caplog.text


@pytest.mark.parametrize("content_kind", ["bare tuple", "image_path with tuple"])
def test_chart_content_tuples_render(generator, chart_path, tmp_path, content_kind):
    second_path = tmp_path / "second.png"
    PILImage.new("RGB", (32, 24), "teal").save(second_path)
    if content_kind == "bare tuple":
        content = (chart_path, second_path)
    else:
        content = {"image_path": str(chart_path), "charts": (second_path,)}
    output = tmp_path / "chart-content.pdf"
    generator.generate_pdf_report(
        {"sections": [{"type": "charts", "title": "Charts", "content": content}]}, str(output),
    )
    assert image_count(PdfReader(output)) == 2


def test_tuple_headers_render_once(generator, tmp_path):
    report = {"sections": []}
    generator.add_table_section(report, "Metrics", [["Signups", 1820]], headers=("HdrMetric", "HdrValue"))
    output = tmp_path / "tuple-headers.pdf"
    generator.generate_pdf_report(report, str(output))
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
    assert text.count("HdrMetric") == 1
    assert "Signups" in text


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


def test_bullet_list_overflow_preserves_every_item(tmp_path):
    """A bullet list longer than one page paginates through _add_flowable and
    keeps every item, instead of the old canvas loop that broke on overflow."""
    output = tmp_path / "bullets.pdf"
    canvas = Canvas(str(output))
    template = ContentPageTemplate(canvas)
    template.start_page("Bullets", 1, "Regression section")
    items = [f"bul{i:04d}" for i in range(120)]
    template.add_bullet_list(items)
    template.finish_page()
    canvas.save()
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
    assert re.findall(r"bul\d{4}", text) == items


class _SampleStyles:
    """The stylesheet a report template provides (getSampleStyleSheet)."""

    styles = getSampleStyleSheet()


@pytest.mark.parametrize("level, style, toc_level", [
    ("2", "Heading2", 1),
    (2, "Heading2", 1),
    (None, "Heading1", 0),
    ("abc", "Heading1", 0),
    (2.5, "Heading1", 0),
    # Levels without a sample heading style render as Heading1, and the
    # contents entry follows the style actually used.
    (7, "Heading1", 0),
    (0, "Heading1", 0),
    (-1, "Heading1", 0),
    (True, "Heading1", 0),
])
def test_section_level_selects_heading_as_in_4_0_0(generator, level, style, toc_level):
    # 4.0.0 formatted the level into a style name and fell back to Heading1
    # for any name the stylesheet lacks, so no level value raised.
    story = generator._build_section_content(
        {"type": "text", "title": "Levels", "level": level, "content": "Body"}, _SampleStyles(),
    )
    heading = story[0]
    assert heading.style.name == style
    assert heading._toc_entry[0] == toc_level


def test_report_with_string_and_none_levels_renders_with_contents(generator, tmp_path):
    report = generator.create_comprehensive_report("Levels", sections=[
        {"type": "text", "title": "Second level", "level": "2", "content": "Body two"},
        {"type": "text", "title": "Default level", "level": None, "content": "Body one"},
        {"type": "text", "title": "Odd level", "level": "abc", "content": "Body odd"},
    ])
    output = tmp_path / "levels.pdf"
    generator.generate_pdf_report(report, str(output))
    text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
    for expected in ("Second level", "Default level", "Odd level", "Body two"):
        assert expected in text


@pytest.mark.parametrize("section_type, key", [("charts", "charts"), ("maps", "maps")])
def test_none_images_render_heading_and_description_as_in_4_0_0(
    generator, tmp_path, section_type, key,
):
    output = tmp_path / f"{key}-none.pdf"
    generator.generate_pdf_report({"sections": [{
        "type": section_type, "title": "Image heading",
        "content": {key: None, "description": "Image description"},
    }]}, str(output))
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Image heading" in text and "Image description" in text
    assert image_count(reader) == 0
