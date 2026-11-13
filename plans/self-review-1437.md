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

- Pre-flight (2026-11-10). Classification follows the operator rule (2026-11-06): a change that alters v4.0.0 caller behaviour is BREAKING. Neither the v4.0.0 tag nor develop `71f02b0b` has a CT 2022 guard; both `place_history.py` copies contain no `_raise_for_ct`/`_CT_RECODED` symbol. A CT county/tract/block-group/block query across 2022 returned a result on v4.0.0 and now raises `ValueError`, so the entry moves from 4.1.0 Changed to BREAKING with a **Migration:** line. No code changed. A trial `merge-tree` against develop `71f02b0b` reports no conflict, so there is no resync; the merge queue handles the behind count.

## Findings
F1 fixed. No new findings.

## Ticket-fitness exemption

Governing ticket: #1437. The #1398 epic and the deferred crosswalk ticket #1795 are context only.

### #1437
Reason: #1437 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1437 states the problem under "## Problem", the probe and trace under "## Evidence" (`geo/place_history.py:36`, `geo/timeseries/longitudinal_data.py:304-323`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1437#issuecomment-6259593773.
Falsification: revert the implementation; `tests/test_1437_ct_2022_boundary_guard.py::test_place_history_ct_tract_crossing_raises` goes red (DID NOT RAISE) because `place_history("09001010100", 2020, 2023)` again reports unchanged lineage. Revert only the F1 level scoping (back to `6ff57933`); `::test_normalization_ct_legislative_districts_pass` goes red because CT SLDU/SLDL frames raise the county-recode error.
Observed revert results (2026-11-05). Command, with `REV` set to the revert target:
`git checkout REV -- siege_utilities/geo/place_history.py siege_utilities/geo/timeseries/longitudinal_data.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1437_ct_2022_boundary_guard.py::test_place_history_ct_tract_crossing_raises test_1437_ct_2022_boundary_guard.py::test_normalization_ct_legislative_districts_pass); git checkout HEAD -- <same files>`
- `REV=dc7d3f76` (develop): 1 failed, 20 passed. The tract test fails; the legislative cases pass because develop has no guard to misfire.
- `REV=6ff57933` (pre-F1 head): 20 failed, 1 passed. All 20 SLDU/SLDL cases fail.
- Current-head green: after the files were restored, `(cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1437_ct_2022_boundary_guard.py)` gave 130 passed before this develop sync, and the same result after it (recorded in this commit). The worktree was clean.

## Current integration round (develop 6c049c2c), Tier C local gate

Appended 2026-11-13 for the merge of develop `6c049c2c` into this branch, whose head is `7502cd88`. Every section above is unchanged and describes earlier rounds.

**History of the voided staging.** An earlier staging of this integration against develop `79f37f4d` was prepared on 2026-11-11 and never committed. #1791 (#1404, Census dual-source client errors) then landed on develop and added a BREAKING bullet at the same CHANGELOG anchor. So that staging was voided, and it was aborted before this restage. No result below is carried over from it.

This round changes no #1437 source or test file. The only conflict was the 5.0.0 `### BREAKING` list in `CHANGELOG.md`. It was resolved markers-only:
- develop's 68-line block first: the three social entries, then the #1404 Census dual-source entry;
- then the #1437 entry, verbatim with its Migration line.

The staged `CHANGELOG.md` blob is `3a75cf1bc7ebdb22bbb27bd3f441d5927ee851e6`. That equals the value precomputed before the merge by three independent constructions. Versus develop `6c049c2c`, `CHANGELOG.md` is +12/-0.

The #1437 BREAKING entry sits under develop's undated `5.0.0` heading, which replaced the `4.1.0 - 2026-10-18` heading. The 4.1.0 wording in the sections above is historical.

**Tier note.** The PR's own content stays at the tier already ruled for it. This merge commit classifies as Tier C locally because develop's delta brings in `.github/workflows/ci.yml` and `.github/actions/apt-install/action.yml`. The fields below meet the Tier C artifact contract for this merge commit only.

Working as: software engineer (develop integration), with geospatial review of the CT recode contracts
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1437#issuecomment-6799942212
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1437#issuecomment-6799942212
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1437#issuecomment-6800241484
Project-contribution: keeps the CT 2022 recode guard mergeable on the 5.0.0 line, so its BREAKING note and Migration line ship under the release they describe.

Scope of those artifacts. The investigation, pre-mortem and the independent adversarial checklist (verdict "proceed with conditions", each condition answered there) were written for the same markers-only plan against develop `79f37f4d`. This restage applies the identical rule against `6c049c2c`. The differences are that develop's side of the hunk now also carries the #1404 bullet, and that develop's delta now includes the #1404 Census files.

## Peer review (current integration round)

- **writing-code:** no `.py` byte was authored in this round. Every `.py` file in the merged tree equals one parent:
  - the staged tree differs from develop `6c049c2c` only on the five #1437 paths;
  - it differs from `7502cd88` only on develop's 72 changed paths since `2c5c34ce`, plus this file.

  Develop's delta now touches four files under `siege_utilities/geo`:
  - `geo/__init__.py`: one lazy-registry name, `CensusServerError`;
  - `geo/census/api.py`;
  - `geo/census/dual_source.py`;
  - `geo/census_api_client.py`.

  None of these is `place_history.py`, `timeseries/longitudinal_data.py`, `geo/django`, or a #1437 test.
- **writing-tests (this round, merged snapshot `6c049c2c`):** `siege_utilities.__file__` resolved inside this worktree before any run.
  - **The four #1437 modules** (`test_1437_ct_2022_boundary_guard`, `test_place_history`, `test_longitudinal_aligner`, `test_longitudinal_normalization_consensus`), run with `pytest -o addopts="" -p no:cacheprovider -rs` -> 203 passed, 0 failed, 0 skipped.
  - `tests/test_credential_url_guard.py` + `tests/test_1812_fidelity_oracle.py` -> 178 passed.
  - **Change from the earlier local runs.** `tests/test_place_history.py::TestPlaceHistory::test_no_provider_returns_error` failed in the earlier local runs recorded above (GDAL dylib not found, Django `ImproperlyConfigured`). It passed in this round, alone and inside the module runs.
  - That code path is byte-identical to `7502cd88`: `place_history.py`, the test, and `geo/django` are unchanged.
  - The local GDAL condition is also unchanged:
    - ctypes `find_library("gdal")` still returns None;
    - importing `siege_utilities.geo.django.providers` outside pytest still raises `ImproperlyConfigured`.
  - **Inference, not verified:** under pytest, `tests/django_project/settings.py` reads `GDAL_LIBRARY_PATH` from the environment. `geo/django/__init__.py` sets that variable to `/opt/homebrew/lib/libgdal.dylib` on macOS when it is unset. So the outcome may depend on import order. Why it differs from the earlier runs is undetermined. This is a local result only; hosted CI decides.
- **Guards on the merged snapshot (this round):**
  - `scripts/check_credential_urls.py` -> 0 unreviewed sites.
  - `scripts/check_exception_contracts.py --list` -> 205 flagged, 0 unlisted, 0 stale.
  - `check_secret_literals` -> PASS, 0 violations.
  - `check_no_stub_docstrings` -> OK.
  - `check_unbounded_io`, library and tests -> 0 violations.
  - `check_subprocess_safety` -> PASS.
  - `check_atomic_writes` -> PASS, 0 unlisted, 0 stale.
  - `check_secure_writes` -> PASS.
  - `check_secret_repr` -> PASS.
  - `validate_extras_coherence` -> OK, 24 extras.
  - `check_lazy_imports` -> OK, 59 packages (`siege_utilities.geo` lazy=348). Its 8 skips are all `geo.django` packages, for the local GDAL absence.
  - `check_test_file_hygiene` -> PASS.
  - `scripts/release_manager.py --check` -> consistent at 5.0.0.
  - `git diff --cached --check` -> clean.
- **NOTRUN this round, with reasons:**
  - `tests/guard/test_exception_contract_guard.py`: its CI invocation (`-c /dev/null`) was refused by a local command guard on 2026-11-11 and was not retried.
  - Lint-ratchet phases 1-4: flake8 is not on the PATH the scripts use.
  - `bandit`: not installed.
  - `twine check` and `scripts/check_wheel_contents.py`: they need a `dist/` build.
  - `scripts/contracts/compare_public_api_contracts.py`, which reads `scripts/contracts/contract_allowlist.json` (#1791 changed that file): it needs baseline and candidate contract exports.

  Hosted CI covers these.
- **writing-claims:** every count above is a pytest summary line or guard output from this round's runs on the `6c049c2c` merged snapshot.

## Lead review (current integration round)

Geospatial: the CT recode contracts are unchanged by this merge, and the named tests in `tests/test_1437_ct_2022_boundary_guard.py` pass on the merged snapshot:
- CT county, tract, block-group and block queries crossing 2022 raise `ValueError` naming the crosswalk;
- non-CT and earlier-vintage inputs are unchanged;
- SLDU/SLDL frames pass;
- recoded-level aliases raise;
- an unresolvable level fails closed.

Longitudinal row-ID behavior is covered by `tests/test_longitudinal_normalization_consensus.py`, which also passes. The #1404 Census changes do not touch these paths.

Out-of-scope follow-up candidate (SU-1). `_get_default_provider` in `siege_utilities/geo/place_history.py` catches `ImportError` and `(RuntimeError, ValueError, TypeError, AttributeError, OSError)`. Django's `ImproperlyConfigured` is not in that list. That exception is raised when Django is installed but GDAL cannot be loaded; this round reproduced it outside pytest. So `place_history(..., provider=None)` can raise instead of recording a provider error. This is not changed here and is tracked separately for a ticket.

Post-mortem: not applicable. This is a develop integration with no regression and no materialized pre-mortem Tiger.

Not claimed: this round does not approve or enqueue the PR or close #1437. Fresh required hosted CI on the new head and an independent whole-PR review are still owed.
