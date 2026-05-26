"""Per-kind special-district boundary models.

Per downstream socialwarehouse design SW#207 Q2 = "one model per kind"
(no parent SpecialDistrict model). Each Census special-district
function gets its own concrete model. Downstream consumers cache the
geoid in a per-kind field on Address (SW already shipped those caches
via SW#191's C-medium batch).

GEOID format varies by district type but is at most 10 digits in
Census Special Districts file outputs. We use a shared 10-char
CharField with a permissive regex.

The Census-published "function" code distinguishes kinds within the
Special Districts file; this module realizes those into separate
Django models for type-safety + reverse-accessor clarity from
downstream consumers (an Address's `fire_protection_districts` is
unambiguous about which kind it returns).
"""

from django.db import models

from .base import CensusTIGERBoundary


def _district_meta(verbose):
    """Build a Meta class for a special-district model with shared shape."""
    name = verbose
    class Meta:
        verbose_name = name
        verbose_name_plural = name + "s"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
        ]
        abstract = False
    Meta.__name__ = "Meta"
    return Meta


class SpecialDistrictBase(CensusTIGERBoundary):
    """Shared shape for all per-kind special-district models.

    Abstract: each concrete kind below inherits and gets its own table.
    """

    governing_body = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Name of the special district's governing body.",
    )
    function_code = models.CharField(
        max_length=10, blank=True, default="",
        db_index=True,
        help_text="Census-published function code distinguishing the district's purpose.",
    )

    class Meta:
        abstract = True


class FireProtectionDistrict(SpecialDistrictBase):
    """Fire protection special district. Census function code typically '24'."""

    class Meta:
        verbose_name = "Fire Protection District"
        verbose_name_plural = "Fire Protection Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
        ]


class WaterSupplyDistrict(SpecialDistrictBase):
    """Water supply special district. Census function code typically '91'."""

    class Meta:
        verbose_name = "Water Supply District"
        verbose_name_plural = "Water Supply Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
        ]


class HospitalDistrict(SpecialDistrictBase):
    """Hospital special district. Census function code typically '40'."""

    class Meta:
        verbose_name = "Hospital District"
        verbose_name_plural = "Hospital Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
        ]


class LibraryDistrict(SpecialDistrictBase):
    """Library special district. Census function code typically '52'."""

    class Meta:
        verbose_name = "Library District"
        verbose_name_plural = "Library Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
        ]


class CemeteryDistrict(SpecialDistrictBase):
    """Cemetery special district. Census function code typically '05'."""

    class Meta:
        verbose_name = "Cemetery District"
        verbose_name_plural = "Cemetery Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
        ]


class MosquitoAbatementDistrict(SpecialDistrictBase):
    """Mosquito abatement special district. Census function code typically '63'."""

    class Meta:
        verbose_name = "Mosquito Abatement District"
        verbose_name_plural = "Mosquito Abatement Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
        ]


class OtherSpecialDistrict(SpecialDistrictBase):
    """Catch-all for special-district kinds not represented by a dedicated
    model. Downstream consumers can filter by `function_code` to scope to
    a specific kind that hasn't graduated to its own model yet.
    """

    class Meta:
        verbose_name = "Other Special District"
        verbose_name_plural = "Other Special Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "function_code", "vintage_year"]),
        ]
