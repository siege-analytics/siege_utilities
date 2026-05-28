# Self-Review: SU#624 — Nominatim Batch Backend

**Domain:** software engineering
**Geospatial cross-cut:** yes (geocoding, rate limiting, Nominatim API)
**Trivial-against-state:** no — new HTTP client with retry logic and rate limiting

## Assumptions

1. NominatimBatchGeocoder wraps Nominatim's `/search` endpoint (no true batch API).
2. Rate limiting defaults: 1.0s for public instance, 0.05s for self-hosted (auto-detected from URL).
3. Match quality is always APPROXIMATE — Nominatim doesn't report exact/interpolated distinction.
4. No GEOIDs returned — Nominatim doesn't provide Census geography; spatial join needed downstream.
5. Uses stdlib `urllib.request` instead of `requests` to avoid pandas dependency chain via geocoding.py.

## Peer Review (Junior)

- Config: 7 tests (backend name, rate limits ×3, server URLs ×2, country codes ×2)
- Geocoding: 5 tests (single match, no match, multiple, exception, empty query)
- Quality: 2 tests (approximate quality, no block GEOID)
- HTTP layer: 4 tests (successful response, empty response, retry on failure, raises after max retries)
- Availability: 1 test
- 21 total tests passing

## Lead Review (Adversarial)

- **Q: Why not use `get_coordinates` from `geocoding.py`?** A: `geocoding.py` eagerly imports pandas at module level. Importing it — even to mock — fails in the test env. Using `urllib.request` directly keeps the module pandas-free.
- **Q: Is `urllib.request` sufficient vs `requests`?** A: For a simple GET with JSON response, yes. The retry loop and timeout cover the essential reliability needs. Self-hosted users who need connection pooling can subclass.
- **Q: Why APPROXIMATE for all matches?** A: Nominatim's response doesn't distinguish match precision. The caller can post-process if finer quality is needed.

## Quantified Claims

- 21 new tests, all passing
- ~170 lines of implementation (class + HTTP request method)
- ~170 lines of tests (2 test classes)
