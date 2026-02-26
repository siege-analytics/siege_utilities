"""
GADM (Global Administrative Areas Database) boundary models.

Six-level administrative hierarchy from country through Admin5.
All inherit from TemporalBoundary (NOT CensusTIGERBoundary, since
GADM doesn't use Census GEOIDs).

Preserves the enterprise dual-FK pattern: each child has both a
Django FK to the parent model and a string gid_N field for parallel
bulk loading (FK resolved after load via populate_parent_relationships()).
"""

from django.db import models

from .base import TemporalBoundary


class GADMBoundary(TemporalBoundary):
    """
    Abstract base for all GADM boundaries.

    GADM uses its own identifier scheme: GID_0 through GID_5.
    Source defaults to "GADM".
    """

    gid = models.CharField(
        max_length=50,
        db_index=True,
        help_text="GADM identifier (e.g. 'USA', 'USA.5_1')",
    )

    class Meta:
        abstract = True
        ordering = ["gid"]

    def __str__(self):
        return f"{self.name} ({self.gid})"

    def save(self, *args, **kwargs):
        """Sync feature_id from gid; default source to GADM."""
        if self.gid:
            self.feature_id = self.gid
            self.boundary_id = self.gid
        if not self.source:
            self.source = "GADM"
        super().save(*args, **kwargs)


class GADMCountry(GADMBoundary):
    """
    GADM Level 0 — Country.

    Example: GID_0 = "USA", NAME_0 = "United States"
    """

    iso3 = models.CharField(
        max_length=3,
        db_index=True,
        help_text="ISO 3166-1 alpha-3 country code",
    )

    class Meta:
        verbose_name = "GADM Country"
        verbose_name_plural = "GADM Countries"
        unique_together = [("gid", "vintage_year")]
        indexes = [
            models.Index(fields=["iso3"]),
        ]


class GADMAdmin1(GADMBoundary):
    """
    GADM Level 1 — First-level subdivision (state, province, region).

    Example: GID_1 = "USA.5_1", NAME_1 = "California"
    """

    country = models.ForeignKey(
        GADMCountry,
        on_delete=models.CASCADE,
        related_name="admin1s",
        null=True,
        help_text="Parent country",
    )
    gid_0_string = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="GID_0 string for parallel loading (resolved to FK post-load)",
    )
    type_1 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Administrative type (e.g. 'State', 'Province', 'Region')",
    )
    engtype_1 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="English type name",
    )

    class Meta:
        verbose_name = "GADM Admin Level 1"
        verbose_name_plural = "GADM Admin Level 1"
        unique_together = [("gid", "vintage_year")]

    def populate_parent_relationships(self):
        """Resolve country FK from gid_0_string."""
        if not self.country_id and self.gid_0_string:
            self.country = GADMCountry.objects.filter(
                gid=self.gid_0_string, vintage_year=self.vintage_year
            ).first()


class GADMAdmin2(GADMBoundary):
    """
    GADM Level 2 — Second-level subdivision (county, department, district).

    Example: GID_2 = "USA.5.37_1", NAME_2 = "Los Angeles"
    """

    admin1 = models.ForeignKey(
        GADMAdmin1,
        on_delete=models.CASCADE,
        related_name="admin2s",
        null=True,
        help_text="Parent admin1",
    )
    gid_1_string = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="GID_1 string for parallel loading",
    )
    type_2 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Administrative type",
    )
    engtype_2 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="English type name",
    )

    class Meta:
        verbose_name = "GADM Admin Level 2"
        verbose_name_plural = "GADM Admin Level 2"
        unique_together = [("gid", "vintage_year")]

    def populate_parent_relationships(self):
        """Resolve admin1 FK from gid_1_string."""
        if not self.admin1_id and self.gid_1_string:
            self.admin1 = GADMAdmin1.objects.filter(
                gid=self.gid_1_string, vintage_year=self.vintage_year
            ).first()


class GADMAdmin3(GADMBoundary):
    """
    GADM Level 3 — Third-level subdivision.

    Example: GID_3 = "USA.5.37.1_1"
    """

    admin2 = models.ForeignKey(
        GADMAdmin2,
        on_delete=models.CASCADE,
        related_name="admin3s",
        null=True,
        help_text="Parent admin2",
    )
    gid_2_string = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="GID_2 string for parallel loading",
    )
    type_3 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Administrative type",
    )
    engtype_3 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="English type name",
    )

    class Meta:
        verbose_name = "GADM Admin Level 3"
        verbose_name_plural = "GADM Admin Level 3"
        unique_together = [("gid", "vintage_year")]

    def populate_parent_relationships(self):
        """Resolve admin2 FK from gid_2_string."""
        if not self.admin2_id and self.gid_2_string:
            self.admin2 = GADMAdmin2.objects.filter(
                gid=self.gid_2_string, vintage_year=self.vintage_year
            ).first()


class GADMAdmin4(GADMBoundary):
    """
    GADM Level 4 — Fourth-level subdivision.
    """

    admin3 = models.ForeignKey(
        GADMAdmin3,
        on_delete=models.CASCADE,
        related_name="admin4s",
        null=True,
        help_text="Parent admin3",
    )
    gid_3_string = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="GID_3 string for parallel loading",
    )
    type_4 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Administrative type",
    )
    engtype_4 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="English type name",
    )

    class Meta:
        verbose_name = "GADM Admin Level 4"
        verbose_name_plural = "GADM Admin Level 4"
        unique_together = [("gid", "vintage_year")]

    def populate_parent_relationships(self):
        """Resolve admin3 FK from gid_3_string."""
        if not self.admin3_id and self.gid_3_string:
            self.admin3 = GADMAdmin3.objects.filter(
                gid=self.gid_3_string, vintage_year=self.vintage_year
            ).first()


class GADMAdmin5(GADMBoundary):
    """
    GADM Level 5 — Fifth-level subdivision (finest granularity).
    """

    admin4 = models.ForeignKey(
        GADMAdmin4,
        on_delete=models.CASCADE,
        related_name="admin5s",
        null=True,
        help_text="Parent admin4",
    )
    gid_4_string = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="GID_4 string for parallel loading",
    )
    type_5 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Administrative type",
    )
    engtype_5 = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="English type name",
    )

    class Meta:
        verbose_name = "GADM Admin Level 5"
        verbose_name_plural = "GADM Admin Level 5"
        unique_together = [("gid", "vintage_year")]

    def populate_parent_relationships(self):
        """Resolve admin4 FK from gid_4_string."""
        if not self.admin4_id and self.gid_4_string:
            self.admin4 = GADMAdmin4.objects.filter(
                gid=self.gid_4_string, vintage_year=self.vintage_year
            ).first()
