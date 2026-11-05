---
ticket_refs:
  - siege-analytics/siege_utilities#1476: comment posted https://github.com/siege-analytics/siege_utilities/issues/1476#issuecomment-6651033883
---

# Self-review: #1476 / PR #1738, keep the 4.0.0 public signature of create_database_config

Working as: software engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1476#issuecomment-6256890449 (required changes 1 and 2)
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1476#issuecomment-6650945239 (fact sheet: `databases.py:105` vs `v4.0.0:databases.py:59`; contract generator `scripts/contracts/generate_public_api_contract.py:16-19`)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1476#issuecomment-6650945239
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1476#issuecomment-6650945239
Hostile-review-artifact: plans/hostile-review-1476-signature.md

## Ticket-fitness exemption

### #1476

Reason: #1476 predates the canonical ticket template; it was filed during the v4.0.0 remediation wave before `evaluate-ticket.sh` gating.
Evidence: Problem, Evidence, Failure scenario, Done when, Assumptions and Falsifier sections live in https://github.com/siege-analytics/siege_utilities/issues/1476; the reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1476#issuecomment-6256890449.
Falsification: revert the implementation; `tests/test_databases_config_roundtrip.py::test_password_roundtrip_uses_reported_env_var` goes red because a hyphenated config name saves a password reference that loading cannot resolve.

## Assumptions

1. CI's contract job compares `str(inspect.signature(obj))` for public symbols against the latest PyPI release (4.0.0), where `create_database_config` is annotated `port: int`.
2. Narrowing only the annotation leaves runtime behavior identical: `_validate_port` still accepts integers and 1 to 5 ASCII digit strings and rejects everything else.
3. 4.1.0 is held and untagged, so the #1476 note belongs in `[4.1.0]` per the reviewer's correction.

## Test plan

- Red before (at `89e8d749`): `test_create_database_config_keeps_the_4_0_0_public_signature` -> failed (`port: int | str` vs `port: int`).
- After the fix: the same test passes, and `test_digit_string_port_is_still_accepted_at_runtime` pins `jdbc:postgresql://localhost:5432/d` for the string `"5432"`.
- Regression set, after merging develop `dc7d3f76`: `tests/test_databases_config_roundtrip.py tests/test_1476_port_host_injection.py tests/test_database_config.py tests/test_secure_credential_writes.py tests/test_backward_compat.py` -> 338 passed (the reviewer's 336 plus 2 new).
- The exact-head CI `api, security and build` job is the authoritative contract run.

## Peer review

- Shelves: writing-tests:1 (red before, passing after, on the exact string CI compares), writing-claims:2 (counts carry a `Verified-by:` trailer); siege-utilities SU-2 (docstring states the runtime allowance).
- Syntax check: `py_compile` on 2 changed `.py` files -> all parse clean (exit 0).
- Test suite: the 5 modules above -> 338 passed (exit 0).
- Instance or class: compared every public `def` in `config/databases.py` with `v4.0.0`; only `create_database_config` had drifted.
- Findings: `_validate_port` and the injection tests are untouched; no contract-allowlist entry was added.
- Notebook API: no notebook calls `create_database_config` (a grep of `notebooks/` finds nothing). That SU-4a coverage gap predates this PR. Doc build N/A.

## Lead review

- Fixes the contract, not just the test: the signature string is byte-identical to 4.0.0, and the checker is not weakened.
- Post-mortem: not applicable. The contract failure was caught by CI and review before merge; no published version carried it.
- Residual: strict type checkers will flag callers that pass string ports, which is documented. Widening the annotation would need a major version.

## Quantified claims

- 338 passed in the database config regression set; 1 red-before signature failure at `89e8d749`.

## Rework ledger

1 self-caught test defect: the first runtime test asserted `config["port"] == 5432`, but the config keeps the port as passed; it now asserts the validated JDBC URL.
