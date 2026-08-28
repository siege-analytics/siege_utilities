"""Bridge :class:`parsons.Table` and :class:`pandas.DataFrame`.

Wrappers in this package MUST route reads through
:func:`parsons_table_to_dataframe` and writes through
:func:`dataframe_to_parsons_table` so callers see ``pd.DataFrame`` in and
out — never a raw ``parsons.Table``.

Design source: :file:`spikes/parsons_adapter/ANALYSIS.md` (P0-3 spike).
The spike verified round-trip fidelity across eight canonical shapes
(empty / single-row / 10k-row / mixed-types / weird-columns /
duplicate-columns / all-none / header-only) with zero real data-loss.
No per-shape guards are needed; a single try/except mapping via
:mod:`._errors` is sufficient.

The one caveat: ``Table.to_dataframe()`` requires pandas, which is a
Parsons *extra* (installed by ``parsons[pandas]`` and pulled into
``siege_utilities[parsons-core]``). If pandas is missing, we surface a
``ConnectorError`` naming the extra rather than letting an
``ImportError`` propagate out of what looks like our adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._errors import map_parsons_exception

if TYPE_CHECKING:
    import pandas as pd
    from parsons import Table

__all__ = [
    "parsons_table_to_dataframe",
    "dataframe_to_parsons_table",
]


def parsons_table_to_dataframe(table: "Table") -> "pd.DataFrame":
    """Convert a Parsons ``Table`` to a pandas ``DataFrame``.

    Round-trip-lossless for every shape verified in the P0-3 spike.

    Raises:
        ConnectorError: pandas not installed (install
            ``siege_utilities[parsons-core]`` or the specific
            ``parsons-*`` extra), or the underlying petl conversion
            failed. Original exception is chained via ``raise ... from``.
    """
    try:
        return table.to_dataframe()
    except (ImportError, ValueError, TypeError, KeyError, AttributeError,
            RuntimeError) as exc:
        # Narrow: MemoryError / RecursionError / SystemExit /
        # KeyboardInterrupt / GeneratorExit / StopIteration are NOT
        # domain errors and should propagate unmodified. (Opus hostile-
        # review 2026-08-24 #2.) The listed classes cover petl / pandas
        # conversion failures and the deferred-pandas-import case.
        raise map_parsons_exception(exc, connector="parsons-adapter") from exc


def dataframe_to_parsons_table(df: "pd.DataFrame") -> "Table":
    """Convert a pandas ``DataFrame`` to a Parsons ``Table``.

    Raises:
        ConnectorError: the underlying petl / Table construction failed.
            Chained via ``raise ... from``.
    """
    # Deferred import so consumers not using Parsons wrappers don't pay
    # the ``parsons`` import cost at ``import siege_utilities``.
    try:
        from parsons import Table
    except ImportError as exc:
        raise map_parsons_exception(exc, connector="parsons-adapter") from exc

    try:
        return Table.from_dataframe(df)
    except (ImportError, ValueError, TypeError, KeyError, AttributeError,
            RuntimeError) as exc:
        # Same narrowing as parsons_table_to_dataframe: don't swallow
        # system-level exceptions (MemoryError, RecursionError, etc.).
        # ImportError included because petl.fromdataframe may lazily
        # import pandas mid-call and fail if pandas got uninstalled
        # after this module was imported.
        raise map_parsons_exception(exc, connector="parsons-adapter") from exc
