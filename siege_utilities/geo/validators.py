"""
Django field validators for Census GEOID formats.

Provides validators that raise ``django.core.exceptions.ValidationError`` when
a GEOID value does not match the expected format for its geography level.
These are thin wrappers around the pure-Python validation functions in
``siege_utilities.geo.geoid_utils`` and are suitable for use in Django model
field ``validators=[...]`` lists.

Usage in a Django model::

    from siege_utilities.geo.validators import (
        StateFIPSValidator,
        CountyFIPSValidator,
        TractGEOIDValidator,
        BlockGroupGEOIDValidator,
    )

    class MyModel(models.Model):
        state_fips = models.CharField(max_length=2, validators=[StateFIPSValidator()])
        county_fips = models.CharField(max_length=5, validators=[CountyFIPSValidator()])
        tract_geoid = models.CharField(max_length=11, validators=[TractGEOIDValidator()])
        block_group_geoid = models.CharField(max_length=12, validators=[BlockGroupGEOIDValidator()])

Each validator is a callable class with ``__eq__`` and ``deconstruct`` so that
Django's migration framework can serialize them correctly.
"""

import re


class _RegexGEOIDValidator:
    """
    Base class for regex-based GEOID validators.

    Subclasses set ``pattern``, ``expected_length``, and ``level_name``.
    """

    pattern: re.Pattern
    expected_length: int
    level_name: str

    def __call__(self, value: str):
        from django.core.exceptions import ValidationError

        if not value or not isinstance(value, str):
            raise ValidationError(
                f"{self.level_name} GEOID must be a non-empty string, "
                f"got {type(value).__name__}"
            )
        if not self.pattern.match(value):
            raise ValidationError(
                f"{self.level_name} GEOID must be exactly "
                f"{self.expected_length} digits, got '{value}'"
            )

    def __eq__(self, other):
        return type(self) is type(other)

    def __repr__(self):
        return f"{type(self).__name__}()"

    def deconstruct(self):
        return (
            f"{self.__class__.__module__}.{self.__class__.__qualname__}",
            (),
            {},
        )


class StateFIPSValidator(_RegexGEOIDValidator):
    """Validates that a value is a 2-digit state FIPS code."""

    pattern = re.compile(r"^\d{2}$")
    expected_length = 2
    level_name = "State FIPS"


class CountyFIPSValidator(_RegexGEOIDValidator):
    """Validates that a value is a 5-digit county FIPS code (state + county)."""

    pattern = re.compile(r"^\d{5}$")
    expected_length = 5
    level_name = "County FIPS"


class TractGEOIDValidator(_RegexGEOIDValidator):
    """Validates that a value is an 11-digit Census tract GEOID."""

    pattern = re.compile(r"^\d{11}$")
    expected_length = 11
    level_name = "Tract"


class BlockGroupGEOIDValidator(_RegexGEOIDValidator):
    """Validates that a value is a 12-digit Census block group GEOID."""

    pattern = re.compile(r"^\d{12}$")
    expected_length = 12
    level_name = "Block group"
