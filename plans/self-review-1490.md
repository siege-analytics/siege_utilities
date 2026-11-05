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

## Findings
F1 fixed and the legacy tests aligned. No new findings.

## Ticket-fitness exemption

Governing ticket: #1490. The #1398 epic is context only.

### #1490
Reason: #1490 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier / Related instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1490 states the rejected-credential, IPv6 and file-path defects under "## Problem", the citations under "## Evidence" (`config/models/database_connection.py`, `siege_utilities/configs/`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1490#issuecomment-6259731280.
Falsification: revert the implementation; `tests/test_1490_database_connection_validation.py::test_shipped_default_connections_construct` goes red because the shipped `default_postgres` password `password` and the `default_duckdb` file connection are rejected, and `::test_rejected_server_assignment_leaves_connection_unchanged` goes red because a rejected `host=''` stays on the object.
Falsification verified 2026-11-05 for `siege_utilities/config/models/database_connection.py`:
- From develop `dc7d3f76`, the two named tests gave 8 failed / 0 passed. At develop the assignment cases fail earlier: the shipped postgres defaults are rejected at construction.
- From the pre-F1 head `f5f84c71`, the 6 assignment cases failed on the post-rejection state assertion, and the 2 shipped-default cases passed.
- With the file restored from the PR head, the whole file gave 91 passed, and the worktree was clean.
