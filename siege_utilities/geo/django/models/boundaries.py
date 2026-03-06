"""
Concrete Census TIGER/Line boundary models.

Each model represents a specific Census geography type with appropriate
parent relationships and GEOID parsing.  All inherit from CensusTIGERBoundary,
which provides: geoid, state_fips, lsad, mtfcc, funcstat, vintage_year,
valid_from/valid_to, geometry, area_land, area_water, internal_point, source.
"""

from django.db import models

from .base import CensusTIGERBoundary


class State(CensusTIGERBoundary):
    """
    US State or Territory boundary.

    GEOID: 2 digits (state FIPS code)
    Example: "06" for California
    """

    abbreviation = models.CharField(
        max_length=2,
        db_index=True,
        help_text="2-letter state abbreviation (e.g., CA)",
    )
    region = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Census region (e.g., West, South, Northeast, Midwest)",
    )
    division = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Census division (e.g., Pacific, Mountain, East South Central)",
    )

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["abbreviation"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{2}$"),
                name="state_geoid_2_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 2

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {"state_fips": geoid[:2]}


class County(CensusTIGERBoundary):
    """
    County or county-equivalent boundary.

    GEOID: 5 digits = state (2) + county (3)
    Example: "06037" for Los Angeles County, CA
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="counties",
        null=True,
        help_text="Parent state",
    )
    county_fips = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit county FIPS code",
    )
    county_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="County name without 'County' suffix",
    )

    class Meta:
        verbose_name = "County"
        verbose_name_plural = "Counties"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "county_fips"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{5}$"),
                name="county_geoid_5_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 5

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
        }


class Tract(CensusTIGERBoundary):
    """
    Census Tract boundary.

    GEOID: 11 digits = state (2) + county (3) + tract (6)
    Example: "06037101100" for tract 1011.00 in LA County, CA
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="tracts",
        null=True,
        help_text="Parent state",
    )
    county = models.ForeignKey(
        County,
        on_delete=models.CASCADE,
        related_name="tracts",
        null=True,
        help_text="Parent county",
    )
    county_fips = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit county FIPS code",
    )
    tract_code = models.CharField(
        max_length=6,
        db_index=True,
        help_text="6-digit tract code",
    )
    urbanicity_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="NCES locale code (11-43)",
    )

    class Meta:
        verbose_name = "Census Tract"
        verbose_name_plural = "Census Tracts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "county_fips", "tract_code"]),
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["urbanicity_code"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{11}$"),
                name="tract_geoid_11_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 11

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
            "tract_code": geoid[5:11],
        }

    @property
    def tract_number(self) -> str:
        """Human-readable tract number (e.g., '1011.00')."""
        code = self.tract_code
        return f"{int(code[:4])}.{code[4:]}"

    @property
    def urbanicity_category(self):
        """NCES locale category (city, suburban, town, rural) or None."""
        if self.urbanicity_code is None:
            return None
        from siege_utilities.config.nces_constants import get_locale_category

        return get_locale_category(self.urbanicity_code)

    @property
    def urbanicity_subcategory(self):
        """NCES locale subcategory (e.g., city_large, rural_remote) or None."""
        if self.urbanicity_code is None:
            return None
        from siege_utilities.config.nces_constants import get_locale_subcategory

        return get_locale_subcategory(self.urbanicity_code)


class BlockGroup(CensusTIGERBoundary):
    """
    Census Block Group boundary.

    GEOID: 12 digits = state (2) + county (3) + tract (6) + block group (1)
    Example: "060371011001" for block group 1 in tract 1011.00, LA County, CA
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="block_groups",
        null=True,
        help_text="Parent state",
    )
    county = models.ForeignKey(
        County,
        on_delete=models.CASCADE,
        related_name="block_groups",
        null=True,
        help_text="Parent county",
    )
    tract = models.ForeignKey(
        Tract,
        on_delete=models.CASCADE,
        related_name="block_groups",
        null=True,
        help_text="Parent tract",
    )
    county_fips = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit county FIPS code",
    )
    tract_code = models.CharField(
        max_length=6,
        db_index=True,
        help_text="6-digit tract code",
    )
    block_group = models.CharField(
        max_length=1,
        db_index=True,
        help_text="1-digit block group number",
    )

    class Meta:
        verbose_name = "Block Group"
        verbose_name_plural = "Block Groups"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "county_fips", "tract_code"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{12}$"),
                name="blockgroup_geoid_12_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 12

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
            "tract_code": geoid[5:11],
            "block_group": geoid[11:12],
        }


class Block(CensusTIGERBoundary):
    """
    Census Block boundary.

    GEOID: 15 digits = state (2) + county (3) + tract (6) + block (4)
    Example: "060371011001001" for block 1001 in tract 1011.00, LA County, CA

    Note: Blocks are very numerous (millions per state). Consider using
    a separate table or partitioning for large-scale deployments.
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="blocks",
        null=True,
        help_text="Parent state",
    )
    county = models.ForeignKey(
        County,
        on_delete=models.CASCADE,
        related_name="blocks",
        null=True,
        help_text="Parent county",
    )
    tract = models.ForeignKey(
        Tract,
        on_delete=models.CASCADE,
        related_name="blocks",
        null=True,
        help_text="Parent tract",
    )
    block_group_ref = models.ForeignKey(
        BlockGroup,
        on_delete=models.CASCADE,
        related_name="blocks",
        null=True,
        help_text="Parent block group",
    )
    county_fips = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit county FIPS code",
    )
    tract_code = models.CharField(
        max_length=6,
        db_index=True,
        help_text="6-digit tract code",
    )
    block_code = models.CharField(
        max_length=4,
        db_index=True,
        help_text="4-digit block code",
    )

    class Meta:
        verbose_name = "Census Block"
        verbose_name_plural = "Census Blocks"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "county_fips", "tract_code"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{15}$"),
                name="block_geoid_15_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 15

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
            "tract_code": geoid[5:11],
            "block_code": geoid[11:15],
        }

    @property
    def block_group(self) -> str:
        """Block group derived from block code (first digit)."""
        return self.block_code[0]


class Place(CensusTIGERBoundary):
    """
    Census Place (city, town, CDP) boundary.

    GEOID: 7 digits = state (2) + place (5)
    Example: "0644000" for Los Angeles city, CA
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="places",
        null=True,
        help_text="Parent state",
    )
    place_fips = models.CharField(
        max_length=5,
        db_index=True,
        help_text="5-digit place FIPS code",
    )
    place_type = models.CharField(
        max_length=2,
        blank=True,
        help_text="Place type code (e.g., C1=incorporated place)",
    )

    class Meta:
        verbose_name = "Place"
        verbose_name_plural = "Places"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "place_fips"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{7}$"),
                name="place_geoid_7_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 7

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "place_fips": geoid[2:7],
        }


class ZCTA(CensusTIGERBoundary):
    """
    ZIP Code Tabulation Area boundary.

    GEOID: 5 digits (the ZCTA code, similar to ZIP)
    Example: "90210" for Beverly Hills area

    Note: ZCTAs approximate but do not exactly match USPS ZIP codes.
    They are defined by Census blocks and may cross state lines.
    """

    zcta5 = models.CharField(
        max_length=5,
        db_index=True,
        help_text="5-digit ZCTA code",
    )

    class Meta:
        verbose_name = "ZCTA"
        verbose_name_plural = "ZCTAs"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["zcta5"]),
            models.Index(fields=["vintage_year"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{5}$"),
                name="zcta_geoid_5_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 5

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {"zcta5": geoid[:5]}


class CongressionalDistrict(CensusTIGERBoundary):
    """
    Congressional District boundary.

    GEOID: 4 digits = state (2) + district (2)
    Example: "0614" for California's 14th district

    Note: District numbers change after reapportionment (every 10 years).
    Use vintage_year to track which Congress the districts represent.
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="congressional_districts",
        null=True,
        help_text="Parent state",
    )
    district_number = models.CharField(
        max_length=2,
        db_index=True,
        help_text="2-digit district number (00=at-large)",
    )
    congress_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Congress number (e.g., 118 for 118th Congress)",
    )
    session = models.CharField(
        max_length=4,
        blank=True,
        help_text="Session identifier (e.g., '118' or '2023')",
    )

    class Meta:
        verbose_name = "Congressional District"
        verbose_name_plural = "Congressional Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "district_number"]),
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["congress_number"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{4}$"),
                name="cd_geoid_4_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 4

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "district_number": geoid[2:4],
        }

    @property
    def is_at_large(self) -> bool:
        """True if this is an at-large district (single representative)."""
        return self.district_number == "00" or self.district_number == "98"

    def __str__(self):
        if self.is_at_large:
            return f"{self.name} At-Large ({self.geoid})"
        return f"{self.name} District {int(self.district_number)} ({self.geoid})"
