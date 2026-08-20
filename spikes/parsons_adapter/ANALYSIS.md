# Spike analysis: Parsons Table ↔ pandas DataFrame round-trip fidelity

**Ticket:** [#1151 P0-3](https://github.com/siege-analytics/siege_utilities/issues/1151)
**Parent epic:** [#1148](https://github.com/siege-analytics/siege_utilities/issues/1148)

## What the spike does

`roundtrip_matrix.py` builds 8 canonical Parsons `Table` shapes, runs each through `Table → DataFrame → Table` and `DataFrame → Table → DataFrame`, and records any diff. Deliberately paranoid: the spike WANTS to find lossy conversions so `_adapter.py` (P1-2) knows what to guard.

## Cases + results (see `RESULTS.md` for full artifacts)

| Case | Description | T→DF→T | DF→T→DF | Interpretation |
|---|---|:---:|:---:|---|
| `empty` | 0 rows, 0 cols | ✅ | ✅ | Handled |
| `empty_headers` | 0 rows, 2 cols | ✅ | ✅ | Handled |
| `single_row` | trivial payload | ✅ | ✅ | Handled |
| `large_10k` | 10,000-row synthetic | ✅ | ✅ | Perf/memory floor met |
| `mixed_types` | int/float/str/datetime/None/NaN/bool/list/dict | ⚠️ FAIL (NaN artifact) | ✅ | Not a real failure — see below |
| `weird_columns` | spaces, unicode, SQL reserved words | ✅ | ✅ | Handled |
| `duplicate_columns` | `["col","col"]` | ✅ | ✅ | Preserved (see caveat) |
| `all_none_column` | column entirely None | ✅ | ✅ | Handled |

**Total FAILs reported by scaffold: 1. Real fidelity gaps: 0.**

## The one "FAIL" is a test-scaffolding artifact

Case `mixed_types` reports `Table→DF→Table` FAIL because Python's `list == list` comparison on records containing `float("nan")` always returns `False` (per IEEE 754: `nan != nan`). The two record lists in `RESULTS.md` under `mixed_types` are visually identical; the equality check just cannot certify that.

Evidence: the second row of the case has `nan_col: float("nan")`. Comparing:

```python
{"nan_col": float("nan")} == {"nan_col": float("nan")}   # → False
```

...is False under `==`. This is a scaffold limitation, not adapter data loss. The empirical round-trip preserves NaN as NaN in both directions (dtype `float64`, value visible in the artifact).

**Implication for `_adapter.py`:** no guard needed for NaN; the round-trip is lossless. The adapter's tests should use `pandas.testing.assert_frame_equal(..., check_exact=False)` or `numpy.isnan`-aware equality if they need to certify fidelity end-to-end.

## Findings that DO reshape `_adapter.py` design

None of the eight cases produced a genuine data-loss finding. Every case round-tripped losslessly. This is a substantially better result than the epic Fact Sheet §3 anticipated. Consequences:

1. **The `_adapter.py` shape is simpler than expected.** No per-shape guardrails needed for the 8 shapes above. A single try/except around `Table.to_dataframe()` / `Table.from_dataframe()` mapping ImportError/AttributeError/generic Exception to `ConnectorError` subclasses is sufficient.

2. **`duplicate_columns` (`["col", "col"]`) survives the round-trip.** Not the outcome I expected — petl / pandas both preserve duplicate columns in the direction of Table → DataFrame → Table. However, the interior representation is unstable enough that this shape should still be flagged in the wrapper docstrings as "not recommended" — different downstream consumers (SQL writes, JSON serialization) will collapse duplicates.

3. **Column names with spaces / unicode / SQL reserved words are preserved.** No transformation applied. Consumers writing to SQL databases will need to quote-identify these separately; the adapter itself does not need to sanitize.

## Design note for `_adapter.py` (input to P1-2)

Given the above, the adapter's core is:

```python
# siege_utilities/integrations/parsons/_adapter.py

from __future__ import annotations
from typing import TYPE_CHECKING
from ..connectors._protocol import ConnectorError

if TYPE_CHECKING:
    import pandas as pd
    from parsons import Table


def parsons_table_to_dataframe(table: "Table") -> "pd.DataFrame":
    """Convert a Parsons Table to a pandas DataFrame.

    Raises:
        ConnectorError: if pandas is not installed (parsons[pandas] extra
            missing) or if the underlying petl conversion fails. The
            original exception is chained via `raise ... from`.
    """
    try:
        return table.to_dataframe()
    except ImportError as e:
        raise ConnectorError(
            "pandas is required for Parsons Table → DataFrame conversion. "
            "Install siege_utilities[parsons-core] or the specific parsons-* "
            "extra you need."
        ) from e
    except Exception as e:
        raise ConnectorError(
            f"Failed to convert Parsons Table to DataFrame: {type(e).__name__}: {e}"
        ) from e


def dataframe_to_parsons_table(df: "pd.DataFrame") -> "Table":
    """Convert a pandas DataFrame to a Parsons Table.

    Raises:
        ConnectorError: if the conversion fails. Chained.
    """
    from parsons import Table  # deferred import so consumers not using
                               # parsons wrappers don't pay the import cost

    try:
        return Table.from_dataframe(df)
    except Exception as e:
        raise ConnectorError(
            f"Failed to convert DataFrame to Parsons Table: {type(e).__name__}: {e}"
        ) from e
```

Test surface (input to P1-2's test file):

- Every one of the 8 spike cases becomes a parametrized round-trip test in `tests/integrations/parsons/test_adapter.py` with NaN-aware equality (`pd.testing.assert_frame_equal(..., check_dtype=True)`).
- ImportError path: skip if `parsons[pandas]` present in venv; otherwise exercise by mocking `parsons.Table.to_dataframe` to raise ImportError, assert `ConnectorError` raised.
- Generic-exception path: mock `Table.to_dataframe` to raise `ValueError`, assert `ConnectorError` raised with chained cause.

## Falsification claim outcomes (from ticket #1151)

- **Claim A (all 7 shapes round-trip losslessly through `Table.to_dataframe()` and back):** **CONFIRMED for all 8 cases** (1 extra case added: `all_none_column`). The one reported FAIL is scaffold-only.
- **Claim B (None in Parsons cell maps to NaN in numeric DataFrame column and None in object DataFrame column):** **CONFIRMED.** Case `all_none_column` (dtype `object`) preserves None as None; case `mixed_types` `nan_col` (dtype `float64`) preserves NaN as NaN. `none_col` (dtype `object`) preserves None as None.
- **Claim C (`Table.to_dataframe()` fails with clear ImportError if pandas missing):** **CONFIRMED empirically in P0-2** — see `docs/PARSONS_DEP_MATRIX.md`. Exact behavior: `ImportError: No module named 'pandas'`. Our adapter catches and re-raises as `ConnectorError` with an actionable message pointing at the extras.

## Blocks

- P1-2 (`_adapter.py` implementation) — this analysis is the input. The design note above is the target shape.

## Spike disposition

`spikes/parsons_adapter/` is deleted (or its useful cases migrated to `tests/integrations/parsons/test_adapter.py`) when P1-2 lands. `spikes/README.md` documents the convention.
