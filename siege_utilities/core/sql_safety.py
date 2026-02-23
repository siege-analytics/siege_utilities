"""
SQL identifier validation for Hive/Spark/PostGIS operations.

Prevents SQL injection by validating that database and table names
contain only safe characters before interpolation into SQL strings.

Originally developed for pure-translation (electinfo/enterprise).
Moved to siege_utilities as shared security-critical infrastructure.
"""

from __future__ import annotations

import re

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_sql_identifier(name: str, label: str = "identifier") -> str:
    """Validate that *name* is a safe SQL identifier.

    Checks that the identifier contains only alphanumeric characters and
    underscores, starts with a letter or underscore, and is non-empty.
    This prevents SQL injection when identifiers must be interpolated
    into SQL strings (e.g., ``CREATE DATABASE {name}``).

    Args:
        name: The identifier to validate (database name, table name, etc.).
        label: Human-readable label for error messages (e.g., "database", "table").

    Returns:
        The validated identifier (unchanged).

    Raises:
        ValueError: If *name* is empty or contains unsafe characters.

    Examples:
        >>> validate_sql_identifier("electronic_silver", "database")
        'electronic_silver'
        >>> validate_sql_identifier("silver; DROP TABLE --", "database")
        Traceback (most recent call last):
            ...
        ValueError: Invalid SQL database: ...
    """
    if not name:
        raise ValueError(f"SQL {label} must not be empty")
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid SQL {label}: {name!r} — "
            f"must match [a-zA-Z_][a-zA-Z0-9_]* (no spaces, dashes, quotes, or special characters)"
        )
    return name
