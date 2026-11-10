---
ticket_refs:
  - siege-analytics/siege_utilities#1405: summarized in the self-review ticket comment
---

# Hostile review: #1405 / PR #1790 allowlist drift, clear() and note

Reviewer: a separate read-only review agent (same model family as the implementer). The cross-family exact-head re-review by the independent PR reviewer is still required and is requested after push.
Scope: the uncommitted diff on top of the develop merge `e1901ef9` (`catalog_cache.py`, `tests/test_1405_census_catalog_cache_disk.py`, `scripts/exception_contracts_allowlist.json`, `CHANGELOG.md`).

## Findings and dispositions

1. No blocker: no caller uses a partial key. `tests/test_census_catalog_cache.py:177` passes a full key and `:186,191` call `clear()`; `CatalogLoader` has no clear wrapper; `spatial_data.py:1584` clears a different object.
2. No blocker: `clear("", year)` raises, `clear("ds", 0)` removes only `ds_0.json`, and the partial-key check runs before the missing-directory early return.
3. No blocker: `requires-python >=3.11`, so `Optional[int] | _Unset` evaluates cleanly when Sphinx resolves hints.
4. No blocker: the allowlist edit swaps only the two fingerprint hashes; justifications are byte-identical and the `clear` keys are untouched.
5. FOLLOW-UP, fixed: "Existing nested entries are refreshed on the next load" overstated it; legacy nested files are never read or cleared. The CHANGELOG and the class docstring now say so.
6. FOLLOW-UP, fixed: added a partial-key test against a missing cache directory.
7. FOLLOW-UP, not in scope: the repository has both `[Unreleased]` and `[4.1.0]` Fixed sections; that inconsistency predates this PR. Cleaning legacy nested files in `clear()` stays a follow-up.

Verdict: no blockers.
