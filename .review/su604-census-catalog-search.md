# Self-Review: SU#604 — Catalog Search

**Domain:** software engineering
**Geospatial cross-cut:** no
**Trivial-against-state:** no — adds search to the core data model

## Assumptions

1. Token-based keyword matching is sufficient for catalog search; no stemming or fuzzy matching needed at this stage.
2. Stop words reuse the existing `_CONCEPT_STOP_WORDS` set from concept keyword extraction.
3. Scoring weights (exact word match = 1.0, substring = 0.5, ID exact = 2.0) provide reasonable ranking without over-engineering.
4. Variable-level search iterates all tables' variables — acceptable for catalog-sized data (thousands, not millions).

## Peer Review (Junior)

- Search works across all 5 levels: Dataset, Subject, Family, Table, Variable.
- Level filter, dataset filter, and max_results all work correctly.
- Results are sorted by score descending, then by ID for stability.
- 20 tests covering tokenization, each level individually, cross-level, ranking, filtering.
- No new dependencies. No I/O — pure in-memory search.

## Lead Review (Adversarial)

- **Q: Why not use a proper full-text search library?** A: The catalog has at most ~30k entries. Linear scan with keyword matching is fast enough and avoids adding a dependency. If performance becomes an issue, we can add an inverted index later.
- **Q: The `_CONCEPT_STOP_WORDS` set is shared with family detection — is that appropriate?** A: Yes, Census concept strings use the same vocabulary across both use cases.
- **Q: Does adding SearchLevel/SearchResult to catalog.py bloat the data model?** A: They're lightweight (enum + dataclass), and search is a core query feature of the catalog, not a separate concern.

## Quantified Claims

- 20 new tests, all passing
- 32 existing catalog tests still pass
- 18 existing cache tests still pass
- ~80 lines of scoring functions + ~80 lines of search method
