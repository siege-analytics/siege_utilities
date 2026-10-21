---
propagation-deferred: "Repo-resident pre-mortem for PR #1832 B1832-1 (#1460); travels with the PR."
---

# Pre-mortem — PR #1832 B1832-1 (#1460)

## What / Context
A falsey nested sensitive container was returned live by _strip_sensitive_fields
and its SecretStr unwrapped to plaintext by _convert_to_yaml_safe
(to_dict/to_yaml/export_entities, exclude_sensitive=True). P0 confidentiality.

## Approach
_redact_sensitive_value: no truthiness; redact a BaseModel/dict/list/tuple/
dataclass regardless of truthiness; redact a present scalar and keep an empty/None
scalar (develop parity). model_extra guard -> is not None. Audit the alias helper.

## Risks
### R1: over-redaction of falsey scalars
Severity: high -- mitigated: scalars keep develop-parity emptiness; 2386 passed
including the 324-export byte-identity.
### R2: residual leak
Severity: high -- mitigated: sensitive containers always redact, so no SecretStr
reaches the YAML walker in the exclude path; 18-case regression green.

## Severity
Overall: high (P0 credential redaction).

## Launch readiness
Red-first 12/18 on ee882655; 18 green at head; 2386 passed. No tiger.
