"""P0-3 spike: parsons.Table <-> pandas.DataFrame round-trip fidelity matrix.

Ticket: siege-analytics/siege_utilities#1151
Parent epic: #1148

Purpose: verify empirically that Table -> DataFrame -> Table (and inverse)
preserves data across the shapes the adapter (_adapter.py, P1-2) will see
in production. Any FAIL is a design finding that reshapes the adapter's
try/except mapping and its input-shape guardrails.

Run: python spikes/parsons_adapter/roundtrip_matrix.py

Expects parsons[pandas]>=6.1.0 in the venv. Writes results to
spikes/parsons_adapter/RESULTS.md (overwrites on each run).
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Silence Parsons's "install has changed" RuntimeWarning during the spike.
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, module="parsons")

import pandas as pd  # noqa: E402
from parsons import Table  # noqa: E402


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "RESULTS.md"


# ---------------------------------------------------------------------------
# Case definitions
# ---------------------------------------------------------------------------


def case_empty() -> Table:
    """Case 1: empty table (0 rows, 0 cols)."""
    return Table([[]])


def case_empty_with_headers() -> Table:
    """Case 1b: header-only table (0 rows, 2 cols)."""
    return Table([["col_a", "col_b"]])


def case_single_row() -> Table:
    """Case 2: single-row table."""
    return Table([["name", "count"], ["alpha", 1]])


def case_large() -> Table:
    """Case 3: 10,000-row table (memory / performance floor)."""
    rows = [["id", "value"]] + [[i, i * 2] for i in range(10_000)]
    return Table(rows)


def case_mixed_types() -> Table:
    """Case 4: int, float, str, datetime, None, NaN, bool, list, dict."""
    return Table([
        ["i", "f", "s", "d", "none_col", "nan_col", "b", "lst", "dct"],
        [
            1,
            2.5,
            "hello",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            None,
            float("nan"),
            True,
            [1, 2, 3],
            {"key": "value"},
        ],
        [
            2,
            3.14,
            "world",
            datetime(2026, 6, 15, tzinfo=timezone.utc),
            None,
            float("nan"),
            False,
            [],
            {},
        ],
    ])


def case_weird_column_names() -> Table:
    """Case 5: spaces, unicode, SQL reserved words."""
    return Table([
        ["col with spaces", "unicode_名前", "select", "from", "where"],
        [1, "a", "x", "y", "z"],
        [2, "b", "x2", "y2", "z2"],
    ])


def case_duplicate_column_names() -> Table:
    """Case 6: duplicated column name — expected to be lossy or raise."""
    return Table([["col", "col"], [1, 2], [3, 4]])


def case_all_none_column() -> Table:
    """Case 7: a column that is entirely None (nullability check)."""
    return Table([
        ["id", "always_none"],
        [1, None],
        [2, None],
        [3, None],
    ])


CASES: list[tuple[str, Callable[[], Table], str]] = [
    ("empty",             case_empty,                "Empty table (0 rows, 0 cols)"),
    ("empty_headers",     case_empty_with_headers,   "Header-only table (0 rows, 2 cols)"),
    ("single_row",        case_single_row,           "Single-row table"),
    ("large_10k",         case_large,                "10,000-row synthetic table"),
    ("mixed_types",       case_mixed_types,          "Mixed types (int/float/str/datetime/None/NaN/bool/list/dict)"),
    ("weird_columns",     case_weird_column_names,   "Column names: spaces, unicode, SQL reserved words"),
    ("duplicate_columns", case_duplicate_column_names, "Duplicated column name (lossiness check)"),
    ("all_none_column",   case_all_none_column,      "Column entirely None (nullability check)"),
]


# ---------------------------------------------------------------------------
# Round-trip mechanics
# ---------------------------------------------------------------------------


def _table_to_records(t: Table) -> list[dict[str, Any]]:
    """Materialize a Parsons Table as a list of dicts for diffing."""
    return list(t.to_dicts())


def _dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.to_dict(orient="records")


def roundtrip_via_dataframe(t: Table) -> tuple[bool, str, dict[str, Any]]:
    """Table -> DataFrame -> Table. Returns (passed, notes, artifacts)."""
    try:
        original_records = _table_to_records(t)
        df = t.to_dataframe()
        t2 = Table.from_dataframe(df)
        roundtripped_records = _table_to_records(t2)
    except Exception as e:  # noqa: BLE001 — spike wants to name every failure
        return False, f"raised {type(e).__name__}: {e}", {"traceback": traceback.format_exc()}

    passed = original_records == roundtripped_records
    notes = "clean round-trip" if passed else "records differ after round-trip"
    return passed, notes, {
        "original_records": _stringify(original_records),
        "roundtripped_records": _stringify(roundtripped_records),
        "df_dtypes": {c: str(d) for c, d in df.dtypes.items()},
    }


def roundtrip_via_table(df: pd.DataFrame) -> tuple[bool, str, dict[str, Any]]:
    """DataFrame -> Table -> DataFrame. Returns (passed, notes, artifacts)."""
    try:
        t = Table.from_dataframe(df)
        df2 = t.to_dataframe()
    except Exception as e:  # noqa: BLE001
        return False, f"raised {type(e).__name__}: {e}", {"traceback": traceback.format_exc()}

    try:
        passed = df.equals(df2)
    except Exception as e:  # noqa: BLE001
        passed = False
        notes = f"df.equals raised {type(e).__name__}: {e}"
        return passed, notes, {
            "df_before": _stringify(df.to_dict(orient="records")),
            "df_after": _stringify(df2.to_dict(orient="records")),
        }

    notes = "clean round-trip" if passed else "DataFrames differ after round-trip"
    return passed, notes, {
        "df_before_dtypes": {c: str(d) for c, d in df.dtypes.items()},
        "df_after_dtypes": {c: str(d) for c, d in df2.dtypes.items()},
    }


def _truncate_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Cap any row-list to 3 elements so RESULTS.md is reviewable."""
    if not isinstance(artifact, dict):
        return artifact
    out = {}
    for k, v in artifact.items():
        if isinstance(v, list) and len(v) > 3:
            out[k] = v[:3] + [f"... ({len(v)-3} more elided; rerun spike for full)"]
        else:
            out[k] = v
    return out


def _stringify(obj: Any) -> Any:
    """Best-effort JSON-serializable rendering for report artifacts."""
    try:
        json.dumps(obj, default=str)
        return obj
    except Exception:
        return repr(obj)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def run() -> int:
    """Run every case, write RESULTS.md, return non-zero if any FAIL."""
    lines: list[str] = []
    fail_count = 0
    lines.append(f"# `parsons.Table` ↔ `pandas.DataFrame` round-trip matrix (P0-3)\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
    lines.append(f"Parsons version: 6.1.0\n")
    lines.append(f"pandas version: {pd.__version__}\n")
    lines.append(f"Python version: {sys.version.split()[0]}\n")
    lines.append("\n## Summary table\n")
    lines.append("| Case | Description | Table→DF→Table | DF→Table→DF |")
    lines.append("|---|---|:---:|:---:|")

    detail_sections: list[str] = []

    for name, factory, description in CASES:
        t2df_pass, t2df_notes, t2df_artifacts = _safely_run(lambda: _build_and_roundtrip_via_df(factory))
        df2t_pass, df2t_notes, df2t_artifacts = _safely_run(lambda: _build_and_roundtrip_via_table(factory))

        t2df_cell = "✅ PASS" if t2df_pass else f"❌ FAIL"
        df2t_cell = "✅ PASS" if df2t_pass else f"❌ FAIL"

        if not t2df_pass:
            fail_count += 1
        if not df2t_pass:
            fail_count += 1

        lines.append(f"| `{name}` | {description} | {t2df_cell} | {df2t_cell} |")

        detail_sections.append(f"### `{name}` — {description}\n")
        detail_sections.append(f"- **Table→DF→Table:** {t2df_notes}")
        detail_sections.append(f"- **DF→Table→DF:** {df2t_notes}\n")
        detail_sections.append(f"<details><summary>Artifacts</summary>\n\n")
        detail_sections.append("```json")
        # Truncate row lists to first 3 entries per case so RESULTS.md
        # stays reviewable — full artifacts are reproducible by re-running
        # the spike locally without the truncation guard.
        detail_sections.append(json.dumps({
            "table_to_df": _truncate_artifact(t2df_artifacts),
            "df_to_table": _truncate_artifact(df2t_artifacts),
        }, indent=2, default=str))
        detail_sections.append("```\n\n</details>\n\n")

    lines.append("")
    lines.append("## Per-case details\n")
    lines.extend(detail_sections)

    lines.append("\n## Overall\n")
    lines.append(f"Total FAILs across both directions: **{fail_count}**\n")
    if fail_count == 0:
        lines.append("All cases round-trip cleanly. `_adapter.py` can proceed with a simple "
                     "try/except → ConnectorError shape.\n")
    else:
        lines.append("At least one case fails. Every FAIL becomes a design finding in the "
                     "adapter's guardrails. See per-case detail above.\n")

    RESULTS.write_text("\n".join(lines))
    print(f"Wrote {RESULTS}")
    print(f"FAILs: {fail_count}")
    return 0 if fail_count == 0 else 1


def _build_and_roundtrip_via_df(factory: Callable[[], Table]) -> tuple[bool, str, dict[str, Any]]:
    t = factory()
    return roundtrip_via_dataframe(t)


def _build_and_roundtrip_via_table(factory: Callable[[], Table]) -> tuple[bool, str, dict[str, Any]]:
    t = factory()
    # Same shape as case, but starting from DataFrame for the inverse test.
    try:
        df = t.to_dataframe()
    except Exception as e:  # noqa: BLE001 — happens for the empty-table case
        return False, f"cannot build starting DataFrame ({type(e).__name__}: {e})", {}
    return roundtrip_via_table(df)


def _safely_run(fn: Callable[[], tuple[bool, str, dict[str, Any]]]) -> tuple[bool, str, dict[str, Any]]:
    """Wrap a case runner so an unexpected raise doesn't stop the whole matrix."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return False, f"case raised {type(e).__name__}: {e}", {"traceback": traceback.format_exc()}


if __name__ == "__main__":
    sys.exit(run())
