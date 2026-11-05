---
ticket_refs:
  - siege-analytics/siege_utilities#1574: comment posted https://github.com/siege-analytics/siege_utilities/issues/1574#issuecomment-6651165898
---

# Self-review: #1574 / PR #1739, single-slash URIs and scheme-less staging paths

Working as: software engineer, data engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1574#issuecomment-6256250477 (required changes 1 to 3)
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1574#issuecomment-6651074254 (fact sheet: `spark_utils.py:1172` regex, `:1175-1176` driver mkdir, callers)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1574#issuecomment-6651074254
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1574#issuecomment-6651074254
Hostile-review-artifact: plans/hostile-review-1574-staging-paths.md

## Ticket-fitness exemption

### #1574

Reason: #1574 predates the canonical ticket template; it was filed before `evaluate-ticket.sh` gating.
Evidence: Problem, Evidence, Failure scenario, Done when, Assumptions and Falsifier sections live in https://github.com/siege-analytics/siege_utilities/issues/1574; the reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1574#issuecomment-6256250477.
Falsification: revert the implementation; `tests/test_atomic_write_with_staging_hadoop_fs.py::test_promotes_output_on_spark_filesystem` goes red because promotion inspects the driver's local disk and the real destination stays empty, and `tests/test_atomic_write_with_staging_hadoop_fs.py::test_unique_staging_directory_authority_less_uri_creates_no_local_tree` goes red because a local `dbfs:` tree appears under the test cwd.

## Assumptions

1. Hadoop reads a leading `name:` (two or more characters) as a scheme, so the helper should treat the same strings as URIs and never create them on the driver.
2. Reviewer option (b) keeps local callers working: `TestCreateUniqueStagingDirectory` builds staging dirs in local temp paths and expects them to exist.
3. A URI with no authority or non-root path has no sensible staging parent; raising is better than returning `s3a:/staging_...`.

## Test plan

- Red before (at `245969d6`): the authority-less drop-in (3 cases) and the empty-URI cases (4) -> 7 failed; the 3 authority-less cases created local `dbfs:`, `hdfs:` and `file:` trees under the test cwd.
- After the fix: `tests/test_atomic_write_with_staging_hadoop_fs.py tests/test_distributed.py tests/test_public_api_surface.py` -> 415 passed, 2 failed. The 2 failures are macOS temp-path spellings (`/private/tmp` vs `/tmp`) in `TestHDFSConfigMethods.test_get_cache_path` and `TestAbstractHDFSOperationsInit.test_sets_up_cache_paths`; `git diff origin/develop` over `hdfs_config.py`, `hdfs_operations.py` and `tests/test_distributed.py` is empty, so they are pre-existing and environment-specific.
- Edge cases: `C:/staging` stays local; a URI in a `pathlib.Path` raises; `s3a://`, `dbfs:`, `hdfs:/`, `file:///` raise.

## Peer review

- Shelves: writing-tests:1 (red before on the filesystem side effect, not only the returned string), writing-tests:2 (edge and negative cases), writing-claims:2 (counts carry `Verified-by:`); siege-utilities SU-2 (summary, `base_path`, Raises and Notes describe the driver-local mkdir).
- Syntax check: `py_compile` on 2 changed `.py` files -> all parse clean (exit 0).
- Test suite: 415 passed with the 2 pre-existing macOS-only failures above.
- Findings: `atomic_write_with_staging` is untouched apart from a docstring cross-reference; the Hadoop-FS promotion tests pass unmodified.
- Notebook API: no notebook calls `create_unique_staging_directory` (grep of `notebooks/` finds nothing). Doc build N/A.

## Lead review

- Both path shapes from the review are handled: authority-less URIs return strings with no local tree, and the scheme-less driver-local behavior is stated in the summary, `base_path`, Notes and CHANGELOG.
- The hostile review's follow-ups (Path-held URIs, error text, lenient test, cross-reference, colon rule) were all applied before commit.
- Post-mortem: not applicable. The defect was caught by review before merge; no published version carried it.
- Residual: no live cluster was available, as in earlier rounds; the helper makes no Hadoop calls, so the fakes and string tests cover it.

## Quantified claims

- 7 red at `245969d6`; 415 passed after (plus 2 pre-existing macOS-only failures).

## Rework ledger

5 follow-ups from the hostile review applied before commit.
