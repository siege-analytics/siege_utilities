# Self-Review: SU#619 — NAICS/SOC Job Code Integration

**Domain:** software engineering
**Geospatial cross-cut:** no (reference data, used by NLRB geo models)
**Trivial-against-state:** partially — extends existing module with lookup tables + query interface

## Assumptions

1. NAICS subsectors (3-digit) are the most useful level for NLRB analysis — finer codes change too frequently between revisions.
2. SOC minor groups cover the main occupation categories referenced in bargaining unit descriptions.
3. `filter_by_naics()` uses prefix matching — "622" matches "622110", "622210", etc. Empty prefix returns empty list.
4. Query interface works with any object that has a `naics_code` attribute or dict key.

## Peer Review (Junior)

- NAICS_SUBSECTORS: 5 tests (count, specific entries, code format validation)
- SOC_MINOR_GROUPS: 4 tests
- Combined lookups: 6 tests (get_naics_lookup, get_soc_lookup)
- Title lookups: 9 tests (naics_title, soc_title at various levels)
- filter_by_naics: 7 tests (prefix, sector, exact, no match, empty, dicts, whitespace)
- filter_by_naics_sector: 2 tests
- group_by_naics_sector: 2 tests
- 35 total tests passing

## Lead Review (Adversarial)

- **Q: Why 3-digit NAICS codes and not the full 6-digit taxonomy?** A: The full NAICS table is 20K+ entries and changes every 5 years. Subsectors (3-digit) are stable across revisions and sufficient for NLRB analysis. The existing fuzzy_match_naics() handles free-text-to-code mapping for finer granularity.
- **Q: Test imports use importlib to bypass reference/__init__.py — fragile?** A: Yes, but the alternative is making the reference package's pandas dependency optional. That's a broader refactor. The test file documents the workaround clearly.

## Quantified Claims

- 35 new tests, all passing
- ~120 NAICS subsector entries, ~90 SOC minor group entries bundled
- 6 new functions: get_naics_lookup, get_soc_lookup, naics_title, soc_title, filter_by_naics, filter_by_naics_sector, group_by_naics_sector
