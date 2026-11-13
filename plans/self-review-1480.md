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
- Pre-flight (2026-11-10). Develop sync: `02c44a00` merges develop `71f02b0b` for a positional CHANGELOG conflict (the #1444 and #1480 Fixed entries). Both are kept, a diff against develop deletes 0 develop lines, and no merged develop behaviour disagrees with this PR. Classification follows the operator rule (2026-11-06): a change that alters v4.0.0 caller behaviour is BREAKING. On the v4.0.0 tag, the `state_senate` keywords include `sldl` and the `state_house` keywords include `sldu` and bare `house`. `fetch_enacted_plan` and `RDHProvider.get_boundary` load `datasets[0]`, and `get_boundary` calls `get_enacted_plans` outside any try. So a multi-match request that loaded a plan now raises, and a lookup `OSError`/`ValueError` now arrives as `BoundaryFetchError` (a `RuntimeError`). The entry moves from 4.1.0 Fixed to BREAKING with a **Migration:** line. No code changed.

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

## Develop integration round (2026-11-13), Tier C

This section is appended in the develop-integration merge. The earlier sections above are left unchanged as a record of their rounds.

**Working as.** The PR author, merging develop `6c049c2cfda6330680a553afd9ac0f149eb80b9c` into PR head `1e439ce7a9b9ab7672cf40675a5fb8aa335029e6` (merge base `71f02b0b`). This round makes no change to #1480 code or tests.

**Why this round was restaged.** History of the voided staging:
- An earlier staging of this integration merged develop `79f37f4d` (staged tree `a949eb80`, CHANGELOG blob `dc412696`). It was never committed.
- Before it was committed, #1791 (the #1404 Census dual-source fallback) landed on develop as `6c049c2c`. Its CHANGELOG bullet sits at the same `### BREAKING` anchor, so the `79f37f4d` staging would have conflicted again.
- That staging was backed up and aborted, then redone against `6c049c2c`.
- Every result below comes from the `6c049c2c` merge. Nothing is carried over from the voided run.

**Artifacts** on #1480, posted before the first staging:
- investigation, pre-mortem and junior task description: issuecomment-6799939326;
- senior adversarial review: issuecomment-6800068223;
- independent senior review: issuecomment-6800268589;
- junior revisions: issuecomment-6800101499, -6800285123 and -6800352613;
- senior re-checks: issuecomment-6800156131 and -6800339915;
- senior sign-off: issuecomment-6800381246.

Those reviews examined the plan against `79f37f4d`. This round applies the same resolution rule to the larger develop block. No new senior review was run for the restage.

**Investigate.** Since the base, the PR changed 5 paths and develop changed 51. `CHANGELOG.md` is the only path both sides changed. Develop's 51 include #1791's 13: `CHANGELOG.md`, the census API, dual-source and API-client modules, `siege_utilities/geo/__init__.py`, three tests, two docs, two plans, and `scripts/contracts/contract_allowlist.json`. None of the 5 PR paths is among them. There is one conflict, in `### BREAKING`. The PR entry is 17 lines. Develop's block is 68 lines: the three social entries, then the 16-line #1404 Census dual-source entry.

**Pre-mortem.** The tigers were stale parents, a resolution that is not markers-only, a hidden source or test change, misreported test results, and a half-merged worktree. None was launch-blocking.

**Resolution.** Markers only. The three marker lines are deleted and the develop block (the social entries, then #1404) moves above the PR block, with no other byte changed. The #1480 entry follows the #1404 entry's last line directly. The `## [5.0.0]` heading and all develop content come from develop unchanged.

**Version relabel.** Develop renamed the pending release from 4.1.0 to 5.0.0 (#1885). So the entry that head commit `1e439ce7` calls "4.1.0 BREAKING" now sits under `## [5.0.0]`. The 4.1.0 references above (the scope note and the 2026-11-10 ledger entry) are read as 5.0.0. The entry text names only v4.0.0 behavior and stays accurate verbatim.

**Merge method.** The first posted plan said the merge would run with `git -c rerere.enabled=false`. Local tooling refuses that config override; this was observed in a sibling integration and not attempted here. A plain `git merge --no-commit --no-ff 6c049c2cfda6330680a553afd9ac0f149eb80b9c` was used, with proof that no prior resolution applied:
- the complete merge output was "Auto-merging CHANGELOG.md / CONFLICT (content): Merge conflict in CHANGELOG.md / Recorded preimage for 'CHANGELOG.md' / Automatic merge failed", with no "using previous resolution" line;
- `git ls-files -u` listed only `CHANGELOG.md`, at stages 1, 2 and 3 (`130c416f`, `9b9bbb92`, `2f1d95fd` = develop `6c049c2c`);
- there were exactly 3 markers, at lines 413, 431 and 500.

rerere recorded this conflict's preimage, and records the resolution at commit, in the clone's shared resolution cache. That side effect is accepted.

**Acceptance checks**, on staged tree `6023475a121e7f8b05557d3f26e55c27bfafbbc9` before this section was appended:
- `CHANGELOG.md` blob is `9ead24f8c3a1c22bcc03d03f67c159c74951a913`, 133011 bytes (develop's 131808 plus the PR entry's 1203). `git diff --cached --numstat 6c049c2c -- CHANGELOG.md` gives `17 0`.
- `git grep --cached` for `^<<<<<<< ` and `^>>>>>>> ` finds 0, the baseline on both parents. For lines of exactly seven `=`, it finds the same 3 reStructuredText underlines as both parents, in `docs/source/packages/engines.rst`, `hygiene.rst` and `testing.rst`.
- Against develop `6c049c2c`: only the 5 PR paths. The 4 that are not `CHANGELOG.md` are byte-identical to the PR head.
- Against the PR head: exactly develop's 51 changed paths. The sha256 of the two sorted name lists matches.

**Tests on the merged snapshot.** Python 3.11.11, pytest 8.4.2, run from the worktree root (`rootdir` is the worktree, `configfile: pytest.ini`):

`python -m pytest tests/test_1480_rdh_chamber_sldu_sldl.py tests/test_redistricting_data_hub.py tests/test_boundary_providers.py -q -p no:cacheprovider --no-cov -rA`

- Result: 218 passed, 0 failed, 0 errors, 0 skipped.
- Per module, from the `-rA` lines: `test_1480_rdh_chamber_sldu_sldl.py` 69, `test_redistricting_data_hub.py` 104, `test_boundary_providers.py` 45.
- Import source: warning tracebacks resolve to `siege_utilities/geo/providers/redistricting_data_hub.py` inside the worktree.
- Coverage gating is off for this focused run. Coverage is CI's job.
- Behavior mapping, all passing:
  - chamber codes and the requested chamber: `test_census_chamber_codes`, `test_loaders_use_the_requested_chamber`;
  - token-boundary matching: `test_chamber_keywords_match_whole_tokens`, `test_chamber_keywords_do_not_match_substrings`;
  - enacted/adopted/official: `test_chamber_match_still_requires_enacted_adopted_or_official`;
  - congressional and non-SLD controls: `test_ambiguous_chamber_is_refused_before_loading` (includes `congress`), `test_provider_argument_errors_stay_value_error` (includes `county`), `TestRDHProvider::test_get_boundary_congress_delegates`;
  - error contract: `test_provider_wraps_ambiguous_plan_in_boundary_fetch_error`, `test_provider_wraps_lookup_failures_in_boundary_fetch_error`;
  - provider dispatch: `TestRDHProvider::test_get_boundary_precinct_delegates`, `::test_get_boundary_no_datasets_raises`, `TestResolveBoundaryProvider`;
  - listing filters: `TestListDatasets::test_list_with_format_filter`, `::test_list_with_dataset_type_filter`.
- Not covered: no test in these modules covers an explicit override of the chamber choice. No claim is made about it.
- Inherited warning: an `RDHClient.__del__` `AttributeError` (`_closed`) in `test_init_missing_requests`. It is already present at the merge base and is not changed here.

**Guards on the merged snapshot**, each run as `python scripts/<guard>.py`:
- `check_credential_urls.py`: 0 unreviewed sites. `tests/test_credential_url_guard.py`: 115 passed.
- `check_exception_contracts.py --list`: 205 handlers flagged; 0 unlisted, 0 stale.
- `check_secret_literals.py`, `check_secret_repr.py`, `check_subprocess_safety.py`: 0 violations in 395 files each.
- `check_lazy_imports.py`: 59 packages OK, including `siege_utilities.geo` with 348 lazy entries and 348 in `__all__`. 8 optional `geo.django` packages are skipped because GDAL is not installed locally.
- `check_error_path_coverage.py --report`: 395 modules pass, 0 fail.
- `check_test_file_hygiene.py`: PASS.
- `validate_extras_coherence.py`: 24 extras coherent.
- `release_manager.py --check`: consistent, canonical 5.0.0.
- Lint ratchet phases 1–4: NOT RUN. `flake8` is not installed in the local interpreter, which fails the phases on that dependency, not on a lint finding. CI's lint job carries this check.
- `scripts/contracts/compare_public_api_contracts.py`, which reads `contract_allowlist.json` (changed by #1791): NOT RUN locally. It needs the baseline and candidate contract snapshots that CI's release-impact job builds. CI carries this check.

**Tested tree = committed tree.** The three test modules and the guards above were re-run after this section was appended, on the final staged tree, with the same results. This section changes only `plans/self-review-1480.md`. It is a single hunk after the file's last line: the first 6484 bytes of the new file hash to the `1e439ce7` blob `6ef98e33`.

**Noted disagreement.** The senior review preferred to put this evidence in a separate commit after the merge. This round keeps it in the merge commit, because the reviewer's integration decision allows a clearly labelled, truthful integration-evidence append in the same round. The byte-prefix proof, the re-run on the final tree, and the merge message's naming of this file answer the substance. The final decision on the PR's shape rests with the reviewer.

**Not claimed.** This section does not claim:
- results of hosted CI;
- composition with #1761 or #1792, which is owed by whichever of those PRs and #1797 lands later;
- that #1480 is resolved.

Residuals, recorded and not fixed here:
- the shared BREAKING anchor collision across PRs, which this restage illustrates;
- the precinct, CVAP and PL 94-171 loaders that still take `datasets[0]`.

## Review fields for the develop integration round

Working as: software engineer (PR author, develop integration)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1480#issuecomment-6799939326
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1480#issuecomment-6799939326

The investigation and pre-mortem were written for the markers-only integration plan against develop 79f37f4d. The 6c049c2c restage applies the same plan, and no new senior review was run for it.

## Peer review (develop integration round)

All results below were run on the merged 6c049c2c snapshot, staged tree `0960ea10`, which is merge commit `4e685c7e`. This follow-up commit changes only this file.

- writing-code: markers-only CHANGELOG resolution; staged blob `9ead24f8` matches the expected blob. Against develop `6c049c2c`, only the 5 PR paths differ, and the 4 that are not CHANGELOG are byte-identical to `1e439ce7`.
- writing-code: guard results, each `python scripts/<guard>.py`:
  - credential URL guard: 0 unreviewed;
  - exception contracts `--list`: 205 flagged, 0 unlisted, 0 stale;
  - secret literal, secret repr and subprocess safety: 0 violations in 395 files each;
  - lazy imports: OK (59 packages, 8 optional GDAL skips);
  - error-path coverage: 395 pass, 0 fail;
  - test file hygiene: PASS;
  - extras coherence: 24 coherent;
  - release check: consistent 5.0.0.
  The lint ratchet was not run (flake8 not installed locally).
- writing-tests: `python -m pytest tests/test_1480_rdh_chamber_sldu_sldl.py tests/test_redistricting_data_hub.py tests/test_boundary_providers.py -q -p no:cacheprovider --no-cov -rA` → 218 passed, 0 failed, 0 skipped (69 / 104 / 45). `tests/test_credential_url_guard.py` → 115 passed.
- writing-claims: the counts above are pytest summary and `-rA` lines and guard outputs from the 6c049c2c run, recorded in the integration section above. Hosted CI is not claimed.
