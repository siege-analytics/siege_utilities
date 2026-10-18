"""Shared bulk-insert helper for the GeoDjango loaders (#1539).

``QuerySet.bulk_create(..., ignore_conflicts=True)`` returns every input
object, including the ones ``ON CONFLICT DO NOTHING`` dropped, so
``len(batch)`` overstates what was written. This helper counts the rows that
match the batch's natural keys before and after the insert instead.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

__all__ = ["bulk_insert_counted"]


def bulk_insert_counted(
    manager: Any,
    objs: Iterable[Any],
    *,
    scope: Mapping[str, Any],
    batch_size: Optional[int] = None,
) -> int:
    """Insert ``objs`` with ``ignore_conflicts=True``; return the rows actually inserted.

    Args:
        manager: The model manager (``Model.objects``).
        objs: Unsaved instances, already passed through ``prepare_for_bulk()``
            where the model defines one.
        scope: ``filter()`` kwargs selecting a set of rows that contains every
            row of the batch (for example ``{"content_type": ct, "year": 2022,
            "dataset": "acs5"}``). It is counted before and after the insert.
            Keep it narrow and indexed: a concurrent writer that commits rows
            inside the scope between the two counts is credited to this batch.
        batch_size: Forwarded to ``bulk_create``.

    Returns:
        The number of rows the insert added within ``scope``.
    """
    objs = list(objs)
    if not objs:
        return 0
    before = manager.filter(**scope).count()
    if batch_size is None:
        manager.bulk_create(objs, ignore_conflicts=True)
    else:
        manager.bulk_create(objs, ignore_conflicts=True, batch_size=batch_size)
    after = manager.filter(**scope).count()
    return after - before
