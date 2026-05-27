# Self-Review: SU#626 — Composite Geocoder

**Domain:** software engineering
**Geospatial cross-cut:** yes (multi-backend geocoding orchestration)
**Trivial-against-state:** no — new composition logic with quality-based fallback

## Assumptions

1. CompositeBatchGeocoder chains backends in priority order (e.g., Census→Nominatim→TAMU).
2. Fallback triggered when match quality is below configurable threshold (default: approximate).
3. Best result across all tried backends is kept per address.
4. Unavailable backends skipped by default (configurable).
5. Backend exceptions caught and logged; processing continues to next backend.
6. Addresses resolved above threshold are not re-sent to subsequent backends (early exit optimization).

## Peer Review (Junior)

- Quality rank: 2 tests (ordering, unknown)
- Config: 4 tests (backend name, requires backends, empty input, all unavailable)
- Fallback: 14 tests (first succeeds, fallback, best result, partial, exception, skip unavailable, don't skip, all fail, quality threshold, exact threshold, three-chain, input_ids, early stop, multi-address)
- 20 total tests passing

## Lead Review (Adversarial)

- **Q: What if backends return different numbers of results than addresses?** A: The zip in the loop pairs results by position. If a backend returns fewer results, the remaining addresses stay in the pending set and fall through to the next backend.
- **Q: Why keep best rather than first-acceptable?** A: A later backend might return a higher-quality match. Since we already pay the API call for pending addresses, keeping the best is free.
- **Q: Why not merge GEOIDs from one backend with coordinates from another?** A: Cross-backend merging introduces correctness risk (different backends may geocode to different locations). The caller can post-process if needed.

## Quantified Claims

- 20 new tests, all passing
- ~130 lines of implementation
- ~220 lines of tests
