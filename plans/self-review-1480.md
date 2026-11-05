---
ticket_refs:
  - siege-analytics/siege_utilities#1480: comment posted
---

# Self-review: #1480 / PR #1797 (RDH chamber selection, provider error contract)

## Assumptions
Domain(s): software engineering, redistricting data access
Goal source: #1480 (RDH SLDU/SLDL chamber mapping)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1480#issuecomment-6650697161
Review being answered: https://github.com/siege-analytics/siege_utilities/issues/1480#issuecomment-6259598610 (exact-head review of d9b24ec1: F1 + process)
Pre-author-inventory: the Investigation section of the plan reference above

## Scope of this round
F1: `RDHProvider.get_boundary` called `get_precinct_data` / `get_enacted_plans`
outside its `try`, so the client's ambiguity `ValueError` escaped unwrapped
while load failures raised `BoundaryFetchError`. The lookup now sits in a
`try` mapping `(OSError, ValueError)` to `BoundaryFetchError` (chained, cause
text in the message), the same mapping as the load block. Argument validation
(unknown level, no state) stays `ValueError` above the `try`. The docstring no
longer claims a `None` return and lists `BoundaryFetchError`.

The `[4.1.0]` note returns to CHANGELOG.md (the body-only convention was not
adopted) and states the provider contract.

## Peer review (the Junior's checklist)

### writing-code
- Severe flake8 (E9,F63,F7,F82,E722,F601,F403,F405,F401,F841,F541) on the changed files -> no output.
- `scripts/check_exception_contracts.py` -> handlers flagged 207, unlisted 0, stale 0.
- `scripts/check_no_stub_docstrings.py` -> OK; `scripts/check_test_file_hygiene.py` -> PASS.

### writing-tests
- Red at cee57289 (new tests, old code): pytest -> 7 failed, 62 passed. The 3
  ambiguity-wrap cases and the 4 lookup-failure cases fail. The 2 argument-error
  cases pass before and after, which shows nothing was over-wrapped.
- After the fix: pytest -> 69 passed (test_1480_rdh_chamber_sldu_sldl.py).
- The old `test_ambiguous_chamber_is_refused_before_loading[get_boundary-*]`
  cases asserted the bare `ValueError` this round removes. They moved to
  `test_provider_wraps_ambiguous_plan_in_boundary_fetch_error`, which asserts
  `BoundaryFetchError`, a `ValueError` cause, and every detail (state, chamber,
  year, titles). The client and `fetch_enacted_plan` cases still assert `ValueError`.
- Collateral (boundary providers/engine, RDH catalog/overlays/selection/silent-wrong-data,
  redistricting data hub, plan status, smoke, runtime guard, sql safety) -> 465 passed,
  5 skipped, 6 failed. All 6 failures are `test_redistricting_plan_status.py`
  cases that import Django GIS, and the local GDAL library cannot load
  (`ImproperlyConfigured`). They are environmental. `test_rdh_precinct_loader.py`
  fails to collect for the same reason and was excluded.

### writing-claims
- The counts are pytest summary lines from this work cycle.

## Lead review
Provider contract (CLAUDE.md, architectural decision 5): the same failure mode
across providers. Caller misuse stays `ValueError`; data-side failures are
`BoundaryFetchError`. Blast radius: one method in `boundary_providers.py`.

Correction: an earlier draft of this review said merge commit 7f534f6c is not
an ancestor of develop dc7d3f76. That was wrong. The local clone is shallow,
so local ancestry checks gave a false answer. GitHub's compare API reports
`compare/dc7d3f76...7f534f6c` as ahead 0 / behind 11, so 7f534f6c is on
develop. `compare/dc7d3f76...d551b2df` reports 5 changed files, all #1480
files. There is no foreign content in this PR.

## Rework ledger
- d9b24ec1/cee57289: lookup outside the try. F1 is fixed in this round.

## Findings
F1 fixed. No new code findings.

## Ticket-fitness exemption

Governing ticket: #1480. The #1398 epic is context only.

### #1480
Reason: #1480 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1480 states the swapped SLDL/SLDU mapping under "## Problem", the code citation under "## Evidence" (`geo/providers/redistricting_data_hub.py`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1480#issuecomment-6259598610.
Falsification: revert the implementation; `tests/test_1480_rdh_chamber_sldu_sldl.py::test_census_chamber_codes` goes red because `state_senate` again selects `va_sldl_2021_adopted_plan`, and `::test_provider_wraps_ambiguous_plan_in_boundary_fetch_error` goes red because an ambiguous plan escapes the provider as a bare `ValueError`.
Observed revert results (2026-11-05). Command, with `REV` set to the revert target:
`git checkout REV -- siege_utilities/geo/providers/boundary_providers.py siege_utilities/geo/providers/redistricting_data_hub.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1480_rdh_chamber_sldu_sldl.py::test_census_chamber_codes test_1480_rdh_chamber_sldu_sldl.py::test_provider_wraps_ambiguous_plan_in_boundary_fetch_error); git checkout HEAD -- <same files>`
- `REV=dc7d3f76` (develop): 5 failed (2 chamber cases, 3 provider cases).
- `REV=cee57289` (pre-F1 head): 3 failed, 2 passed. The provider cases fail; the chamber cases pass.
- Current-head green: after the files were restored, `(cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1480_rdh_chamber_sldu_sldl.py)` gave 69 passed. The worktree was clean.
