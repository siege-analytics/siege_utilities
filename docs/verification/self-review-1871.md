# Self-review: #1871 apt installs in CI that survive a slow or stalled mirror

Review-Tier: C (CI workflow; required checks and the merge queue depend on it).

## Assumptions
Working as: software engineer (Junior) and CI/release tech lead (Lead).
Domain(s): CI infrastructure (GitHub Actions, actions/cache, apt on Ubuntu runners).
Geospatial cross-cut: no.
Goal source: #1871. Merge-queue run 42282238657 lost the required `test-postgis` job when `apt-get install` went quiet on the Azure Ubuntu mirror from 19:47:29Z until the 20-minute job timeout at 20:04:34Z; battle-test did the same on run 42268417109. The first fix direction was bounded apt retries and timeouts plus a step timeout. The hub review of 2e61f1fc, based on CI evidence (below), redirected it: cache the `.deb` archives, fall back to another mirror on retry, and never fail an install that is still making progress.
Plan reference: docs/verification/self-review-1871.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1871.md#investigation
Investigate-artifact: docs/verification/self-review-1871.md
Pre-mortem-artifact: docs/verification/self-review-1871.md
Hostile-review-artifact: docs/verification/self-review-1871.md (Lead review below). Independent review of the PR head is pending; this is NOT a pass.
Project-contribution: a slow or stalled mirror no longer cancels required CI jobs or dequeues merge-queue entries, and most runs download no packages.

## Investigation
- `.github/workflows/ci.yml` at develop `560a858e` installs `gdal-bin libgdal-dev libgeos-dev libproj-dev` with plain `sudo apt-get update` and `sudo apt-get install -y --no-install-recommends` in five jobs: `notebook-governance` (:121), `test` (:229), `test-postgis` (:345), `makemigrations-check` (:620) and `battle-test` (:705). Every job checks out the repository before that step. Only `test-postgis` sets a job `timeout-minutes` (20, :311). `.github/workflows/publish-tag.yml` has no `apt-get`.
- CI on this PR was slow, not stalled:
  - Run 42289023968 (682d5069), job `django models match migrations`: liblapack3 (2.6 MB) took 64 s, about 41 KB/s; python3-numpy (4.4 MB) took 96 s.
  - Run 42291165894 (2e61f1fc), jobs `django models` and `notebook governance (3.13)`: the same rate.
  - In every case a new `Get:` line arrived every few seconds, and both attempts ended with exit 124 mid-download.
  - The second attempt reused the `.deb` files already downloaded ("Need to get 64.3 MB/72.1 MB").
  - At that rate, 72 MB takes about 25 minutes.
- Slow installs do finish. Develop run 42112634904 (560a858e): `test (3.11)` install step 21:26:24Z to 22:05:00Z (38m36s) exited 0; `django models` took 34 min and exited 0. Healthy install steps take 21 to 67 s (develop run 42007861238).
- apt-transport-http(1): `Acquire::http::Timeout` "applies to the connection as well as the data timeout". apt has no low-speed limit; `Dl-Limit` is a cap, not a floor.
- The hosted runner writes `/etc/apt/apt-mirrors.txt` (azure.archive.ubuntu.com priority 1, archive.ubuntu.com priority 2, security.ubuntu.com priority 3) and points `ubuntu.sources` at `mirror+file:/etc/apt/apt-mirrors.txt` (actions/runner-images `images/ubuntu/scripts/build/configure-apt-sources.sh`; the job log shows "Get:1 file:/etc/apt/apt-mirrors.txt Mirrorlist [144 B]"). The mirror method moves to the next entry after an error, not after a slow transfer.
- `ci.yml` runs on pushes to develop and main and on PRs to them, so develop runs save caches that PRs targeting develop can restore.

## Design decision: slow vs stalled
Two options were offered: (a) catch only a true stall (no bytes for N seconds) with apt's own limits, or (b) keep a wall-clock cap but leave the final attempt uncapped within the step timeout.

Chosen: (a) for the final attempt, combined with a wall-clock cap on the first attempt.
- **Final attempt:** network phases (`update`, `install --download-only`) have no wall-clock cap. apt's data timeout (30 s without bytes) and `Acquire::Retries=3` are the stall detector, which is the "no bytes for N seconds" rule.
- **Why not (b):** any fixed step timeout either kills the evidenced slow installs that exit 0 (38m36s, 34 min) or is too long to bound anything.
- **First attempt:** the network phases keep a 120 s wall-clock cap. On a slow primary mirror this costs nothing: the downloaded `.deb` files stay in `/var/cache/apt/archives` and the retry reuses them (evidence above). The retry also runs against the fallback mirror.
- **dpkg phase:** installing from the downloaded files, the `dpkg --configure -a` repair and `autoclean` stay capped (300 s) on every attempt. A hang that is not a download is therefore still bounded.
- **Install steps:** they carry no `timeout-minutes`. The job timeout still applies where one is set (`test-postgis`, 20 min).

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The wrapper reports success after failing. Mitigation: the failure status is captured in an `else` branch, the script ends with `exit 1`, and `test_two_failed_attempts_fail_the_step` covers it.
2. Tiger (launch-blocking). Severity: P1. A broken or empty cache is saved and poisons later runs. Mitigation:
   - the save runs only when the script wrote `cache-ready=true`, which needs an install that exited 0 and a refresh with at least one `.deb`;
   - it never runs over an exact hit;
   - apt checks every cached `.deb` against the package index and downloads anything stale.
   Covered by `test_failed_install_does_not_stage_the_cache` and `test_apt_action_restores_installs_then_saves_the_archive`.
3. Tiger (launch-blocking). Severity: P1. The final attempt hangs with no step timeout. Mitigation: network phases end after 30 s without data (apt, 3 retries); the dpkg phase is capped (`test_dpkg_phase_stays_bounded_on_the_final_attempt`); the job timeout applies where set.
4. Paper Tiger. Severity: P2. The mirror rewrite misses a sources layout. Mitigation: every `apt-mirrors.txt`, `sources.list`, `sources.list.d/*.list` and `*.sources` naming the primary host is rewritten, with a warning when none does. Covered by `test_stalled_primary_mirror_falls_back_on_the_retry` and `test_retry_without_a_primary_mirror_source_warns`.
5. Paper Tiger. Severity: P2. Concurrent jobs race to save the same key. Mitigation: `actions/cache/save` logs a reservation conflict as a warning; the first save wins.
6. Paper Tiger. Severity: P2. A future job adds raw `apt-get` or calls the script directly and bypasses the cache. Mitigation: `test_no_workflow_step_runs_apt_get_or_the_script_directly` checks every workflow.
7. Elephant. Severity: P3. Caches are ref-scoped (see "Cache scope round" below):
   - Pull requests into develop restore the copy that develop push runs save; `test_develop_pushes_run_the_install_and_save_a_shared_cache` keeps that path intact.
   - Merge-queue runs skip the save, which would land on a temporary ref.
   - Whether a merge-queue run can restore develop's copy is undocumented. If it cannot, that run downloads as before, with the fallback mirror. It is measured on the first merge-queue run after the merge, not claimed here.
8. Elephant. Severity: P3. An exact hit keeps the `.deb` files as of that image version; later archive updates are downloaded until the image version, and with it the key, changes.

## Peer review (Junior: shelves, gates)
- Shelves: separate slow from stalled using the transport's own data timeout; fall back to another mirror; cache downloads rather than raising budgets; behavioural tests with stubs over a real `timeout`.
- Gate 1 (syntax): `bash -n` and `shellcheck` on `scripts/ci_apt_install.sh` are clean. `yaml.safe_load` parses the workflows and the action in the guard tests, and the action's key step runs under bash in `test_cache_key_follows_the_image_and_the_package_set`. flake8 on the new test is clean at the CI limit of 127 characters. `actionlint` is not installed locally.
- Gate 2 (tests): `tests/test_1871_ci_apt_install.py` gives 17 passed; with the changelog tests, 42 passed.
- Gate 3 (guards): `scripts/check_test_file_hygiene.py` passes.

## Lead review (adversarial)
Phase A coherence: each hub requirement maps to a change.
- **.deb cache:** `.github/actions/apt-install` uses only `actions/cache/restore@v4` and `actions/cache/save@v4`. The key combines ImageOS, a package-list digest and ImageVersion; the restore prefix omits ImageVersion. The archives are restored into a user-owned directory under `runner.temp` and copied into `/var/cache/apt/archives` with `sudo cp`. They are saved after a fresh install that exits 0.
- **Mirror fallback:** before attempt 2, azure.archive.ubuntu.com is rewritten to archive.ubuntu.com.
- **Slow but progressing:** a slow download is not killed on the final attempt (see the design decision above).
- **dpkg repair:** retained from the previous round.

Phase B verification: stubs drive the real script through each case.
- Cache hit: no download.
- Cache miss: downloads, then stages the archive.
- Primary mirror stall: retry on the fallback.
- Slow download on both attempts: the second finishes.
- Interrupted install: repair before the retry.
- dpkg phase on the final attempt: still bounded.
- Repair failure: a warning, and the retry still runs.
- Two failures: exit 1.
- Usage error: exit 2.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | An unbounded apt install can consume a required job's whole budget | stall detection, mirror fallback, `.deb` cache, bounded dpkg phase |
| F2 | P1 | A wall-clock kill on every attempt fails slow but live installs (2e61f1fc CI) | final attempt network phases have no wall-clock cap; no step timeout |
| F3 | P2 | No package cache | `.deb` cache through `actions/cache` |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1871
- **Reason:** #1871 is an operational CI ticket written as Symptom / Impact / Fix direction rather than the canonical template, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the #1871 body holds the symptom (run 42282238657, job 128113913494, silent from 19:47:29Z until the 20:04:34Z cancellation), the impact (a required check dequeues the merge-queue group) and the fix direction. This change's task records are https://github.com/siege-analytics/siege_utilities/issues/1871#issuecomment-6694687820 and, for the redesign, https://github.com/siege-analytics/siege_utilities/issues/1871#issuecomment-6696387959.
- **Falsification:** revert the implementation by restoring `.github/workflows/ci.yml` from develop `560a858e`. Then:
  - `test_no_workflow_step_runs_apt_get_or_the_script_directly` goes red, naming all five jobs that call `apt-get` directly;
  - `test_install_steps_use_the_cached_action_without_a_step_timeout` goes red because no step uses the action.

  Verified on 2026-11-06: 2 failed against develop's `ci.yml`; 16 passed after.

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11); GNU `timeout` from coreutils; macOS `/bin/bash` 3.2 runs the script in the tests, and CI runs bash 5.
- `python -m pytest tests/test_1871_ci_apt_install.py`: 16 passed at 7a972cbd (twice in a row, about 50 s each); 17 passed after the cache scope round.
- Against the 2e61f1fc script and `ci.yml`: 11 failed and 5 passed. The five that pass cover behaviour the old script shares (usage error, no staging on failure, capped dpkg phase) plus the two action-file checks.
- Adding `tests/test_release_process.py tests/test_user_config_export_changelog.py`: 41 passed at 7a972cbd; 42 after the cache scope round.

## Review round on 682d5069 (hub finding: interrupted dpkg)
Finding: if `timeout` stops `apt-get install` during the dpkg unpack/configure phase, dpkg is left interrupted. The retry then fails at once with "dpkg was interrupted, you must manually run 'sudo dpkg --configure -a'" or on the dpkg lock.

Fix (2e61f1fc):
- Before every retry the script runs `sudo timeout --kill-after=30 <cap> dpkg --configure -a`. If it fails, the script prints a warning, and any remaining problem surfaces from the following `apt-get`.
- The per-command default was lowered from 180 s to 120 s to keep the worst case inside the 13-minute step timeout. The next round removed that step timeout.

Red: with the 682d5069 script, 4 failed and 4 passed. After the fix, 8 passed.

## Redesign round on 2e61f1fc (hub finding: slow mirror, not stall)
Finding: CI on 682d5069 and 2e61f1fc showed both attempts killed mid-download at about 40 to 46 KB/s while still making progress (Investigation above). A fixed wall-clock cap cannot pass a 72 MB install at that rate. Jobs without a job timeout would turn slow successes, such as the 38-minute install on develop, into 13-minute failures.

Fix:
- **New:** `.github/actions/apt-install`, the `.deb` cache around the script.
- **Script:**
  - network and dpkg phases are now separate (`install --download-only`, then `install`);
  - the network cap applies to the first attempt only, and the dpkg phase is capped on every attempt;
  - the fallback mirror is used before the retry;
  - the cache is seeded and refreshed, and `cache-ready` is written to `GITHUB_OUTPUT`;
  - `APT::Keep-Downloaded-Packages=true` is set explicitly.
- **Workflow:** the five steps use the action, with no step timeout.
- **Tests:** the stub now models mirrors, archives and the dpkg repair. New tests cover:
  - cache hit;
  - cache miss and staging;
  - no staging after a failure;
  - primary stall followed by the fallback mirror;
  - a slow download that finishes on the final attempt;
  - a dpkg phase that stays bounded on the final attempt;
  - the warning when no primary mirror source exists;
  - the action's structure and its cache key.

Red: with the 2e61f1fc script and `ci.yml`, 11 failed and 5 passed. After the fix, 16 passed.

## Hosted evidence (run 42302877291 on 7a972cbd, conclusion success)
- **Key:** `apt-debs-ubuntu24-36253bc8d112ecb3-20261101.360.1`. ImageOS and ImageVersion are set on the hosted runner, so no placeholder was used.
- **Miss and first save:** `django models` logged "Need to get 72.1 MB", "Fetched 72.1 MB in 38s", then "Need to get 0 B/72.1 MB" in the dpkg phase, and staged 109 `.deb` files. One save landed: 72,002,225 B on `refs/pull/1872/merge` at 22:12:50Z.
- **Concurrent saves:** "Failed to save: Unable to reserve cache with key …, another job may be creating this cache." followed by `##[warning]Cache save failed.` The step still exited 0.
- **Hits:** `test-postgis` and `battle-test` logged "Cache hit", "seeded 109 .deb files" and "Need to get 0 B/72.1 MB", and installed in 22 to 23 s with no save.
- **Live fallback** (`test (3.11)`, job 128184809443):
  - The Azure mirror was slow; attempt 1 exited 124 after 120 s.
  - "apt sources: /etc/apt/apt-mirrors.txt now uses archive.ubuntu.com instead of azure.archive.ubuntu.com".
  - "Need to get 69.2 MB/72.1 MB" (the earlier downloads were reused), then "Fetched 67.8 MB in 23s (3008 kB/s)".
  - The install exited 0 on attempt 2 after 3m07s.
- **Overall:** all 10 install steps exited 0.

## Cache scope round on 7a972cbd (hub: verify cache scope)
Rule (GitHub docs, "Restrictions for accessing a cache"): a run can restore caches from its current branch and the default branch (`main`), and pull-request runs also from the base branch. Caches saved on a pull request's merge ref "can only be restored by re-runs of the pull request". The docs say nothing about merge queues. Other projects skip saves in `merge_group` runs because those land on a temporary `gh-readonly-queue/<base>/pr-…` ref (for example, Vello's `save-if: github.event_name != 'merge_group'`).

Consequences:
- **Develop-scoped save:** after the merge, the develop push run cannot see the `refs/pull/1872/merge` cache, so it misses and saves on `refs/heads/develop`. Later pull requests into develop restore that copy. Nothing extra is needed, because `ci.yml` runs on pushes to develop and the five install jobs have no job condition. `test_develop_pushes_run_the_install_and_save_a_shared_cache` now guards this: the develop push and pull_request triggers, five action jobs with no `if:`, and a save condition that excludes only `merge_group`.
- **Merge-queue saves:** now skipped (`github.event_name != 'merge_group'` added to the save condition), so a queue run does not store 72 MB on a ref nobody reads.
- **Main:** caches on `main`, the default branch, are readable everywhere; main push runs save there once the action reaches main.
- **Unverified:** whether a merge-queue run restores develop's copy.

Red: with the 7a972cbd action, `test_apt_action_restores_installs_then_saves_the_archive` and the new develop-save test fail (2 failed). After the change, 17 passed.

## Rework ledger
- During the first red check, a blocked command left the new `ci.yml` unstaged, so the restore reverted it to develop's version. The edit was re-applied and verified (five script calls, no `apt-get`) before the red check was repeated correctly. Nothing was committed in between.
- Redesign round: the first stub followed a call-order plan with 1 s caps. Under machine load, a capped stub was stopped before it read its plan entry. The `hang` then landed on the uncapped final attempt, and one run hit the 60 s subprocess limit; the call log showed the shifted plan. The script behaved correctly. The stub now uses rules that do not depend on call order (hang on a mirror, slow or failing commands, hang until the dpkg repair has run), and the test caps rose to 5 s. Two consecutive runs then passed with 16 of 16.
