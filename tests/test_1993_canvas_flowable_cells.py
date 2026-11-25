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
from reportlab.platypus import Flowable, ImageAndFlowables, KeepInFrame, ListFlowable, ListItem, Paragraph

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


# --- hand-written flowables that use the canvas while they are measured -----------------------------
#
# During a build ReportLab hands every flowable the page canvas before it calls
# wrap() or split(), so a flowable may use it there. The fitting code measures
# cells before the build, so it has to hand a canvas over as well: with None,
# these cells raised AttributeError where the same table built on 6.0.0.

class _CanvasMeasured(Flowable):
    """Sizes itself in wrap() with the canvas: a method, an attribute, or the document behind it."""

    seen = []

    def __init__(self, text, how):
        Flowable.__init__(self)
        self.text, self.how = text, how

    def wrap(self, availWidth, availHeight):
        _CanvasMeasured.seen.append(tuple(self.canv._pagesize))
        if self.how == "method":
            self.width = self.canv.stringWidth(self.text, "Helvetica", 10)
        elif self.how == "attribute":
            self.width = min(availWidth, self.canv._pagesize[0] / 10.0)
        else:
            self.width = min(availWidth, self.canv._doctemplate.pagesize[0] / 10.0)
        self.height = 14
        return self.width, self.height

    def draw(self):
        self.canv.setFont("Helvetica", 10)
        self.canv.drawString(0, 3, self.text)


class _CanvasSplit(Flowable):
    """Twelve points a line; split() uses the canvas and returns two parts."""

    def __init__(self, tokens):
        Flowable.__init__(self)
        self.tokens = list(tokens)

    def wrap(self, availWidth, availHeight):
        self.width, self.height = 60, 12.0 * len(self.tokens)
        return self.width, self.height

    def split(self, availWidth, availHeight):
        self.canv.stringWidth("x", "Helvetica", 10)
        keep = int(availHeight // 12.0)
        if keep < 1 or keep >= len(self.tokens):
            return []
        return [_CanvasSplit(self.tokens[:keep]), _CanvasSplit(self.tokens[keep:])]

    def draw(self):
        self.canv.setFont("Helvetica", 10)
        for index, token in enumerate(self.tokens):
            self.canv.drawString(0, self.height - 12.0 * (index + 1) + 3, token)


WIDE = "the quick brown fox jumps over the lazy dog near the river bank today"


def _canvas_tables(how):
    """name -> (rows, headers) for one canvas-measured cell in each kind of table."""
    def cell():
        return _CanvasMeasured("ZN00000", how)
    flowable_headers = [Paragraph("A", BODY), Paragraph("B", BODY)]
    return {
        "beside-plain-cells": ([[cell(), "COMPANION", 12.5], ["plain", "row", 3]], ["A", "B", "C"]),
        "every-cell-a-flowable": ([[cell(), Paragraph("COMPANION", BODY)]], flowable_headers),
        "in-a-list-cell": ([[[Paragraph("above", BODY), cell()], "COMPANION"]], ["A", "B"]),
        "in-a-table-wider-than-the-frame": ([[cell()] + [WIDE + " COMPANION"] + [WIDE] * 4],
                                            ["A", "B", "C", "D", "E", "F"]),
        "beside-a-cell-taller-than-a-page": ([[Paragraph(_words("ZQ", 800), BODY), cell()]], flowable_headers),
    }


@pytest.mark.parametrize("layout", ["beside-plain-cells", "every-cell-a-flowable", "in-a-list-cell",
                                    "in-a-table-wider-than-the-frame", "beside-a-cell-taller-than-a-page"])
@pytest.mark.parametrize("how", ["method", "attribute", "document"])
def test_a_flowable_that_measures_itself_with_the_canvas_is_drawn(tmp_path, how, layout):
    _CanvasMeasured.seen = []
    rows, headers = _canvas_tables(how)[layout]
    out = _render(tmp_path, rows, headers=headers)
    assert _tokens(out, "ZN") == ["ZN00000"]
    if layout == "beside-a-cell-taller-than-a-page":
        assert sorted(_tokens(out, "ZQ")) == [f"ZQ{i:05d}" for i in range(800)]
    else:
        assert _tokens(out, "COMPANION") == ["COMPANION"]
    # Measured on the page size the document is built with (US letter), never another one.
    assert set(_CanvasMeasured.seen) == {(612.0, 792.0)}


def test_a_flowable_whose_split_uses_the_canvas_is_split_across_pages(tmp_path):
    cell = _CanvasSplit([f"ZN{i:05d}" for i in range(100)])
    out = _render(tmp_path, [[cell, "COMPANION"]], headers=["A", "B"])
    assert _tokens(out, "ZN") == [f"ZN{i:05d}" for i in range(100)]
    assert _tokens(out, "COMPANION") == ["COMPANION"]
    assert len(PdfReader(str(out)).pages) > 2
