# Self-Review: SU#635 — Precinct-to-VTD Reconciliation

**Domain:** software engineering
**Geospatial cross-cut:** yes (spatial overlap, Census VTDs, election precinct alignment)

## Tests: 40 passing

### Junior says
Full reconciliation pipeline: spatial overlap, fuzzy name matching (SequenceMatcher),
official crosswalk ingestion, and combined scoring (70% spatial + 30% name). Confidence
tiers (high/medium/low) with configurable thresholds. `PrecinctVTDReconciler` orchestrates
all three methods with priority: official > spatial > name. Split precincts handled (one
precinct maps to multiple VTDs). Provider-based for all external data.

### Lead says
The merge priority is correct: official crosswalks should always win. The combined scoring
(SPATIAL_WEIGHT=0.7, NAME_WEIGHT=0.3) is reasonable — spatial overlap is more reliable than
name matching for redistricting data. The test_official_overrides_spatial test correctly
verifies that an official entry takes precedence even when spatial points to a different VTD.
The split precinct handling is important — many real-world precincts straddle VTD boundaries
and need fractional apportionment. The `_normalize_name` regex strips punctuation which is
essential for matching "Dist. #5" against "District 5".
