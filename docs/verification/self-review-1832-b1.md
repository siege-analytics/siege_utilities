# Self-review — PR #1832 B1832-1 (#1460) (Tier C)

Review-Tier: C (P0 credential-redaction / confidentiality: the sensitive-field export path).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering; security (credential redaction).
Geospatial cross-cut: no.
Goal source: fresh-surge hostile review of PR #1832 (B1832-1 P0 FAIL @ee882655) + hub FINAL.
Plan reference: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/plans/pre-mortem-1832.md
Pre-author-inventory: docs/verification/investigate-1832-b1.md (its ### Verified Shapes inventories the at-ee882655 _strip_sensitive_fields truthiness branches, _convert_to_yaml_safe unwrap, develop parity, and the alias helper)
Investigate-artifact: docs/verification/investigate-1832-b1.md
Pre-mortem-artifact: docs/verification/pre-mortem-1832-b1.md
Hostile-review-artifact: sessions/261019-fresh-surge/data/SU-1832-hostile-review.md (P0 FAIL @ee882655; this commit addresses B1832-1; fresh-surge re-reviews via the steward at the new SHA).
Project-contribution: closes a P0 plaintext-credential leak in the entity export path so a SecretStr inside a falsey sensitive container can never reach to_dict/to_yaml/export_entities(exclude_sensitive=True) as plaintext.

## Test plan
- Red-first: the fresh-surge 18-case regression against ee882655 is 12 failed / 6 controls pass. Observed.
- Green: the 18-case regression at head is 18 passed. Observed.
- No regression / 324-export byte-identity: 2386 passed across tests/test_1460_round5/6/7, bypass, actor-types, config-sensitive, person-actor, person-exclude-sensitive (byte-identity + public URL/metadata round-trips), sensitive-path-parity, private-key-names, changelog, reporting/idml export. Observed.

## Peer review (Junior)
- writing-code: one small helper _redact_sensitive_value; no truthiness on models/containers (type checks); scalar emptiness preserves develop parity.
- Credential-safety (K4 / SU-2): a sensitive container always redacts, so no SecretStr reaches _convert_to_yaml_safe in the exclude path; verified no plaintext SENTINEL in any of the 18 cases.
- Audit (rule 3): the alias-aware helper (_sensitivity.field_has_sensitive_name) and _sensitive_name use isinstance / regex / is-None only; no truthiness guards, left unchanged.
- Gate 1 Syntax: `ast.parse` on person.py -> exit 0.
- Gate 2 Test suite: `pytest` the #1460/export/sensitivity files -> 2386 passed; the 18-case regression -> 18 passed (12 red-first on ee882655).
- Gate 3 Doc build: N/A. Gate 4 Notebook API: N/A.

## Lead review (adversarial)
Phase A coherence: the fresh-surge finding (falsey sensitive container returned live, SecretStr unwrapped) maps directly to _redact_sensitive_value and the two rewired branches plus the model_extra guard; no drift.
Phase B verification: did it fix or move the problem? Fixed. A sensitive container is redacted regardless of truthiness, so the leak path is closed, matching develop (which never classified these entry points sensitive). Scalars keep develop-parity emptiness, so the 324-export byte-identity and public round-trips are unchanged (an earlier always-_REDACTED attempt over-redacted falsey scalars and regressed 223 tests; the container/scalar split resolves that).

Post-mortem applicability: N/A -- forward P0 security fix closing a reviewer FAIL, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | nested plain-str repr/log exposure | filed #1856 (Refs #1460), non-blocking. |
| F2 | P3 | computed-field omission in the redaction walker | filed #1857 (Refs #1460), non-blocking. |
| F3 | P3 | scanner coverage-discovery warning on the undecodable-bytes handler | filed #1858 (Refs #1460), non-blocking. |

## Quantified claims
- "12 red / 18 green" -- tests/test_1832_falsey_regression.py on ee882655 vs head.
- "2386 passed" -- the #1460/export/sensitivity suite list with the fix.

## Evidence-predates-work
Artifact: docs/verification/self-review-1832-b1.md, committed in the same additive work commit (self-ancestor). Written post-implementation, pre-push.
