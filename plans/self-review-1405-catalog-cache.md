---
ticket_refs:
  - siege-analytics/siege_utilities#1405: comment posted https://github.com/siege-analytics/siege_utilities/issues/1405#issuecomment-6651506189
---

# Self-review: #1405 / PR #1790, allowlist fingerprints, yearless clear() and release note

Working as: software engineer, data engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1405#issuecomment-6259568906 (findings F1, F2 and return criteria)
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1405#issuecomment-6651437360 (fact sheet: allowlist lines 78-79, `catalog_cache.py:243-246`, callers)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1405#issuecomment-6651437360
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1405#issuecomment-6651437360
Hostile-review-artifact: plans/hostile-review-1405-catalog-cache.md

## Ticket-fitness exemption

### #1405

Reason: #1405 predates the canonical ticket template. Its body carries Problem, Evidence, Failure scenario, Done when and Falsifier sections, but not the canonical Assumptions section.
Evidence: those sections live in https://github.com/siege-analytics/siege_utilities/issues/1405; the reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1405#issuecomment-6259568906.
Falsification: revert the implementation; `tests/test_1405_census_catalog_cache_disk.py::test_clear_removes_only_the_named_entry` goes red because `clear('eits/resconst', None)` does not remove exactly that one entry (on develop it returns 0 because the entry is nested out of sight; at the previous PR head `46f2447f` it removed all 3 files), and `tests/test_1405_census_catalog_cache_disk.py::test_catalog_survives_disk_round_trip` goes red because `clear()` cannot see the nested entry and returns 0 instead of 1.
Verified 2026-11-05: with `siege_utilities/geo/census/catalog_cache.py` checked out from `origin/develop`, `pytest tests/test_1405_census_catalog_cache_disk.py -k "test_clear_removes_only_the_named_entry or test_catalog_survives_disk_round_trip"` -> 4 failed, 1 passed (`:70 assert 0 == 1` for the 3 round-trip cases; `:161 assert 0 == 1` for the yearless clear; the yearful clear case passes on develop); after `git checkout HEAD --` -> 5 passed, worktree clean.

## Assumptions

1. The allowlist fingerprints identify the same reviewed `get` and `put` handlers; only their hashes changed with the key rewrite, so swapping the keys keeps the guard's intent.
2. `clear(dataset)` without a year never meant "delete everything"; raising on partial keys is safer than guessing.
3. #1749 is an open proposal, so the repository convention is still a CHANGELOG entry in held `[4.1.0]`.
4. Under the operator's standing rule (2026-11-06: an entry is BREAKING when code that worked on 4.0.0 now behaves differently), the #1405 entry moves from `[4.1.0]` `### Fixed` to `### BREAKING` with a Migration line. A partial-key `clear()` raises, and filenames change for slash-containing ids and for yearless entries. At v4.0.0, `_cache_path` wrote `f"{dataset}_{year}.json"`, so `year=None` gave `_None.json`; it is now `_none.json`. That corrects the PR body's earlier claim that ids without a slash keep their filenames. The develop `71f02b0b` merge kept both `[4.1.0]` Fixed entries (a union); develop's lines are unchanged.

## Test plan

- F1 red before (at `46f2447f`, after the develop merge): `scripts/check_exception_contracts.py --list` -> unlisted 2, stale 2 (the reviewer's exact fingerprints). After: unlisted 0, stale 0; `tests/guard/test_exception_contract_guard.py` -> 52 passed.
- F2 red before: the new clear tests -> 4 failed (`clear('eits/resconst', None)` removed 3 files; partial keys did not raise). After: `tests/test_1405_census_catalog_cache_disk.py tests/test_census_catalog_cache.py tests/test_rdh_catalog.py` -> 82 passed.

## Peer review

- Shelves: writing-tests:1 (red before on file counts left on disk), writing-tests:2 (partial-key and missing-directory negative paths), writing-claims:2 (counts carry `Verified-by:`); siege-utilities SU-1 (no silent wipe on ambiguous input) and SU-2 (docstring and CHANGELOG describe nested legacy files honestly).
- Syntax check: `py_compile` on 2 changed `.py` files -> all parse clean (exit 0).
- Test suite: 82 cache tests and 52 guard tests passed (exit 0).
- Findings: no library, notebook or example caller passes a partial key; the `clear` handler fingerprints did not change.
- Notebook API: no notebook calls `CatalogCache.clear` (grep). Doc build N/A.

## Lead review

- F1 fixed at the source of truth (the guard's output), not by hand-copying; zero stale entries proves no dead keys remain.
- F2 fixed for the whole method family: `get`, `put` and `clear` all accept `year=None`.
- PR body corrected separately: it claimed cache documentation changes and unchanged filenames, both inaccurate.
- Post-mortem: not applicable. Caught by review and CI before merge; no published version carried it.

## Quantified claims

- Guard: 2 unlisted and 2 stale before, 0 and 0 after; 52 guard tests passed. Cache: 4 red before, 82 passed after.

## Rework ledger

2 hostile-review follow-ups applied (nested-entry wording, missing-directory test).
