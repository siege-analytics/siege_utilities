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
