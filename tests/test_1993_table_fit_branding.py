"""Regression tests for #1993, #1789 and #1588 item 1.

#1993: tables from ``ReportGenerator.add_table_section`` ran off the page and
ignored the branding colours. #1789 / #1588 item 1: ``generate_pdf_report``
built its page template without the client's branding, so headers, footers,
page numbers and margins never followed it.

Several cases come from the independent review of the earlier attempt at
#1993 (PR #2002); they pin behaviour that must not regress while fixing it.
"""

import inspect
import logging

import pytest

pytest.importorskip("reportlab")
import requests
from matplotlib import colors as mcolors
from PyPDF2 import PdfReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, Paragraph, Table

from siege_utilities import ReportGenerator
from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator
from siege_utilities.reporting.client_branding import ClientBrandingManager
from siege_utilities.reporting.templates import base_template

LONG = (
    "Audit Foodservice items for stock and readiness, especially GG MEATBALL, "
    "MTO CHICKEN BOOM SANDWICH, BF CHORIZO AND AMERICAN, BF BURR CHORIZO, and "
    "BF BURR PINTO BEANS."
)
FRAME_PADDING = 12  # ReportLab Frame default: 6 pt on each side.


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Keep branding/image caches out of the real home; never touch the network."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    calls = []

    def offline_get(url, *args, **kwargs):
        calls.append(url)
        raise requests.exceptions.ConnectionError(f"offline test: {url}")

    monkeypatch.setattr(base_template.requests, "get", offline_get)
    return calls


def _text(path):
    return " ".join(" ".join(page.extract_text().split()) for page in PdfReader(str(path)).pages)


def _page_texts(path):
    return [page.extract_text() for page in PdfReader(str(path)).pages]


def _doc_with_table(rg, data, headers=None):
    doc = rg.create_comprehensive_report(title="t", report_type="daily", table_of_contents=False)
    rg.add_table_section(doc, "Sec", data, headers=headers)
    return doc


def _render(rg, where, data, headers=None):
    where.mkdir(parents=True, exist_ok=True)
    out = where / "out.pdf"
    rg.generate_pdf_report(_doc_with_table(rg, data, headers), str(out))
    return out


def _table(rg, where, data, headers=None):
    """Build the table flowable; keep the original cells before wrap replaces them."""
    where.mkdir(parents=True, exist_ok=True)
    doc = _doc_with_table(rg, data, headers)
    template = rg._get_template(str(where / "flow.pdf"))
    section = [s for s in doc["sections"] if s.get("type") == "table"][0]
    story = rg._build_section_content(section, template)
    table = [f for f in story if isinstance(f, Table)][0]
    # Once wrapped, ReportLab holds a flowable cell as a one-item tuple.
    table.su_cells = [
        [cell[0] if isinstance(cell, tuple) and len(cell) == 1 and isinstance(cell[0], Flowable)
         else cell for cell in row]
        for row in table._cellvalues
    ]
    avail = template.doc.width - FRAME_PADDING
    table.wrap(avail, template.doc.height - FRAME_PADDING)
    return table, avail


def _rgba(colour):
    return tuple(round(float(part), 3) for part in colour.rgba())


def _luminance(rgb):
    def channel(value):
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = (channel(part) for part in rgb[:3])
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first, second):
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _header_bg(table):
    return [cmd[3] for cmd in table._bkgrndcmds if cmd[0] == "BACKGROUND"][0]


def _header_text_colour(table):
    cell = table.su_cells[0][0]
    if isinstance(cell, Paragraph):
        return cell.style.textColor
    return table._cellStyles[0][0].color


def _branded(**colours):
    return {"name": "Demo", "colors": colours, "fonts": {}}


# --- #1993: the table fits the frame -----------------------------------------------------

def test_issue_table_fits_the_frame(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, avail = _table(rg, tmp_path / "o", [["Manager", LONG, "Before 9am"]],
                          headers=["Owner", "Action", "Due"])
    assert sum(table._colWidths) <= avail + 0.01


def test_narrow_columns_keep_their_width_and_long_column_takes_the_rest(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, avail = _table(rg, tmp_path / "o", [["Manager", LONG, "Before 9am"]],
                          headers=["Owner", "Action", "Due"])
    owner, action, due = table._colWidths
    assert owner < 80 and due < 80, table._colWidths
    assert action == pytest.approx(avail - owner - due)
    # Short cells stay as they were; only the long column is wrapped.
    assert table.su_cells[1][0] == "Manager"
    assert isinstance(table.su_cells[1][1], Paragraph)


def test_table_that_fits_is_left_exactly_as_before(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [["a", 1, None]], headers=["A", "B", "C"])
    assert table._argW == [None, None, None]
    # ReportLab itself normalises a None cell to "" (unchanged legacy behaviour).
    assert table.su_cells == [["A", "B", "C"], ["a", 1, ""]]
    assert table.splitInRow == 0


def test_ten_column_row_with_an_email_stays_on_one_line(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    row = ["alexandria.ocasio@example.org"] + [str(i) for i in range(9)]
    table, avail = _table(rg, tmp_path / "o", [row], headers=["email"] + [f"c{i}" for i in range(9)])
    assert sum(table._colWidths) <= avail + 0.01
    assert table._rowHeights[1] < 30, table._rowHeights


def test_eight_numeric_columns_stay_on_one_line(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [[1234567.89] * 8], headers=[f"c{i}" for i in range(8)])
    assert table._rowHeights[1] < 25, table._rowHeights


def test_wide_numeric_table_fits_without_wrapping_short_columns(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    row = [LONG] + [1234567.89] * 5
    table, avail = _table(rg, tmp_path / "o", [row], headers=["note"] + [f"c{i}" for i in range(5)])
    assert sum(table._colWidths) <= avail + 0.01
    assert table.su_cells[1][1:] == [1234567.89] * 5


def test_too_many_columns_logs_a_warning_and_still_writes(tmp_path, caplog):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    row = [LONG] * 30
    with caplog.at_level(logging.WARNING, logger="siege_utilities.reporting.report_generator"):
        out = _render(rg, tmp_path / "o", [row], headers=[f"c{i}" for i in range(30)])
    assert out.is_file()
    assert any("'Sec'" in record.getMessage() and "30 columns" in record.getMessage()
               for record in caplog.records)


# --- #1993: cells ---------------------------------------------------------------------------

def test_caller_paragraph_cell_is_kept_as_is_when_the_table_is_fitted(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    cell = Paragraph("caller wrapped text", getSampleStyleSheet()["BodyText"])
    table, avail = _table(rg, tmp_path / "o", [[cell, LONG, "x"]], headers=["A", "B", "C"])
    assert table.su_cells[1][0] is cell
    assert sum(table._colWidths) <= avail + 0.01


def test_caller_paragraph_cell_prints_its_text(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    cell = Paragraph("wrapped cell text", getSampleStyleSheet()["BodyText"])
    text = _text(_render(rg, tmp_path / "o", [[cell, LONG]], headers=["A", "B"]))
    assert "wrapped cell text" in text
    assert "Paragraph(" not in text


def test_facade_table_prints_cell_text_not_an_object_dump(tmp_path):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path / "o")
    path = gen.create_website_performance_report(
        {"load_time": 1.25, "tables": [{"title": "Pages", "headers": ["Page", "Views"],
                                        "data": [["/home", 1234], ["/about", 56]]}]},
        ["load_time"], "Website")
    text = _text(path)
    assert "/home" in text and "1234" in text
    assert "Paragraph(" not in text and "caseSensitive" not in text


def test_facade_wide_dataframe_keeps_its_page_count(tmp_path):
    import pandas as pd
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path / "o")
    frame = pd.DataFrame({f"c{i}": range(5) for i in range(40)})
    path = gen.create_custom_analytics_report("dataframe", frame, {"title": "Wide"})
    assert len(PdfReader(str(path)).pages) <= 10


def test_facade_dataframe_of_sentences_writes_a_pdf(tmp_path):
    import pandas as pd
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path / "o")
    frame = pd.DataFrame({f"c{i}": ["Stock and readiness check for the morning shift"] * 5
                          for i in range(12)})
    path = gen.create_custom_analytics_report("dataframe", frame, {"title": "Sentences"})
    # ReportLab sizes this all-Paragraph table itself, as before; at twelve
    # columns it breaks long words, so compare without spaces.
    assert "morningshift" in _text(path).replace(" ", "")


def test_none_cell_in_a_wrapped_column_prints_empty(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [[LONG, "x"], [None, "y"]], headers=["A", "B"])
    assert isinstance(table.su_cells[2][0], Paragraph)
    assert table.su_cells[2][0].getPlainText() == ""
    text = _text(_render(rg, tmp_path / "p", [[LONG, "x"], [None, "y"]], headers=["A", "B"]))
    assert "None" not in text


def test_newlines_in_a_wrapped_cell_keep_their_lines(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    lines, _ = _table(rg, tmp_path / "a", [["a\nb\nc\nd\ne\nf " + LONG, "x"]], headers=["A", "B"])
    flat, _ = _table(rg, tmp_path / "b", [["a b c d e f " + LONG, "x"]], headers=["A", "B"])
    assert isinstance(lines.su_cells[1][0], Paragraph)
    assert lines._rowHeights[1] > flat._rowHeights[1] + 40, (lines._rowHeights, flat._rowHeights)


def test_ragged_rows_in_a_fitted_table_render(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    text = _text(_render(rg, tmp_path / "o", [[LONG, "x", "ZZLAST"], ["short"]],
                         headers=["A", "B", "C"]))
    assert "ZZLAST" in text and "short" in text


def test_markup_in_a_wrapped_cell_prints_literally(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    text = _text(_render(rg, tmp_path / "o", [["<b>bold</b> & co <3 " + LONG, "x"]],
                         headers=["A", "B"]))
    assert "<b>bold</b> & co <3" in text


@pytest.mark.parametrize("columns,chars", [(3, 3000), (6, 1000), (12, 400), (1, 20000)])
def test_long_cell_splits_across_pages_instead_of_failing(tmp_path, columns, chars):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    words = ("lorem ipsum dolor sit amet " * (chars // 27 + 1))[:chars] + " ZZEND"
    row = [words] + [str(i) for i in range(columns - 1)]
    out = _render(rg, tmp_path / "o", [row], headers=[f"c{i}" for i in range(columns)])
    assert "ZZEND" in _text(out), "the end of the long cell is missing from the PDF"


def test_rows_are_split_only_when_a_row_is_taller_than_the_frame(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    short, _ = _table(rg, tmp_path / "a", [[LONG, "x"]], headers=["A", "B"])
    tall, _ = _table(rg, tmp_path / "b", [[LONG * 60, "x"]], headers=["A", "B"])
    frame_height = rg._get_template(str(tmp_path / "t.pdf")).doc.height - FRAME_PADDING
    assert len(short._rowHeights) == 2
    # The tall row becomes several rows, each fitting a page under the header;
    # ReportLab's in-row splitting is never switched on.
    assert len(tall._rowHeights) > 2
    assert max(tall._rowHeights[1:]) <= frame_height - tall._rowHeights[0]
    assert short.splitInRow == tall.splitInRow == 0
    assert tall.su_cells[-1][1] == ""


# --- #1993: styling -----------------------------------------------------------------------

UNBRANDED_COMMANDS = [
    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 10),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 1), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]


def test_unbranded_table_style_is_unchanged(tmp_path, monkeypatch):
    import siege_utilities.reporting.report_generator as rgmod
    seen = []
    real = rgmod.TableStyle

    def spy(commands, *args, **kwargs):
        seen.append(list(commands))
        return real(commands, *args, **kwargs)

    monkeypatch.setattr(rgmod, "TableStyle", spy)
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    _table(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    _table(rg, tmp_path / "p", [[LONG, "b"]], headers=["A", "B"])
    assert seen == [UNBRANDED_COMMANDS, UNBRANDED_COMMANDS]


def test_unbranded_wrapped_cells_keep_the_table_font_colour_and_centre(tmp_path):
    from reportlab.lib.enums import TA_CENTER
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [[LONG, "x"]], headers=["A" * 300, "B"])
    header, body = table.su_cells[0][0], table.su_cells[1][0]
    assert (header.style.fontName, header.style.fontSize) == ("Helvetica-Bold", 10)
    assert header.style.textColor == colors.whitesmoke
    assert (body.style.fontName, body.style.fontSize) == ("Helvetica", 9)
    assert body.style.textColor == colors.black
    assert header.style.alignment == body.style.alignment == TA_CENTER


@pytest.mark.parametrize("primary", ["navy", "tab:blue", "#abc", "#13293D", "#13293D80",
                                     (0.1, 0.2, 0.3), [0.1, 0.2, 0.3, 0.5]])
def test_header_colour_matches_the_chart_parser(tmp_path, primary):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                         branding_config=_branded(primary=primary))
    table, _ = _table(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    expected = tuple(round(part, 3) for part in mcolors.to_rgba(primary))
    assert _rgba(_header_bg(table)) == expected


@pytest.mark.parametrize("key,value", [("primary", "notacolour"), ("primary", 0x1000000),
                                       ("primary", True), ("text_color", "0xZZZZZZ"),
                                       ("text_color", "#12"), ("primary", (2, 0, 0)),
                                       ("accent", "nope"), ("header_footer_text_color", "zz"),
                                       ("text_color", None), ("header_footer_text_color", None),
                                       ("primary", None)])
def test_invalid_brand_colour_raises_a_named_error_when_created(tmp_path, key, value):
    from siege_utilities.reporting.client_branding import BrandingColorError
    colours = {"primary": "#13293D", key: value}
    with pytest.raises(BrandingColorError) as info:
        ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                        branding_config=_branded(**colours))
    assert isinstance(info.value, ValueError)
    assert f"colors.{key}" in str(info.value) and repr(value) in str(info.value)


def test_unread_colour_keys_are_not_validated(tmp_path):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                         branding_config=_branded(primary="#13293D", palette=["#000", "#fff"]))
    assert _render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"]).is_file()


def test_colors_that_are_not_a_mapping_raise_a_named_error(tmp_path):
    from siege_utilities.reporting.client_branding import BrandingColorError
    with pytest.raises(BrandingColorError, match="colors must be a mapping"):
        ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                        branding_config={"colors": ["#13293D"]})


def test_colour_changed_after_creation_raises_when_the_table_is_built(tmp_path):
    from siege_utilities.reporting.client_branding import BrandingColorError
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                         branding_config=_branded(primary="#13293D"))
    rg.branding_config["colors"]["primary"] = "notacolour"
    with pytest.raises(BrandingColorError, match="colors.primary"):
        _table(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])


def test_template_with_an_invalid_text_colour_raises_a_named_error(tmp_path):
    from siege_utilities.reporting.client_branding import BrandingColorError
    with pytest.raises(BrandingColorError, match="colors.text_color"):
        base_template.BaseReportTemplate(str(tmp_path / "t.pdf"),
                                         branding_config={"colors": {"text_color": "nope"}})


def test_colour_helpers_report_missing_parsers(monkeypatch):
    from siege_utilities.reporting import _brand_colors
    monkeypatch.setattr(_brand_colors, "Color", None)
    with pytest.raises(ImportError, match="ReportLab is required"):
        _brand_colors.brand_color("navy", "primary")
    monkeypatch.setattr(_brand_colors, "to_rgba", None)
    monkeypatch.setattr(_brand_colors, "toColor", None)
    with pytest.raises(ImportError, match="matplotlib or ReportLab"):
        _brand_colors._rgba("navy", "primary")
    # With nothing able to draw, validation has nothing to protect.
    assert _brand_colors.validate_brand_colors({"colors": {"primary": "nope"}}) is None


def test_reportlab_parser_is_used_without_matplotlib(monkeypatch):
    from siege_utilities.reporting import _brand_colors
    from siege_utilities.reporting.client_branding import BrandingColorError
    monkeypatch.setattr(_brand_colors, "to_rgba", None)
    assert _rgba(_brand_colors.brand_color("#13293D", "primary")) == (0.075, 0.161, 0.239, 1.0)
    with pytest.raises(BrandingColorError, match="colors.primary"):
        _brand_colors.brand_color("notacolour", "primary")


@pytest.mark.parametrize("primary", ["#FFFFFF", "#FFD100", "#1D365D", "#0B3D91", "#777777"])
@pytest.mark.parametrize("long_header", [False, True])
def test_header_text_is_readable_on_the_brand_colour(tmp_path, primary, long_header):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                         branding_config=_branded(primary=primary))
    headers = ["A" * (300 if long_header else 1), "B"]
    table, _ = _table(rg, tmp_path / "o", [["a", "b"]], headers=headers)
    assert isinstance(table.su_cells[0][0], Paragraph) is long_header
    ratio = _contrast(_header_bg(table).rgb(), _header_text_colour(table).rgb())
    assert ratio >= 4.5, f"contrast ratio {ratio:.2f}"


def test_text_color_reaches_body_cells_raw_and_wrapped(tmp_path):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                         branding_config=_branded(primary="#13293D", text_color="darkred"))
    table, _ = _table(rg, tmp_path / "o", [[LONG, "b"]], headers=["A", "B"])
    expected = tuple(round(part, 3) for part in mcolors.to_rgba("darkred"))
    assert _rgba(table.su_cells[1][0].style.textColor) == expected
    assert _rgba(table._cellStyles[1][1].color) == expected


def test_branded_grid_stays_visible_on_a_light_primary(tmp_path):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                         branding_config=_branded(primary="#FFFFFF", text_color="#222222"))
    table, _ = _table(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    grid = [cmd[4] for cmd in table._linecmds if cmd[0] == "GRID"][0]
    assert _contrast(grid.rgb(), (1.0, 1.0, 1.0)) >= 3.0


@pytest.mark.parametrize("primary", ["navy", "tab:blue", "C0"])
def test_registered_client_with_named_colours_renders(tmp_path, primary):
    branding = {"name": "Named", "fonts": {},
                "colors": {"primary": primary, "text_color": "black",
                           "header_footer_text_color": "dimgray"}}
    ClientBrandingManager().create_client_branding("Named", branding)
    rg = ReportGenerator(client_name="Named", output_dir=tmp_path / "o")
    assert rg.branding_config["colors"]["primary"] == primary
    out = _render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    assert out.is_file() and out.stat().st_size > 0


# --- ReportGenerator branding_config argument -----------------------------------------------

def test_branding_dict_is_copied_and_shared_with_charts(tmp_path):
    branding = _branded(primary="#13293D")
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    branding["colors"]["primary"] = "#FF0000"
    assert rg.branding_config["colors"]["primary"] == "#13293D"
    assert rg.chart_generator.branding_config["colors"]["primary"] == "#13293D"


def test_empty_branding_dict_means_unbranded_even_for_a_known_client(tmp_path):
    rg = ReportGenerator(client_name="siege_analytics", output_dir=tmp_path / "o", branding_config={})
    template = rg._get_template(str(tmp_path / "t.pdf"))
    assert rg.branding_config == {} and template.branding_config == {}
    table, _ = _table(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    assert _header_bg(table) == colors.grey


def test_branding_config_must_be_a_mapping(tmp_path):
    with pytest.raises(TypeError, match="branding_config"):
        ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config="navy")


# --- #1789 / #1588 item 1: the page template follows branding -----------------------------

def test_template_for_builtin_client_has_branding(tmp_path):
    rg = ReportGenerator(client_name="elect_info", output_dir=tmp_path / "o")
    template = rg._get_template(str(tmp_path / "t.pdf"))
    assert template.branding_config["header"]["left_text"] == "ElectInfo Analysis"


def test_builtin_client_margins_and_frame_width_reach_the_template(tmp_path):
    rg = ReportGenerator(client_name="siege_analytics", output_dir=tmp_path / "o")
    template = rg._get_template(str(tmp_path / "t.pdf"))
    assert template.doc.leftMargin == pytest.approx(54.0)
    assert template.doc.width == pytest.approx(612 - 2 * 54.0)


@pytest.mark.parametrize("table_of_contents", [False, True])
def test_branding_dict_header_footer_and_page_number_on_every_page(tmp_path, table_of_contents):
    branding = {
        "name": "Demo", "colors": {"primary": "#13293D", "text_color": "#222222"},
        "fonts": {"default_font": "Helvetica"},
        "header": {"left_text": "ZZHEADERLEFT", "right_text": "ZZHEADERRIGHT"},
        "footer": {"left_text": "ZZFOOTERLEFT", "right_text": "ZZFOOTERRIGHT",
                   "page_number_format": "ZZPAGE %s"},
    }
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    doc = rg.create_comprehensive_report(title="t", report_type="daily",
                                         table_of_contents=table_of_contents)
    for index in range(3):
        rg.add_text_section(doc, f"S{index}", "words " * 1500)
    out = tmp_path / "o" / "pages.pdf"
    rg.generate_pdf_report(doc, str(out))
    pages = _page_texts(out)
    assert len(pages) >= 3
    for number, text in enumerate(pages, 1):
        assert "ZZHEADERLEFT" in text, f"page {number} has no header"
        assert "ZZFOOTERLEFT" in text, f"page {number} has no footer"
        assert f"ZZPAGE {number}" in text, f"page {number} has no page number"


def test_builtin_client_header_text_is_in_the_pdf(tmp_path):
    rg = ReportGenerator(client_name="siege_analytics", output_dir=tmp_path / "o")
    text = _text(_render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"]))
    assert "Siege Analytics Report" in text
    assert "Prepared by: Siege Analytics" in text


def test_unbranded_report_has_no_header_or_footer(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    template = rg._get_template(str(tmp_path / "t.pdf"))
    assert template.branding_config == {}
    assert "Page 1" not in _text(_render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"]))


def test_template_config_path_still_wins_over_the_branding_dict(tmp_path):
    import yaml
    path = tmp_path / "b.yaml"
    path.write_text(yaml.safe_dump({"header": {"left_text": "FROM_YAML"}, "colors": {}}))
    rg = ReportGenerator(client_name="siege_analytics", output_dir=tmp_path / "o")
    template = rg._get_template(str(tmp_path / "t.pdf"), template_config=str(path))
    assert template.branding_config["header"]["left_text"] == "FROM_YAML"


def _png(path):
    from PIL import Image
    Image.new("RGB", (40, 20), (200, 30, 30)).save(path)
    return path


def _has_image(pdf_path):
    resources = PdfReader(str(pdf_path)).pages[0].get("/Resources") or {}
    return "/XObject" in resources


def _three_page_doc(rg):
    doc = rg.create_comprehensive_report(title="t", report_type="daily", table_of_contents=False)
    for index in range(3):
        rg.add_text_section(doc, f"S{index}", "words " * 1500)
    return doc


def test_remote_logo_makes_no_network_call_by_default(tmp_path, _isolated, caplog):
    import hashlib
    url = "https://siegeanalytics.com/logo.png"
    # Even a cached copy from an earlier opted-in build is not used.
    cache = tmp_path / "home" / ".siege_utilities" / "image_cache"
    cache.mkdir(parents=True)
    _png(cache / f"{hashlib.md5(url.encode()).hexdigest()}.png")
    rg = ReportGenerator(client_name="siege_analytics", output_dir=tmp_path / "o")
    out = tmp_path / "o" / "default.pdf"
    with caplog.at_level(logging.INFO, logger="siege_utilities.reporting.templates.base_template"):
        rg.generate_pdf_report(_three_page_doc(rg), str(out))
    assert _isolated == []
    assert "Siege Analytics Report" in _text(out)
    assert not _has_image(out)
    skipped = [r for r in caplog.records if "fetch_remote_assets=True" in r.getMessage()]
    assert len(skipped) == 1 and skipped[0].levelno == logging.INFO


def test_local_logo_path_is_drawn_without_opting_in(tmp_path, _isolated):
    logo = _png(tmp_path / "logo.png")
    branding = {"colors": {"primary": "#13293D"}, "header": {"left_text": "ZZHEADERLEFT"},
                "logo": {"image_url": str(logo), "width": 1.0, "height": 0.5}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    out = _render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    assert _isolated == []
    assert _has_image(out)


def test_opted_in_remote_logo_is_downloaded_once(tmp_path, monkeypatch):
    logo_bytes = _png(tmp_path / "remote.png").read_bytes()
    calls = []

    class Response:
        headers = {"Content-Type": "image/png"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield logo_bytes

    def fake_get(url, *args, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr(base_template.requests, "get", fake_get)
    rg = ReportGenerator(client_name="siege_analytics", output_dir=tmp_path / "o",
                         fetch_remote_assets=True)
    out = tmp_path / "o" / "remote.pdf"
    rg.generate_pdf_report(_three_page_doc(rg), str(out))
    assert calls == ["https://siegeanalytics.com/logo.png"]
    assert _has_image(out)


def test_unreachable_logo_is_tried_once_per_document(tmp_path, _isolated):
    rg = ReportGenerator(client_name="siege_analytics", output_dir=tmp_path / "o",
                         fetch_remote_assets=True)
    doc = rg.create_comprehensive_report(title="t", report_type="daily", table_of_contents=False)
    for index in range(3):
        rg.add_text_section(doc, f"S{index}", "words " * 1500)
    out = tmp_path / "o" / "logo.pdf"
    rg.generate_pdf_report(doc, str(out))
    assert len(PdfReader(str(out)).pages) >= 3
    assert _isolated == ["https://siegeanalytics.com/logo.png"]


def test_template_accepts_a_branding_dict_directly(tmp_path):
    branding = {"colors": {"text_color": "navy", "header_footer_text_color": "dimgray"},
                "page_margins": {"left": 0.5, "right": 0.5}}
    template = base_template.BaseReportTemplate(str(tmp_path / "t.pdf"), branding_config=branding)
    branding["colors"]["text_color"] = "red"
    assert template.branding_config["colors"]["text_color"] == "navy"
    assert template.doc.width == pytest.approx(612 - 72)
    expected = tuple(round(part, 3) for part in mcolors.to_rgba("navy"))
    assert _rgba(template.styles["BodyText"].textColor) == expected


def test_unregistered_brand_font_falls_back_to_helvetica(tmp_path, caplog):
    branding = {"colors": {"text_color": "#111111"}, "fonts": {"default_font": "No-Such-Font"},
                "header": {"left_text": "ZZHEADERLEFT"}}
    with caplog.at_level(logging.WARNING, logger="siege_utilities.reporting.templates.base_template"):
        rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
        out = _render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    assert "ZZHEADERLEFT" in _text(out)
    assert any("No-Such-Font" in record.getMessage() for record in caplog.records)
    template = rg._get_template(str(tmp_path / "t.pdf"))
    assert template.styles["h1"].fontName == "Helvetica-Bold"
    assert template.styles["BodyText"].fontName == "Helvetica"


def test_builtin_profile_with_a_font_that_may_be_missing_renders(tmp_path):
    rg = ReportGenerator(client_name="masai_interactive", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    assert "Masai Interactive Report" in _text(out)


def test_branding_with_empty_colour_and_font_sections_renders(tmp_path):
    branding = {"colors": None, "fonts": None, "header": {"left_text": "ZZHEADERLEFT"}}
    template = base_template.BaseReportTemplate(str(tmp_path / "t.pdf"), branding_config=branding)
    assert template.styles["BodyText"].fontName == "Helvetica"


def test_template_rejects_both_a_path_and_a_dict(tmp_path):
    with pytest.raises(ValueError, match="branding_config"):
        base_template.BaseReportTemplate(str(tmp_path / "t.pdf"), branding_config_path=tmp_path / "x.yaml",
                                         branding_config={"colors": {}})


def test_signature_documents_the_branding_argument():
    assert "branding_config" in inspect.signature(ReportGenerator.__init__).parameters
    assert "branding_config" in (ReportGenerator.__init__.__doc__ or "")


# --- Review round 2: tokens on a float boundary, formatted numbers, tall cells and headers ----

def _laid_out_lines(cell):
    """Number of laid-out lines of a wrapped cell; a plain string counts as one."""
    if not isinstance(cell, Paragraph):
        return 1
    return len(cell.blPara.lines)


def _built_table(rg, template, data, repeat_rows=1):
    table = rg._build_table(data, repeat_rows, "Sec", template)
    table.wrap(template.doc.width - FRAME_PADDING, template.doc.height - FRAME_PADDING)
    return table, [
        [cell[0] if isinstance(cell, tuple) and len(cell) == 1 and isinstance(cell[0], Flowable)
         else cell for cell in row]
        for row in table._cellvalues
    ]


def test_float_cells_on_a_width_boundary_are_not_split(tmp_path):
    import pandas as pd
    note = "Amended filing received after the deadline; totals restated by the committee treasurer."
    frame = pd.DataFrame({
        "County": ["Travis", "Harris"],
        "Total receipts for the first quarter": [123456789.01, 234567890.12],
        "Total receipts for the second quarter": [345678901.23, 456789012.34],
        "Total receipts for the third quarter": [567890123.45, 678901234.56],
        "Total receipts for the fourth quarter": [789012345.67, 890123456.78],
        "Year to date total receipts": [912345678.91, 923456789.12],
        "Notes": [note, note],
    })
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, avail = _table(rg, tmp_path / "o", frame)
    assert sum(table._colWidths) <= avail + 0.01
    split = [(row, column) for row in (1, 2) for column in range(1, 6)
             if _laid_out_lines(table.su_cells[row][column]) != 1]
    assert not split, f"float cells drawn on two lines: {split}"


def test_number_shapes_are_never_split_at_their_floor(tmp_path):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    template = rg._get_template(str(tmp_path / "flow.pdf"))
    short_words = "aa bb cc dd ee ff gg hh " * 10
    numbers = [1.5e+20, -2.25e-07, 1e+300, 123456789.123456789, 0.1 + 0.2]
    for digits in range(6, 26):
        base = int("1234567890123456789012345678"[:digits])
        numbers += [base, -base]
        for decimals in (1, 2, 3):
            if digits <= 15:
                value = float(f"{str(base)[:-decimals]}.{str(base)[-decimals:]}")
                numbers += [value, -value]
    pinned, split = 0, []
    for number in numbers:
        for columns in (3, 6, 8, 10):
            data = [["n"] + ["a"] * columns, [short_words] * (columns + 1), [number] + ["x"] * columns]
            table, cells = _built_table(rg, template, data)
            floor = stringWidth(str(number), "Helvetica", 9) + 12
            if abs(table._colWidths[0] - floor) <= 1.5:
                pinned += 1
            if _laid_out_lines(cells[2][0]) != 1:
                split.append((number, columns))
    assert pinned > 50, "the sweep no longer pins numbers at their floor"
    assert not split, split[:10]


@pytest.mark.parametrize("word", ["jacqueline.ocasio@example.org", "nathaniel.ocasio@example.com"]
                         + ["w" * size for size in range(6, 30)])
def test_words_at_their_floor_are_not_broken_when_the_table_fits(tmp_path, word):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    template = rg._get_template(str(tmp_path / "flow.pdf"))
    short_words = "aa bb cc dd ee ff gg hh " * 10
    data = [["h", "a", "b", "c"], [short_words] * 4, [word, "x", "y", "z"]]
    table, cells = _built_table(rg, template, data)
    assert sum(table._colWidths) <= template.doc.width - FRAME_PADDING + 0.01
    assert _laid_out_lines(cells[2][0]) == 1, cells[2][0].blPara.lines


@pytest.mark.parametrize("value", ["1,234,567.89", "$1,234,567.89", "45.25%", "(1,234,567)",
                                   "2026-11-23", "512-555-0100", "78701-1234"])
def test_formatted_numbers_are_not_split_in_a_crowded_table(tmp_path, value):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [[value] * 14], headers=[f"c{i}" for i in range(14)])
    assert all(_laid_out_lines(cell) == 1 for cell in table.su_cells[1]), table.su_cells[1][0]


def test_words_still_wrap_in_a_crowded_table(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, avail = _table(rg, tmp_path / "o", [[LONG] * 6], headers=[f"c{i}" for i in range(6)])
    assert sum(table._colWidths) <= avail + 0.01
    assert _laid_out_lines(table.su_cells[1][0]) > 1


_TALL_CELL_SCRIPT = """
import sys
from pathlib import Path
from PyPDF2 import PdfReader
from siege_utilities import ReportGenerator
lines, out = int(sys.argv[1]), Path(sys.argv[2])
text = "\\n".join(f"ZQ{i:04d}" for i in range(lines))
rg = ReportGenerator(client_name="NoBrand", output_dir=out.parent)
doc = rg.create_comprehensive_report(title="t", report_type="daily", table_of_contents=False)
rg.add_table_section(doc, "Sec", [[text, "a"]], headers=["A", "B"])
rg.generate_pdf_report(doc, str(out))
seen = []
for page in PdfReader(str(out)).pages:
    def visit(text, cm, tm, font, size):
        if text.startswith("ZQ"):
            # Page y of the text origin: the text matrix composed with the CTM.
            seen.append((text.strip(), cm[1] * tm[4] + cm[3] * tm[5] + cm[5]))
    page.extract_text(visitor_text=visit)
print("TOKENS", len(seen), len({token for token, _ in seen}))
print("YRANGE", min(y for _, y in seen), max(y for _, y in seen))
"""


@pytest.mark.parametrize("lines", [56, 96, 200])
def test_tall_plain_multi_line_cell_splits_without_hanging(tmp_path, lines):
    import os
    import subprocess
    import sys
    from pathlib import Path

    import siege_utilities
    script = tmp_path / "tall.py"
    script.write_text(_TALL_CELL_SCRIPT)
    env = dict(os.environ, PYTHONPATH=str(Path(siege_utilities.__file__).parents[1]),
               HOME=str(tmp_path / "home"))
    try:
        proc = subprocess.run([sys.executable, str(script), str(lines), str(tmp_path / "tall.pdf")],
                              capture_output=True, text=True, timeout=120, env=env, cwd=str(tmp_path))
    except subprocess.TimeoutExpired:
        pytest.fail(f"a {lines}-line cell did not finish building within 120 s")
    assert proc.returncode == 0, proc.stderr[-800:]
    report = dict(line.split(" ", 1) for line in proc.stdout.splitlines() if " " in line)
    total, distinct = map(int, report["TOKENS"].split())
    assert total == distinct == lines, report
    low, high = map(float, report["YRANGE"].split())
    # Every line is drawn inside the 72 pt margins of the letter page.
    assert 72 - 1 <= low and high <= 792 - 72 + 1, report


def test_tall_plain_multi_line_cell_keeps_its_lines(tmp_path):
    from reportlab.platypus import XPreformatted
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    text = "\n".join(f"ZQ{i:05d}" for i in range(80))
    table, _ = _table(rg, tmp_path / "o", [[text, "a"]], headers=["A", "B"])
    assert table.splitInRow == 0
    pieces = [row[0] for row in table.su_cells[1:]]
    assert len(pieces) > 1 and all(isinstance(piece, XPreformatted) for piece in pieces)
    # Every line is drawn once, in order, inside the page.
    out = _render(rg, tmp_path / "p", [[text, "a"]], headers=["A", "B"])
    seen = _token_positions(out, "ZQ")
    assert [token for token, _, _ in sorted(seen, key=lambda s: (s[1], -s[2]))] \
        == [f"ZQ{i:05d}" for i in range(80)]


def test_an_image_cell_in_a_wide_table_is_fitted(tmp_path):
    from reportlab.platypus import Image as RLImage
    picture = _png(tmp_path / "small.png")
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    data = [[RLImage(str(picture), width=60, height=30), LONG, "x"]]
    table, avail = _table(rg, tmp_path / "o", data, headers=["A", "B", "C"])
    assert sum(table._colWidths) <= avail + 0.01
    out = _render(rg, tmp_path / "p", data, headers=["A", "B", "C"])
    assert any("/XObject" in (page.get("/Resources") or {}) for page in PdfReader(str(out)).pages)


@pytest.mark.parametrize("columns,words", [(19, 20), (24, 20), (16, 30), (24, 30), (12, 45), (24, 45)])
def test_long_repeated_headers_fall_back_instead_of_failing(tmp_path, caplog, columns, words):
    import pandas as pd
    question = ("How satisfied are you with the overall quality of the service that the department "
                "provided during your most recent visit and would you recommend it to a colleague or "
                "a member of your family if they asked you for advice about where to go next time").split()
    header = " ".join(question[:words])
    frame = pd.DataFrame({f"Q{i}. {header}": ["Agree", "Disagree", "Neutral"] for i in range(columns)})
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    with caplog.at_level(logging.WARNING, logger="siege_utilities.reporting.report_generator"):
        out = _render(rg, tmp_path / "o", frame)
    assert out.is_file()
    assert "Agree" in _text(out)


def test_header_taller_than_a_page_falls_back_with_a_warning(tmp_path, caplog):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    with caplog.at_level(logging.WARNING, logger="siege_utilities.reporting.report_generator"):
        table, _ = _table(rg, tmp_path / "o", [["a", "b"]], headers=[LONG * 25, "B"])
        out = _render(rg, tmp_path / "p", [["a", "b"]], headers=[LONG * 25, "B"])
    assert out.is_file()
    assert table.su_cells[0][0] == LONG * 25  # unfitted, as before
    assert any("header row" in record.getMessage() and "'Sec'" in record.getMessage()
               for record in caplog.records)


# --- Review round 2: colour forms, branding shape, logos, positions ------------------------

@pytest.mark.parametrize("value", ["0x13293D", 0x13293D])
def test_hex_integer_colour_forms_still_work_for_template_yaml(tmp_path, value):
    import yaml
    path = tmp_path / "b.yaml"
    path.write_text(yaml.safe_dump({"colors": {"text_color": value, "header_footer_text_color": value},
                                    "header": {"left_text": "ZZHEADERLEFT"}}))
    template = base_template.BaseReportTemplate(str(tmp_path / "t.pdf"), branding_config_path=path)
    assert _rgba(template.styles["BodyText"].textColor) == _rgba(colors.HexColor(0x13293D))
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    doc = _doc_with_table(rg, [["a", "b"]], headers=["A", "B"])
    out = tmp_path / "o" / "yaml.pdf"
    rg.generate_pdf_report(doc, str(out), template_config=str(path))
    assert "ZZHEADERLEFT" in _text(out)


@pytest.mark.parametrize("value", ["0x222222", 0x222222])
def test_registered_profile_with_hex_integer_text_colours_renders(tmp_path, value):
    branding = {"name": "Hexy", "fonts": {},
                "colors": {"primary": "#13293D", "text_color": value, "header_footer_text_color": value}}
    ClientBrandingManager().create_client_branding("Hexy", branding)
    rg = ReportGenerator(client_name="Hexy", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    assert _rgba(table._cellStyles[1][0].color) == _rgba(colors.HexColor(0x222222))
    assert _render(rg, tmp_path / "p", [["a", "b"]], headers=["A", "B"]).is_file()


@pytest.mark.parametrize("key", ["primary", "secondary", "accent"])
@pytest.mark.parametrize("value", ["0x13293D", 0x13293D])
def test_chart_colours_in_hex_integer_form_raise_a_named_error(tmp_path, key, value):
    from siege_utilities.reporting.client_branding import BrandingColorError
    with pytest.raises(BrandingColorError, match=f"colors.{key}.*charts cannot read"):
        ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                        branding_config={"colors": {key: value}})


@pytest.mark.parametrize("branding,key", [
    ({"fonts": "Helvetica"}, "fonts"),
    ({"fonts": {"h1": "big"}}, "fonts.h1"),
    ({"fonts": {"h1": {"font_size": "20"}}}, "fonts.h1.font_size"),
    ({"fonts": {"default_font": 12}}, "fonts.default_font"),
    ({"header": "Acme"}, "header"),
    ({"footer": ["Acme"]}, "footer"),
    ({"header": {"left_text": 5}}, "header.left_text"),
    ({"logo": "logo.png"}, "logo"),
    ({"logo": {"image_url": 5}}, "logo.image_url"),
    ({"logo": {"image_url": "x.png", "width": "wide"}}, "logo.width"),
    ({"page_margins": [1, 1, 1, 1]}, "page_margins"),
    ({"page_margins": {"left": "1"}}, "page_margins.left"),
    ({"page_margins": {"left": -1}}, "page_margins.left"),
    ({"footer": {"page_number_format": "Page {page}"}}, "footer.page_number_format"),
    ({"footer": {"page_number_format": "Page %s of %s"}}, "footer.page_number_format"),
    ({"footer": {"page_number_format": None}}, "footer.page_number_format"),
])
def test_malformed_branding_entries_raise_a_named_error(tmp_path, branding, key):
    from siege_utilities.reporting.client_branding import BrandingConfigError
    with pytest.raises(BrandingConfigError) as info:
        ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    assert isinstance(info.value, ValueError)
    assert key in str(info.value)
    with pytest.raises(BrandingConfigError, match=key.replace(".", r"\.")):
        base_template.BaseReportTemplate(str(tmp_path / "t.pdf"), branding_config=branding)


def test_margins_leaving_no_frame_raise_a_named_error(tmp_path):
    from siege_utilities.reporting.client_branding import BrandingConfigError
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o",
                         branding_config={"page_margins": {"left": 4, "right": 4}})
    with pytest.raises(BrandingConfigError, match="page_margins"):
        rg._get_template(str(tmp_path / "t.pdf"))


def test_template_yaml_that_is_not_a_mapping_raises_a_named_error(tmp_path):
    from siege_utilities.reporting.client_branding import BrandingConfigError
    path = tmp_path / "b.yaml"
    path.write_text("- just\n- a list\n")
    with pytest.raises(BrandingConfigError, match="mapping"):
        base_template.BaseReportTemplate(str(tmp_path / "t.pdf"), branding_config_path=path)


def test_unset_branding_sections_are_treated_as_empty(tmp_path):
    branding = {"colors": {"primary": "#13293D"}, "header": None, "footer": None,
                "page_margins": None, "logo": None,
                "fonts": {"h1": None, "BodyText": {"font_size": None}, "default_font": None}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    out = _render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"])
    assert out.is_file()
    template = rg._get_template(str(tmp_path / "t.pdf"))
    assert template.doc.leftMargin == pytest.approx(72.0)


@pytest.mark.parametrize("page_format", ["Page %d", "p. %s", "%s"])
def test_valid_page_number_formats_are_accepted(tmp_path, page_format):
    branding = {"colors": {"primary": "#13293D"}, "footer": {"page_number_format": page_format}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    assert _render(rg, tmp_path / "o", [["a", "b"]], headers=["A", "B"]).is_file()


def test_missing_local_logo_is_logged_once_per_document(tmp_path, caplog):
    branding = {"colors": {"primary": "#13293D"}, "header": {"left_text": "ZZHEADERLEFT"},
                "logo": {"image_url": str(tmp_path / "missing.png"), "width": 1.0, "height": 0.5}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    out = tmp_path / "o" / "missing.pdf"
    with caplog.at_level(logging.ERROR, logger="siege_utilities.reporting.templates.base_template"):
        rg.generate_pdf_report(_three_page_doc(rg), str(out))
    assert len(PdfReader(str(out)).pages) >= 3
    missing = [r for r in caplog.records if "Local image file not found" in r.getMessage()]
    assert len(missing) == 1


def test_left_header_and_footer_text_sit_inside_the_page_on_every_page(tmp_path):
    branding = {"colors": {"primary": "#13293D"},
                "header": {"left_text": "ZZHEADERLEFT"}, "footer": {"left_text": "ZZFOOTERLEFT"},
                "page_margins": {"left": 0.75, "right": 0.75, "top": 1.0, "bottom": 1.0}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
    out = tmp_path / "o" / "positions.pdf"
    rg.generate_pdf_report(_three_page_doc(rg), str(out))
    pages = PdfReader(str(out)).pages
    assert len(pages) >= 3
    for number, page in enumerate(pages, 1):
        found = {}

        def visit(text, cm, tm, font, size, found=found):
            for token in ("ZZHEADERLEFT", "ZZFOOTERLEFT"):
                if token in text:
                    found[token] = (cm[0] * tm[4] + cm[2] * tm[5] + cm[4],
                                    cm[1] * tm[4] + cm[3] * tm[5] + cm[5])

        page.extract_text(visitor_text=visit)
        assert set(found) == {"ZZHEADERLEFT", "ZZFOOTERLEFT"}, f"page {number}: {found}"
        header_x, header_y = found["ZZHEADERLEFT"]
        footer_x, footer_y = found["ZZFOOTERLEFT"]
        # Left texts start at the 0.75 in left margin, in the top and bottom margin bands.
        assert header_x == pytest.approx(54.0, abs=1.0) and footer_x == pytest.approx(54.0, abs=1.0)
        assert 792 - 72 < header_y < 792 and 0 < footer_y < 72, (number, found)


# --- Facade generators pass branding and the remote-logo opt-in through (S4-6) ---------------

class _QuietConnector:
    """A social connector with one account and no posts or insights."""

    platform_name = "fakebook"

    def get_account_info(self):
        return {"followers_count": 10, "following_count": 5}

    def get_account_insights(self, start_date, end_date):
        import pandas as pd
        return pd.DataFrame()

    def get_posts(self, start_date, end_date, *, limit):
        import pandas as pd
        return pd.DataFrame()


def _facade_pdf(kind, client, output_dir, **options):
    from datetime import date

    from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator
    if kind == "analytics":
        generator = AnalyticsReportGenerator(client, output_dir=output_dir, **options)
        path = generator.create_website_performance_report(
            {"load_time": 1.25, "tables": [{"title": "Pages", "headers": ["Page", "Views"],
                                            "data": [["/home", 1234]]}]},
            ["load_time"], "Website")
    else:
        generator = SocialMediaReportGenerator(client, output_dir=output_dir, **options)
        path = generator.create_social_media_report(
            [_QuietConnector()], date(2026, 1, 1), date(2026, 3, 31), title="Social")
    return generator, path


@pytest.mark.parametrize("kind", ["analytics", "social"])
def test_facade_report_for_a_builtin_client_makes_no_network_call_by_default(tmp_path, _isolated, kind):
    generator, path = _facade_pdf(kind, "siege_analytics", tmp_path / "o")
    assert generator.report_generator.fetch_remote_assets is False
    assert _isolated == []
    assert "Siege Analytics Report" in _text(path)
    assert not _has_image(path)


@pytest.mark.parametrize("kind", ["analytics", "social"])
def test_facade_report_can_opt_in_to_remote_logos(tmp_path, monkeypatch, kind):
    logo_bytes = _png(tmp_path / "remote.png").read_bytes()
    calls = []

    class Response:
        headers = {"Content-Type": "image/png"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield logo_bytes

    def fake_get(url, *args, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr(base_template.requests, "get", fake_get)
    generator, path = _facade_pdf(kind, "siege_analytics", tmp_path / "o", fetch_remote_assets=True)
    assert generator.report_generator.fetch_remote_assets is True
    assert calls == ["https://siegeanalytics.com/logo.png"]
    assert _has_image(path)


@pytest.mark.parametrize("kind", ["analytics", "social"])
def test_facade_report_takes_a_branding_dict(tmp_path, kind):
    branding = {"colors": {"primary": "#13293D"}, "header": {"left_text": "ZZFACADEHEADER"}}
    generator, path = _facade_pdf(kind, "Acme", tmp_path / "o", branding_config=branding)
    branding["header"]["left_text"] = "changed"
    assert generator.report_generator.branding_config["header"]["left_text"] == "ZZFACADEHEADER"
    assert "ZZFACADEHEADER" in _text(path)


@pytest.mark.parametrize("kind", ["analytics", "social"])
def test_facade_rejects_a_malformed_branding_dict(tmp_path, kind):
    from siege_utilities.reporting.client_branding import BrandingConfigError
    from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator
    facade = AnalyticsReportGenerator if kind == "analytics" else SocialMediaReportGenerator
    with pytest.raises(BrandingConfigError, match="page_margins"):
        facade("Acme", output_dir=tmp_path / "o", branding_config={"page_margins": "wide"})


# --- Review round 4: rows taller than a page never lose or misplace content --------------------

def _lines_of(prefix, count):
    return "\n".join(f"{prefix}{i:05d}" for i in range(count))


def _token_positions(pdf_path, prefix):
    """[(token, page, y)] for every drawn token starting with *prefix* (y: page baseline)."""
    found = []
    for number, page in enumerate(PdfReader(str(pdf_path)).pages, 1):
        def visit(text, cm, tm, font, size, number=number):
            for token in text.split():
                if token.startswith(prefix):
                    found.append((token, number, cm[1] * tm[4] + cm[3] * tm[5] + cm[5]))
        page.extract_text(visitor_text=visit)
    return found


def _assert_all_lines_on_the_page(pdf_path, prefix, count):
    seen = _token_positions(pdf_path, prefix)
    tokens = [token for token, _, _ in seen]
    assert sorted(tokens) == [f"{prefix}{i:05d}" for i in range(count)], (len(tokens), count)
    # Inside the 72 pt margins of the letter page (with slack for text-matrix rounding).
    outside = [entry for entry in seen if not 72 - 14 <= entry[2] <= 720 + 14]
    assert not outside, outside[:5]


class _MultiLineObject:
    def __str__(self):
        return "OBJLINE1\nOBJLINE2\nOBJLINE3"


@pytest.mark.parametrize("companion,token", [
    (987654.25, "987654.25"), (4242, "4242"), (True, "True"),
    ("plain text", "plain"), (None, None),
    (b"BYTESVALUE", "BYTESVALUE"),
    (__import__("decimal").Decimal("12.75"), "12.75"),
    (__import__("pandas").Timestamp("2026-11-23"), "2026-11-23"),
    (_MultiLineObject(), "OBJLINE3"),
])
def test_cells_beside_a_tall_cell_are_all_drawn(tmp_path, companion, token):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", [[_lines_of("ZQ", 100), companion, "ZZEND"]],
                  headers=["A", "B", "C"])
    _assert_all_lines_on_the_page(out, "ZQ", 100)
    text = _text(out)
    assert text.count("ZZEND") == 1
    if token is not None:
        assert text.count(token) == 1, (token, text.count(token))


def test_a_dataframe_row_with_a_long_note_keeps_its_numbers_and_dates(tmp_path):
    import pandas as pd
    frame = pd.DataFrame({"note": [_lines_of("ZQ", 100), "short"], "amount": [1234.5, 99.5],
                          "count": [7, 8],
                          "when": [pd.Timestamp("2026-11-23"), pd.Timestamp("2026-11-24")]})
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", frame)
    _assert_all_lines_on_the_page(out, "ZQ", 100)
    text = _text(out)
    assert {token: text.count(token) for token in ("1234.5", "99.5", "2026-11-23", "2026-11-24")} \
        == {"1234.5": 1, "99.5": 1, "2026-11-23": 1, "2026-11-24": 1}


@pytest.mark.parametrize("first,second", [(147, 23), (201, 100), (330, 100)])
def test_two_multi_line_cells_in_a_tall_row_stay_on_the_page(tmp_path, first, second):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", [[_lines_of("ZQ", first), _lines_of("ZR", second)]],
                  headers=["A", "B"])
    _assert_all_lines_on_the_page(out, "ZQ", first)
    _assert_all_lines_on_the_page(out, "ZR", second)


@pytest.mark.parametrize("lines", [96, 108, 109, 110, 113, 117, 256, 283])
def test_tall_cells_at_any_line_count_build(tmp_path, lines):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", [[_lines_of("ZQ", lines), "COMPANION"]], headers=["A", "B"])
    _assert_all_lines_on_the_page(out, "ZQ", lines)
    assert _text(out).count("COMPANION") == 1


def test_a_row_that_fits_stays_on_the_page_beside_a_tall_row(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", [[_lines_of("ZQ", 120), "a"], [_lines_of("ZR", 45), "b"]],
                  headers=["A", "B"])
    _assert_all_lines_on_the_page(out, "ZQ", 120)
    _assert_all_lines_on_the_page(out, "ZR", 45)


@pytest.mark.parametrize("data,headers,label", [
    ([[Paragraph(" ".join(f"ZQ{i:05d}" for i in range(800)), getSampleStyleSheet()["BodyText"]),
       "x\nCOMPANION\nz"]], ["A", "B"], "A"),
    ([[_lines_of("ZQ", 120)] + ["the quick brown fox jumps over the lazy dog near the river"] * 6
      + ["COMPANION"]], [f"c{i}" for i in range(8)], "c0"),
])
def test_tall_rows_repeat_the_header_once_per_page(tmp_path, data, headers, label):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", data, headers=headers)
    per_page = [sum(1 for line in text.splitlines() if line.strip() == label)
                for text in _page_texts(out)]
    assert max(per_page) <= 1, per_page
    assert _text(out).count("COMPANION") == 1


def test_tall_first_row_without_headers_keeps_the_header_look(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [[_lines_of("ZQ", 150), "x"], ["a", "b"]])
    pieces = [index for index, row in enumerate(table.su_cells) if row[1] in ("x", "")]
    assert len(pieces) > 1
    header_rows = {row for cmd in table._bkgrndcmds if cmd[0] == "BACKGROUND" and cmd[3] == colors.grey
                   for row in range(cmd[1][1], cmd[2][1] + 1)}
    assert set(pieces) <= header_rows


def test_an_image_taller_than_a_page_raises_a_named_error_and_writes_nothing(tmp_path):
    from reportlab.platypus import Image as RLImage

    from siege_utilities.reporting.report_generator import TableRowTooTallError
    picture = _png(tmp_path / "tall.png")
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    with pytest.raises(TableRowTooTallError, match="'Sec'.*row 1, column 0") as info:
        _render(rg, tmp_path / "o", [[RLImage(str(picture), width=100, height=900), "x"]],
                headers=["A", "B"])
    assert isinstance(info.value, ValueError)
    assert not (tmp_path / "o" / "out.pdf").exists()


def test_several_flowables_taller_than_a_page_raise_a_named_error(tmp_path):
    from siege_utilities.reporting.report_generator import TableRowTooTallError
    style = getSampleStyleSheet()["BodyText"]
    cell = [Paragraph(" ".join(["word"] * 400), style) for _ in range(4)]
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    with pytest.raises(TableRowTooTallError, match="several flowables"):
        _render(rg, tmp_path / "o", [[cell, "x"]], headers=["A", "B"])


class _TextObject:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


@pytest.mark.parametrize("make", [
    lambda text: _TextObject(text),
    lambda text: text.encode(),
], ids=["object-with-multi-line-str", "bytes"])
def test_a_tall_non_string_cell_alone_is_split_and_drawn(tmp_path, make):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", [[make(_lines_of("ZQ", 120)), "COMPANION"]], headers=["A", "B"])
    _assert_all_lines_on_the_page(out, "ZQ", 120)
    assert _text(out).count("COMPANION") == 1


def test_a_large_array_cell_builds(tmp_path):
    import numpy as np
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    out = _render(rg, tmp_path / "o", [[np.arange(3400), "x\nCOMPANION"]], headers=["A", "B"])
    assert _text(out).count("COMPANION") == 1


def test_a_header_taller_than_a_page_raises_a_named_error(tmp_path):
    from siege_utilities.reporting.report_generator import TableRowTooTallError
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    with pytest.raises(TableRowTooTallError, match="'Sec'.*header row"):
        _render(rg, tmp_path / "o", [["COMPANION", "b"]], headers=[_lines_of("ZQ", 100), "B"])
    assert not (tmp_path / "o" / "out.pdf").exists()


def test_bytes_cells_print_their_text_when_wrapped(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    table, _ = _table(rg, tmp_path / "o", [[LONG.encode(), "x"]], headers=["A", "B"])
    assert table.su_cells[1][0].getPlainText().startswith("Audit Foodservice")
    assert "b'" not in _text(_render(rg, tmp_path / "p", [[LONG.encode(), "x"]], headers=["A", "B"]))


def test_cell_text_helper_renders_plain_values():
    from siege_utilities.reporting.report_generator import _cell_text
    assert _cell_text(None) == ""
    assert _cell_text(b"caf\xc3\xa9") == "café"
    assert _cell_text(bytearray(b"\xff")) == "�"
    assert _cell_text(12.5) == "12.5"


def test_opted_in_logo_saved_under_another_name_is_downloaded_once(tmp_path, monkeypatch):
    import io

    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), (19, 41, 61)).save(buffer, "JPEG")
    calls = []

    class Response:
        headers = {"Content-Type": "image/jpeg"}  # the URL says .png

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield buffer.getvalue()

    def fake_get(url, *args, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr(base_template.requests, "get", fake_get)
    branding = {"colors": {"primary": "#13293D"}, "header": {"left_text": "ZZHEADERLEFT"},
                "logo": {"image_url": "https://brand.invalid/logo.png", "width": 1.0, "height": 0.5}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding,
                         fetch_remote_assets=True)
    out = tmp_path / "o" / "renamed.pdf"
    rg.generate_pdf_report(_three_page_doc(rg), str(out))
    assert len(PdfReader(str(out)).pages) >= 3
    assert calls == ["https://brand.invalid/logo.png"]


@pytest.mark.parametrize("branding,key", [
    ({"page_margins": {"left": float("nan")}}, "page_margins.left"),
    ({"page_margins": {"top": float("inf")}}, "page_margins.top"),
    ({"fonts": {"h1": {"font_size": float("nan")}}}, "fonts.h1.font_size"),
])
def test_non_finite_numbers_raise_a_named_error_when_created(tmp_path, branding, key):
    from siege_utilities.reporting.client_branding import BrandingConfigError
    with pytest.raises(BrandingConfigError, match=key.replace(".", r"\.")):
        ReportGenerator(client_name="Demo", output_dir=tmp_path / "o", branding_config=branding)
