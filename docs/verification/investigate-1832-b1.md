---
propagation-deferred: "Repo-resident investigation for PR #1832 B1832-1 (#1460); travels with the PR."
---

# Investigation — PR #1832 B1832-1 falsey sensitive-container leak (#1460)

Source of record: the fresh-surge hostile review
(sessions/261019-fresh-surge/data/SU-1832-hostile-review.md, P0 FAIL @ee882655)
and its 18-case test_falsey_regression.py, plus a develop-parity read and
red-first replay.

### Verified Shapes
- PROBED: person.py _strip_sensitive_fields used `_REDACTED if value else value`
  for a sensitive model field (:674) and a sensitive mapping key (:685).
  _convert_to_yaml_safe (:612) unwraps SecretStr via get_secret_value(). PR #1832's
  alias/bytes-key classification routes a falsey nested CredentialBundle (a model
  whose __len__ is 0 but which holds a SecretStr) into the sensitive branch; being
  falsey it is returned live and then unwrapped to plaintext. Reproduced: the
  fresh-surge 18-case test is 12 failed / 6 passed on ee882655.
- PROBED: develop (f236eac7) has the identical `_REDACTED if value else value`
  but never hits it for these cases because its classifier does not treat
  bytes-keys/aliases as sensitive, so they fall to the safe recursion branch.
- PROBED: the alias-aware helper _sensitivity.field_has_sensitive_name and
  _sensitive_name use isinstance / regex / is-None only -- no truthiness guard.

### Findings
- B1832-1 (P0): remove truthiness from the sensitivity path; a sensitive
  container must redact regardless of truthiness while scalars keep develop-parity
  emptiness. Verified: 18 green at head, 2386 passed across the export suites.
- Non-blocking follow-ups (filed, Refs #1460): #1856 nested plain-str repr/log
  exposure; #1857 computed-field omission in the redaction walker; #1858 scanner
  coverage-discovery warning on the undecodable-bytes handler.
