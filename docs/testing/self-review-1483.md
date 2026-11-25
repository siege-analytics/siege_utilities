# Self-review: Spark JDBC driver coordinates (#1483, PR #1804)

Scope of this artifact: the PR as a whole at its code head ebfbfd15, plus the later commits that sync with develop, add this file, and bump two default driver pins. The 71f02b0b sync changed no library code; the fa8ecff5 sync bumps the pgjdbc and MySQL Connector/J pins (see "Sync with develop fa8ecff5") and moves the #1483 note to `[Unreleased]` / `### BREAKING`. The PR body was also refreshed.

Review-Tier: A for the process commit (documentation only). The code commits under review were reviewed independently at an earlier head by the external reviewer.

## Assumptions

- Goal source: ticket #1483. `create_spark_session_with_databases` selected vulnerable JDBC driver versions (pgjdbc 42.3.1, mysql-connector-java 8.0.28, ojdbc8 21.1.0.0) and added the PostgreSQL driver even without database names; the defaults come from one coordinate map, overridable through `conf.settings.SPARK_JDBC_PACKAGES`.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the earlier approval on the ticket and PR.
- The code diff against `origin/develop` after the sync is `siege_utilities/config/databases.py`, `tests/test_1483_spark_jdbc_cve.py` and `CHANGELOG.md`. The 71f02b0b sync commit added no library code; the fa8ecff5 sync changes only the two pin strings, the docstring example and two test floors.
- Release convention: user-visible notes belong in `CHANGELOG.md` under `[Unreleased]`. The #1483 entry sits under `### BREAKING` in `[Unreleased]`; `grep` finds exactly one `(#1483)` in the file and the section boundaries were read after the sync. No other entry was touched.
- The pgjdbc 42.7.15 and MySQL Connector/J 26.10.0 coordinates were checked on Maven Central in the fa8ecff5 sync; the ojdbc8 version is the PR author's statement. No live JDBC connection or JVM startup is claimed anywhere.
- Pre-author-inventory: NONE. Trivial-against-state: after the sync, `git diff origin/develop -- CHANGELOG.md` shows only the #1483 entry as an addition.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_1483_spark_jdbc_cve.py test_database_config.py` -> 27 passed in 0.17s.
- Hosted CI at the pushed head is recorded in the PR body once it finishes. The earlier body said CI results were pending; the head had not moved since.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1483 entry under `[Unreleased]` / `### BREAKING` exactly once and none under a released section.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively with no conflicts. Develop wins on any disagreement, and none exists: no develop change touches `siege_utilities/distributed/` or `siege_utilities/config/`.

Classification: caller code that worked on v4.0.0 now behaves differently (with no override, empty or None `database_names` adds no JDBC driver where v4.0.0 added the PostgreSQL driver; the MySQL coordinate moved; the new MySQL default needs Server 8.4+). The entry already carried migration text under `### Security`; it now sits under `### BREAKING` in `[4.1.0]` with an explicit Migration line, at its own position in the BREAKING list so it does not conflict with the other open PRs. `git diff origin/develop -- CHANGELOG.md` shows 12 added lines and 0 removed lines. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_1483_spark_jdbc_cve.py test_database_config.py -q` -> 27 passed in 0.17s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Sync with develop fa8ecff5

Develop released the old `[4.1.0]` bucket as `[5.0.0] - 2026-11-20`, so the entry described in Pre-flight would have merged, without a conflict, into a released section. This sync merges develop additively and moves the #1483 entry to the top of `### BREAKING` in `[Unreleased]`. It also bumps two default pins in `siege_utilities/config/databases.py`. `org.postgresql:postgresql` goes from 42.7.14 to 42.7.15, which is the patched version in the 14 pgjdbc advisories published on 2026-11-23 against 42.7.14 and earlier. GHSA-hcjv-f5jh-r55v (low, 42.7.14 and earlier) lists no patched version and remains open. `com.mysql:mysql-connector-j` goes from 26.7.0 to 26.10.0: 26.7.0 is the version named as affected by CVE-2026-101768 (Oracle October 2026 CPU), and 26.10.0 is the next release, which the advisory does not list as affected. The 26.10.0 release notes do not name a CVE, so this is not a verified fix. The ojdbc8 pin is unchanged. `test_default_drivers_are_patched` now requires at least 42.7.15 and 26.10.0, so the previous pins fail it.

## Ticket-fitness exemption

Governing ticket: #1483 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1483 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (`create_spark_session_with_databases` selecting vulnerable pgjdbc, MySQL and Oracle JDBC driver versions and adding the PostgreSQL driver without database names), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1483, and in the PR description, https://github.com/siege-analytics/siege_utilities/pull/1804. The reviewer verdicts are recorded on the ticket thread and the PR conversation.
- **Falsification:** revert the implementation (the `siege_utilities/config/databases.py` changes of this PR); `tests/test_1483_spark_jdbc_cve.py::test_default_drivers_are_patched` goes red because the default coordinates return to the vulnerable versions. Observed revert run: with `siege_utilities/config/databases.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/config/databases.py`), `python -m pytest test_1483_spark_jdbc_cve.py::test_default_drivers_are_patched -q`, run from the tests directory, gave 1 failed in 0.11s (AssertionError: the default coordinates are not the patched versions). After `git checkout HEAD --` of the file the command gave 1 passed in 0.08s, `test_1483_spark_jdbc_cve.py` gave 16 passed on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The process-only commits (the 71f02b0b sync and this document) change no library behavior. The library change of this PR, including the fa8ecff5 pin bumps, is the breaking change classified above. No claim in this artifact exceeds what was observed.
