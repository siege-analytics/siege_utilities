"""Keep the chart, table, and PDF narrative in count units for #1673."""

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import nbformat
import pytest


NOTEBOOK = (
    Path(__file__).resolve().parents[1]
    / "notebooks/reports/01_charts_and_pdf.ipynb"
)


@pytest.fixture
def report_inputs(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    """Inspect valid notebook source and evaluate the actual report inputs."""
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    cells = {cell.id: cell for cell in notebook.cells}
    monkeypatch.setenv("MPLBACKEND", "Agg")
    namespace: dict[str, Any] = {}
    try:
        # Rendered PDF table values are covered by test_pdf_table_renders_counts.
        for cell_id in ("c1", "c2", "c3"):
            source = cells[cell_id].source.replace("%matplotlib inline\n", "")
            exec(compile(source, f"{NOTEBOOK.name}:{cell_id}", "exec"), namespace)

        sections = {
            section["type"]: section["content"]
            for section in namespace["report"]["sections"]
            if section["type"] in {"text", "charts", "table"}
        }
        headers = sections["table"]["headers"]
        rows = (
            dict(zip(headers, values)) for values in sections["table"]["data"][1:]
        )
        row = next(
            row for row in rows
            if row["metric"].startswith("volunteer sign-ups")
        )
        yield {
            "cells": cells,
            "axis": namespace["ax"],
            "row": row,
            "summary": sections["text"],
            "caption": sections["charts"]["description"],
        }
    finally:
        if "tmpdir" in namespace:
            namespace["tmpdir"].cleanup()


def test_signups_use_counts_in_chart_table_and_report(report_inputs: dict[str, Any]) -> None:
    axis = report_inputs["axis"]
    labels = {
        "chart title": axis.get_title(),
        "chart axis": axis.get_ylabel(),
        "table metric": report_inputs["row"]["metric"],
        "report summary": report_inputs["summary"],
        "report caption": report_inputs["caption"],
    }
    for surface, label in labels.items():
        assert "count" in label.lower(), f"{surface} must label sign-ups as counts"
        assert not re.search(
            r"share|registered Democrats|\(%\)|percentage of", label, re.IGNORECASE
        ), f"{surface} mixes count and share units: {label}"

    # Month-end cumulative counts make March's endpoint the Q1 table total.
    assert "cumulative" in axis.get_ylabel().lower()
    assert "cumulative" in report_inputs["caption"].lower()
    assert list(axis.lines[0].get_xdata()) == ["Jan", "Feb", "Mar"]
    assert list(axis.lines[0].get_ydata()) == [42, 45, 51]
    assert report_inputs["row"]["Q1 2026"] == axis.lines[0].get_ydata()[-1]
    for cell_id in ("c1", "c2", "c3"):
        assert "share" not in report_inputs["cells"][cell_id].source.lower()


def test_growth_matches_counts_on_every_report_surface(report_inputs: dict[str, Any]) -> None:
    row = report_inputs["row"]
    baseline, current = row["Q4 2025 baseline"], row["Q1 2026"]
    assert (baseline, current) == (37, 51)
    expected_growth = round((current - baseline) / baseline * 100, 1)
    assert expected_growth == 37.8
    assert row["delta"].startswith(f"{current - baseline:+d} ")

    for surface, text in {
        "chart": report_inputs["axis"].get_title(),
        "table": row["delta"],
        "summary": report_inputs["summary"],
        "caption": report_inputs["caption"],
    }.items():
        percentages = re.findall(r"([+-]?\d+(?:\.\d+)?)%", text)
        assert percentages, f"{surface} must show growth from the count baseline"
        assert [float(value) for value in percentages] == [expected_growth], (
            f"{surface} growth must match ({current} - {baseline}) / {baseline}"
        )
    assert str(current) in report_inputs["summary"]
    assert str(baseline) in report_inputs["summary"]


def test_pdf_table_renders_counts(monkeypatch):
    import siege_utilities.reporting.report_generator as rgmod
    rendered = []

    class Spy(rgmod.Table):
        def __init__(self, data, *a, **k):
            super().__init__(data, *a, **k)
            rendered.append([list(r) for r in self._cellvalues])

    monkeypatch.setattr(rgmod, "Table", Spy)
    monkeypatch.setenv("MPLBACKEND", "Agg")
    nb = nbformat.read(NOTEBOOK, as_version=4)
    ns = {}
    for cell in nb.cells:
        if cell.cell_type == "code":
            exec(compile(cell.source.replace("%matplotlib inline\n", ""), cell.id, "exec"), ns)
    table = rendered[0]  # first Table is the unsplit original
    assert table[0] == ["metric", "Q1 2026", "Q4 2025 baseline", "delta"]
    assert ["volunteer sign-ups (count)", 51, 37, "+14 (+37.8%)"] in table
