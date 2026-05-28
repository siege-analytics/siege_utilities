# Self-Review: SU#621 — NLRB Caching

**Domain:** software engineering
**Geospatial cross-cut:** no (infrastructure)
**Trivial-against-state:** partially — follows CatalogCache pattern from WS1-T3

## Assumptions

1. JSON cache at `~/.siege_utilities/cache/nlrb/` — same convention as Census catalog cache.
2. 30-day default TTL matches data.gov update frequency.
3. NLRBLoader follows cache → fetch → cache-write pattern from CatalogLoader.
4. Failed fetches (errors, zero records) are not cached.

## Peer Review (Junior)

- Date helpers: 5 tests (to_str, from_str, None, invalid)
- Serialization: 4 tests (roundtrip, fetched_at, JSON serializable, empty)
- NLRBCache: 9 tests (miss, hit, mkdir, expiry, invalidate, invalidate_all, corrupted)
- NLRBLoader: 4 tests (cache hit, cache miss, force refresh, failed not cached)
- 22 total tests passing

## Lead Review (Adversarial)

- **Q: Why not Parquet like the epic specifies?** A: Same reasoning as the Census catalog cache (WS1-T3) — the data is a mix of records at different levels (cases, elections, charges). JSON preserves the heterogeneous structure naturally. Parquet is tabular.
- **Q: TTL check uses local time — clock skew?** A: The cache is local-only (single machine). Clock skew isn't a concern. Both put and get use `datetime.now()` consistently.

## Quantified Claims

- 22 new tests, all passing
- NLRBCache (~80 lines) + NLRBLoader (~40 lines) + serialization (~100 lines)
