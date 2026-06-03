"""Table data utilities for the reporting module."""

from __future__ import annotations

from typing import List, Optional, Union

__all__ = ["sort_table_data"]


def sort_table_data(
    table_data: List[List],
    sort_by: Optional[Union[int, str]] = None,
    sort_order: str = "asc",
    has_header: bool = True,
) -> List[List]:
    """Sort table rows by a column.

    Args:
        table_data: Table as list of lists. First row may be headers.
        sort_by: Column index (int) or header name (str) to sort by.
            ``None`` preserves existing order.
        sort_order: ``'asc'`` or ``'desc'``.
        has_header: Whether the first row is a header row.

    Returns:
        A new list with rows sorted. The header row (if present) stays first.

    Raises:
        ValueError: If *sort_order* is not ``'asc'`` or ``'desc'``,
            or *sort_by* names a column not found in the header.
        IndexError: If *sort_by* is an int outside the column range.
    """
    if sort_by is None:
        return list(table_data)

    if sort_order not in ("asc", "desc"):
        raise ValueError(
            f"sort_order must be 'asc' or 'desc', got {sort_order!r}"
        )

    if not table_data:
        return list(table_data)

    if has_header:
        header = table_data[0]
        rows = table_data[1:]
    else:
        header = None
        rows = list(table_data)

    if isinstance(sort_by, str):
        if header is None:
            raise ValueError(
                "sort_by is a column name but has_header=False"
            )
        try:
            col_idx = [str(h) for h in header].index(sort_by)
        except ValueError:
            raise ValueError(
                f"Column {sort_by!r} not found in headers {header}"
            ) from None
    else:
        col_idx = sort_by
        if table_data and (col_idx < 0 or col_idx >= len(table_data[0])):
            raise IndexError(
                f"sort_by index {col_idx} out of range for "
                f"{len(table_data[0])} columns"
            )

    def _sort_key(row):
        val = row[col_idx]
        if isinstance(val, str):
            cleaned = val.replace(",", "").replace("%", "").rstrip("s")
            try:
                return (0, float(cleaned))
            except (ValueError, TypeError):
                return (1, val.lower())
        if val is None:
            return (2, "")
        return (0, val)

    sorted_rows = sorted(rows, key=_sort_key, reverse=(sort_order == "desc"))

    if header is not None:
        return [header] + sorted_rows
    return sorted_rows
