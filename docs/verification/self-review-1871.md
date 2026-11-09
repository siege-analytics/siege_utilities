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

Chosen: (a) for the final attempt, combined with a wall-clock cap on the first attempt, plus a generous final budget (added in the CodeRabbit round below).
- **Final attempt:** apt's data timeout (30 s without bytes) and `Acquire::Retries=3` are the stall detector, the "no bytes for N seconds" rule. The network phases (`update`, `install --download-only`) also share one 2700 s (45 min) wall-clock budget. That is above the whole slowest install that exited 0 (2316 s), so a slow but live download completes, and a trickle that never trips the stall detector still ends.
- **Correction:** the 7a972cbd version argued that any fixed cap either kills the evidenced successes or bounds nothing. That was wrong. A cap above the evidence still bounds the six-hour tail (CodeRabbit comment 4498224208; hub).
- **First attempt:** the network phases keep a 120 s wall-clock cap. On a slow primary mirror this costs nothing: the downloaded `.deb` files stay in `/var/cache/apt/archives` and the retry reuses them (evidence above). The retry also runs against the fallback mirror.
- **dpkg phase:** installing from the downloaded files, the `dpkg --configure -a` repair and `autoclean` stay capped (300 s) on every attempt. A hang that is not a download is therefore still bounded.
- **Install steps:** in the four jobs without a job timeout, `timeout-minutes: 80` sits above the script's own bounded worst case (4391 s, about 73 min), so the script reports first and the six-hour default never applies. `test-postgis` uses shorter limits (worst case 851 s) under `timeout-minutes: 15`, leaving 5 minutes of its 20-minute job for the other steps (see "CodeRabbit round on e4679b66").

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The wrapper reports success after failing. Mitigation: the failure status is captured in an `else` branch, the script ends with `exit 1`, and `test_two_failed_attempts_fail_the_step` covers it.
2. Tiger (launch-blocking). Severity: P1. A broken or empty cache is saved and poisons later runs. Mitigation:
   - the save runs only when the script wrote `cache-ready=true`, which needs an install that exited 0 and a refresh with at least one `.deb`;
   - it never runs over an exact hit;
   - apt checks every cached `.deb` against the package index and downloads anything stale.
   Covered by `test_failed_install_does_not_stage_the_cache` and `test_apt_action_restores_installs_then_saves_the_archive`.
3. Tiger (launch-blocking). Severity: P1. The final attempt holds the runner. Mitigation:
   - network phases end after 30 s without data (apt, 3 retries) and within a shared 45-minute budget (`test_final_download_stops_when_its_budget_runs_out`);
   - the dpkg phase is capped (`test_dpkg_phase_stays_bounded_on_the_final_attempt`);
   - every install step has a step timeout above the script's worst case for its limits: 80 minutes where the job has no timeout, 15 minutes in `test-postgis`, inside its 20-minute job (`test_install_steps_are_bounded_above_the_slowest_evidenced_install`, `test_test_postgis_limits_fit_its_job_with_room_for_the_tests`).
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
- Gate 2 (tests): `tests/test_1871_ci_apt_install.py` gives 21 passed; with the changelog tests, 46 passed.
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
| F4 | P1 | Final attempt unbounded against a trickle; six-hour job default (CodeRabbit 4498224208) | 45-minute final network budget; 80-minute step timeout where no job timeout applies |
| F5 | P2 | Test assertions depended on capped stubs starting within the cap (CodeRabbit 4498224221) | logging and decisions moved to the uncapped `sudo` stub |
| F6 | P1 | `test-postgis` install bounded only by its 20-minute job timeout, so a slow mirror cancels the job (CodeRabbit 4499528288) | shorter limits (worst case 851 s) under a 15-minute step timeout |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1871
- **Reason:** #1871 is an operational CI ticket written as Symptom / Impact / Fix direction rather than the canonical template, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the #1871 body holds the symptom (run 42282238657, job 128113913494, silent from 19:47:29Z until the 20:04:34Z cancellation), the impact (a required check dequeues the merge-queue group) and the fix direction. This change's task records are https://github.com/siege-analytics/siege_utilities/issues/1871#issuecomment-6694687820 and, for the redesign, https://github.com/siege-analytics/siege_utilities/issues/1871#issuecomment-6696387959.
- **Falsification:** revert the implementation by restoring `.github/workflows/ci.yml` from develop `560a858e`. Then:
  - `test_no_workflow_step_runs_apt_get_or_the_script_directly` goes red, naming all five jobs that call `apt-get` directly;
  - `test_install_steps_are_bounded_above_the_slowest_evidenced_install` (named `test_install_steps_use_the_cached_action_without_a_step_timeout` before the CodeRabbit round) goes red because no step uses the action.

  Verified on 2026-11-06: 2 failed against develop's `ci.yml`; 16 passed after.

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11); GNU `timeout` from coreutils; macOS `/bin/bash` 3.2 runs the script in the tests, and CI runs bash 5.
- `python -m pytest tests/test_1871_ci_apt_install.py`: 16 passed at 7a972cbd (twice in a row, about 50 s each); 17 passed after the cache scope round; 19 passed after the CodeRabbit round; 21 after the test-postgis round.
- Against the 2e61f1fc script and `ci.yml`: 11 failed and 5 passed. The five that pass cover behaviour the old script shares (usage error, no staging on failure, capped dpkg phase) plus the two action-file checks.
- Adding `tests/test_release_process.py tests/test_user_config_export_changelog.py`: 41 passed at 7a972cbd; 42 after the cache scope round; 44 after the CodeRabbit round; 46 after the test-postgis round.

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

## CodeRabbit round on 6c500ea5 (comments 4498224208 and 4498224221)
**4498224208 (Major): bound the final network attempt.** Valid. A mirror that delivers a byte at least every 30 s never trips `Acquire::http::Timeout`. With no step timeout, the four jobs without a job timeout could hold a runner for the six-hour default.

Fix:
- `APT_FINAL_NETWORK_TIMEOUT` (default 2700 s) is one wall-clock budget shared by the final attempt's `update` and `install --download-only`. It starts after the repair and the mirror switch. Each phase's cap is what is left of the budget, with a floor of 1 s, so an exhausted budget still runs and stops the command rather than skipping it.
- **Why 2700 s:** the slowest install that exited 0 took 2316 s for the whole step (develop run 42112634904, `test (3.11)`); 2700 s is 17% above it. In the evidenced slow-mirror case on this design (`test (3.11)` in run 42302877291), attempt 1 used about 2 minutes and the fallback mirror delivered 67.8 MB in 23 s.
- **Bounded worst case** with the defaults, at 4391 s (about 73 min):
  - attempt 1: 2 x (120 + 30) + (300 + 30);
  - repair and delay: (300 + 30) + 10;
  - final network: 2700 + 1 + 2 x 30;
  - final dpkg phase and autoclean: 2 x (300 + 30).
- **Step timeout:** `timeout-minutes: 80` (4800 s) on the four install steps whose job has no timeout. It is above the script's own bound, so the script's diagnostics appear first, and well under 360 minutes. `test-postgis` keeps no step timeout, because its 20-minute job timeout is tighter.
- **Tests:**
  - `test_final_download_stops_when_its_budget_runs_out`: a download that outlasts a 7 s budget ends with exit 124 on attempt 2 and the step exits 1;
  - `test_slow_download_finishes_within_the_final_budget`: an 8 s slow download completes within a 30 s budget, and the caps come from it;
  - `test_script_defaults_bound_the_final_attempt_above_the_evidence`: the script defaults match `WORST_CASE_SECONDS`, and the final budget exceeds 2316 s;
  - `test_install_steps_are_bounded_above_the_slowest_evidenced_install`: replaces the no-step-timeout guard.

**4498224221 (Minor): remove the stub start-up timing dependency.** Valid, and the same class as the hang in the rework ledger.

Fix:
- The script runs `sudo timeout --kill-after=30 CAP apt-get …`, so the `sudo` stub runs before `timeout` starts its clock and is never capped. It now does all the bookkeeping:
  - it logs each `apt-get` and `dpkg` call with its cap, the mirror at call time and the files still to fetch;
  - it decides the call's behaviour from the rules;
  - it records a `dpkg --configure -a` that will exit 0;
  - it then `exec`s the original command line.
- The `apt-get` stub only carries out the behaviour it is given. The command lists, mirrors, fetch lists and caps that the tests assert are therefore fixed before any capped process starts. The stalled-mirror test now asserts the full list, including the stopped call on the primary mirror.
- **Remaining timing, and why it is safe:** a stub that is not told to hang or run slow must exit within its cap (5 s network, 6 s dpkg). Measured locally, a whole non-hanging scenario (`test_successful_install_uses_bounded_apt_options`, six Python process starts, a `sudo` and an `apt-get` stub per call, plus bash) takes 0.71 s, about 0.12 s per start, so the caps are about 40 times the per-process cost. The earlier flake came from a 1 s cap combined with logging inside the capped process. Both are gone.

Red: with the 6c500ea5 script and `ci.yml`, 4 failed and 15 passed (the two final-budget tests, the defaults check and the step-timeout guard). After the fix, 19 passed.

## CodeRabbit round on e4679b66 (comment 4499528288)
**Bound the apt install step in `test-postgis`.** Valid. With the default limits the script's bounded worst case is 4391 s, but `test-postgis` has a 20-minute (1200 s) job timeout and no step timeout. A slow but live final download would therefore run until GitHub cancels the job. That cancels the required check and dequeues the merge group with no step failure and no script message.

Evidence (`test-postgis`, all exited 0):

| Run | Before install (s) | Install (s) | After install (s) | Not install (s) |
|---|---|---|---|---|
| 42327200169 | 27 | 19 | 109 | 136 |
| 42302877291 | 29 | 22 | 127 | 156 |
| develop 42112634904 | 26 | 22 | 109 | 135 |
| develop 42007861238 | 27 | 43 | 154 | **181** |

Healthy phases elsewhere:
- a cold 72 MB download took 38 s;
- the dpkg phase took 13 to 22 s;
- the fallback mirror delivered 67.8 MB in 23 s.

Fix:
- The action takes optional `attempt-timeout`, `final-network-timeout` and `dpkg-timeout` inputs, passed to the script as `APT_ATTEMPT_TIMEOUT`, `APT_FINAL_NETWORK_TIMEOUT` and `APT_DPKG_TIMEOUT`. Blank inputs keep the script defaults (`${VAR:-default}`), so the other four jobs are unchanged.
- `test-postgis`:
  - step: `timeout-minutes: 15` (900 s), leaving 300 s of the 1200 s job for the other steps, 1.66 times the longest seen (181 s);
  - limits: attempt 60 s (cold download 38 s), dpkg 60 s (13 to 22 s), final network 240 s (the fallback needed 23 s for 67.8 MB);
  - worst case: 2 x (60 + 30) + (60 + 30) + (60 + 30) + 10 + 240 + 1 + 2 x 30 + 2 x (60 + 30) = 851 s, under 900 s.
  - A trickling mirror therefore ends this step with the script's own message, and the job reports a step failure, not a cancellation.
- `test-postgis` cannot finish a 72 MB download at about 40 KB/s within 20 minutes under any limits. The `.deb` cache is what makes that job fast: it hit the cache in runs 42302877291 and 42313335868.
- Tests:
  - `test_install_steps_are_bounded_above_the_slowest_evidenced_install` now requires, for every install step: script worst case (for that step's limits) < step timeout. Where the job has a timeout, the step must also leave at least 1.5 times 181 s; otherwise the step keeps the default limits and stays under 360 minutes.
  - `test_test_postgis_limits_fit_its_job_with_room_for_the_tests` pins 851 s < 900 s < 1200 s, plus each limit against its evidence.
  - `test_blank_limits_from_the_action_keep_the_script_defaults` runs the script with blank values and asserts the default caps.
  - The action test asserts the input-to-variable wiring.

Red: with the e4679b66 `ci.yml` and action, 3 failed and 1 passed. The blank-limits test passes on both, because the script already treated blanks as unset; it pins that guarantee for the action. After the fix, 21 passed.

## Rework ledger
- During the first red check, a blocked command left the new `ci.yml` unstaged, so the restore reverted it to develop's version. The edit was re-applied and verified (five script calls, no `apt-get`) before the red check was repeated correctly. Nothing was committed in between.
- Redesign round: the first stub followed a call-order plan with 1 s caps. Under machine load, a capped stub was stopped before it read its plan entry. The `hang` then landed on the uncapped final attempt, and one run hit the 60 s subprocess limit; the call log showed the shifted plan. The script behaved correctly. The stub now uses rules that do not depend on call order (hang on a mirror, slow or failing commands, hang until the dpkg repair has run), and the test caps rose to 5 s. Two consecutive runs then passed with 16 of 16.
