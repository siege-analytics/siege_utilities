"""
Temporal political models — Phase A.

CongressionalTerm, Seat, and StateElectionCalendar form the temporal
backbone for mapping political activity to time periods and geographic
units.

Design principles (from SPATIO_TEMPORAL_EVENTS.md):
- Seat is identity, not geography — persists across redistricting cycles
- CongressionalTerm is atomic — 2-year unit, everything else is views over sequences
- DateTimeField for events, DateField for boundaries
- Parameterize, don't hardcode — election dates, cycles, structures in config
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .boundaries import State


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

OFFICE_TYPE_CHOICES = [
    ("PRESIDENT", "President"),
    ("US_SENATE", "U.S. Senate"),
    ("US_HOUSE", "U.S. House"),
    ("GOVERNOR", "Governor"),
    ("STATE_SENATE", "State Senate"),
    ("STATE_HOUSE", "State House"),
]

SENATE_CLASS_CHOICES = [
    (1, "Class I"),
    (2, "Class II"),
    (3, "Class III"),
]

PRIMARY_TYPE_CHOICES = [
    ("open", "Open"),
    ("closed", "Closed"),
    ("semi_closed", "Semi-Closed"),
    ("semi_open", "Semi-Open"),
    ("top_two", "Top-Two"),
    ("top_four", "Top-Four / Ranked Choice"),
    ("blanket", "Blanket"),
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CongressionalTerm(models.Model):
    """A 2-year congressional term — the atomic unit of political time.

    Seeded from the 1st Congress (1789) through the current Congress.
    The election_year is always term start_date.year - 1 for odd-year
    start dates (e.g., 119th Congress starts Jan 3 2025, election was 2024).
    """

    congress_number = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        help_text="Congress number (1st, 2nd, ..., 119th, ...)",
    )
    start_date = models.DateField(
        help_text="First day of the term (e.g. 2025-01-03)",
    )
    end_date = models.DateField(
        help_text="Last day of the term (e.g. 2027-01-03)",
    )
    election_year = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="Year of the general election for this Congress",
    )
    is_presidential = models.BooleanField(
        default=False,
        help_text="True if a presidential election occurs this cycle",
    )
    senate_classes_up = models.JSONField(
        default=list,
        blank=True,
        help_text="List of Senate classes up for election (e.g. [1] or [2, 3])",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Congressional Term"
        verbose_name_plural = "Congressional Terms"
        ordering = ["congress_number"]
        indexes = [
            models.Index(fields=["election_year"]),
        ]

    def __str__(self):
        ordinal = self._ordinal(self.congress_number)
        return f"{ordinal} Congress ({self.election_year})"

    @staticmethod
    def _ordinal(n: int) -> str:
        if 11 <= (n % 100) <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"


class Seat(models.Model):
    """A political seat — identity that persists across redistricting cycles.

    A Seat represents "U.S. House CA-12" or "U.S. Senate TX Class II"
    independent of who holds it or what its district geometry looks like.
    Races are run *for* a Seat within a CongressionalTerm.
    """

    office = models.CharField(
        max_length=20,
        choices=OFFICE_TYPE_CHOICES,
        db_index=True,
    )
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="seats",
        null=True,
        blank=True,
        help_text="State (NULL for PRESIDENT)",
    )
    district_label = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="District number/label (e.g. '12' for CA-12, '' for at-large/statewide)",
    )
    senate_class = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=SENATE_CLASS_CHOICES,
        help_text="Senate class (1, 2, or 3) — only for US_SENATE",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this seat currently exists (districts can be eliminated)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seat"
        verbose_name_plural = "Seats"
        unique_together = [("office", "state", "district_label")]
        indexes = [
            models.Index(fields=["office", "state"]),
            models.Index(fields=["office"]),
        ]

    def __str__(self):
        parts = [self.get_office_display()]
        if self.state:
            parts.append(self.state.abbreviation if hasattr(self.state, 'abbreviation') else str(self.state))
        if self.district_label:
            parts.append(self.district_label)
        if self.senate_class:
            parts.append(f"Class {self.senate_class}")
        return " ".join(parts)


class StateElectionCalendar(models.Model):
    """Per-state, per-term election calendar.

    Stores primary/general dates, registration deadlines, and early
    voting windows. Initially empty — populated per election cycle from
    state election authority data.
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="election_calendars",
    )
    congressional_term = models.ForeignKey(
        CongressionalTerm,
        on_delete=models.CASCADE,
        related_name="election_calendars",
    )

    # Primary
    primary_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of state primary election",
    )
    primary_type = models.CharField(
        max_length=20,
        choices=PRIMARY_TYPE_CHOICES,
        blank=True,
        default="",
        help_text="Primary election type",
    )
    primary_runoff_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of primary runoff (if applicable)",
    )

    # General
    general_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of general election",
    )
    general_runoff_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of general election runoff (if applicable)",
    )

    # Registration & early voting
    registration_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Voter registration deadline",
    )
    early_voting_start = models.DateField(
        null=True,
        blank=True,
    )
    early_voting_end = models.DateField(
        null=True,
        blank=True,
    )
    mail_ballot_request_deadline = models.DateField(
        null=True,
        blank=True,
    )
    mail_ballot_return_deadline = models.DateField(
        null=True,
        blank=True,
    )

    # Certification
    certification_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="State deadline to certify results",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "State Election Calendar"
        verbose_name_plural = "State Election Calendars"
        unique_together = [("state", "congressional_term")]
        indexes = [
            models.Index(fields=["state", "congressional_term"]),
        ]

    def __str__(self):
        return f"{self.state} — {self.congressional_term}"
