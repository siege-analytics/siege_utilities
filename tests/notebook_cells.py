"""Run selected code cells of a committed notebook by cell ID (#1661, #1780).

Cells are chosen by their nbformat ``id``, not their position, so adding or
reordering cells cannot point a test at the wrong one. The selected cells
still run in notebook order, whatever order the IDs are given in, so a test
also catches a cell that depends on a later one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run_cells(notebook: Path, *cell_ids: str) -> dict[str, Any]:
    """Execute the code cells ``cell_ids`` of ``notebook`` in one namespace.

    Raises ``KeyError`` naming any unknown ID, and ``AssertionError`` if an ID
    is repeated, selects a non-code cell, or the notebook repeats an ID.
    """
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    ids = [cell.get("id") for cell in cells]
    assert len(set(ids)) == len(ids), f"{notebook.name} repeats a cell id: {ids}"
    assert len(set(cell_ids)) == len(cell_ids), f"cell ids requested twice: {cell_ids}"
    unknown = sorted(set(cell_ids) - set(ids))
    if unknown:
        raise KeyError(f"{notebook.name} has no cells with ids {unknown}")

    namespace: dict[str, Any] = {}
    for cell in cells:
        if cell.get("id") not in cell_ids:
            continue
        assert cell["cell_type"] == "code", f"{notebook.name}:{cell['id']} is not a code cell"
        source = cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])
        # Executing the committed notebook's own source is the point of these
        # tests; nothing outside the repository is run.
        exec(compile(source, f"{notebook.name}:{cell['id']}", "exec"), namespace)  # noqa: S102
    return namespace
