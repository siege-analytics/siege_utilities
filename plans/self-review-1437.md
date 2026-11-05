---
ticket_refs:
  - siege-analytics/siege_utilities#1437: comment posted
---

# Self-review: #1437 / PR #1796 (CT 2022 recode guard)

## Assumptions
Domain(s): software engineering, geospatial (Census geography vintages)
Goal source: #1437 (CT 2022 planning-region recode passes through as unchanged geography)
Goal source verification: PASS (ticket has Problem, Evidence, Done-when, Falsifier)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1437#issuecomment-6650549658
Review being answered: https://github.com/siege-analytics/siege_utilities/issues/1437#issuecomment-6259593773 (exact-head review of 6ff57933: F1, PR body, process)
Pre-author-inventory: the Investigation section of the plan reference above

## Scope of this round
F1: `_raise_for_ct_2022_crossing` decided by GEOID shape only, and
`_normalize_boundaries_multi_year` never passed its `geography_level`. CT
SLDU (09001-09036) and SLDL (09001-09151) GEOIDs are five digits, so they
collided with the county codes and raised a misleading recode error.

Fix: the guard takes an optional `geography_level`. A level that the canonical
registry (`resolve_geographic_level`) maps outside {county, tract, block_group,
block, tabblock20, tabblock10} is exempt. Recoded levels, their aliases, `None`,
and unrecognized strings keep the GEOID-shape check, so the change cannot
disable the guard for an affected level. `place_history` has no level
parameter, so its signature is unchanged and a bare 5-digit CT GEOID there is
still read as a county (documented in the guard docstring).

## Peer review (the Junior's checklist)

### writing-code
- `py_compile` on the three changed .py files -> exit 0.
- Severe flake8 (E9,F63,F7,F82,F401,F811,F841) on the changed files -> no output.
- `scripts/check_exception_contracts.py` -> handlers flagged 207, unlisted 0, stale 0.
  The new `except ValueError` in `_is_ct_recode_exempt_level` maps to "not exempt",
  which is the stricter path. It does not swallow a failure as data.
- `scripts/check_no_stub_docstrings.py` -> OK. `scripts/check_test_file_hygiene.py` -> PASS.

### writing-tests
- Red at 6ff57933 (new tests, old production code): pytest -> 20 failed, 110 passed.
  All 20 failures are `test_normalization_ct_legislative_districts_pass`
  (5 level spellings x 2 GEOID sets x 2 target years).
- Green after the fix: pytest -> 130 passed (guard file). The 6 alias cases and
  3 unknown-level cases pass both before and after, which shows nothing was loosened.
- Collateral: test_1437 + test_place_history + test_longitudinal_aligner +
  test_longitudinal_normalization_consensus -> 202 passed, 1 failed. The failure,
  `test_no_provider_returns_error` (years 2000->2020, so it never reaches the
  guard), fails on its own because the local GDAL dylib cannot load (Django
  `ImproperlyConfigured`). It is environmental and unrelated to this change.
- Critical paths with the guard file: test_smoke + test_runtime_guard + test_sql_safety
  + test_1437 -> 245 passed.

### writing-claims
- "20 failed" was counted from the red run's progress line. "130", "202" and "245"
  are the pytest summary lines.

## Lead review
Geospatial: the 2022 CT recode changed the county-equivalent code. The county,
tract, block-group and block GEOIDs that embed it changed with it. Legislative
districts, places, CDs, ZCTAs and VTDs do not embed a county code in that way,
or are not published post-2022 at that level.

Junior dismissed, reported as debt: CT county subdivisions (10-digit) embed the
county code and were recoded too. The original guard never covered them, and an
existing test asserts that, so widening is a separate ticket decision. Integer
GEOIDs still bypass the `isinstance(str)` check, as the reviewer noted. Unchanged.

Behavior change: CT SLDU/SLDL normalization across 2022 no longer raises.
Blast radius: one private helper plus one call site.

## Rework ledger
- Round 1 (6ff57933): shape-only guard. Review F1 is fixed in this round.
- PR body: rewritten so it no longer claims non-CT rows keep their behavior inside a
  nationwide frame. Such a frame raises for the whole request.

## Findings
F1 fixed. No new findings.

## Ticket-fitness exemption

Governing ticket: #1437. The #1398 epic and the deferred crosswalk ticket #1795 are context only.

### #1437
Reason: #1437 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1437 states the problem under "## Problem", the probe and trace under "## Evidence" (`geo/place_history.py:36`, `geo/timeseries/longitudinal_data.py:304-323`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1437#issuecomment-6259593773.
Falsification: revert the implementation; `tests/test_1437_ct_2022_boundary_guard.py::test_place_history_ct_tract_crossing_raises` goes red (DID NOT RAISE) because `place_history("09001010100", 2020, 2023)` again reports unchanged lineage, and `::test_normalization_ct_legislative_districts_pass` goes red because CT SLDU/SLDL frames raise the county-recode error.
