---
ticket_refs:
  - siege-analytics/siege_utilities#1574: summarized in the self-review ticket comment
---

# Hostile review: #1574 / PR #1739 staging-directory path shapes

Reviewer: a separate read-only review agent (same model family as the implementer). The cross-family exact-head re-review by the independent PR reviewer is still required and is requested after push.
Scope: the uncommitted diff on top of the develop merge `378ca022` (`spark_utils.py`, `tests/test_atomic_write_with_staging_hadoop_fs.py`, `CHANGELOG.md`).

## Findings and dispositions

1. No blocker: the scheme regex `^[A-Za-z][A-Za-z0-9+.-]+:` keeps `C:/x`, `C:\x` and `\\server\share` local, matches uppercase schemes, and `rstrip('/')` keeps `file:///tmp/` and `hdfs://nn:8020/` intact.
2. No blocker, documented: relative paths with a leading `name:` (`data:2024/x`) are now read as URIs. This matches Hadoop's own parsing, so it agrees with `atomic_write_with_staging`. Docstring and CHANGELOG now say so (follow-up 5, fixed).
3. FOLLOW-UP, fixed: `Path("s3a://bucket/x")` stringifies to `s3a:/bucket/x`, silently losing the authority. A URI held in a `pathlib.Path` now raises `ValueError`; test `test_unique_staging_directory_rejects_a_uri_held_in_a_path`.
4. FOLLOW-UP, fixed: the error text said "no authority or path" for `hdfs:/` and `file:///`, which do have a root path. Now "no authority or non-root path".
5. FOLLOW-UP, fixed: the authority-less test accepted `ValueError`. It now requires the returned path.
6. FOLLOW-UP, fixed: the `atomic_write_with_staging` `staging_directory` docstring now cross-references `create_unique_staging_directory` and the `fs.defaultFS` vs driver-local difference.
7. No blocker: the new tests fail on `245969d6` (7 of 9 red there); the `Path.mkdir` patch uses `monkeypatch` and does not leak.

Verdict: no blockers; all follow-ups applied.
