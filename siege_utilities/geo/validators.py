"""
GEOID validators for Django models and standalone use.

Provides both Django field validators and standalone validation functions
for Census GEOID formats at various geographic levels.

Example usage (standalone):
    from siege_utilities.geo.validators import is_valid_state_fips, is_valid_tract_geoid

    is_valid_state_fips("06")        # True (California)
    is_valid_tract_geoid("06037101100")  # True

Example usage (Django):
    from siege_utilities.geo.validators import StateFIPSValidator

    class MyModel(models.Model):
        state_fips = models.CharField(max_length=2, validators=[StateFIPSValidator()])
"""

import re

from siege_utilities.config.census_constants import STATE_FIPS_CODES, FIPS_TO_STATE


# =============================================================================
# STANDALONE VALIDATION FUNCTIONS
# =============================================================================

def is_valid_state_fips(value: str) -> bool:
    """Validate a 2-digit state FIPS code against known codes."""
    return isinstance(value, str) and value in FIPS_TO_STATE


def is_valid_county_fips(value: str) -> bool:
    """Validate a 5-digit county FIPS code (2-digit state + 3-digit county)."""
    if not isinstance(value, str) or not re.match(r'^\d{5}$', value):
        return False
    return value[:2] in FIPS_TO_STATE


def is_valid_tract_geoid(value: str) -> bool:
    """Validate an 11-digit tract GEOID (2-digit state + 3-digit county + 6-digit tract)."""
    if not isinstance(value, str) or not re.match(r'^\d{11}$', value):
        return False
    return value[:2] in FIPS_TO_STATE


def is_valid_block_group_geoid(value: str) -> bool:
    """Validate a 12-digit block group GEOID (state + county + tract + block group)."""
    if not isinstance(value, str) or not re.match(r'^\d{12}$', value):
        return False
    return value[:2] in FIPS_TO_STATE


# =============================================================================
# DJANGO VALIDATORS
# =============================================================================

try:
    from django.core.exceptions import ValidationError

    class StateFIPSValidator:
        """Django validator for 2-digit state FIPS codes."""

        message = "Enter a valid 2-digit state FIPS code."
        code = "invalid_state_fips"

        def __call__(self, value):
            if not is_valid_state_fips(value):
                raise ValidationError(self.message, code=self.code, params={"value": value})

    class CountyFIPSValidator:
        """Django validator for 5-digit county FIPS codes."""

        message = "Enter a valid 5-digit county FIPS code (2-digit state + 3-digit county)."
        code = "invalid_county_fips"

        def __call__(self, value):
            if not is_valid_county_fips(value):
                raise ValidationError(self.message, code=self.code, params={"value": value})

    class TractGEOIDValidator:
        """Django validator for 11-digit tract GEOIDs."""

        message = "Enter a valid 11-digit Census tract GEOID."
        code = "invalid_tract_geoid"

        def __call__(self, value):
            if not is_valid_tract_geoid(value):
                raise ValidationError(self.message, code=self.code, params={"value": value})

    class BlockGroupGEOIDValidator:
        """Django validator for 12-digit block group GEOIDs."""

        message = "Enter a valid 12-digit Census block group GEOID."
        code = "invalid_block_group_geoid"

        def __call__(self, value):
            if not is_valid_block_group_geoid(value):
                raise ValidationError(self.message, code=self.code, params={"value": value})

except ImportError:
    # Django not installed — standalone functions still available
    pass
