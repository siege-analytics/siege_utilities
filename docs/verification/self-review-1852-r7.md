# Self-review: #1852 round 7 (develop 6c049c2c integration)

This round merges develop 6c049c2c into fix/engine-cluster. It changes no source or test file. The merge commit is 3be56709. It has first parent fcb7ad21 and second parent 6c049c2c, and the merge base is 560a858e.

## Assumptions

Goal source: https://github.com/siege-analytics/siege_utilities/pull/1852#issuecomment-6842558231
Working as: software engineer
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/pull/1852#issuecomment-6842558231
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/pull/1852#issuecomment-6842558231
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/pull/1852#issuecomment-6842558231
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/pull/1852#issuecomment-6842919068

- The plan for this round is plan v3 on #1852 (comment 6842558231). Its investigation fact sheet and pre-mortem are part of that comment.
- An independent review of plan v2 is comment 6842565446. Plan v3 maps each of its findings to a change.
- An independent review of the staged merge result is comment 6842919068.
- The PR head on GitHub before this round was 91ab40fd. fcb7ad21 was a local commit on top of it, a one-line wording fix to self-review-1852-r5.md, and this push publishes it.
- The review-tier record check for this round reads every comment on #1852. The two new plan and review comments (6842558231 and 6842565446) carry the task description, investigation, pre-mortem and Senior checklist sections on their own. The check cannot exclude the earlier comments of 2026-11-05 from the previous round.

## Merge-tree result

`git merge-tree --write-tree --name-only fcb7ad21 6c049c2c` exited 1 with trial tree 0ba241d7. The only conflicted path was CHANGELOG.md ("CONFLICT (content): Merge conflict in CHANGELOG.md").

## CHANGELOG construction

Both sides insert entries after base line 321, the blank line under the first `### BREAKING` heading of the pending release:
- develop inserts 69 lines, which are develop lines 413 to 481;
- this branch inserts 72 lines, which are fcb7ad21 lines 322 to 393.

The resolved file was built from the two parents' own bytes, independently of git's conflict region:
1. Before the merge, `git hash-object CHANGELOG.md` was 02d16398. That equals `git rev-parse fcb7ad21:CHANGELOG.md`. Lines 322 to 393 of that file were copied out.
2. Next came `git merge --no-ff --no-commit 6c049c2cfda6330680a553afd9ac0f149eb80b9c`.
3. Then `git checkout --theirs -- CHANGELOG.md`. After it, `git hash-object CHANGELOG.md` was 2f1d95fd, which equals `git rev-parse 6c049c2c:CHANGELOG.md`. Line 481 is blank, and line 482 begins the `CensusDataSource.fetch_geographic_boundaries` entry.
4. The expected file is develop lines 1 to 481, then the 72 branch lines, then develop line 482 onward. That is 481 + 72 + 1560 = 2113 lines, and `git hash-object` gives 7fbe4d2d1659fb136e86637de3d42c77b00d6af7.
5. That file was placed and staged. `git rev-parse :CHANGELOG.md` gave 7fbe4d2d1659fb136e86637de3d42c77b00d6af7, equal to the expected blob.

Develop's entries come first and this branch's four entries follow unchanged. Each block keeps its own trailing blank line. Develop renamed `[4.1.0] - 2026-10-18` to `[5.0.0]`, so this branch's entries now sit under 5.0.0. They go there rather than under `[Unreleased]` because 5.0.0 is the pending release; develop filed #1404 the same way (7795a2bb). Git also recorded this resolution in its local rerere cache.

## Verification

The staged checks ran before the commit. The commit checks ran again on 3be56709.

| Check | Command | Result |
|---|---|---|
| CHANGELOG blob | `git rev-parse :CHANGELOG.md`, then `git rev-parse 3be56709:CHANGELOG.md` | 7fbe4d2d both times, equal to the expected blob: PASS |
| One insertion against develop | `git diff -U0 --no-ext-diff --no-textconv --no-color 6c049c2c 3be56709 -- CHANGELOG.md` | a single hunk `@@ -481,0 +482,72 @@`: PASS |
| CHANGELOG numstat against develop | `git diff --cached --numstat 6c049c2c -- CHANGELOG.md` | 72 0: PASS |
| CHANGELOG numstat against fcb7ad21 | `git diff --cached --numstat fcb7ad21 -- CHANGELOG.md` | 172 2, the same as develop's own 560a858e to 6c049c2c numstat: PASS |
| Hunks against fcb7ad21 | `git diff --cached -U0 fcb7ad21 -- CHANGELOG.md` | develop's seven base hunks, the BREAKING insertion as the single hunk `@@ -321,0 +413,69 @@`: PASS |
| Path set against develop | `git diff --name-only 6c049c2c 3be56709` | 15 paths, this branch's changes since 560a858e: PASS |
| Path set against fcb7ad21 | `git diff --name-only fcb7ad21 3be56709` | 67 paths, develop's changes since 560a858e: PASS |
| Conflict markers | `grep -c` for marker lines in CHANGELOG.md | 0: PASS |
| Index state | `git status --porcelain` before the commit; `git ls-files -u` | only staged entries; no unmerged entries: PASS |
| Parents | `git log -1 --format=%P 3be56709` | fcb7ad21 6c049c2c: PASS |
| Remote heads | `git ls-remote origin refs/heads/develop refs/heads/fix/engine-cluster` | 6c049c2c and 91ab40fd, before the merge: PASS |

The pre-push `ls-remote` check and the ancestry checks for 91ab40fd and fcb7ad21 are recorded in the PR after the push, because this record is committed first.

## Tests

- **Local tests: NOT RUN.** This covers both the baseline at fcb7ad21 and the merged-tree run. An optional local probe was refused by a command guard, so CI is the evidence. No source or test file changes in this round. Develop changes nothing under siege_utilities/engines/ and no engine test module. Its version line and the `CensusServerError` lazy export in siege_utilities/geo/__init__.py are on the engine modules' import path.
- **Fingerprint scan of the commit messages:** the separate scan was refused by a local command guard and is recorded as not run.
- **Hosted CI on the pushed head is the authority:**
  - Every job must succeed or be an expected skip, except "api, security and build".
  - In "api, security and build", every step must succeed except the pip-audit dependency audit. That step fails on develop today for the advisory tracked in #1895, and its log must show only that advisory.
  - The battle-test job must pass.

## Peer review

- **writing-claims:2.** Every count in this record comes from a command run in the same sequence: the 15 and 67 path counts, the 72 0 and 172 2 numstats, the 2113-line expected file and the blob IDs. Each command exited with exit 0, except the expected exit 1 from merge-tree on a conflict.
- **Leak scan:** a scan of this file and both commit messages for local paths, environment names and attribution found nothing: CLEAN.

## Lead review

- **Does the round do what #1852 needs?** It clears the CONFLICTING state with develop 6c049c2c without changing any #1852 content. The staged-merge review (comment 6842919068) reports no S1 or S2 findings, and its verdict is that the staged result may be committed.
- **Its S3 notes, none acted on in this merge:**
  - the r5 and r6 records still say 4.1.0, where the heading is now 5.0.0; they are historical;
  - the blank line between the two BREAKING blocks;
  - fcb7ad21 being published by this push;
  - the four separate `### BREAKING` subsections already present in `[5.0.0]`.
- **Still open after the push:** hosted CI on the new head, and GitHub's `mergeable` field reading MERGEABLE, which may read UNKNOWN while GitHub recomputes. Both are reported on the PR once observed.
- **Follow-up:** the wording question about `SparkEngine.nearest`, in this branch's #1497 entry against the #1463 entry, goes to a separate issue.

## Quantified claims

| Claim | Command | Value |
|---|---|---|
| Paths this branch changed since the merge base | `git diff --name-only 560a858e fcb7ad21` | 15 |
| Paths develop changed since the merge base | `git diff --name-only 560a858e 6c049c2c` | 67 |
| Lines this branch inserted in CHANGELOG.md | `git diff --numstat 560a858e fcb7ad21 -- CHANGELOG.md` | 72 0 |
| Develop's CHANGELOG.md numstat | `git diff --numstat 560a858e 6c049c2c -- CHANGELOG.md` | 172 2 |
| Line count of the expected file | `wc -l` | 2113 |
| Conflicted paths in the trial merge | `git merge-tree --write-tree --name-only` | 1 (CHANGELOG.md) |

## Rollback

This is a merge commit on a branch that targets develop. After the push, fix forward. Do not `git revert -m 1` the merge: when the PR lands, that would reverse develop's 67 paths.
