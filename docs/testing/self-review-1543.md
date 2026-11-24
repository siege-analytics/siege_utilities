# Self-review: git option injection in branch and remote helpers (#1543, PR #1735)

Scope of this artifact: the PR as a whole at its code head d23c722e, plus the process-only commits that sync with develop and add this file. The process commits change `CHANGELOG.md` conflict handling and this document and no library code.

Review-Tier: A for the process commit (documentation only). The code commits under review were reviewed independently at an earlier head by the external reviewer.

## Assumptions

- Goal source: ticket #1543. Git helpers must not interpret caller-supplied remotes as options or branch names as checkout pathspecs; names such as leading-hyphen names, `HEAD`, `@`, bare filenames and bare file or directory collisions are rejected before any git command runs.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the earlier approval on the ticket.
- The code diff against `origin/develop` after the sync touches `siege_utilities/git/git_operations.py`, `git_workflow.py`, `validation.py`, `README.md`, two test files and `CHANGELOG.md`. This commit adds no library code.
- The #1543 note sits in `CHANGELOG.md` as one entry under `[Unreleased]` / `### BREAKING` (see "Sync with develop fa8ecff5" below). It began as a Changed entry and a Fixed entry in the old `[4.1.0]` bucket; at the 71f02b0b sync the only conflict with develop was in the Fixed section, settled by keeping the #1543 entry and every develop entry, with no wording changed.
- Pre-author-inventory: NONE. Trivial-against-state: `git diff origin/develop -- CHANGELOG.md` shows only the #1543 entry as an addition after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_git_operations.py test_git_option_injection.py` -> 112 passed in 0.31s.
- Hosted CI at the pushed head is recorded in the PR body once it finishes. The queued CI mentioned in the earlier body belongs to an old head and is superseded.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1543 entry under `[Unreleased]` / `### BREAKING` and none under a released section.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. Develop wins on any disagreement, and none exists: no develop change touches `siege_utilities/git/`.

Classification: caller code that worked on v4.0.0 now fails (a bare dotted name such as `v1.2`, a name equal to a top-level file or directory, option-like refs and reserved aliases now raise; Git 2.23 or newer is required; `switch_branch` no longer matches a partial name). The PR had two notes, a `### Changed` note about those inputs and a `### Fixed` note about the validation. They are now one entry under `### BREAKING` in `[4.1.0]` with a Migration line, at its own position in the BREAKING list so it does not conflict with the other open PRs. `git diff origin/develop -- CHANGELOG.md` shows 19 added lines and 0 removed lines. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_git_operations.py test_git_option_injection.py -q` -> 112 passed in 0.29s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Sync with develop fa8ecff5

Develop released the old `[4.1.0]` bucket as `[5.0.0] - 2026-11-20`, so the entry described in Pre-flight would have merged, without a conflict, into a released section. This sync merges develop additively and moves the #1543 entry, unchanged apart from "reject refs that 6.0.0 and earlier releases accepted", to `[Unreleased]` / `### BREAKING`. Neither 5.0.0 nor 6.0.0 contains this change. No library code or test changes in this commit.

## Ticket-fitness exemption

Governing ticket: #1543 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1543 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (caller-supplied remotes interpreted as git options and branch names as checkout pathspecs), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1543, and in the PR description, https://github.com/siege-analytics/siege_utilities/pull/1735. The reviewer verdicts are recorded on the ticket thread and the PR conversation.
- **Falsification:** revert the implementation (the `siege_utilities/git/` changes of this PR); `tests/test_git_option_injection.py::test_every_ref_rejected_before_any_git` and `tests/test_git_option_injection.py::test_remote_tracking_uses_exact_ref_and_switch` go red because option-like or path-like refs are no longer rejected before git runs and `switch_branch` stops resolving exact refs. Observed revert run: with `siege_utilities/git/git_operations.py`, `git_workflow.py` and `validation.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/git/git_operations.py siege_utilities/git/git_workflow.py siege_utilities/git/validation.py`), `python -m pytest test_git_option_injection.py::test_remote_tracking_uses_exact_ref_and_switch test_git_option_injection.py::test_every_ref_rejected_before_any_git -q`, run from the tests directory, gave 15 failed in 0.16s (`Failed: DID NOT RAISE GitSecurityError or ValueError`, and an argv assertion for the exact-ref switch). Running the whole `test_git_option_injection.py` file under the revert gave 34 failed, 12 passed. One test I first considered, `test_remote_options_rejected_before_any_git`, still passed under the revert (develop already rejects option-like remotes), so it is not cited. After `git checkout HEAD --` of the files the two tests gave 15 passed in 0.10s, `test_git_operations.py` with `test_git_option_injection.py` gave 112 passed on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The process-only commits (the develop syncs and this document) change no library behavior. The library change of this PR is the breaking change classified above. No claim in this artifact exceeds what was observed.
