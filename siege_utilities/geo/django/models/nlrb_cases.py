"""NLRB case, election, ULP, and bargaining unit Django models.

Non-spatial models for NLRB case data. These link to NLRBRegion via FK
but don't carry their own geometry.
"""

from django.db import models

__all__ = [
    'NLRBCase',
    'ElectionResult',
    'ULPCharge',
    'BargainingUnit',
]


class NLRBCase(models.Model):
    """An NLRB case (representation petition, ULP charge, etc.)."""

    case_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="NLRB case number (e.g. '05-RC-123456')",
    )
    case_type = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Case type code (R, RC, CA, CB, etc.)",
    )
    case_name = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Employer or party name",
    )
    status = models.CharField(
        max_length=50,
        blank=True,
        default="Unknown",
        db_index=True,
    )
    date_filed = models.DateField(null=True, blank=True, db_index=True)
    date_closed = models.DateField(null=True, blank=True)
    region = models.ForeignKey(
        "NLRBRegion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases",
    )
    region_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Region number extracted from case number",
    )
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="", db_index=True)
    union_name = models.CharField(max_length=300, blank=True, default="")
    unit_description = models.TextField(blank=True, default="")
    naics_code = models.CharField(
        max_length=10,
        blank=True,
        default="",
        db_index=True,
    )
    employee_count = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Data source: 'datagov', 'labordata', 'nxgen'",
    )

    class Meta:
        verbose_name = "NLRB Case"
        verbose_name_plural = "NLRB Cases"
        indexes = [
            models.Index(fields=["case_type", "status"]),
            models.Index(fields=["date_filed"]),
            models.Index(fields=["state"]),
        ]

    def __str__(self):
        return f"{self.case_number} ({self.case_name})"

    def to_record(self):
        """Convert to NLRBCaseRecord dataclass."""
        from siege_utilities.geo.providers.nlrb_clients import NLRBCaseRecord

        return NLRBCaseRecord(
            case_number=self.case_number,
            case_type=self.case_type,
            case_name=self.case_name,
            status=self.status,
            date_filed=self.date_filed,
            date_closed=self.date_closed,
            region=self.region_number,
            city=self.city,
            state=self.state,
            union_name=self.union_name,
            unit_description=self.unit_description,
            naics_code=self.naics_code,
            employee_count=self.employee_count,
            source=self.source,
        )

    @classmethod
    def from_record(cls, record):
        """Create model instance from NLRBCaseRecord dataclass."""
        return cls(
            case_number=record.case_number,
            case_type=record.case_type,
            case_name=record.case_name,
            status=record.status,
            date_filed=record.date_filed,
            date_closed=record.date_closed,
            region_number=record.region,
            city=record.city,
            state=record.state,
            union_name=record.union_name,
            unit_description=record.unit_description,
            naics_code=record.naics_code,
            employee_count=record.employee_count,
            source=record.source,
        )


class ElectionResult(models.Model):
    """Election tally result for an NLRB representation case."""

    case = models.ForeignKey(
        NLRBCase,
        on_delete=models.CASCADE,
        related_name="election_results",
    )
    tally_date = models.DateField(null=True, blank=True, db_index=True)
    eligible_voters = models.PositiveIntegerField(null=True, blank=True)
    votes_for = models.PositiveIntegerField(null=True, blank=True)
    votes_against = models.PositiveIntegerField(null=True, blank=True)
    void_ballots = models.PositiveIntegerField(null=True, blank=True)
    union_name = models.CharField(max_length=300, blank=True, default="")
    source = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "Election Result"
        verbose_name_plural = "Election Results"
        indexes = [
            models.Index(fields=["tally_date"]),
        ]

    def __str__(self):
        return f"Election {self.case.case_number} ({self.tally_date})"

    def to_record(self):
        from siege_utilities.geo.providers.nlrb_clients import ElectionRecord

        return ElectionRecord(
            case_number=self.case.case_number,
            tally_date=self.tally_date,
            eligible_voters=self.eligible_voters,
            votes_for=self.votes_for,
            votes_against=self.votes_against,
            void_ballots=self.void_ballots,
            union_name=self.union_name,
            source=self.source,
        )


class ULPCharge(models.Model):
    """Unfair labor practice charge filed with the NLRB."""

    case = models.ForeignKey(
        NLRBCase,
        on_delete=models.CASCADE,
        related_name="ulp_charges",
    )
    allegation = models.TextField(blank=True, default="")
    charging_party = models.CharField(max_length=300, blank=True, default="")
    charged_party = models.CharField(max_length=300, blank=True, default="")
    section_of_act = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="NLRA section cited (e.g. '8(a)(1)')",
    )
    date_filed = models.DateField(null=True, blank=True, db_index=True)
    source = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "ULP Charge"
        verbose_name_plural = "ULP Charges"
        indexes = [
            models.Index(fields=["date_filed"]),
        ]

    def __str__(self):
        return f"ULP {self.case.case_number}: {self.section_of_act}"

    def to_record(self):
        from siege_utilities.geo.providers.nlrb_clients import ULPRecord

        return ULPRecord(
            case_number=self.case.case_number,
            allegation=self.allegation,
            charging_party=self.charging_party,
            charged_party=self.charged_party,
            section_of_act=self.section_of_act,
            date_filed=self.date_filed,
            source=self.source,
        )


class BargainingUnit(models.Model):
    """Bargaining unit description with industry/occupation codes."""

    case = models.ForeignKey(
        NLRBCase,
        on_delete=models.CASCADE,
        related_name="bargaining_units",
    )
    unit_description = models.TextField(blank=True, default="")
    naics_code = models.CharField(
        max_length=10,
        blank=True,
        default="",
        db_index=True,
        help_text="NAICS industry code",
    )
    soc_codes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of SOC occupation codes",
    )
    employee_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Bargaining Unit"
        verbose_name_plural = "Bargaining Units"
        indexes = [
            models.Index(fields=["naics_code"]),
        ]

    def __str__(self):
        return f"Unit: {self.case.case_number} ({self.naics_code})"
