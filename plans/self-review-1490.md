---
ticket_refs:
  - siege-analytics/siege_utilities#1490: comment posted
---

# Self-review: #1490 / PR #1808 (DatabaseConnection validation by type)

## Assumptions
Domain(s): software engineering, configuration models (pydantic v2)
Goal source: #1490 (shipped default connections fail validation)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1490#issuecomment-6651468896
Review being answered: https://github.com/siege-analytics/siege_utilities/issues/1490#issuecomment-6259731280 (exact-head review of 4116f50f: F1, CI, process)
Owner review: PR #1808 review 5566197235 (align the legacy password-policy tests)
Pre-author-inventory: the Investigation section of the plan reference above

## Scope of this round
F1: with `validate_assignment=True`, pydantic installs an assigned value before
`model_validator(mode='after')` checks the server requirements, so a rejected
assignment left the object mutated. `DatabaseConnection.__setattr__` now
snapshots the field's current value and `__pydantic_fields_set__`, delegates
to pydantic, and restores both on `ValidationError` before re-raising. Only
declared model fields take this path. A field-level rejection never installs
the value, so the restore is a no-op for it.

Legacy tests (owner review): the five password-policy tests in
test_config_model_validation.py become one parametrized test asserting that
each former case loads, stays wrapped and stays redacted, plus an
empty-server-password error test. The hydra weak-password test asserts a
redacted load. In test_config_secret_repr.py, the DatabaseConnection overlong,
composition and byte cases become accepted-and-redacted tests. The nested
Person/ClientProfile error tests now fail on an invalid host with the
sentinel password still present. The assignment case asserts that the stored
password is accepted and stays wrapped, and that a rejected `host=''`
assignment echoes nothing and changes nothing.

## Peer review (the Junior's checklist)

### writing-code
- Severe flake8 on the changed files -> no output.
- `scripts/check_exception_contracts.py` -> 207 flagged, 0 unlisted, 0 stale. The new handler re-raises.
- `scripts/check_secret_repr.py` -> PASS, 0 violations; `scripts/check_secret_literals.py` -> PASS, 0 violations.
- `scripts/check_test_file_hygiene.py` -> PASS.

### writing-tests
- Red at f5f84c71 (new tests, old model): pytest -> 23 failed, 312 passed across
  test_1490 + config_model_validation + hydra_integration + config_secret_repr.
  That is 8 new F1 state tests plus the 15 legacy policy assertions. The
  field-level, accepted-assignment and no-echo controls pass before and after.
- After the fix: pytest -> 458 passed (those four files + smoke + runtime_guard
  + sql_safety). test_person_exclude_sensitive + test_config_sensitive_fields -> 1599 passed.

### writing-claims
- The counts are pytest summary lines from this work cycle.

## Lead review
Pydantic v2 documents that after-validators see the already-assigned model.
The override uses only `__dict__` and `__pydantic_fields_set__`, both stable on
BaseModel. The SecretStr object is restored as-is, so redaction is unchanged.
Blast radius: one model class and its tests. No notebook constructs
`DatabaseConnection`. A grep over notebooks/ finds only a prose mention in
a markdown cell of `foundations/01_configuration.ipynb`.

## Rework ledger
- 4116f50f/f5f84c71: rejected assignments mutated the object, and the legacy policy tests were left red. Both are fixed in this round.
- The 4.1.0 note is restored to CHANGELOG.md and mentions the assignment guarantee.
- Pre-flight (2026-11-10). Develop sync: `08c190b4` merges develop `71f02b0b` for a positional CHANGELOG conflict (the #1444 and #1490 Fixed entries). Both are kept, a diff against develop deletes 0 develop lines, and no merged develop behaviour disagrees with this PR. Classification follows the operator rule (2026-11-06): a change that alters v4.0.0 caller behaviour is BREAKING. On the v4.0.0 tag, `validate_password` required at least 8 characters, an uppercase letter, a lowercase letter and a digit, and rejected common passwords, with `validate_assignment=True`. Removing that policy means code that relied on the rejection now behaves differently. That part moves to 4.1.0 BREAKING with a **Migration:** line. The coordinator withdrew its 11-06 "not BREAKING" ruling for this reason. IPv6 hosts, file paths and credential-free file connections stay under Fixed, because they only accept inputs v4.0.0 wrongly rejected. No code changed.

## Findings
F1 fixed and the legacy tests aligned. No new findings.

## Ticket-fitness exemption

Governing ticket: #1490. The #1398 epic is context only.

### #1490
Reason: #1490 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier / Related instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1490 states the rejected-credential, IPv6 and file-path defects under "## Problem", the citations under "## Evidence" (`config/models/database_connection.py`, `siege_utilities/configs/`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1490#issuecomment-6259731280.
Falsification: revert the implementation; `tests/test_1490_database_connection_validation.py::test_shipped_default_connections_construct` goes red because the shipped `default_postgres` password `password` and the `default_duckdb` file connection are rejected, and `::test_rejected_server_assignment_leaves_connection_unchanged` goes red because a rejected `host=''` stays on the object.
Observed revert results (2026-11-05). Command, with `REV` set to the revert target:
`git checkout REV -- siege_utilities/config/models/database_connection.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1490_database_connection_validation.py::test_shipped_default_connections_construct test_1490_database_connection_validation.py::test_rejected_server_assignment_leaves_connection_unchanged); git checkout HEAD -- siege_utilities/config/models/database_connection.py`
- `REV=dc7d3f76` (develop): 8 failed, 0 passed. At develop the assignment cases fail earlier: the shipped postgres defaults are rejected at construction.
- `REV=f5f84c71` (pre-F1 head): 6 failed, 2 passed. The 6 assignment cases fail on the post-rejection state assertion; the 2 shipped-default cases pass.
- Current-head green: after the file was restored, `(cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1490_database_connection_validation.py)` gave 91 passed. The worktree was clean.

## Current integration round (develop 6c049c2c), Tier C local gate

Appended 2026-11-13 for the merge of develop `6c049c2c` into head `44dba809`. The sections above are frozen history and are left unchanged; their "4.1.0" wording predates develop's rename of the release section to 5.0.0.

Working as: software engineer (release integration), tech lead (merge review)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1490#issuecomment-6799999766 (Investigation Fact Sheet section, posted 2026-11-11 15:32:09Z for the first staging of this integration)
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1490#issuecomment-6799999766 (Pre-Mortem section, same comment)
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1490#issuecomment-6800152944 (independent Senior adversarial review by a fresh-context reviewer, with responses; posted 2026-11-11 15:38:36Z, 11250 characters)

The local review gate for this round is Tier C. The PR's own change is a configuration model, but the merge brings in develop's `.github/workflows/ci.yml` and `.github/actions/apt-install/action.yml`, which raise the whole-tree classification to C.

### History: voided first staging (develop 79f37f4d)
On 2026-11-11 this integration was first staged against develop `79f37f4d` (staged tree `d3e6baed`, CHANGELOG blob `e6430e97`) and was never committed. Before any commit, #1791 landed on develop as `6c049c2c`. It adds the #1404 Census dual-source bullet at the same BREAKING anchor, so the earlier staging would have conflicted with the new develop. That staging was aborted after a verified backup of the worker-authored self-review blob, and the merge was redone against `6c049c2c`. The plan, investigation, pre-mortem and independent review linked above were written for the first staging; the method is unchanged, and develop's BREAKING block now also includes the #1404 bullet.

### Scope of the integration round
The only path both sides changed since the merge base `71f02b0b` is `CHANGELOG.md`. Both sides inserted bullets at the top of the `[5.0.0]` Fixed and BREAKING lists. Under Fixed, develop's 3 bullets (#1882, #1458, #1474) come first, followed by the #1490 bullet. Under BREAKING, develop's 3 social bullets and the #1404 Census bullet come first, followed by the #1490 bullet with its Migration note. Each of the two conflicts was resolved by deleting the three marker lines and placing develop's block above this PR's block, with no other byte changed. No #1490 code or test changed in this round. The rerere cache held no earlier resolution: the merge printed "Recorded preimage for 'CHANGELOG.md'" and no "Resolved ... using previous resolution" line.

### Integration checks (writing-claims: each item observed on the 6c049c2c merge)
- `git ls-remote` immediately before the merge gave develop `6c049c2c` and head `44dba809`. MERGE_HEAD is `6c049c2c`.
- Before the hand resolution there were 6 marker lines: 2 hunks, 3 markers each, no base section. The Fixed hunk was 6 PR lines against 33 develop lines; the BREAKING hunk was 9 PR lines against 68 develop lines.
- After resolution: the staged `CHANGELOG.md` blob is `ed7cc59f`, which equals the expected blob; the conflict marker count is 0.
- The staged tree differs from develop `6c049c2c` only on the seven #1490 paths, and from `44dba809` only on develop's changed paths plus this appended section.

### Tests and guards on the 6c049c2c merged tree (writing-tests, writing-code)
Rerun on 2026-11-13 with Python 3.11.11 and hydra-core 1.3.2; `sys.path[0]` was this worktree. None of these results are carried over from the voided staging.
- pytest on the six target modules gave 356 passed, 0 skipped: `test_1490_database_connection_validation`, `test_config_model_validation`, `test_config_secret_repr`, `test_hydra_integration`, `test_config_hydra_optional` and `test_config_models_actor_types_errors`.
- `test_credential_url_guard` gave 115 passed.
- `check_secret_literals` PASS; `check_secret_repr` PASS; `check_credential_urls` reports 0 unreviewed sites; `check_test_file_hygiene` PASS.
- `check_exception_contracts --list`, rerun fresh, reports 0 unlisted and 0 stale.
- `check_lazy_imports` OK, with 8 optional skips (GDAL is not installed locally).
- flake8 with the phase 4 rules on the 5 PR Python files gave no output.
- Not run locally, and left to hosted CI:
  - the lint ratchet scripts, because no `flake8` executable is on PATH;
  - the exception-contract guard self-test;
  - bandit, which is not installed;
  - the public API contract comparison, which needs CI-built baseline and candidate contracts. #1791 changed its allowlist, and this PR does not touch the public API.
- The GitGuardian check on the PR is still failing. This round takes no provider, fixture, credential or history action on it.
