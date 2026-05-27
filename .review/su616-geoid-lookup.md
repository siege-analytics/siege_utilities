# Self-Review: SU#616 — GEOID Lookup Mode

**Domain:** software engineering
**Geospatial cross-cut:** yes (GEOID-to-locale mapping)
**Trivial-against-state:** no — new LocaleIndex class + classify_geoid methods

## Assumptions

1. LocaleIndex is a simple dict wrapper — GEOIDs are strings, locale codes are ints.
2. `from_dataframe()` factory skips invalid locale codes silently (log warning would add noise for large datasets).
3. `classify_geoid_or_point()` tries index first, falls back to spatial — caller provides both GEOID and coordinates.
4. The index is set externally (e.g., from NCES district data) rather than auto-built, keeping the classifier I/O-free.

## Peer Review (Junior)

- LocaleIndex: 7 tests (add/get, missing, bulk, contains, from_dataframe, invalid codes, custom columns).
- ClassifyGeoid: 5 tests (with index, without index, missing GEOID, fallback priority, fallback to spatial).
- 52 total locale tests passing.

## Lead Review (Adversarial)

- **Q: Why not auto-build the index from NCES data?** A: That would couple the classifier to I/O. The index is populated externally — from district data, school locations, or a precomputed Parquet file. Same separation as CensusCatalog/CensusCatalogPopulator.
- **Q: What about tract-level GEOIDs?** A: The index accepts any GEOID format. Tract-level mapping would come from a spatial join (classify each tract centroid once, store the results). That's a data-preparation step, not a classifier concern.

## Quantified Claims

- 12 new tests, 52 total passing
- ~80 lines of LocaleIndex + ~25 lines of classifier methods
