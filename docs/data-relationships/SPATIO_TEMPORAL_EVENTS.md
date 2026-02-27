# Spatio-Temporal Event Model and Election Cycle Architecture

Design document for temporal structures, election cycles, races, and
spatio-temporal events in siege_utilities.

**Status:** PROPOSED — design review

---

## Problem Statement

The current data model handles *features that exist in space over time*
(boundaries, demographics) but lacks abstractions for:

1. **Events** — discrete occurrences with their own spatiotemporal
   footprint (hurricanes, court rulings, protests, facility closures)
2. **Election cycles** — the interlocking federal temporal structure
   (presidential, midterm, Senate classes)
3. **Races** — contests for specific seats, where electoral and exogenous
   events happen
4. **Regimes** — redistricting plans that map abstract political seats to
   concrete boundary polygons for a time window
5. **Partial returns** — high-frequency election result snapshots as they
   come in on election night and the days after

---

## Design Principles

1. **Seat is identity, not geography.** TX-28 is a label that persists
   across redistricting cycles. What geography it covers changes every
   decade (or mid-decade via court order). The Seat model carries the
   label; the RedistrictingPlan maps it to a polygon.

2. **Events own their geography.** A hurricane has its own storm track
   polygon. A court ruling affects a state. These are independent spatial
   objects that get *linked* to races, not embedded in them.

3. **CongressionalTerm is the atomic temporal unit.** Everything else
   (presidential cycle, Senate class cycle) is a view over sequential
   terms. This avoids modeling overlapping cycle definitions.

4. **DateTimeField for events, DateField for boundaries.** Events have
   clock time ("polls closed at 7pm", "landfall at 2:10am"). Boundaries
   only need date precision.

5. **Parameterize, don't hardcode.** Election dates, filing deadlines,
   and cycle structures should come from config, not Python literals.

---

## Abstract Hierarchy (Extended)

```
TemporalGeographicFeature (existing root — no geometry)
│
├── TemporalBoundary (existing — MultiPolygon)
│   ├── CensusTIGERBoundary → State, County, Tract, ...
│   ├── GADMBoundary → GADMCountry, GADMAdmin1-5
│   └── NLRBRegion, FederalJudicialDistrict, ...
│
├── TemporalLinearFeature (existing — MultiLineString)
│
├── TemporalPointFeature (existing — Point)
│
└── TemporalEvent (NEW — any geometry type)
        geometry: GeometryCollectionField(srid=4326, nullable=True)
        event_start: DateTimeField
        event_end: DateTimeField (nullable — instantaneous events)
        event_category: CharField
```

TemporalEvent inherits `feature_id`, `vintage_year`, `valid_from`,
`valid_to`, `source` from the root. It adds `GeometryCollectionField`
instead of `MultiPolygonField` because events can be points (shooting),
lines (hurricane track), polygons (flood zone), or combinations.

---

## Model Specifications

### 1. CongressionalTerm (Temporal Backbone)

The 2-year congressional term is the atomic temporal unit. Everything
else is composed from sequences of terms.

```python
class CongressionalTerm(models.Model):
    """
    A 2-year US Congressional term (e.g., 118th Congress).

    The atomic temporal unit for federal election cycles.
    Presidential cycles span 2 terms. Senate class cycles span 3 terms.
    """
    congress_number = models.PositiveSmallIntegerField(
        unique=True,
        help_text="e.g., 118 for the 118th Congress",
    )
    start_date = models.DateField(
        help_text="Inauguration day (Jan 3 of odd year)",
    )
    end_date = models.DateField(
        help_text="End of term (Jan 3 of next odd year)",
    )
    is_presidential = models.BooleanField(
        help_text="True if this term starts in a presidential inauguration year",
    )
    senate_classes_up = ArrayField(
        models.PositiveSmallIntegerField(),
        help_text="Senate classes with seats up for election [1], [2], or [3]",
    )
    election_year = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="Year of the general election for this term (even year)",
    )
```

**Relationships:**
- `CongressionalTerm.objects.filter(is_presidential=True)` → presidential years
- `CongressionalTerm.objects.filter(senate_classes_up__contains=[2])` → Class II election years
- Sequential: `previous_term` / `next_term` via congress_number ± 1

**Seed data:** Computed from first Congress (1789) forward. The 118th
Congress: number=118, start=2023-01-03, end=2025-01-03,
is_presidential=False, senate_classes_up=[1], election_year=2024.

---

### 2. Seat (Political Identity)

A seat is a position to be filled — no geometry, pure identity.

```python
class Seat(models.Model):
    """
    A political seat that persists across redistricting cycles.

    TX-28 the Seat has existed since Texas had 28+ districts.
    What geography it covers changes with each redistricting plan.
    """
    OFFICE_CHOICES = [
        ("PRESIDENT", "President of the United States"),
        ("US_SENATE", "United States Senate"),
        ("US_HOUSE", "United States House of Representatives"),
        ("GOVERNOR", "Governor"),
        ("STATE_SENATE", "State Senate"),
        ("STATE_HOUSE", "State House / Assembly"),
    ]

    office = models.CharField(max_length=20, choices=OFFICE_CHOICES, db_index=True)
    state = models.ForeignKey(
        "State", on_delete=models.CASCADE, null=True, blank=True,
        help_text="Null for President",
    )
    district_label = models.CharField(
        max_length=10, blank=True, default="",
        help_text="District number/label. Empty for statewide offices.",
    )
    senate_class = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Senate class 1/2/3. Null for non-Senate seats.",
    )

    class Meta:
        unique_together = [("office", "state", "district_label")]
```

**Query patterns:**
- "All House seats in Texas": `Seat.objects.filter(office="US_HOUSE", state__abbreviation="TX")`
- "Senate Class II seats": `Seat.objects.filter(office="US_SENATE", senate_class=2)`
- "Full history of TX-28": `Race.objects.filter(seat__office="US_HOUSE", seat__state__abbreviation="TX", seat__district_label="28").order_by("congressional_term")`

---

### 3. Race (Contest)

A race is a contest for a specific seat in a specific term.

```python
class Race(models.Model):
    """
    A contest for a Seat in a CongressionalTerm.

    Regular elections happen every cycle. Special elections fill vacancies
    and can overlap with regular elections for the same seat.
    """
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name="races")
    congressional_term = models.ForeignKey(
        CongressionalTerm, on_delete=models.CASCADE, related_name="races",
    )
    is_special = models.BooleanField(default=False)
    cause_of_special = models.CharField(
        max_length=50, blank=True, default="",
        help_text="DEATH, RESIGNATION, EXPULSION, COURT_ORDER",
    )

    class Meta:
        indexes = [
            models.Index(fields=["seat", "congressional_term"]),
            models.Index(fields=["is_special"]),
        ]
```

**Connection to FEC data:** The existing `Candidacy` model gets a
nullable FK to `Race`. A candidacy is a person's participation in a race.

---

### 4. StateElectionCalendar (State-Administered Dates)

Per-state, per-term election administration dates.

```python
class StateElectionCalendar(models.Model):
    """
    State-specific election dates and deadlines for a congressional term.

    Dates vary by state: TX primary is in March, CA may use jungle primary,
    GA has a runoff threshold, etc.
    """
    state = models.ForeignKey("State", on_delete=models.CASCADE)
    congressional_term = models.ForeignKey(CongressionalTerm, on_delete=models.CASCADE)

    # Primary
    primary_date = models.DateField(null=True, blank=True)
    primary_type = models.CharField(
        max_length=20, blank=True, default="",
        help_text="OPEN, CLOSED, SEMI_CLOSED, BLANKET, JUNGLE",
    )
    primary_runoff_date = models.DateField(null=True, blank=True)

    # General
    general_date = models.DateField(
        help_text="First Tuesday after first Monday in November",
    )
    general_runoff_date = models.DateField(null=True, blank=True)

    # Registration and voting windows
    registration_deadline = models.DateField(null=True, blank=True)
    early_voting_start = models.DateField(null=True, blank=True)
    early_voting_end = models.DateField(null=True, blank=True)
    mail_ballot_request_deadline = models.DateField(null=True, blank=True)
    mail_ballot_receipt_deadline = models.DateField(null=True, blank=True)

    # Certification
    certification_deadline = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("state", "congressional_term")]
```

---

### 5. SpatioTemporalEvent (Things That Happen in the World)

An event with its own geography, independent of any race.

```python
class SpatioTemporalEvent(TemporalGeographicFeature):
    """
    A discrete occurrence with its own spatiotemporal footprint.

    Hurricanes, court rulings, protests, facility closures, pandemics —
    anything that happens somewhere at some time. The geometry can be
    any type: point, line, polygon, or collection.
    """
    EVENT_CATEGORIES = [
        ("NATURAL_DISASTER", "Natural Disaster"),
        ("COURT_RULING", "Court Ruling"),
        ("LEGISLATIVE_ACTION", "Legislative Action"),
        ("CIVIL_UNREST", "Civil Unrest"),
        ("PUBLIC_HEALTH", "Public Health Emergency"),
        ("INFRASTRUCTURE", "Infrastructure Event"),
        ("REDISTRICTING", "Redistricting Action"),
        ("EXECUTIVE_ORDER", "Executive Order"),
    ]

    geometry = models.GeometryCollectionField(
        srid=4326, null=True, blank=True,
        help_text="Spatial extent (point, line, polygon, or collection)",
    )
    event_start = models.DateTimeField(
        help_text="When the event began",
    )
    event_end = models.DateTimeField(
        null=True, blank=True,
        help_text="When the event ended (null = ongoing or instantaneous)",
    )
    event_category = models.CharField(
        max_length=30, choices=EVENT_CATEGORIES, db_index=True,
    )
    description = models.TextField(blank=True, default="")
    external_url = models.URLField(blank=True, default="")

    # Affected boundaries (M2M — which geographies were impacted)
    affected_boundaries = models.ManyToManyField(
        "BoundaryIntersection",  # or through a dedicated join table
        blank=True,
        help_text="Boundaries affected by this event",
    )

    class Meta:
        indexes = [
            models.Index(fields=["event_category"]),
            models.Index(fields=["event_start"]),
            models.Index(fields=["event_category", "event_start"]),
        ]
```

---

### 6. RaceEvent (Things That Happen in a Race)

A milestone or occurrence within a specific race.

```python
class RaceEvent(models.Model):
    """
    Something that happens in the timeline of a Race.

    Electoral events (PRIMARY, GENERAL) don't have their own geometry —
    they inherit spatial scope from the Race's Seat and active
    redistricting plan.

    Exogenous events (EXTERNAL_IMPACT) link to a SpatioTemporalEvent
    that has its own geometry.
    """
    RACE_EVENT_TYPES = [
        # Electoral milestones
        ("FILING_OPEN", "Filing Period Opens"),
        ("FILING_CLOSE", "Filing Deadline"),
        ("PRIMARY", "Primary Election"),
        ("PRIMARY_RUNOFF", "Primary Runoff"),
        ("GENERAL", "General Election"),
        ("GENERAL_RUNOFF", "General Runoff"),
        ("SPECIAL_ELECTION", "Special Election"),
        ("RECOUNT", "Recount"),
        ("CERTIFICATION", "Result Certification"),
        # Candidate events
        ("CANDIDATE_ENTRY", "Candidate Enters Race"),
        ("CANDIDATE_WITHDRAWAL", "Candidate Withdraws"),
        ("ENDORSEMENT", "Major Endorsement"),
        # External impacts
        ("EXTERNAL_IMPACT", "Impacted by External Event"),
        # Administrative
        ("REDISTRICTING_CHANGE", "District Boundaries Changed"),
        ("COURT_ORDER", "Court Order Affecting Race"),
    ]

    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=RACE_EVENT_TYPES, db_index=True)
    event_date = models.DateField(null=True, blank=True)
    event_start = models.DateTimeField(null=True, blank=True)
    event_end = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default="")

    # Link to external event (for EXTERNAL_IMPACT type)
    external_event = models.ForeignKey(
        SpatioTemporalEvent, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="race_impacts",
    )

    class Meta:
        indexes = [
            models.Index(fields=["race", "event_type"]),
            models.Index(fields=["event_date"]),
        ]
        ordering = ["event_date", "event_start"]
```

---

### 7. RedistrictingPlan and PlanDistrictAssignment (Regime)

Maps abstract Seats to concrete boundary polygons for a time window.

```python
class RedistrictingPlan(models.Model):
    """
    A redistricting plan that was in effect for one or more terms.

    Maps Seats to boundary polygons. When a court strikes down a plan,
    effective_to_term is set and a new plan takes over.
    """
    PLAN_TYPES = [
        ("CONGRESSIONAL", "Congressional Districts"),
        ("STATE_SENATE", "State Senate Districts"),
        ("STATE_HOUSE", "State House Districts"),
    ]

    state = models.ForeignKey("State", on_delete=models.CASCADE)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, db_index=True)
    plan_name = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Official name or identifier of the plan",
    )
    effective_from_term = models.ForeignKey(
        CongressionalTerm, on_delete=models.CASCADE,
        related_name="plans_starting",
    )
    effective_to_term = models.ForeignKey(
        CongressionalTerm, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="plans_ending",
        help_text="Null = still active",
    )
    enacted_date = models.DateField(null=True, blank=True)
    enacted_by = models.CharField(
        max_length=30, blank=True, default="",
        help_text="LEGISLATURE, COMMISSION, COURT, SPECIAL_MASTER",
    )
    court_case = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["state", "plan_type"]),
            models.Index(fields=["effective_from_term"]),
        ]


class PlanDistrictAssignment(models.Model):
    """
    Maps a Seat to a concrete boundary polygon under a specific plan.

    Answers: "Under this plan, Seat TX-28 corresponds to
    CongressionalDistrict(geoid='4828', vintage_year=2022)."
    """
    plan = models.ForeignKey(
        RedistrictingPlan, on_delete=models.CASCADE,
        related_name="assignments",
    )
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)

    # Generic FK to the boundary (CongressionalDistrict, StateLegislativeUpper, etc.)
    content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.CASCADE,
    )
    object_id = models.CharField(max_length=20)
    boundary = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = [("plan", "seat")]
```

---

### 8. ReturnSnapshot (Partial Election Returns)

High-frequency election result snapshots as returns come in.

```python
class ReturnSnapshot(models.Model):
    """
    A point-in-time snapshot of election returns for a Race.

    On election night, these are captured every few minutes as precincts
    report. In the days after, updates arrive as mail ballots and
    provisional ballots are counted.
    """
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name="returns")
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When this snapshot was captured",
    )
    source = models.CharField(
        max_length=50, db_index=True,
        help_text="AP, state_sos, county_clerk, etc.",
    )

    # Reporting progress
    precincts_reporting = models.PositiveIntegerField(default=0)
    total_precincts = models.PositiveIntegerField(default=0)
    pct_reporting = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
    )

    # Ballots
    total_ballots_counted = models.PositiveIntegerField(null=True, blank=True)
    ballots_outstanding = models.PositiveIntegerField(null=True, blank=True)

    # Results per candidate: {candidate_id: {votes: N, pct: 0.XX, party: "DEM"}}
    results = models.JSONField(default=dict)

    is_final = models.BooleanField(
        default=False, db_index=True,
        help_text="True when this is the certified final result",
    )

    class Meta:
        unique_together = [("race", "timestamp", "source")]
        indexes = [
            models.Index(fields=["race", "source", "-timestamp"]),
            models.Index(fields=["is_final"]),
        ]
        ordering = ["timestamp"]
```

**Query patterns:**
- "Latest returns for TX-28": `ReturnSnapshot.objects.filter(race=tx28_race).order_by("-timestamp").first()`
- "Election night timeline": `ReturnSnapshot.objects.filter(race=tx28_race, source="AP").order_by("timestamp")`
- "Final certified result": `ReturnSnapshot.objects.get(race=tx28_race, is_final=True)`
- "Races still counting": `Race.objects.exclude(returns__is_final=True)`

---

## Model Relationship Diagram

```
CongressionalTerm ←──── StateElectionCalendar (per state dates)
    │
    ├──── Race ←──── Candidacy (from FEC models)
    │       │
    │       ├──── RaceEvent
    │       │       └── external_event → SpatioTemporalEvent
    │       │
    │       └──── ReturnSnapshot (partial returns timeline)
    │
    ├──── RedistrictingPlan
    │       └── PlanDistrictAssignment
    │               ├── seat → Seat
    │               └── boundary → CongressionalDistrict (etc.)
    │
    └──── (linked to DimTime.is_election_day in warehouse)

Seat ←──── Race (contest for this seat)
    │
    └── identity only: office + state + district_label

SpatioTemporalEvent (independent — has own geometry + time)
    └── race_impacts → RaceEvent (linked via FK)
```

---

## Connection to Existing Models

### FEC Integration

| Existing FEC Model | Connection |
|---|---|
| `Candidate` | Represents an FEC entity. One Candidate may have Candidacies across multiple Races. |
| `Candidacy` | Add nullable FK to `Race`. A candidacy is participation in a race. |
| `Filing` | Coverage period sits within a `CongressionalTerm`. Add nullable FK. |
| `CommitteeSummary` | `election_year` maps to `CongressionalTerm.election_year`. |
| `Transaction` | `transaction_date` falls within `RaceEvent` windows. |

### Warehouse Integration

| Existing Warehouse Model | Connection |
|---|---|
| `DimTime` | `is_election_day` flag aligns with `StateElectionCalendar.general_date`. |
| `DimGeography` | Boundary polygons that `PlanDistrictAssignment` references. |
| `FactElectionResult` | Populated from `ReturnSnapshot` where `is_final=True`. |

### Boundary Integration

| Existing Boundary Model | Connection |
|---|---|
| `CongressionalDistrict` | Target of `PlanDistrictAssignment` for congressional plans. |
| `StateLegislativeUpper` | Target for state senate plans. |
| `StateLegislativeLower` | Target for state house plans. |
| `State` | FK on `Seat`, `StateElectionCalendar`, `RedistrictingPlan`. |
| `VTD` | Geographic unit for precinct-level `ReturnSnapshot` disaggregation. |

---

## Parameterization Plan

The following currently-hardcoded structures should move to config:

| Current Location | What | Target |
|---|---|---|
| `CensusDatasetMapper._initialize_datasets()` | 5 dataset definitions | YAML registry |
| `CensusDataSelector.analysis_patterns` | 7 analysis patterns | YAML registry |
| `VARIABLE_GROUPS` in census_api_client | 14+ variable sets | YAML registry |
| `DimensionLoader.KNOWN_SURVEYS` | Survey year ranges | Derive from registry |
| `GEOID_PREFIX_LENGTHS` in rollup_service | GEOID nesting | Derive from `CANONICAL_GEOGRAPHIC_LEVELS` |
| Senate class rotation schedule | Which classes in which years | Seed data or computed |
| State primary dates/types | Per-state per-cycle | `StateElectionCalendar` records |

---

## Implementation Phases

### Phase A: Temporal Backbone
- `CongressionalTerm` model + seed data (1st through ~125th Congress)
- `Seat` model + seed data (current seats from Census/CQ)
- `StateElectionCalendar` model (initially empty, populated per cycle)

### Phase B: Races and Events
- `Race` model
- `RaceEvent` model
- `SpatioTemporalEvent` (new abstract in base.py + concrete model)
- `ReturnSnapshot` model

### Phase C: Redistricting Regime
- `RedistrictingPlan` model
- `PlanDistrictAssignment` model
- Migration tooling to link existing `CongressionalDistrict` boundaries

### Phase D: FEC Integration
- Add `Race` FK to `Candidacy`
- Add `CongressionalTerm` FK to `Filing`
- Backfill existing FEC data with race/term linkages

### Phase E: Parameterization
- Census dataset YAML registry
- Variable group YAML registry
- Analysis pattern YAML registry
- Derive duplicated constants from canonical sources

---

## Open Questions

1. **Where do these models live?** Options:
   - `siege_utilities.geo.django.models.elections` (keeps everything in siege_utilities)
   - `siege_utilities.elections.django.models` (new top-level module)
   - Split: temporal backbone in siege_utilities, FEC-specific in enterprise

2. **ReturnSnapshot granularity:** Should there be a sub-race level for
   precinct-by-precinct returns? Or is the JSON results field sufficient
   for candidate-level data within each snapshot?

3. **Historical depth:** How far back should CongressionalTerm seed data
   go? 1st Congress (1789) or modern era only (e.g., 1960+)?

4. **State-level offices:** The Seat model includes GOVERNOR, STATE_SENATE,
   STATE_HOUSE. Should it also cover other statewide offices (AG, SoS,
   Treasurer, etc.)?

---

## Related Tickets

- [su#161](https://github.com/siege-analytics/siege_utilities/issues/161) — Consolidate Census data structures (parameterization)
- [su#162](https://github.com/siege-analytics/siege_utilities/issues/162) — PL 94-171 redistricting data pipeline
- [su#166](https://github.com/siege-analytics/siege_utilities/issues/166) — TimezoneGeometry model
