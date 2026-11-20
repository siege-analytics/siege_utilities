"""Timezone-safe expiry comparisons for the config models (#1496).

Expiry fields may hold naive or timezone-aware datetimes: naive values come
from the models' own ``datetime.now()`` arithmetic and from older saved files,
aware values from ISO strings such as ``2026-01-01T00:00:00Z``. Comparing the
two directly raises ``TypeError``, so every expiry comparison goes through
these helpers.

A naive value is local wall-clock time, the convention the config models use
throughout (``datetime.now()``). Converting it with ``astimezone`` keeps the
instant v4.0.0 compared against ``datetime.now()``.

Storage contract: expiry fields are stored as given. A naive value stays
naive; a value supplied timezone-aware (for example an ISO string ending in
``Z``) stays aware on the attribute. Nothing is converted at validation; both
sides are converted only inside each comparison. v4.0.0 could not construct a
model with an aware expiry (its future-only validator compared it with a naive
``datetime.now()`` and raised ``TypeError``), so an aware attribute is not a
regression.
"""

from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    """Return *value* as an aware UTC datetime; naive values are local time."""
    return value.astimezone(timezone.utc)


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)
