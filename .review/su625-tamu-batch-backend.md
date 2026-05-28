# Self-Review: SU#625 — TAMU Batch Backend

**Domain:** software engineering
**Geospatial cross-cut:** yes (geocoding, Census geography extraction, TAMU API)
**Trivial-against-state:** no — new HTTP client with response parsing and GEOID extraction

## Assumptions

1. TAMUBatchGeocoder wraps TAMU's HTTP geocoding API (one address at a time, no true batch endpoint).
2. API key required — from constructor or TAMU_API_KEY env var. `is_available()` returns False without key.
3. TAMU returns Census geography directly — state/county/tract/block FIPS codes extracted from CensusValues.
4. Match quality mapping: Exact/NearExact→exact, Interpolated→interpolated, Approximate→approximate.
5. Zero lat/lon treated as no match (TAMU returns 0,0 for failures).
6. Uses stdlib urllib.request to avoid requests/pandas dependency.

## Peer Review (Junior)

- Config: 9 tests (backend name, availability ×2, API key sources ×2, rate limits ×2, census year ×2)
- Geocoding: 6 tests (empty, no key, single match, no match, multiple, exception, empty query)
- Response parser: 11 tests (match types ×4, empty geocodes, missing lat/lon, zero lat/lon, no census, partial GEOID, input_id, matched_address)
- HTTP layer: 3 tests (successful, retry, max retries)
- 30 total tests passing

## Lead Review (Adversarial)

- **Q: Why 0,0 rejection?** A: TAMU returns (0,0) when it can't geocode rather than omitting coordinates. Treating it as a match would place addresses at Null Island.
- **Q: Should the API key be validated on construction?** A: No — `is_available()` and the early return in `geocode()` handle this. Fail-fast at use time, not construction time, allows configuration before key is set.
- **Q: Why not use the TAMU batch endpoint?** A: TAMU's batch endpoint requires file upload and asynchronous polling. The single-address endpoint is simpler and sufficient for the volumes we handle. A batch adapter could be added later if needed.

## Quantified Claims

- 30 new tests, all passing
- ~200 lines of implementation
- ~220 lines of tests
