# Self-Review: SU#622 — BatchGeocoder Interface

**Domain:** software engineering
**Geospatial cross-cut:** yes (geocoding, GEOID schemas)
**Trivial-against-state:** no — new ABC + result schema + address normalization

## Assumptions

1. GeocodingResult carries block/tract/county/state GEOIDs as strings — not all backends provide all levels.
2. MatchQuality enum covers the main quality tiers across Census (exact/non-exact), Nominatim (interpolated), and TAMU.
3. AddressInput normalizes dict/string/dataclass inputs into a common format for all backends.
4. BatchGeocodingResult provides both DataFrame and GeoDataFrame output (lazy pandas/geopandas import).
5. is_available() defaults to True — override for backends needing API keys or connectivity checks.

## Peer Review (Junior)

- GeocodingResult: 5 tests (default, exact, block check, tract check, to_dict)
- MatchQuality: 2 tests
- BatchGeocodingResult: 3 tests (empty, counts, errors)
- AddressInput: 3 tests (one_line, partial, empty)
- normalize_addresses: 7 tests (dicts, strings, AddressInput, empty, address key, id key, unsupported)
- BatchGeocoder ABC: 5 tests (no instantiate, concrete, strings, dicts, id preservation)
- 25 total tests passing

## Lead Review (Adversarial)

- **Q: Why not reuse CensusGeocodeResult?** A: It's Census-specific (FIPS components, TIGER fields). The unified GeocodingResult uses composite GEOIDs and a backend-agnostic quality enum. A converter from CensusGeocodeResult to GeocodingResult is WS5-T2's responsibility.
- **Q: GeoDataFrame output lazy-imports geopandas — what if it's not installed?** A: ImportError propagates naturally. The method is on BatchGeocodingResult, not the ABC, so backends don't need geopandas to function.

## Quantified Claims

- 25 new tests, all passing
- ~220 lines of implementation (result schema, address normalization, ABC)
