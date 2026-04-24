"""Structural hygiene checks for canonical notebooks.

Enforces the contract each rewritten notebook in ELE-2456 must follow:

- Opens with a ``# Title`` markdown cell
- Has a ``## What this shows`` cell in the first two cells
- Has exactly one ``## Related`` cell, at the end
- Contains no stale ``NB0\\d`` / ``NB1\\d`` / ``NB2\\d`` cross-references
- Has no ``try: import X; HAS_X = True`` guards at cell top level
- Has no ``if HAS_[A-Z_]+:`` guards wrapping main content

Notebooks that have been rewritten against the ELE-2456 template are listed
in :data:`RE_WRITTEN`. Everything else is skipped until its rewrite PR lands
— we don't want to fail CI on notebooks we haven't gotten to yet.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_ROOT = REPO_ROOT / "notebooks"


RE_WRITTEN: list[str] = [
    # PR 1 (ELE-2457): foundations
    "foundations/01_configuration.ipynb",
    "foundations/02_profiles_branding.ipynb",
    # PR 2 (ELE-2458): data acquisition
    "spatial/01_boundaries.ipynb",
    "spatial/02_geocoding.ipynb",
    "analytics/01_connectors.ipynb",
    "engines/04_statistics_primitives.ipynb",
    # Already in the ELE-2456 template shape from prior work:
    "reports/03_polling_survey_analysis.ipynb",
]


def _load(rel: str):
    path = NOTEBOOK_ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} not present")
    return json.loads(path.read_text())


def _markdown(cell):
    return "".join(cell.get("source", [])) if cell["cell_type"] == "markdown" else ""


def _code(cell):
    return "".join(cell.get("source", [])) if cell["cell_type"] == "code" else ""


@pytest.mark.parametrize("rel", RE_WRITTEN)
class TestCanonicalHygiene:
    """Per-notebook structural checks."""

    def test_opens_with_title(self, rel):
        nb = _load(rel)
        assert nb["cells"], f"{rel}: notebook is empty"
        first = _markdown(nb["cells"][0]).lstrip()
        assert first.startswith("# "), (
            f"{rel}: first cell must be a markdown `# Title`, got: {first[:60]!r}"
        )

    def test_has_what_this_shows_near_top(self, rel):
        nb = _load(rel)
        head = "\n".join(_markdown(c) for c in nb["cells"][:2])
        assert "## What this shows" in head, (
            f"{rel}: must contain `## What this shows` in one of the first two cells"
        )

    def test_exactly_one_related_at_end(self, rel):
        nb = _load(rel)
        related_positions = [
            i
            for i, c in enumerate(nb["cells"])
            if _markdown(c).lstrip().startswith("## Related")
        ]
        assert len(related_positions) == 1, (
            f"{rel}: expected exactly one `## Related` cell, got {len(related_positions)}"
        )
        n = len(nb["cells"])
        assert related_positions[0] >= n - 2, (
            f"{rel}: `## Related` must be at (or very near) the end; "
            f"found at index {related_positions[0]} of {n}"
        )

    def test_no_stale_nb_refs(self, rel):
        nb = _load(rel)
        pat = re.compile(r"\bNB0\d\b|\bNB1\d\b|\bNB2\d\b")
        offenders = []
        for i, c in enumerate(nb["cells"]):
            if c["cell_type"] != "markdown":
                continue
            if pat.search(_markdown(c)):
                offenders.append(i)
        assert not offenders, (
            f"{rel}: cells {offenders} still contain stale NB## refs"
        )

    def test_no_top_level_try_import_guards(self, rel):
        nb = _load(rel)
        offenders = []
        for i, c in enumerate(nb["cells"]):
            src = _code(c).lstrip()
            if src.startswith("try:") and "import" in src[: src.find("except") or len(src)]:
                offenders.append(i)
        assert not offenders, (
            f"{rel}: cells {offenders} open with `try: import X` guards; "
            "assume extras are installed and let it error loudly if not"
        )

    def test_no_has_x_guards_wrapping_main_content(self, rel):
        """Blocks `if HAS_SOMETHING:` around a notebook's main capability cell."""
        nb = _load(rel)
        pat = re.compile(r"^\s*if\s+HAS_[A-Z_]+\b")
        offenders = []
        for i, c in enumerate(nb["cells"]):
            src = _code(c)
            if not src:
                continue
            first_line = src.lstrip().split("\n", 1)[0]
            if pat.match(first_line):
                offenders.append(i)
        assert not offenders, (
            f"{rel}: cells {offenders} use `if HAS_X:` guards — "
            "inline the capability and let missing extras raise at import"
        )
