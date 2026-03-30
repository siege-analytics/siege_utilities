"""
Temporal event models — Phase B.

Race, RaceEvent, SpatioTemporalEvent, and ReturnSnapshot model the
event-driven layer: contests for seats, milestones in the race timeline,
discrete real-world events with their own geometry, and election-night
result snapshots.

Design principles:
- Events own their geometry (independent spatial objects)
- DateTimeField for events (sub-day precision matters for results)
- ReturnSnapshot captures progressive reporting (AP calls, etc.)
"""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base import TemporalGeographicFeature
from .temporal_political import CongressionalTerm, Seat


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

SPECIAL_CAUSE_CHOICES = [
    ("death", "Death"),
    ("resignation", "Resignation"),
    ("expulsion", "Expulsion"),
    ("recall", "Recall"),
    ("vacancy", "Vacancy"),
]

RACE_EVENT_TYPE_CHOICES = [
    ("FILING_OPEN", "Filing Period Opens"),
    ("FILING_CLOSE", "Filing Period Closes"),
    ("PRIMARY", "Primary Election"),
    ("PRIMARY_RUNOFF", "Primary Runoff"),
    ("GENERAL", "General Election"),
    ("GENERAL_RUNOFF", "General Runoff"),
    ("RECOUNT", "Recount"),
    ("CERTIFICATION", "Result Certification"),
    ("INAUGURATION", "Inauguration / Swearing In"),
    ("COURT_RULING", "Court Ruling"),
]

EVENT_CATEGORY_CHOICES = [
    ("NATURAL_DISASTER", "Natural Disaster"),
    ("COURT_RULING", "Court Ruling"),
    ("REDISTRICTING", "Redistricting Event"),
    ("LEGISLATION", "Legislation"),
    ("EXECUTIVE_ORDER", "Executive Order"),
    ("PROTEST", "Protest / Civil Action"),
    ("INFRASTRUCTURE", "Infrastructure Event"),
    ("PUBLIC_HEALTH", "Public Health Event"),
    ("OTHER", "Other"),
]

RESULT_SOURCE_CHOICES = [
    ("ap", "Associated Press"),
    ("state_sos", "Secretary of State"),
    ("county", "County Clerk / Board of Elections"),
    ("manual", "Manual Entry"),
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Race(models.Model):
    """A contest for a Seat in a CongressionalTerm.

    A regular Race exists for every Seat every cycle. Special elections
    create additional Race records with is_special=True.
    """

    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name="races",
    )
    congressional_term = models.ForeignKey(
        CongressionalTerm,
        on_delete=models.CASCADE,
        related_name="races",
    )
    is_special = models.BooleanField(
        default=False,
        help_text="True for special elections",
    )
    cause_of_special = models.CharField(
        max_length=20,
        choices=SPECIAL_CAUSE_CHOICES,
        blank=True,
        default="",
        help_text="Reason for special election (blank for regular)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Race"
        verbose_name_plural = "Races"
        indexes = [
            models.Index(fields=["seat", "congressional_term"]),
            models.Index(fields=["congressional_term"]),
            models.Index(fields=["is_special"]),
        ]

    def __str__(self):
        prefix = "Special: " if self.is_special else ""
        return f"{prefix}{self.seat} — {self.congressional_term}"


class SpatioTemporalEvent(TemporalGeographicFeature):
    """A discrete real-world event with its own geometry.

    Examples: hurricanes (polygon), court rulings (point of courthouse),
    redistricting orders, infrastructure failures.

    Inherits feature_id, name, vintage_year, valid_from/to, source
    from TemporalGeographicFeature. Adds geometry and event-specific fields.
    """

    geometry = gis_models.GeometryCollectionField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Event geometry — polygon for affected area, point for location",
    )
    event_start = models.DateTimeField(
        help_text="When the event began",
    )
    event_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the event ended (NULL = ongoing or instantaneous)",
    )
    event_category = models.CharField(
        max_length=30,
        choices=EVENT_CATEGORY_CHOICES,
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed description of the event",
    )
    affected_boundaries = models.ManyToManyField(
        "State",
        blank=True,
        related_name="affecting_events",
        help_text="Boundaries affected by this event",
    )

    class Meta:
        verbose_name = "Spatio-Temporal Event"
        verbose_name_plural = "Spatio-Temporal Events"
        indexes = [
            models.Index(fields=["event_category"]),
            models.Index(fields=["event_start"]),
        ]


class RaceEvent(models.Model):
    """A milestone or occurrence in a Race's timeline.

    Links race-specific events (filing opens, primary date, general date,
    certification, etc.) and optionally references a SpatioTemporalEvent
    (e.g., a court ruling that changed the race).
    """

    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(
        max_length=20,
        choices=RACE_EVENT_TYPE_CHOICES,
        db_index=True,
    )
    event_date = models.DateField(
        help_text="Date of this race event",
    )
    event_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Precise start time (e.g. polls open)",
    )
    event_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Precise end time (e.g. polls close)",
    )
    external_event = models.ForeignKey(
        SpatioTemporalEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="race_events",
        help_text="Optional link to a real-world event that triggered this",
    )
    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Race Event"
        verbose_name_plural = "Race Events"
        ordering = ["event_date"]
        indexes = [
            models.Index(fields=["race", "event_type"]),
            models.Index(fields=["event_date"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.race} ({self.event_date})"


class ReturnSnapshot(models.Model):
    """Election results snapshot — progressive reporting.

    Captures election-night AP calls, Secretary of State updates, etc.
    Multiple snapshots per race track results as they come in.
    The is_final flag marks the certified result.
    """

    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name="return_snapshots",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When this snapshot was captured",
    )
    source = models.CharField(
        max_length=20,
        choices=RESULT_SOURCE_CHOICES,
        help_text="Source of this result data",
    )

    # Reporting progress
    precincts_reporting = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    total_precincts = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    pct_reporting = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Percentage of precincts reporting",
    )

    # Ballot counts
    total_ballots_counted = models.BigIntegerField(
        null=True,
        blank=True,
    )
    ballots_outstanding = models.BigIntegerField(
        null=True,
        blank=True,
    )

    # Per-candidate results as JSON: {candidate_id: {votes, pct, party}}
    results = models.JSONField(
        default=dict,
        help_text="Candidate results: {candidate_id: {votes, pct, party}}",
    )

    is_final = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True when this is the certified final result",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Return Snapshot"
        verbose_name_plural = "Return Snapshots"
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["race", "timestamp"]),
            models.Index(fields=["race", "is_final"]),
        ]

    def __str__(self):
        status = "FINAL" if self.is_final else f"{self.pct_reporting or 0:.1f}%"
        return f"{self.race} — {self.timestamp} ({status})"
