"""Validation for identifiers interpolated into structured CRM queries."""

import re

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DOTTED_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


def _validate_identifier(identifier: str, *, allow_dotted: bool = False) -> str:
    """Return a safe ASCII identifier or raise ValueError.

    Each component starts with a letter or underscore, followed by letters,
    digits or underscores (including custom suffixes such as __c and __r).
    Relationship fields may opt into dot-separated components. Expressions,
    whitespace and query clauses are never accepted as identifiers.
    """
    pattern = _DOTTED_IDENTIFIER if allow_dotted else _IDENTIFIER
    if not isinstance(identifier, str) or pattern.fullmatch(identifier) is None:
        raise ValueError(f"Invalid CRM identifier: {identifier!r}")
    return identifier
