# Self-Review: SU#610 — Demographics Overlay

**Domain:** software engineering
**Geospatial cross-cut:** yes (Census demographics, time series, crosswalk-aware GEOID querying)
**Trivial-against-state:** partially — standard provider pattern, key value is crosswalk-aware querying

## Assumptions

1. DemographicsOverlay queries DemographicSnapshot data for a GEOID + time range.
2. Accepts terminal_geoids from lineage to query across crosswalk-changed GEOIDs.
3. Provider pattern (DemographicsDataProvider ABC) decouples from Django.
4. Results sorted by (year, geoid) for consistent timeline output.
5. Optional dataset filter (acs5, acs1, dec, dec_pl).
6. DemographicPoint stores summary fields + full values dict for flexibility.

## Peer Review (Junior)

- DemographicPoint: 2 tests (defaults, fields)
- DemographicsOverlayResult: 6 tests (empty, years, for_year, population series ×2, has_data)
- DictDemographicsProvider: 7 tests (empty, add/get, geoid filter, year range, dataset, sorted, reverse)
- DemographicsOverlay: 9 tests (is_overlay, single geoid, empty, no provider, terminal geoids, dedup, dataset filter, sorted, multi-year)
- 24 total tests passing

## Lead Review (Adversarial)

- **Q: How does this handle split GEOIDs (one GEOID becomes two)?** A: The caller passes terminal_geoids from the lineage. Both target GEOIDs are queried, and both sets of data appear in the time series. Population allocation is the caller's responsibility (or handled by LongitudinalAligner if needed).
- **Q: Why not integrate directly with LongitudinalAligner?** A: LongitudinalAligner requires pandas. The overlay stays pandas-free for testability. When Django + pandas are available, the Django provider can use LongitudinalAligner internally.

## Quantified Claims

- 24 new tests, all passing
- ~180 lines of implementation
- ~170 lines of tests
