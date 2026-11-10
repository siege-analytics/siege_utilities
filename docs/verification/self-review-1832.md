# Self-review: PR #1832 sensitive-field redaction bypasses (#1460), integration round

Review-Tier: C (credential redaction in config exports).

## Assumptions
Working as: software engineer (Junior) and security-minded tech lead (Lead).
Domain(s): software engineering (Pydantic config models, export redaction).
Geospatial cross-cut: no.
Goal source: the #1460 Done-when and the reproduction requirements quoted in the PR #1832 body. Code at cf9eefa1 has an independent exact-head PASS on code (recorded in the PR body). This round is integration only: develop sync, canonical CHANGELOG.md note, this artifact, exact-head CI. No library behavior changes.
Plan reference: docs/verification/self-review-1832.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1832.md#investigation
Investigate-artifact: docs/verification/self-review-1832.md
Pre-mortem-artifact: docs/verification/self-review-1832.md
Hostile-review-artifact: PR #1832 body, section "Verification at cf9eefa1": an independent exact-head review PASS on code with 91 boundary cases, where restoring only the previous person.py fails 38. Re-review of the integration head is pending; this is NOT a pass of it.
Project-contribution: closes the two remaining P0 redaction bypasses (credential aliases and non-string keys) and the falsey-value leaks, so `exclude_sensitive=True` exports contain no secret values.

## Investigation
- PR files (10): `siege_utilities/config/models/_sensitivity.py`, `siege_utilities/config/models/person.py`, `tests/test_1460_sensitive_field_bypass.py`, five `tests/test_1832_*.py` modules (renamed by behaviour in the pre-flight round below), `tests/test_config_hydra_optional.py`, `tests/test_config_sensitive_fields.py`.
- At cf9eefa1, CHANGELOG.md had no #1460 entry; the note lived only in the PR body. The owner's criteria on #1484 (issuecomment-6649267710) state that a PR-body note alone is not the adopted release-note location.
- GitHub reported the branch BEHIND develop dc7d3f76. A local three-way merge conflicted only positionally in CHANGELOG.md, against develop's #1463 entry.
- The redaction decision sites are unchanged: `person.py` `_redact_sensitive_value`, `_strip_sensitive_fields`, `_convert_to_yaml_safe`; `_sensitivity.py` `field_has_sensitive_name`.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The develop merge alters redaction code through an auto-merge. Mitigation: `git diff cf9eefa1` on the PR's production and test paths is empty after the merge, and the tree differs from develop only in the 10 PR files.
2. Paper Tiger. Severity: P2. The CHANGELOG entry conflicts with develop again. Mitigation: placed at the end of `[4.1.0]` / `### Fixed`, away from develop's new entries.
3. Paper Tiger. Severity: P2. The PR body goes stale ("no CHANGELOG.md diff"). Mitigation: those sentences are updated.
4. Elephant. Severity: P3. Hosted CI fails only the known DuckDB 2.0 tests until the pin lands (#1861/#1863). Labelled, not chased.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (fail-closed redaction is unchanged). Release-note discipline: the canonical CHANGELOG.md entry now matches the PR body block and also states the identity-only rule from cf9eefa1.
- Gate 1 (syntax): no Python changed in this round; pytest imported every PR module -> 2455 passed.
- Gate 2 (tests): pytest on the merged tree -> 2455 passed across the required four-file command, the #1460 round 5/6/7 security suites, the five #1832 modules, the Hydra probe and the changelog tests.
- Gate 3 (guards): lint ratchet phases 1 to 4 against develop dc7d3f76 (recorded in the PR body for this head).
- Gate 4 (docs/notebooks): CHANGELOG.md only; no notebook call sites change.

## Lead review (adversarial)
Phase A coherence: the CHANGELOG text matches the behaviour in `_redact_sensitive_value` and `field_has_sensitive_name` at cf9eefa1, which are unchanged here.
Phase B verification: the merge left the PR files identical to cf9eefa1, so the earlier independent code PASS still applies to the code. Only CHANGELOG.md and this artifact are new.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | Release note only in the PR body | canonical CHANGELOG.md entry added |
| F2 | P3 | Branch behind develop with a positional CHANGELOG conflict | additive merge, develop entry kept |

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11), run from the worktree root, merged tree.
- `python -m pytest tests/test_1460_sensitive_field_bypass.py tests/test_config_sensitive_fields.py tests/test_actor_types_exclude_sensitive.py tests/test_person_actor.py tests/test_person_exclude_sensitive.py tests/test_1460_round5_dropin.py tests/test_1460_round6_dropin.py tests/test_1460_round7_security.py tests/test_1832_empty_builtins_preserved.py tests/test_1832_empty_secret_roundtrip.py tests/test_1832_exact_type_boundaries.py tests/test_1832_falsey_regression.py tests/test_1832_remaining_falsey.py tests/test_config_hydra_optional.py tests/test_release_process.py tests/test_user_config_export_changelog.py --no-cov` -> 2455 passed.
- `git diff --stat origin/develop` -> 10 PR files before this commit; `git diff cf9eefa1` on those paths -> empty.

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket. The #1398 epic is context only.

### #1460
- **Reason:** #1460 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the problem (credential values leaking through `exclude_sensitive=True` exports), the evidence and the done-when criteria live in the #1460 body under `## Problem`, `## Evidence` and `## Done when`. The two reopened bypasses this PR addresses are quoted in the PR #1832 body ("Exemption: ticket-fitness" section). The earlier post-merge verification of #1460 is at https://github.com/siege-analytics/siege_utilities/issues/1460#issuecomment-6194494266. No public reviewer verdict for this PR exists yet; the earlier PASS on code at `cf9eefa1` is recorded in the PR body under "Verification at cf9eefa1". Investigation, pre-mortem and Junior/Senior records are on the ticket at issuecomment-6651153998 and issuecomment-6651203609.
- **Falsification:** revert the implementation (restore `siege_utilities/config/models/person.py` from develop) and `tests/test_1460_sensitive_field_bypass.py::test_alias_field_redaction[alias-nested-to_dict]` goes red, because a field aliased `client_secret` keeps its dummy value in the `to_dict` export instead of being redacted. `test_non_str_key_redaction[credential-bytes-nested-to_dict]` goes red the same way for a `b"access_token"` key. This was verified on 2026-11-05: with develop's `person.py` in place, 96 failed and 125 passed; with the PR's file restored, 221 passed. Reverting `_sensitivity.py` as well makes the module fail to import, because the shared alias helper is new in this PR.

## Pre-flight round on db526ae7 (develop 71f02b0b)
**Develop merge (61cadc8f).** The PR was CONFLICTING. The only conflict was the CHANGELOG 4.1.0 Security position against the #1439 Instagram entry from develop; both entries are kept, develop first. Against develop the merged tree changes only the twelve PR files. No library code changed in this round.

**Review thread 4429112649** (rename the `test_1832_*` files by behaviour, remove the duplicate empty-value case, share the hostile secret stubs). Fixed in the next commit. Test-only; no library change.
- **Renamed** (`git mv`):
  - `test_1832_empty_builtins_preserved.py` → `test_config_redaction_empty_values.py`;
  - `test_1832_exact_type_boundaries.py` → `test_config_redaction_exact_type_boundaries.py`;
  - `test_1832_empty_secret_roundtrip.py` → `test_config_export_empty_secret_roundtrip.py`;
  - `test_1832_falsey_regression.py` → `test_config_redaction_falsey_nested_credentials.py`;
  - `test_1832_remaining_falsey.py` → `test_config_redaction_falsey_values.py`.
  Issue-numbered names are allowed by `scripts/check_test_file_hygiene.py` (develop has 20 such files), so this is a clarity change, not a rule fix; the hygiene check passes either way.
- **Duplicate removed:** the 10-value exact-empty parametrization was a subset of the 11-value one (which adds `-0.0` and a sign check). One test now holds the 11-value version, `test_exact_empty_builtin_is_preserved_with_type_and_sign` in `test_config_redaction_empty_values.py`; the copy in the boundaries file is gone.
- **Shared stub:** `tests/hostile_secrets.py::unwrap_recording_subclass(base, calls)` builds a `SecretStr`/`SecretBytes` subclass whose `get_secret_value()` records each call and unwraps to empty. The direct-call test (now parametrized over `SecretStr` and `SecretBytes`) and the export-surface test in the boundaries file use it, and both assert the secret was never consulted. The round-trip file's direct-call subclass test became an exact duplicate of the direct-call test and was removed, so that file covers only the export→import round trip. The metaclass-masquerade and falsey `__bool__` stubs test different attacks and stay local.
- **Overlap with `test_1460_*`:** `test_1460_sensitive_field_bypass.py` has no exact-empty or secret-subclass cases, so nothing was merged from it.
- **Counts:** the eight #1832 test modules went from 474 to 464 passed, the full self-review list from 2455 to 2445. Every one of the 10 is accounted for:
  - the exact-empty subset replaced by the 11-value version in one place and removed in the other: −10;
  - the direct-call subclass test now covers `SecretBytes` too: +1;
  - the round-trip duplicate removed: −1.

**CHANGELOG classification.** The #1460 Security note documents a behaviour change from 4.0.0: `exclude_sensitive=True` exports redact more fields and values. Under the pre-flight rule, a short BREAKING entry with a Migration line now points to it: read credentials from the live model or a secret store, and note that `import_entities` rejects redacted exports. The Security note itself stays where the canonical-placement rule puts security fixes.

## Rework ledger
Empty.
