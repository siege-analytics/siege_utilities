# Self-review: PR #1827 Census dual-source provenance, cache expiry, nation and bulk integrity (#1406)

Review-Tier: C (data provenance and cache integrity for Census retrieval; pre-flight round with a BREAKING classification and a `[4.0.0]` correction).

## Assumptions
Working as: software engineer (Junior) and data-platform tech lead (Lead).
Domain(s): software engineering (Census API and Summary File bulk sources, parquet cache, retries).
Geospatial cross-cut: light (FIPS geography clauses only).
Goal source: #1406 (bulk provenance kept only the first URL, no cache-hit metadata, parquet expiry race, nation requests, unbounded bulk downloads, retry timeouts not reaching fallback). This round is a pre-flight of the existing implementation at `40adef9b`: restore the CHANGELOG entries (moved to the PR body) as BREAKING against the v4.0.0 tag, apply the PR body's `[4.0.0]` correction, and re-run red/green evidence. No library code changed in this round.
Plan reference: docs/verification/self-review-1827.md#pre-mortem
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1406#issuecomment-6759219793
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1406#issuecomment-6759219793
Project-contribution: every Census frame says exactly where its data came from and whether it was cached, and a cache built from a partial download is never reused.

## Investigation
- GitHub reported PR #1827 MERGEABLE. The 10-19 battle-test failure has expired logs; the fresh run on this push replaces it.
- v4.0.0 `dual_source.py:254` returned `Provenance("bulk", urls[0], 1, False)` (first URL only) and API results had `url_or_path=None`; the branch sets `url_or_path=served[0]` for API results (`dual_source.py:146`). Both are named in the entry.
- v4.0.0 rejected the `nation` geography in `DatasetSelector` (`dataset_selector.py:86`, observed in the red run), so nation support is new; the state/county-filter `ValueError` is therefore not a v4.0.0 regression and is not presented as one in the Migration line.
- `[4.0.0]` correction: the existing #1374 entry says "Year-based discovery is unchanged and builds byte-identical URLs." That is false: v3.23.0 used `CENSUS_API_BASE_URL = "https://api.census.gov/data"` (`config/census_registry.py:303`) with a `/data/{year}` path (`catalog_populator.py:98`), producing `/data/data/{year}`, and #1373 (`dda8ecaa`) normalized it in v4.0.0. Only that sentence is replaced, with the PR body's text; no other `[4.0.0]` line changes.
- `geo/census/api.py` changed between v4.0.0 and this branch's merge base (#1400, #1498, #1509); the red run below is against the v4.0.0 tag itself.
- REST: 0 inline review comments and 0 reviews on PR #1827.

## Pre-mortem
1. Tiger. Severity: P2. Editing the released `[4.0.0]` section reads as rewriting history. Mitigation: one factually false sentence replaced with evidence above; the entry keeps its date, section and scope.
2. Tiger. Severity: P2. The BREAKING entry overclaims (presents new nation support as a break). Mitigation: corrected after the red run showed v4.0.0 rejected `nation`.
3. Paper Tiger. Severity: P2. Red evidence inflated by new-API failures. Mitigation: failure classes listed below.
4. Tiger. Severity: P1. Wrong ref or non-fast-forward push. Mitigation: explicit refspec, no force, remote head checked to advance from `40adef9b`.

## Peer review (Junior: shelves, gates)
- Shelves: DDIA frame (the Census API/Summary File is the system of record; the parquet cache is derived data, now integrity-checked so a partial download cannot outlive the code that wrote it); SU-1 (an expired-key race is a cache miss, not an error or empty frame).
- Gate 1 (syntax): no Python file changed in this round.
- Gate 2 (tests): on the branch, `tests/test_1406_census_dual_source.py` 24 passed; `tests/test_dual_source_1375.py tests/test_summary_file_1385.py` 115 passed.

## Lead review (adversarial)
Phase A coherence: CHANGELOG entry, PR body and tests describe the total deadline, SHA-256 cache checks, provenance fields, nation support, expiry race and timeout fallback.
Phase B verification (red/green): `tests/test_1406_census_dual_source.py` copied into a detached v4.0.0 worktree (`9c3463b1`) -> 23 failed, 1 passed. Failure classes on v4.0.0:
- defect at the tag: `FileNotFoundError: another worker removed the expired key` (expiry race), national bulk rows and multi-table provenance counts wrong (`assert 2 == 4`, `CensusAPIError: No county rows ...`, frame mismatch), exhausted API timeouts not reaching the bulk fallback (`Live network is forbidden`), `nation` rejected by `DatasetSelector`;
- new API surface: `Provenance` has no `location`/`cache_hit`; `BulkFileSource(total_timeout=...)` is a new keyword.
On the branch -> 24 passed. Import paths were checked to resolve to the worktree package.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | CHANGELOG entries only in the PR body | restored under `[4.1.0] ### BREAKING` with Migration |
| F2 | P2 | False "byte-identical URLs" sentence in the `[4.0.0]` #1374 entry | replaced with the PR body's correction |
| F3 | P3 | Entry draft presented nation support as a break | corrected; nation support stated as new |
| F4 | P3 | Tip lacked review trailers | this commit carries them |
