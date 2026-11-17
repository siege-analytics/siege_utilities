"""The shared ID-based notebook cell runner used by the analytics/01 tests (#1780)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.notebook_cells import run_cells


def _notebook(tmp_path: Path, cells: list[dict[str, Any]]) -> Path:
    path = tmp_path / "example.ipynb"
    path.write_text(json.dumps({"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": cells}), encoding="utf-8")
    return path


def _code(cell_id: str, source: str | list[str]) -> dict[str, Any]:
    return {"cell_type": "code", "id": cell_id, "metadata": {}, "outputs": [], "execution_count": None,
            "source": source}


def test_cells_run_in_notebook_order_whatever_order_they_are_named(tmp_path: Path) -> None:
    notebook = _notebook(tmp_path, [
        _code("first", "order = ['first']\n"),
        {"cell_type": "markdown", "id": "note", "metadata": {}, "source": "text"},
        _code("second", ["order.append(", "'second')\n"]),
    ])

    assert run_cells(notebook, "second", "first")["order"] == ["first", "second"]


def test_unknown_cell_id_is_named(tmp_path: Path) -> None:
    notebook = _notebook(tmp_path, [_code("first", "x = 1\n")])

    with pytest.raises(KeyError, match="missing"):
        run_cells(notebook, "first", "missing")


def test_markdown_cell_is_refused(tmp_path: Path) -> None:
    notebook = _notebook(tmp_path, [{"cell_type": "markdown", "id": "note", "metadata": {}, "source": "x = 1"}])

    with pytest.raises(AssertionError, match="note is not a code cell"):
        run_cells(notebook, "note")


def test_repeated_ids_are_refused(tmp_path: Path) -> None:
    notebook = _notebook(tmp_path, [_code("same", "x = 1\n"), _code("same", "x = 2\n")])

    with pytest.raises(AssertionError, match="repeats a cell id"):
        run_cells(notebook, "same")
    with pytest.raises(AssertionError, match="requested twice"):
        run_cells(_notebook(tmp_path, [_code("one", "x = 1\n")]), "one", "one")


def test_analytics_notebook_code_cells_have_the_ids_the_tests_use() -> None:
    notebook = Path(__file__).resolve().parents[1] / "notebooks/analytics/01_connectors.ipynb"
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    code_ids = {cell["id"] for cell in cells if cell["cell_type"] == "code"}

    # New cells may be added freely; these four must stay code cells.
    assert {"c1", "c2", "c3", "c5"} <= code_ids
