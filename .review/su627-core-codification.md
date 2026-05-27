# Self-Review: SU#627 — Core Codification Function

**Domain:** software engineering
**Geospatial cross-cut:** yes (geocoding → block assignment → area profiling)
**Trivial-against-state:** no — new composition layer binding geocoding to Census geography

## Assumptions

1. `codify_area()` is the entry point: addresses → geocode → block profiles.
2. BlockProfile holds per-block data with slots for demographics/urbanicity/recency (T3/T4/T5).
3. CodificationResult provides geographic spread metrics (block/tract/county/state counts).
4. Default geocoder is CensusBatchGeocoder; caller can inject any BatchGeocoder.
5. Addresses without block GEOIDs fall back to tract or county grouping.
6. Blocks sorted by address count (most common).

## Peer Review (Junior)

- BlockProfile: 2 tests
- CodificationResult: 4 tests (empty, counts, top_blocks, summarize)
- _build_block_profiles: 6 tests (empty, single, multiple, sorted, fallback, hierarchy)
- codify_area: 8 tests (empty, default geocoder, basic, partial match, exception, census_year, multi-block, summarize)
- 20 total tests passing

## Lead Review (Adversarial)

- **Q: Why slots for demographics/urbanicity/recency instead of computing them here?** A: Separation of concerns. T1 defines the skeleton; T3/T4/T5 populate it. This avoids circular dependencies and keeps the core function testable without heavy dependencies.
- **Q: What about addresses that geocode but have no block GEOID?** A: Falls back to tract_geoid, county_geoid, or "unknown". The caller can filter these out or handle them as needed.

## Quantified Claims

- 20 new tests, all passing
- ~190 lines of implementation
- ~190 lines of tests
