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

Counts in the sections from "Investigation" through "Findings" F1 to F5 are historical: each was recorded on the commit or tree it names, before the develop integration and the review fix described in "Develop integration and whole-PR review fix". The current-tree counts are in that last section.

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

## Reviewer ruling round (no-backends behaviour and coverage)
Ruling: with no available backend, return one `MatchQuality.ERROR` row per input (caller identity, multiplicity and order kept, no invented coordinates), keep the capability summary, and put per-row diagnostics carrying the caller ID (no address text, credentials, provider body or stack, no invented "raised exception") in the existing `errors` list.

Library change (`geo/providers/composite_geocoder.py`, two edits): missing/duplicate per-row diagnostics name the caller ID (`inputs[batch_id].input_id`) instead of the internal batch ID; each input left without any backend result appends "No geocoding backend produced a result for input_id <caller id>". The "No available geocoding backends" summary stays first.

Coverage map (`tests/test_1410_batch_geocode_alignment.py` unless noted):
| Required control | Test | v4.0.0 (`9c3463b1`) | tip `57257f67` | this round |
|---|---|---|---|---|
| empty input | `test_empty_input_returns_no_rows_and_calls_no_backend` (plus existing `test_composite_geocoder.py::test_empty_input`) | passes (control) | passes | passes |
| duplicate caller IDs | `test_duplicate_and_blank_caller_ids_get_distinct_response_rows[census,batch,composite]` (existing) | fails | passes | passes |
| mixed caller IDs (`1` vs `"1"`) | `test_mixed_type_caller_ids_are_joined_by_internal_ids_not_stringified_ones` | fails (`[3.0, 2.0, 1.0]`) | passes | passes |
| all failed, no backends | `test_no_available_backend_gives_one_error_row_per_input_with_caller_ids` | fails (`[] == ['a', 'a', '', 7]`: no rows) | fails (`0 == 4`: no per-row diagnostics) | passes |
| unknown / duplicate / missing submitted IDs never attach another input's data | `test_corrupted_submitted_ids_never_attach_another_inputs_data[unknown,duplicate,missing]` | fails (rows attached to the wrong inputs) | fails only on the caller-ID diagnostic | passes |
Whole file: v4.0.0 30 failed, 1 passed (the empty-input control); this round 31 passed.

Second develop test modified:
- File and test: `tests/test_composite_geocoder.py::TestCompositeConfig::test_all_unavailable_returns_error` (from #654, `d27dbe68`; not touched by this PR before this round).
- Change: `len(result.errors) == 1` becomes `== 2`; added `"input_id '0'" in result.errors[1]` and `"123 Main St" not in result.errors[1]`. `"No available" in result.errors[0]` is unchanged, and nothing else in the test changes (`git diff --stat`: 3 insertions, 1 deletion).
- Reason: it encoded the pre-ruling one-error contract; the ruling puts per-row diagnostics into the same `errors` list.
- Evidence: (a) unmodified test with the patched code fails (`assert 2 == 1`); (b) modified test with the patched code passes; (c) mutation control, summary dropped (`errors = []`): fails (`assert 1 == 2`); (d) mutation control, per-row diagnostic dropped: fails (`assert 1 == 2`). Both mutations were restored, and the composite diff against HEAD is exactly the two intended edits.
- Touched suites on the final tree (the 1410 file, eight provider files, notebook hygiene/capability, the #1667 file): 432 passed.

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
| F1 | P2 | No CHANGELOG entry in `CHANGELOG.md` (moved to PR body) | entry restored under `[4.1.0] ### BREAKING` with Migration; after the develop integration it sits under `[5.0.0] ### BREAKING` |
| F2 | P2 | PR body labels caller-visible changes as Fixed | body addendum states BREAKING |
| F3 | P3 | Tip lacked review trailers | this commit carries them |
| F4 | P1 | Semantic conflict with develop's #1667 notebook stub (caller IDs) | develop merged `51cfbc10`; stub echoes submitted IDs, with (a)-(d) evidence; merged-tree suites 426 passed |
| F5 | P1 | Reviewer ruling: no-backends per-input error rows with caller-ID diagnostics; required coverage controls | two composite edits; four new test groups (coverage map above); #654 test updated with (a)-(d) evidence; 432 passed |
| F6 | S2 | Whole-PR review of the develop integration: a row a backend returns as `error`, with an empty batch `errors` list, leaves no evidence once another backend's non-error result is kept | the composite reports each such error row in `errors`; seven new tests (nine cases); see the section below |

## Develop integration and whole-PR review fix
Develop `a37044aa` is brought into this branch by a merge (head `ee7d1312`, merge base `2deb6a1f`). The only conflict was `CHANGELOG.md`, inside `[5.0.0] ### BREAKING`: develop's entries are kept as written and the #1410 entry follows them word for word as it stood at the branch head (one of its sentences is reworded later in this section). Against develop the first staged merge differed only in this PR's 15 files, with the same per-file line counts as this PR's own diff from the merge base.

The whole-PR review of that merge tree (`d4f358ce`, https://github.com/siege-analytics/siege_utilities/pull/1824#issuecomment-7015618337) failed with one S2. A backend may return a row with `match_quality == "error"` and leave the batch `errors` list empty; the schema does not require a second, batch-level copy of the failure. The composite copied only batch-level messages, so when a later backend returned an exact match for that row, the final result was an exact row with `errors == []`, and nothing showed that the first attempt had failed. That contradicted the docstring, the CHANGELOG entry and the Migration note, which all say failures stay visible after a successful fallback.

Fix (`geo/providers/composite_geocoder.py`): while each backend's rows are read, a row the backend itself returned as `error` is noted as "Backend <name> returned an error result for input_id <caller id>; a non-error result from another backend was kept". Rows the composite marks as errors because a response was missing or duplicated already get their own message and are not noted twice. When the results are built, the notes for a row are added to `errors` only if its final row is not `error`, that is, if another backend's non-error result was kept: a later backend's match, or an earlier backend's match below the quality threshold when the last backend fails. A row that stays `error` is unchanged: the final row itself shows the failure. In a nested composite the inner composite returns the error row and the outer composite records it under the name `composite`. Caller IDs, coordinates and the number of rows are unchanged. The docstring states the rule, `docs/source/geocoding.rst` adds one sentence for custom backends, and the CHANGELOG sentence on composite fallback now says errors are kept "when another backend's non-error result is kept, including an error row a backend returns without a message" instead of "even when a later backend succeeds". (A first rewording omitted "non-error"; the source audit of tree `e64bed30` noted that two error rows in a row keep the second with `errors` empty, so the qualifier is required.)

Wording round: the first version of the note said "a later backend recovered it". The delta review of that tree (`cf784f07`) found it false in one ordering: with `min_quality="exact"`, an earlier backend's centroid match is kept when the last backend returns `error`, so nothing ran after the failure. The note, the docstring, the rst sentence and the CHANGELOG sentence now use order-neutral wording, and a test pins that ordering.

Version labels: `docs/source/geocoding.rst` and `notebooks/spatial/02_geocoding.ipynb` said "v4.1.0"; both now say "v5.0.0", matching the CHANGELOG section. The notebook change is that one string; its cell layout and trailing newline are unchanged.

Tests (`tests/test_1410_batch_geocode_alignment.py`, seven new tests, nine cases; each asserts the exact message):
- an error row followed by a later match is reported, for a direct backend and a nested composite, each with distinct and with duplicate caller IDs (4); each also checks caller IDs, addresses, match quality and coordinates;
- an error row followed by a later match below the quality threshold is reported (1);
- an earlier match below the threshold followed by an error from the last backend, with `min_quality="exact"`: the earlier match is kept and the error is reported with the order-neutral note (1);
- in a mixed batch only the row with a kept match is reported, and the row that stays missing keeps its own message (1);
- controls: an unrecovered error row adds no message, and a recovered missing row is reported once (2).

Results on the current tree:
- Red, with `composite_geocoder.py` as in `d4f358ce` and the first eight cases: 6 failed and 2 passed. Every failing case passed its caller-ID, address, quality and coordinate checks and failed only on `errors` (for example `[] == ['Backend error-rows returned an error result for input_id ...']`); the two controls passed.
- Red for the wording, with `composite_geocoder.py` as in `cf784f07` and all nine cases: 7 failed and 2 passed. The earlier-match ordering failed on the old note ending "a later backend recovered it", and the six other message checks failed on the same text; the two controls passed.
- The review's four-case witness file, run unmodified: 2 failed and 2 passed on `d4f358ce` (recorded by the review), 4 passed with the fix and with the reworded note.
- After the fix: the nine cases pass. `tests/test_1410_batch_geocode_alignment.py` 40 tests; with `test_1667_geocoding_cache_notebook_truth`, `test_census_batch`, `test_census_geocoder` and `test_composite_geocoder`, 118 passed. The geocoding neighbours (`test_batch_geocoder`, `test_census_geocoder_errors`, `test_geo_geocoding_core_errors`, `test_geo_geocoding_errors`, `test_geocode_results_to_dataframe`, `test_geocode_validation_crs`, `test_geocode_validation_pandas`, `test_nominatim_batch`, `test_nominatim_geocoder_errors`, `test_tamu_batch`) with the release-process and changelog-export tests and notebook hygiene and capability coverage: 439 passed.
- `ruff check --select F,E9` on the changed Python files: no findings. Exception-contract scanner: 208 flagged, 0 unlisted, 0 stale. Test-file hygiene: pass.
- Not run: `tests/test_property_geocoding.py` sends live requests through `get_coordinates` and `use_nominatim_geocoder`, which this PR does not change. A combined run that included it stopped making progress while the network was unreliable, so it was left out rather than sending those requests to the external service.
