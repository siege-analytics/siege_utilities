# Self-Review: SU#628 — Block Assignment

**Domain:** software engineering
**Geospatial cross-cut:** yes (geocoding results → block-level grouping, spatial spread)

## Assumptions

1. assign_blocks() converts GeocodingResult to BlockAssignment, filtering unmatched.
2. group_by_block() groups by block GEOID with centroid calculation, sorted by count.
3. compute_spread() provides Herfindahl concentration index, bounding box, and geographic hierarchy counts.
4. Missing block GEOIDs fall back to tract or county.

## Tests: 18 passing

- assign_blocks: 5 tests (empty, skip unmatched, convert, input_id, multiple)
- group_by_block: 6 tests (empty, single, multiple, sorted, centroid, fallback)
- compute_spread: 7 tests (empty, single block, two equal, counts, bbox, precomputed, skewed)
