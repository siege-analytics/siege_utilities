"""Regression tests for #1993 review finding 6-S2-1: table cells that need a canvas.

ReportLab's container flowables (``KeepInFrame``, ``ListFlowable``,
``ImageAndFlowables``) read ``self.canv`` inside ``wrap()`` and ``split()``.
ReportLab itself always measures through ``wrapOn(canv, ...)`` and
``splitOn(canv, ...)``, which set that attribute first. The table fitting code
called ``wrap()`` and ``split()`` directly, so a table holding one of these
cells raised ``AttributeError: ... object has no attribute 'canv'`` and no PDF
was written, where the same table built before the fitting code existed.

Two code paths are pinned:

* ``_cell_widths``: every cell is measured when at least one cell of the table
  is a plain value, so an ordinary small table was enough to fail.
* ``_cell_chunks``: every cell of a row taller than a page is measured and
  split, including when all cells are flowables.
"""

import pytest

pytest.importorskip("reportlab")
import requests
from PyPDF2 import PdfReader
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage
from reportlab.platypus import ImageAndFlowables, KeepInFrame, ListFlowable, ListItem, Paragraph

from siege_utilities import ReportGenerator
from siege_utilities.reporting.templates import base_template

BODY = getSampleStyleSheet()["BodyText"]


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Keep branding/image caches out of the real home; never touch the network."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    def offline_get(url, *args, **kwargs):
        raise requests.exceptions.ConnectionError(f"offline test: {url}")

    monkeypatch.setattr(base_template.requests, "get", offline_get)


def _png(path):
    from PIL import Image
    Image.new("RGB", (40, 20), (200, 30, 30)).save(path)
    return str(path)


def _words(prefix, count):
    return " ".join(f"{prefix}{i:05d}" for i in range(count))


def _render(tmp_path, data, headers):
    rg = ReportGenerator(client_name="NoBrand", output_dir=tmp_path / "o")
    doc = rg.create_comprehensive_report(title="t", report_type="daily", table_of_contents=False)
    rg.add_table_section(doc, "Sec", data, headers=headers)
    out = tmp_path / "o" / "out.pdf"
    rg.generate_pdf_report(doc, str(out))
    return out


def _tokens(pdf_path, prefix):
    """Every drawn token starting with *prefix*, in reading order."""
    return [token for page in PdfReader(str(pdf_path)).pages
            for token in page.extract_text().split() if token.startswith(prefix)]


def _small_cells(tmp_path):
    """name -> (factory for a small canvas-needing cell, the tokens it must draw)."""
    picture = _png(tmp_path / "small.png")
    one, three = ["ZN00000"], ["ZN00000", "ZN00001", "ZN00002"]
    return {
        "KeepInFrame-shrink": (
            lambda: KeepInFrame(150, 60, [Paragraph("ZN00000 kept", BODY)], mode="shrink"), one),
        "KeepInFrame-truncate": (
            lambda: KeepInFrame(150, 60, [Paragraph("ZN00000 kept", BODY)], mode="truncate"), one),
        "ListFlowable-bullets": (
            lambda: ListFlowable([Paragraph(f"ZN{i:05d}", BODY) for i in range(3)],
                                 bulletType="bullet"), three),
        "ListFlowable-numbered": (
            lambda: ListFlowable([ListItem(Paragraph(f"ZN{i:05d}", BODY)) for i in range(3)],
                                 bulletType="1"), three),
        "ImageAndFlowables": (
            lambda: ImageAndFlowables(RLImage(picture, width=30, height=30),
                                      [Paragraph("ZN00000 beside an image", BODY)]), one),
        "list-holding-a-KeepInFrame": (
            lambda: [Paragraph("ZN00001 above", BODY),
                     KeepInFrame(150, 60, [Paragraph("ZN00000 kept", BODY)])],
            ["ZN00001", "ZN00000"]),
    }


SMALL_CELLS = ["KeepInFrame-shrink", "KeepInFrame-truncate", "ListFlowable-bullets",
               "ListFlowable-numbered", "ImageAndFlowables", "list-holding-a-KeepInFrame"]


@pytest.mark.parametrize("kind", SMALL_CELLS)
def test_a_container_flowable_beside_plain_cells_is_drawn(tmp_path, kind):
    """Nothing wide, nothing tall: one container cell in a table that also holds plain values."""
    make, expected = _small_cells(tmp_path)[kind]
    out = _render(tmp_path, [[make(), "COMPANION", 12.5], ["plain", "row", 3]],
                  headers=["A", "B", "C"])
    assert _tokens(out, "ZN") == expected
    assert _tokens(out, "COMPANION") == ["COMPANION"]
    assert _tokens(out, "12.5") == ["12.5"]


@pytest.mark.parametrize("kind", ["KeepInFrame-shrink", "ListFlowable-bullets", "ImageAndFlowables"])
def test_a_small_container_flowable_beside_a_tall_cell_is_drawn(tmp_path, kind):
    """Every cell is a flowable, so only the tall-row code measures the container."""
    make, expected = _small_cells(tmp_path)[kind]
    out = _render(tmp_path, [[Paragraph(_words("ZQ", 800), BODY), make()]],
                  headers=[Paragraph("A", BODY), Paragraph("B", BODY)])
    assert sorted(_tokens(out, "ZQ")) == [f"ZQ{i:05d}" for i in range(800)]
    assert _tokens(out, "ZN") == expected


@pytest.mark.parametrize("headers", [
    [Paragraph("A", BODY), Paragraph("B", BODY)],
    ["A", "B"],
], ids=["all-cells-flowables", "plain-headers"])
def test_an_image_and_flowables_cell_taller_than_a_page_is_split_and_drawn(tmp_path, headers):
    """ImageAndFlowables can split, but only when it is asked through splitOn."""
    cell = ImageAndFlowables(RLImage(_png(tmp_path / "small.png"), width=30, height=30),
                             [Paragraph(_words("ZN", 800), BODY)])
    out = _render(tmp_path, [[cell, Paragraph("COMPANION", BODY)]], headers=headers)
    assert sorted(_tokens(out, "ZN")) == [f"ZN{i:05d}" for i in range(800)]
    assert _tokens(out, "COMPANION") == ["COMPANION"]
    assert len(PdfReader(str(out)).pages) > 2


@pytest.mark.parametrize("headers", [
    [Paragraph("A", BODY), Paragraph("B", BODY)],
    ["A", "B"],
], ids=["all-cells-flowables", "plain-headers"])
@pytest.mark.parametrize("kind", ["KeepInFrame", "ListFlowable"])
def test_an_unsplittable_container_taller_than_a_page_raises_the_named_error(tmp_path, kind, headers):
    """KeepInFrame and ListFlowable do not split: the caller gets the named error, not AttributeError."""
    from siege_utilities.reporting.report_generator import TableRowTooTallError
    if kind == "KeepInFrame":
        cell = KeepInFrame(200, 2000, [Paragraph(_words("ZN", 60), BODY) for _ in range(6)])
    else:
        cell = ListFlowable([Paragraph(f"ZN{i:05d}", BODY) for i in range(120)], bulletType="bullet")
    with pytest.raises(TableRowTooTallError, match=f"'Sec'.*row 1, column 0.*{kind} cannot be split") as info:
        _render(tmp_path, [[cell, Paragraph("COMPANION", BODY)]], headers=headers)
    assert isinstance(info.value, ValueError)
    assert not (tmp_path / "o" / "out.pdf").exists()
