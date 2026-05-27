# Self-Review: SU#607 — Core Place History Query Function

**Domain:** software engineering
**Geospatial cross-cut:** yes (spatio-temporal crosswalk chaining, Census vintage transitions)
**Trivial-against-state:** no — new query API composing existing crosswalk infrastructure

## Assumptions

1. `place_history()` is the single entry point for "what's the story of this place over time?"
2. Crosswalk chaining uses decade transitions (1990, 2000, 2010, 2020, 2030) — same as existing `LongitudinalAligner`.
3. Provider pattern (CrosswalkProvider ABC) decouples from Django for testability.
4. DictCrosswalkProvider enables full testing without Django/pandas.
5. Overlay system accepts a registry parameter — WS2-T2 will implement the registry.
6. Forward queries chain source→target; reverse queries chain target→source.

## Peer Review (Junior)

- Decade transitions: 8 tests (same year, same decade, 1/2/3 decade forward, reverse)
- Dataclasses: 4 tests (step defaults, lineage unchanged/changed/split)
- PlaceHistoryResult: 4 tests (direction, has_lineage)
- DictCrosswalkProvider: 5 tests (empty, forward, reverse, split, wrong transition)
- Lineage building: 9 tests (same decade, identical, renamed, split, multi-decade, no data, min weight, reverse, direction flag)
- Integration: 10 tests (basic, no provider, split, overlays ×4, same decade, reverse, state_fips)
- 40 total tests passing

## Lead Review (Adversarial)

- **Q: Why a new chaining implementation instead of using build_reallocation_chain?** A: The existing function requires pandas DataFrames and is coupled to crosswalk_analytics. The place_history chaining uses the same algorithm but operates on simple lists/dicts via the provider protocol. Both are tested independently.
- **Q: Why not query Django models directly?** A: Test env has no Django. The provider abstraction lets us test all logic (decade transitions, chaining, overlay dispatch, error handling) without Django. The Django provider is a thin adapter.
- **Q: What about merged boundaries (reverse of split)?** A: Reverse queries use get_reverse_mappings, which finds all source GEOIDs that map to the target. The same weight/min_weight filtering applies.

## Quantified Claims

- 40 new tests, all passing
- ~300 lines of implementation (result types + provider + chaining + query function)
- ~280 lines of tests (6 test classes)
