"""
SQL identifier validation + literal escaping for Hive/Spark/PostGIS/DuckDB/Snowflake.

Prevents SQL injection where identifiers (database/table/column names)
must be interpolated into SQL strings — most dialects don't permit
parameter-bound identifiers, so we validate against a strict allow-list
instead. For value escaping, prefer parameter binding; this module's
:func:`escape_sql_string_literal` is the fallback for cases where the
underlying API genuinely cannot bind (Sedona spatial UDFs, hand-written
SQL files for re-import, etc.).

Originally developed for pure-translation (electinfo/enterprise).
Moved to siege_utilities as shared security-critical infrastructure.
"""

from __future__ import annotations

import re
from typing import Sequence

__all__ = [
    "validate_sql_identifier",
    "validate_sql_identifier_in",
    "escape_sql_string_literal",
]


_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_sql_identifier(
    name: str,
    label: str = "identifier",
    *,
    allow_dotted: bool = False,
) -> str:
    """Validate that *name* is a safe SQL identifier.

    Checks that the identifier contains only alphanumeric characters and
    underscores, starts with a letter or underscore, and is non-empty.
    This prevents SQL injection when identifiers must be interpolated
    into SQL strings (e.g., ``CREATE DATABASE {name}``).

    Args:
        name: The identifier to validate (database name, table name, etc.).
        label: Human-readable label for error messages (e.g., "database", "table").
        allow_dotted: If True, accept ``schema.table`` or
            ``catalog.schema.table`` — every dot-separated component must
            itself be a safe identifier. Defaults to False to preserve
            backwards-compatible single-component behaviour.

    Returns:
        The validated identifier (unchanged).

    Raises:
        ValueError: If *name* is empty, structurally invalid, or
            (when ``allow_dotted=False``) contains a dot.

    Examples:
        >>> validate_sql_identifier("electronic_silver", "database")
        'electronic_silver'
        >>> validate_sql_identifier("silver; DROP TABLE --", "database")
        Traceback (most recent call last):
            ...
        ValueError: Invalid SQL database: ...
        >>> validate_sql_identifier("public.users", "table", allow_dotted=True)
        'public.users'
    """
    if not name:
        raise ValueError(f"SQL {label} must not be empty")
    if not isinstance(name, str):
        raise ValueError(f"SQL {label} must be a string, got {type(name).__name__}")
    parts = name.split(".") if allow_dotted else [name]
    for part in parts:
        if not _IDENTIFIER_RE.match(part):
            raise ValueError(
                f"Invalid SQL {label}: {name!r} — "
                f"must match [a-zA-Z_][a-zA-Z0-9_]* "
                f"(no spaces, dashes, quotes, or special characters)"
            )
    return name


def validate_sql_identifier_in(
    name: str,
    allowed: Sequence[str],
    label: str = "identifier",
) -> str:
    """Validate that *name* is both structurally safe AND in *allowed*.

    Use this when the caller has a known set of legal values — the
    typical case is a column name that must exist on a DataFrame::

        validate_sql_identifier_in(geometry_col, df.columns, "column")

    Raises:
        ValueError: *name* is structurally unsafe OR not in *allowed*.
    """
    validate_sql_identifier(name, label, allow_dotted=False)
    if name not in allowed:
        sample = sorted(allowed)[:10]
        more = "..." if len(allowed) > 10 else ""
        raise ValueError(
            f"SQL {label} {name!r} not in allowed set ({sample}{more})"
        )
    return name


def escape_sql_string_literal(value: str) -> str:
    """SQL-escape a string for use inside single-quoted SQL literals.

    Use sparingly — parameter binding is always preferred. The cases
    that legitimately need this are:

    * Sedona / Spark-SQL spatial UDFs (``ST_GeomFromText``) where Spark
      parameter substitution doesn't apply uniformly across versions.
    * Hand-written SQL files generated for human inspection / batch
      re-import — defensive escaping in case the row data is later
      hand-edited.

    The escape rule is the SQL standard: replace ``'`` with ``''``. NUL
    bytes are rejected — most drivers refuse to send them anyway and
    they can split a query in C-string-aware backends.

    Raises:
        TypeError: *value* is not a string.
        ValueError: *value* contains a NUL byte.
    """
    if not isinstance(value, str):
        raise TypeError(
            f"escape_sql_string_literal: expected str, got {type(value).__name__}"
        )
    if "\x00" in value:
        raise ValueError("escape_sql_string_literal: NUL byte in string literal")
    return value.replace("'", "''")
