---
ticket_refs:
  - siege-analytics/siege_utilities#1486: comment posted
---

# Self-review: #1486 / PR #1799 (GEOID alphabets, float normalization, slug round trip)

## Assumptions
Domain(s): software engineering, Census geography identifiers
Goal source: #1486 (GEOID utils reject real district codes, accept invalid numerics)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6650825979
Review being answered: https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6259604009 (exact-head review of ae2f057a: F1, PR body, process)
Pre-author-inventory: the Investigation section of the plan reference above

## Scope of this round
F1: `slug_to_geoid` lowercases the whole slug and returned the cd/sldu/sldl
district tail as-is, so `06ZZZ -> ca-sldu-ZZZ -> 06zzz`, which fails the
uppercase-only district alphabet. The tail is now uppercased. Digit tails are
unchanged by `upper()`, and `geoid_to_slug` output is unchanged.

Body: the "VTD behavior unchanged" claim was inaccurate. `can_normalize_geoid`
now delegates to `normalize_geoid`, whose VTD path only pads and checks length.
`can_normalize_geoid("0100100000A", "vtd")` was False at df87cdca and is now
True. `can_normalize_geoid("0100100000!", "vtd")` is also True, while
`validate_geoid` on that value is False (probed at this head). The CHANGELOG
and PR body now say so.

## Peer review (the Junior's checklist)

### writing-code
- Severe flake8 (E9,F63,F7,F82,E722,F601,F403,F405,F401,F841,F541) on the changed files -> no output.
- `scripts/check_exception_contracts.py` -> handlers flagged 207, unlisted 0, stale 0.

### writing-tests
- Red at f23be9a5 (new tests, old code): pytest -> 29 failed, 78 passed. All 25
  alphanumeric round trips and the 4 mixed-case canonicalization cases fail. The 3
  numeric round trips (4801 cd, 48001 sldu, 48150 sldl) pass before and after.
- After the fix: the selection from the round-1 PR body plus the new tests
  (test_1486, geoid_utils, geoid_validator(s), geoid_slugs, geographic_levels,
  district_geoid_constraints/followups, smoke, runtime_guard, sql_safety,
  api_contract_tools; `-m "not integration and not postgis"`) -> 630 passed,
  36 skipped, 4 deselected. The skips are GeoDjango/GDAL not available locally.

### writing-claims
- The counts are pytest summary lines from this work cycle. The VTD values come
  from a direct probe at this head.

## Lead review
No live notebook calls `slug_to_geoid` or `geoid_to_slug` (checked with grep over
`siege_utilities/` and `notebooks/`). Blast radius: one branch of `slug_to_geoid`.

Junior dismissed, reported as debt: VTD slug round trips are lossy, because VTD
tails allow mixed case and `./-`, and the slug is lowercased and split on `-`.
VTD `can_normalize_geoid` accepts characters that `validate_geoid` rejects. Both
come from the padding-only VTD normalization, which predates this PR and is
outside #1486.

## Rework ledger
- ae2f057a/f23be9a5: the district tail lost its case. F1 is fixed in this round.
- PR body VTD claim corrected; the 4.1.0 note restored to CHANGELOG.md.
- Pre-flight (2026-11-10). Develop sync: `48e9d580` merges develop `71f02b0b` for a positional CHANGELOG conflict (the #1444 and #1486 Fixed entries). Both are kept, a diff against develop deletes 0 develop lines, and no merged develop behaviour disagrees with this PR. Classification follows the operator rule (2026-11-06): a change that alters v4.0.0 caller behaviour is BREAKING. On the v4.0.0 tag, `normalize_geoid` only calls `zfill`, so `"CA037"`/county returned `"CA037"` and `"1001020100"`/block_group returned `"001001020100"`. `slug_to_geoid` lowercases the slug, so `"ca-cd-zz"` returned `"06zz"`. This PR's tests (`test_normalization_rejects_wrong_alphabet`, `test_ten_digit_tract_cannot_become_a_block_group`, `test_district_slug_tail_canonicalizes_to_uppercase`) assert the new raises and the uppercase output. The entry moves from 4.1.0 Fixed to BREAKING with a **Migration:** line. No code changed.

## Findings
F1 fixed. VTD debt reported (see Lead review).

## Ticket-fitness exemption

Governing ticket: #1486. The #1398 epic is context only.

### #1486
Reason: #1486 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier / Related instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1486 states the alphabet, padding and float defects under "## Problem", the citations under "## Evidence" (`geo/geoid_utils.py`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6259604009.
Falsification: revert the implementation; `tests/test_1486_geoid_utils.py::test_district_validation_accepts_census_alphabet` goes red because `validate_geoid("06ZZZ", "sldu")` is False again, and `::test_district_slug_round_trip_preserves_geoid` goes red because `slug_to_geoid` returns `06zzz`.
Observed revert results (2026-11-05). Command, with `REV` set to the revert target:
`git checkout REV -- siege_utilities/geo/geoid_utils.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1486_geoid_utils.py::test_district_validation_accepts_census_alphabet test_1486_geoid_utils.py::test_district_slug_round_trip_preserves_geoid); git checkout HEAD -- siege_utilities/geo/geoid_utils.py`
- `REV=dc7d3f76` (develop): 48 failed, 3 passed. The 3 passes are the numeric round-trip controls.
- `REV=f23be9a5` (pre-F1 head): 25 failed, 26 passed. The 25 alphanumeric round trips fail; the alphabet-validation cases pass.
- Current-head green: after the file was restored, `(cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1486_geoid_utils.py)` gave 107 passed. The worktree was clean.

## Develop 6c049c2c integration, Tier C local gate

Appended 2026-11-13 for the merge of develop `6c049c2c` into this branch, whose head was `6a61f8be`. Every section above is unchanged and describes earlier work.

**History: a voided first staging.** A first integration was staged on 2026-11-11 against develop `79f37f4d` (staged tree `bcc7033c`). It was never committed. Develop then advanced to `6c049c2c` when #1791 landed with the #1404 Census dual-source change. That change adds a bullet at the same 5.0.0 `### BREAKING` anchor, so the earlier staging would conflict. It was backed up, hash-verified 40/40, aborted, and restaged against `6c049c2c`. No result from that staging is carried into this section.

This integration changes no #1486 source or test file. The only conflict was the 5.0.0 `### BREAKING` list in `CHANGELOG.md`. It was resolved markers-only: develop's four entries come first (the three social-connector entries, then #1404 with its Migration line), followed by the #1486 entry verbatim with its Migration line. The staged `CHANGELOG.md` blob is `9a00575d147ec070ccb72a2992a3c06bdf43827f`, equal to the value precomputed before the merge.

Rerere is enabled in the local git configuration. The merge output read "Recorded preimage for 'CHANGELOG.md'", with no "Resolved … using previous resolution" line. The working file kept exactly 3 conflict markers, at 413, 434 and 503, until the hand resolution.

Develop replaced the `4.1.0 - 2026-10-18` heading with an undated `5.0.0` heading, so the #1486 BREAKING entry now sits under 5.0.0. The 4.1.0 wording in the sections above is historical.

**Tier note.** The PR's own content stays at the tier already ruled for it. This merge commit classifies as Tier C locally because develop's delta brings in `.github/workflows/ci.yml` and `.github/actions/apt-install/action.yml`. The fields below meet the Tier C artifact contract for this merge commit only.

Working as: software engineer (develop integration), with geospatial review of the GEOID contracts
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6799953625
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6799953625
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6800137961
Project-contribution: keeps the GEOID alphabet and normalization fixes mergeable on the 5.0.0 line, so their BREAKING note and Migration line ship under the release they describe.

The investigation, pre-mortem and independent hostile review above were written for the first staging against `79f37f4d`. This restage uses the same markers-only method, and the reviewer's seven required actions (answered in https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6800139956) are carried out again here. The one material difference is the added #1404 bullet on the develop side of the conflict, which this section records.

**Correction to the preparation notes.** `tests/test_1486_geoid_utils.py` exists on the PR side only, not on develop. The other four GEOID modules exist on both parents.

## Peer review (develop 6c049c2c integration)

- **writing-code:** no `.py` byte was authored in this integration.
  - Acceptance checks on the pre-append staged tree `d69a5db2`:
    - Against develop `6c049c2c`, exactly the six #1486 paths differ, and `CHANGELOG.md` is +20/-0.
    - Against `6a61f8be`, exactly develop's 51 paths since `71f02b0b` differ. The two ordered path lists have the same sha256. The only `CHANGELOG.md` line removed relative to `6a61f8be` is develop's own edit since that base: the `4.1.0` heading.
    - The preparation trial tree `9ebd1ab6` is not in this repository's object store ("bad object"). The trial comparison was therefore replaced by the two parent comparisons above: every non-CHANGELOG path carries exactly one parent's blob.
  - This file is the one further path. Its diff against `6a61f8be` is append-only.
  - `git diff --cached --check` is clean.
  - A direct `flake8 --select=E9,F63,F7,F82,E722,F601,F403,F405,F401,F841,F541` on `siege_utilities/geo/geoid_utils.py` and the three PR test files produced no output. This is not the lint ratchet.
- **writing-tests (merged snapshot).** A non-editable `siege_utilities` 3.17.2 is installed in the local Python 3.11 interpreter. Tests ran as `python -m pytest` from this worktree, whose `pytest.ini` sets `pythonpath = .`. `test_1486_geoid_utils.py` passing in full shows the worktree code was imported, because pre-PR code fails it (see the revert results above). Each module ran separately with `pytest -o addopts="" -p no:cacheprovider -m "not postgis" -rs`:
  - `test_1486_geoid_utils.py`: 107 passed.
  - `test_geoid_utils.py`: 183 passed.
  - `test_geoid_validator.py`: 85 passed, 0 skipped, 4 deselected. The 4 deselected tests are `postgis`.
  - `test_geoid_validators.py`: 61 passed. It tests `siege_utilities/geo/validators.py`, which does not import `geoid_utils`, so it is a control.
  - `test_geoid_slugs.py`: 35 passed.
  - Control `test_district_geoid_constraints.py`: 36 passed. This exercises the DB-constraint lowercase and hyphen policy.
  - `tests/test_credential_url_guard.py`: 115 passed.
  - **GeoDjango coverage.** In this run the shell set `GDAL_LIBRARY_PATH` to the local Homebrew GDAL. The GeoDjango tests in `test_geoid_validator.py` and the district-constraint control therefore ran instead of skipping. Develop's delta since `79f37f4d` touches no test configuration, so the inference is that the difference from the voided run is environmental.
- **Guards on the merged snapshot:**
  - `scripts/check_credential_urls.py siege_utilities`: 0 unreviewed sites.
  - `scripts/check_exception_contracts.py --list`: 205 flagged, 0 unlisted, 0 stale. This was run fresh after #1791 changed `scripts/contracts/contract_allowlist.json`.
  - `check_secret_literals`: PASS, 0 violations in 395 files.
  - `check_no_stub_docstrings`: OK.
  - `check_unbounded_io`, library and tests: 0 violations each.
  - `check_subprocess_safety`: PASS.
  - `check_atomic_writes`: PASS, 0 unlisted, 0 stale.
  - `check_secure_writes`: PASS.
  - `check_secret_repr`: PASS.
  - `validate_extras_coherence`: OK, 24 extras.
  - `check_lazy_imports`: OK, 59 packages. Its 8 skips are all `geo.django` packages; this checker does not pick up the test configuration's GDAL path.
  - `check_error_path_coverage --report`: 395 modules, 0 fail. `geoid_utils.py` and the #1404 Census modules PASS. This guard is advisory in CI.
  - `check_test_file_hygiene`: PASS.
  - `scripts/release_manager.py --check`: consistent at 5.0.0.
- **NOTRUN, with reasons:**
  - `tests/guard/test_exception_contract_guard.py` and lint-ratchet phases 1-4: a local command guard refused both CI invocations on 2026-11-11, so neither was attempted again.
  - `scripts/contracts/compare_public_api_contracts.py`: it needs the baseline and candidate snapshots that CI generates.
  - `bandit`, `twine check` and `scripts/check_wheel_contents.py`: not run locally.

  Hosted CI covers these.
- **writing-claims:** every count above is a pytest summary line or guard output from runs on the `6c049c2c` merged snapshot during this integration.

## Lead review (develop 6c049c2c integration)

Geospatial: this merge does not change the GEOID contracts. On the merged snapshot, the listed modules pass for:
- uppercase alphanumeric SLD/CD validation and slug round trips;
- numeric widths, zero-padding and the state-`00` guard;
- malformed-character and length rejection;
- uppercase canonicalization of district slug tails.

The #1404 changes from develop touch only the Census API and dual-source modules, not `geoid_utils`.

Whole-PR question, not changed here. On 4.0.0, `normalize_geoid` only called `zfill`, so `normalize_geoid("501-1", "sldu")` and `normalize_geoid("0200a", "sldu")` returned the input unchanged. Under this PR's district pattern (`[0-9]{2}[0-9A-Z]{n}`, `siege_utilities/geo/geoid_utils.py:61-63`) they raise. The Django district constraints still accept those codes; `tests/test_district_geoid_constraints.py`, which ran and passed (36) in this integration, asserts that at lines 25-57. The Migration line names only numeric levels. This is raised for the whole-PR review in https://github.com/siege-analytics/siege_utilities/issues/1486#issuecomment-6800139956. No source or CHANGELOG wording changes in this integration.

Post-mortem: not applicable. This is a develop integration with no regression; the pre-mortem's stale-target Tiger was caught before commit, and the restage is its mitigation.

Not claimed: this integration does not approve or enqueue the PR or close #1486. Fresh required hosted CI on the new head and an independent whole-PR review are still owed.
