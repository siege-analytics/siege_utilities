# Self-review: PR #1824 batch geocoding alignment and partial chunk success (#1410)

Review-Tier: C (geocoding provider contracts; pre-flight round with a BREAKING classification).

## Assumptions
Working as: software engineer (Junior) and geospatial/data-platform tech lead (Lead).
Domain(s): software engineering (batch geocoding providers, Census batch CSV submission).
Geospatial cross-cut: yes (address-to-coordinate alignment; no CRS logic changed).
Goal source: #1410 (batch responses attached coordinates to the wrong address when a backend reordered or dropped rows; a Census chunk failure erased earlier successes). This round is a pre-flight of the existing implementation at `27e050d1`: restore the CHANGELOG entry as BREAKING against the v4.0.0 tag and re-run red/green evidence. No library code changed in this round.
Plan reference: docs/verification/self-review-1824.md#pre-mortem
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1410#issuecomment-6759207036
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1410#issuecomment-6759207036
Project-contribution: geocoded coordinates always belong to the address that was submitted, and one failed Census chunk no longer discards the others.

## Investigation
- GitHub reported PR #1824 MERGEABLE/CLEAN against develop. A read-only trial merge (`git merge-tree --write-tree`) of `0a38d40f` against develop `2deb6a1f` reported no conflicted files (tree `b7926c4b`). A temporary merged-tree test run then showed a semantic conflict with develop's #1667 notebook test (1 failed, 8 passed; the same file on develop alone: 9 passed), so develop was merged (`51cfbc10`) as approved for a demonstrated semantic conflict; see "Develop test modified".
- Commit `27e050d1` and its predecessor moved the entry into the PR body under the #1749 convention; #1749 is an open proposal and develop pull requests record entries in `CHANGELOG.md`, so the entry is restored there.
- `census_geocoder.py` changed between v4.0.0 and this branch's merge base (#1400 URL redaction, #1709 fail-loudly). The v4.0.0 red run below confirms the alignment defects exist at the tag itself.
- `GeocodingResult.matched` (`batch_geocoder.py:74`) and `MatchQuality.ERROR = "error"` (`batch_geocoder.py:40`) are the names the CHANGELOG entry cites.
- REST: 0 inline review comments and 0 reviews on PR #1824.

## Develop test modified
- File and helper: `tests/test_1667_geocoding_cache_notebook_truth.py`, `_install_offline_services()` (landed on develop for #1667 via #1783), used by `test_geo_notebook_group_runs_offline[spatial/02_geocoding.ipynb]`.
- Change: only the `addressbatch` stub. `return_value` (rows hard-coded with the caller IDs "1".."5") becomes a `side_effect` that reads the submitted CSV (column 0, no header, input order; `census_geocoder.py:347-360`) and echoes those IDs positionally onto the same five rows. The notebook and every assertion (`addressbatch.assert_called_once()`, `len(results) == 5`, `matched_ids == ['1', '2', '3']`, `unmatched['id'] == ['4', '5']`) are unchanged; no other develop test changes.
- Reason: #1410 submits library-assigned batch IDs and rejects unknown or duplicate response IDs; caller IDs are restored on output. A stub that answers with caller IDs is the kind of backend the documented BREAKING contract rejects ("custom backends must echo the submitted input_id"), so the notebook fell into its `CensusGeocodeError` path and collected no results. Echoing the submitted IDs is what the Census batch API does.
- Evidence on the merged tree (`51cfbc10` plus the stub change):
  - (a) old stub: `test_geo_notebook_group_runs_offline[spatial/02_geocoding.ipynb]` fails at `assert len(results) == 5` (1 failed, 8 passed for the file);
  - (b) echo stub: the file gives 9 passed;
  - (c) mutation control on what #1667 protects (the timed cell is an in-memory scan, not a second geocoder run): cell `c5` temporarily re-runs `geocode_batch(...)` before the scan; with the echo stub in place the test fails, `Expected 'addressbatch' to have been called once. Called 2 times.` (1 failed, 8 passed). The notebook was then restored from HEAD and `git status` shows only the test file modified;
  - (d) contract control: `tests/test_1410_batch_geocode_alignment.py::test_census_rejects_ambiguous_response_ids[unknown]` raises `CensusGeocodeError` ("unknown or duplicate"), and the composite variant `test_composite_rejects_ambiguous_response_ids[unknown]` marks the row `error`; both pass on the merged tree.

## Pre-mortem
1. Tiger. Severity: P2. The entry under-describes the `"error"` quality and the `input_id` contract. Mitigation: the entry names `MatchQuality.ERROR`, `matched`, `CensusGeocodeError`, the `chunk_size` `ValueError` and the echo requirement, with a Migration line.
2. Paper Tiger. Severity: P2. The v4.0.0 red run fails for import reasons. Mitigation: failures read; they are alignment and contract assertions (`[3.0, 2.0, 1.0] == [1.0, 2.0, 3.0]` for the reversed stub, `[1.0, 1.0, 3.0, 3.0] == [1.0, 2.0, 3.0, 4.0]` for duplicate/blank IDs, `'no_match' == 'error'`, `DID NOT RAISE CensusGeocodeError`).
3. Paper Tiger. Severity: P3. The CHANGELOG insertion conflicts with develop. Mitigation: read-only trial merge against `2deb6a1f` before push.
4. Tiger. Severity: P1. Wrong ref or non-fast-forward push. Mitigation: explicit refspec, no force, remote head checked to advance from `27e050d1`.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (failed rows are `error`, never a success-shaped `no_match`); SU-2 (results join by the ID the library submitted, as documented); DDIA frame: the submitted address list is the system of record and geocoded coordinates are derived data keyed by a stable ID.
- Gate 1 (syntax): no Python file changed in this round.
- Gate 2 (tests): on the branch, `tests/test_1410_batch_geocode_alignment.py` 25 passed; provider suites (`test_composite_geocoder`, `test_census_batch`, `test_census_geocoder`, `test_census_geocoder_errors`, `test_batch_geocoder`, `test_geocode_results_to_dataframe`, `test_nominatim_batch`, `test_tamu_batch`) 159 passed; notebook hygiene and capability coverage 233 passed (the PR edits `notebooks/spatial/02_geocoding.ipynb`).

## Lead review (adversarial)
Phase A coherence: the CHANGELOG entry, PR body and tests describe ID-based joins, per-chunk errors and the custom-backend contract.
Phase B verification (red/green): `tests/test_1410_batch_geocode_alignment.py` copied into a detached v4.0.0 worktree (`9c3463b1`) -> 25 failed. On the branch -> 25 passed. Import paths were checked to resolve to the worktree package.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | No CHANGELOG entry in `CHANGELOG.md` (moved to PR body) | entry restored under `[4.1.0] ### BREAKING` with Migration |
| F2 | P2 | PR body labels caller-visible changes as Fixed | body addendum states BREAKING |
| F3 | P3 | Tip lacked review trailers | this commit carries them |
| F4 | P1 | Semantic conflict with develop's #1667 notebook stub (caller IDs) | develop merged `51cfbc10`; stub echoes submitted IDs, with (a)-(d) evidence; merged-tree suites 426 passed |
