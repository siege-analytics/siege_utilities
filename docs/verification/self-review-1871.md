# Self-review: #1871 bounded apt installs in CI

Review-Tier: C (CI workflow; required checks and the merge queue depend on it).

## Assumptions
Working as: software engineer (Junior) and CI/release tech lead (Lead).
Domain(s): CI infrastructure (GitHub Actions, apt on Ubuntu runners).
Geospatial cross-cut: no.
Goal source: #1871. Merge-queue run 42282238657 lost the required `test-postgis` job when `apt-get install` stalled on the Azure Ubuntu mirror from 19:47:29Z until the 20-minute job timeout at 20:04:34Z; battle-test stalled the same way on run 42268417109. The fix direction is bounded apt retries and timeouts, plus a step timeout shorter than the job with one retry, without raising job timeouts.
Plan reference: docs/verification/self-review-1871.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1871.md#investigation
Investigate-artifact: docs/verification/self-review-1871.md
Pre-mortem-artifact: docs/verification/self-review-1871.md
Hostile-review-artifact: docs/verification/self-review-1871.md (Lead review below). Independent review of the PR head is pending; this is NOT a pass.
Project-contribution: a mirror stall no longer cancels required CI jobs or dequeues merge-queue entries.

## Investigation
- `.github/workflows/ci.yml` at develop `560a858e` installs `gdal-bin libgdal-dev libgeos-dev libproj-dev` with plain `sudo apt-get update` and `sudo apt-get install -y --no-install-recommends` in five jobs: `notebook-governance` (:121), `test` (:229), `test-postgis` (:345), `makemigrations-check` (:620) and `battle-test` (:705). Every job checks out the repository before that step.
- Only `test-postgis` sets `timeout-minutes` (20, :311); no step sets one, and no apt retry or timeout option is set.
- `.github/workflows/publish-tag.yml` has no `apt-get`.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The wrapper reports success after failing. Mitigation: the failure status is captured in an `else` branch, and the final `exit 1` is covered by `test_two_failed_attempts_fail_the_step`.
2. Tiger (launch-blocking). Severity: P1. The step timeout is too short for two attempts, or longer than the job budget. Mitigation: worst case is 2 x (180 s + 180 s) + 10 s = 730 s. The steps use 13 minutes (780 s), which is under `test-postgis`'s 20. `test_apt_install_steps_have_a_step_timeout_inside_the_job_budget` asserts both bounds for every install step.
3. Paper Tiger. Severity: P2. `timeout` cannot stop a hung apt under `sudo`. Mitigation: `timeout` itself runs under `sudo` with `--kill-after=30`. The stall tests show exit 124 and a retry.
4. Paper Tiger. Severity: P2. A future job adds raw `apt-get`. Mitigation: `test_no_workflow_step_runs_apt_get_directly` covers every workflow file.
5. Elephant. Severity: P3. There is no `.deb` cache or prebuilt image, which the ticket lists as optional. Deferred.

## Peer review (Junior: shelves, gates)
- Shelves: bounded network waits; fail fast and retry rather than raising budgets; behavioral tests with stubs over a real `timeout`.
- Gate 1 (syntax): `bash -n` and `shellcheck` on `scripts/ci_apt_install.sh` -> clean; `yaml.safe_load` parses both workflows in the guard test; flake8 on the new test -> clean.
- Gate 2 (tests): pytest -> 7 passed in `tests/test_1871_ci_apt_install.py`; with the changelog tests, 32 passed.
- Gate 3 (guards): `scripts/check_test_file_hygiene.py` -> PASS.

## Lead review (adversarial)
Phase A coherence: each ticket requirement maps to a change.
- Apt retries and connection timeouts come from the `-o Acquire::...` options on both commands.
- Per-command stall bounds come from `timeout`.
- The two attempts are the step's retry, run inside the script because GitHub Actions has no native step retry.
- Each step has its own `timeout-minutes: 13`.
- Job timeouts are unchanged.

Phase B verification: the stub tests drive the real script through each case.
- Success: `update` then `install`, each with the three `-o` options.
- Stalled `update`: cut off with exit 124, then retried successfully.
- Stalled `install`: retried successfully.
- Double failure: exit 1.
- No packages: usage error, exit 2.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | Unbounded apt install can consume a required job's whole budget | bounded options, per-command timeout, two attempts, step timeout |
| F2 | P3 | No package cache | deferred (ticket marks it optional) |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1871
- **Reason:** #1871 is an operational CI ticket written as Symptom / Impact / Fix direction rather than the canonical template, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the symptom (run 42282238657, job 128113913494, a silent stall from 19:47:29Z until the 20:04:34Z cancellation), the impact (a required check dequeues the merge-queue group) and the fix direction (bounded apt retries and timeouts, a step timeout shorter than the job with one retry, job timeouts unchanged) live in the #1871 body. This change's task record is https://github.com/siege-analytics/siege_utilities/issues/1871#issuecomment-6694687820.
- **Falsification:** revert the implementation (restore `.github/workflows/ci.yml` from develop `560a858e`) and `tests/test_1871_ci_apt_install.py::test_no_workflow_step_runs_apt_get_directly` goes red, naming all five jobs that call `apt-get` directly. `test_apt_install_steps_have_a_step_timeout_inside_the_job_budget` goes red because no install step uses the bounded script. Verified on 2026-11-06: 2 failed and 5 passed against develop's `ci.yml`; 7 passed after.

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11); GNU `timeout` from coreutils.
- `python -m pytest tests/test_1871_ci_apt_install.py` -> 7 passed; with develop's `ci.yml`, 2 failed and 5 passed.
- Adding `tests/test_release_process.py tests/test_user_config_export_changelog.py` -> 32 passed.

## Rework ledger
During the red check, a blocked command left the new `ci.yml` unstaged, so the restore reverted it to develop's version. The edit was re-applied and verified (five script calls, no `apt-get`) before the red check was repeated correctly. Nothing was committed in between.
