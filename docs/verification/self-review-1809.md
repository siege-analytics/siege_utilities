# Self-review: PR #1809 battle-test wrapper (#1475), R-1809-3

Review-Tier: C (CI wrapper script and its regression guards).

## Assumptions
Working as: software engineer (Junior) and CI/release tech lead (Lead).
Domain(s): software engineering (CI test lanes, shell pipelines).
Geospatial cross-cut: no.
Goal source: the #1475 Problem/Done-when, and two reviewer findings on 85b49cb3. First, the substring selection guard accepted four unsafe variants and rejected four safe reformats (review notes for R-1809-2). Second, a failed `tee` write still produced exit 0 and a summary with `exit_code` 0 (https://github.com/siege-analytics/siege_utilities/issues/1475#issuecomment-6645851362).
Plan reference: docs/verification/self-review-1809.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1809.md#investigation
Investigate-artifact: docs/verification/self-review-1809.md
Pre-mortem-artifact: docs/verification/self-review-1809.md
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1475#issuecomment-6645851362 (reviewer finding). Exact-head re-review of the pushed commit is pending; this is NOT a pass.
Project-contribution: the battle-test job reports real, provisioned-lane results and cannot report success without its test log.

## Investigation
- `scripts/run_overnight_comprehensive.sh:32-61` at 85b49cb3: `set +e`, then `... 2>&1 | tee overnight_results/test_output.txt` and `TEST_EXIT_CODE=${PIPESTATUS[0]}` in both the uv and python branches. The summary uses that code only, so a `tee` failure is invisible.
- `tests/test_1809_battle_selection.py:17-31` at 85b49cb3: joins `\`-newline pairs, keeps lines containing the literal `pytest tests/`, and requires literal marker and ignore substrings anywhere on them.
- `tests/test_1475_overnight_script.py`: copies the wrapper into a disposable repository and runs it with an allow-listed `PATH` and stub `pytest`/`python`/`uv`; the new guard reuses that design.
- Branch state: GitHub compare showed 85b49cb3 11 behind / 4 ahead of develop, and `CHANGELOG.md` had no #1475 entry.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The new guard parses argv wrongly and passes an unsafe command. Mitigation: explicit last-wins `-m` parsing (`-m X` and `-mX`), `--ignore=X` and `--ignore X`, value-taking options skipped; the reviewer's eight variants are fixtures on both branches.
2. Tiger (launch-blocking). Severity: P1. The tee fix still reports success without an artifact. Mitigation: all `PIPESTATUS` values are captured in one statement; the run fails when tee is non-zero or the log is not a regular file; a forced-failure test pre-creates the log path as a directory.
3. Paper Tiger. Severity: P2. Status-preservation tests regress. Mitigation: the `exit_code` key and pytest's own non-zero codes are kept, and `tests/test_1475_overnight_script.py` still passes (8 cases).
4. Paper Tiger. Severity: P2. A positional `CHANGELOG.md` conflict on the develop sync drops an entry. Mitigation: the branch had no #1475 entry, so the develop side was kept whole; the #1475 note is added in its own commit.
5. Elephant. Severity: P3. Hosted CI is red on DuckDB 2.0 and `gis.W001` drift, and battle-test is skipped downstream of the failed matrix. Disclosed in the PR body.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (no success-shaped summary without the artifact); behavioural tests over text matching; red-first.
- Gate 1 (syntax): `bash -n scripts/run_overnight_comprehensive.sh` -> exit 0; flake8 --max-line-length=127 on the new test -> exit 0.
- Gate 2 (tests): pytest -> 172 passed (battle, overnight, smoke, runtime-guard, SQL-safety and changelog tests) on the fix and again on the post-merge tree.
- Gate 3 (docs): `CHANGELOG.md` `[4.1.0]` Fixed entry added.

## Lead review (adversarial)
Phase A coherence: each finding maps to one change. F1 maps to the argv-based guard and the eight variants. The tee false pass maps to the `PIPE_STATUS` capture, the artifact check and the summary fields.
Phase B verification:
- Wrapper red: with `scripts/run_overnight_comprehensive.sh` from 85b49cb3, the new tests give 6 failed / 18 passed. A failed tee with pytest exit 0 exits 0 (the review's false pass), the error message is absent, and the summary lacks the new fields.
- Guard red: with the 85b49cb3 substring predicate substituted into the variant tests, all 16 variant cases fail (four unsafe accepted, four safe rejected, on both branches). The behavioural guard classifies all 16 correctly.
- After: 24 tests in `tests/test_1809_battle_selection.py` pass. One real-wrapper policy case and one real-artifact case run per branch, and the artifact case shows `overnight_results/test_output.txt` written by real `tee`.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | Substring guard misclassifies 8 variants | behavioural argv guard |
| F2 | P2 | Failed tee write reports exit 0 | both pipeline statuses checked; artifact required |
| F3 | P3 | No canonical #1475 release note | `CHANGELOG.md` `[4.1.0]` entry |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket. The #1398 epic is context only.

### #1475
- **Reason:** #1475 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the problem (the battle job ran zero tests and masked status), its evidence and the done-when criteria live in the #1475 body under `## Problem`, `## Evidence` and `## Done when`. The reviewer verdicts are https://github.com/siege-analytics/siege_utilities/pull/1809#pullrequestreview-5566966773 and the current-head finding https://github.com/siege-analytics/siege_utilities/issues/1475#issuecomment-6645851362. This round's investigation, pre-mortem and task records are at https://github.com/siege-analytics/siege_utilities/issues/1475#issuecomment-6651599219.
- **Falsification:** revert the implementation (restore `scripts/run_overnight_comprehensive.sh` from 85b49cb3). Then `tests/test_1809_battle_selection.py::test_failed_tee_write_fails_the_run[0-1-uv]` goes red because the wrapper exits 0 when `tee` cannot write `overnight_results/test_output.txt`. Revert the guard to the substring check, and `test_guard_rejects_unsafe_variants[later-weaker-marker-uv]` goes red because a later `-m "not integration"` is accepted. Verified on 2026-11-05: 6 failed / 18 passed with the old wrapper; 16 of 16 variant cases failed with the old guard; 24 passed after.

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11), run from `tests/` with `--rootdir=..`.
- `python -m pytest tests/test_1809_battle_selection.py` -> 24 passed (fix); 6 failed / 18 passed (85b49cb3 wrapper); 16 failed of 16 selected guard cases (old substring guard).
- `python -m pytest tests/test_1809_battle_selection.py tests/test_1475_overnight_script.py tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py tests/test_release_process.py tests/test_user_config_export_changelog.py` -> 172 passed, before and after the develop sync.

## Rework ledger
The guard red was demonstrated by temporarily substituting the 85b49cb3 predicate into the variant tests and then restoring the committed test file; the committed file contains only the behavioural guard.
