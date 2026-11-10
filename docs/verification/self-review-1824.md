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
- GitHub reported PR #1824 MERGEABLE/CLEAN against develop; a read-only trial merge against develop `2deb6a1f` after this round's commit is recorded in the commit message. No develop merge was needed.
- Commit `27e050d1` and its predecessor moved the entry into the PR body under the #1749 convention; #1749 is an open proposal and develop pull requests record entries in `CHANGELOG.md`, so the entry is restored there.
- `census_geocoder.py` changed between v4.0.0 and this branch's merge base (#1400 URL redaction, #1709 fail-loudly). The v4.0.0 red run below confirms the alignment defects exist at the tag itself.
- `GeocodingResult.matched` (`batch_geocoder.py:74`) and `MatchQuality.ERROR = "error"` (`batch_geocoder.py:40`) are the names the CHANGELOG entry cites.
- REST: 0 inline review comments and 0 reviews on PR #1824.

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
