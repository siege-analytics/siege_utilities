"""Regression tests for issue #1993.

Tables rendered by ``ReportGenerator._build_section_content`` were built with no
``colWidths`` and raw-string cells (no ``Paragraph`` wrapping), so a table with a
long text column bled off both page margins and long cells never wrapped. The
``TableStyle`` was also hard-coded grey/beige, ignoring any branding config.

These tests pin: columns fit the available content width, cells are wrapped
Paragraphs, a supplied branding palette reaches the table, and the historical
unbranded look still renders.
"""

import pathlib

import pytest

pytest.importorskip("reportlab")
from reportlab.platypus import Paragraph, Table
from reportlab.lib.colors import HexColor

from siege_utilities import ReportGenerator


LONG = (
    "Audit Foodservice items for stock and readiness, especially GG MEATBALL, "
    "MTO CHICKEN BOOM SANDWICH, BF CHORIZO AND AMERICAN, BF BURR CHORIZO, and "
    "BF BURR PINTO BEANS."
)


def _table_flowable(rg, output_dir):
    doc = rg.create_comprehensive_report(
        title="t", report_type="daily", table_of_contents=False)
    rg.add_table_section(
        doc, "Action plan", [["Manager", LONG, "Before 9am"]],
        headers=["Owner", "Action", "Due"])
    template = rg._get_template(str(output_dir / "out.pdf"))
    section = [s for s in doc["sections"] if s.get("type") == "table"][0]
    story = rg._build_section_content(section, template)
    table = [f for f in story if isinstance(f, Table)][0]
    return table, template, doc


def test_columns_fit_content_width(tmp_path):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path)
    table, template, _ = _table_flowable(rg, tmp_path)
    assert table._colWidths is not None
    # Columns are sized to the frame, not auto-expanded past the margins.
    assert sum(table._colWidths) <= template.doc.width + 0.5


def test_cells_are_wrapped_paragraphs(tmp_path):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path)
    table, _, _ = _table_flowable(rg, tmp_path)
    # Every rendered cell is a Paragraph (wraps) rather than a raw string.
    for row in table._cellvalues:
        for cell in row:
            assert isinstance(cell, Paragraph)


def test_branding_palette_reaches_table_header(tmp_path):
    branding = {"name": "Demo", "colors": {"primary": "#13293D"}, "fonts": {}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path,
                         branding_config=branding)
    table, _, _ = _table_flowable(rg, tmp_path)
    # The brand primary reaches a table background command (header row), instead
    # of the hard-coded grey/beige the pre-fix style always used.
    brand = HexColor("#13293D")
    bg_colors = [cmd[3] for cmd in table._bkgrndcmds if cmd[0] == "BACKGROUND"]
    assert brand in bg_colors


def test_branding_config_shared_with_charts(tmp_path):
    branding = {"name": "Demo", "colors": {"primary": "#13293D"}, "fonts": {}}
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path,
                         branding_config=branding)
    # The same dict feeds the chart generator, so charts and document share a brand.
    assert rg.branding_config is branding
    assert rg.chart_generator.branding_config is branding


def test_unbranded_table_still_renders(tmp_path):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path)
    doc = rg.create_comprehensive_report(
        title="t", report_type="daily", table_of_contents=False)
    rg.add_table_section(doc, "T", [["a", "b"]], headers=["H1", "H2"])
    out = tmp_path / "out.pdf"
    rg.generate_pdf_report(doc, str(out))
    assert out.exists() and out.stat().st_size > 0
