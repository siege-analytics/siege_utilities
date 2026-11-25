"""Shared name and alias classification for config exports and marker checks."""

from pydantic import AliasChoices, AliasPath
from pydantic.fields import FieldInfo

from siege_utilities.core._sensitivity import SECRET_FIELD_NAME

__all__ = ["SECRET_FIELD_NAME", "field_has_sensitive_name"]


def field_has_sensitive_name(name: str, field: FieldInfo) -> bool:
    """Check the internal name and every alias against the secret-name floor.

    Marker policy belongs to the caller; this only classifies names. An
    AliasChoices entry may itself be an AliasPath, whose string components
    all count as names regardless of their position around integer indexes.
    """
    def matches(alias) -> bool:
        if isinstance(alias, str):
            return SECRET_FIELD_NAME.search(alias) is not None
        if isinstance(alias, AliasChoices):
            return any(matches(choice) for choice in alias.choices)
        if isinstance(alias, AliasPath):
            return any(matches(part) for part in alias.path)
        return False

    return any(matches(candidate) for candidate in (
        name, field.alias, field.validation_alias, field.serialization_alias,
    ))
