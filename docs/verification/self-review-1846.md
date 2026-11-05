# Self-review: CRM connector cluster (#1846)

Scope: PR #1846 at work commit `681d28a5` (head `fce16051` is an empty marker
commit). This file adds the in-repo self-review and the ticket-fitness
exemption. It changes no connector code.

## Assumptions

Domain(s): software engineering (CRM connectors, credential redaction,
exception contracts).
Goal source: the eight linked tickets (#1417, #1425, #1426, #1427, #1428,
#1429, #1431, #1436) and the successive merge-gate reviews recorded in the PR
body, including the R-1846-7a retry_after amendment.
Base: merge base `7f534f6c` with develop; the branch is additive (no rebase,
force-push or merge).
Working as: software engineer (Junior) and tech lead (Lead); both reviews are
below.

## Peer review

- Redaction boundary: `_SecretRedactionMixin.__init_subclass__` wraps every
  public connector callable it enumerates, including `__init__`, coroutines,
  generators, async generators and property, classmethod and staticmethod
  descriptors. `tests/test_1846_r6_enumerate_boundary.py` checks the wrapping
  by enumeration.
- Strict short or failed credential policy: diagnostics carry a trusted
  constant (class name plus a validated HTTP status), never message text, and
  the logger emits the fixed constant whether or not the record has args.
- Metadata: one fail-closed read; a status is kept only when its type is
  exactly `int` in 100-599; a `retry_after` is kept only when its type is
  exactly `int` or `float` and it is non-finite or non-negative (R-1846-7a).
  Originals are never copied back onto the rebuilt error.
- Requests: the four connectors import `requests` inside
  `try/except ImportError`, set `REQUESTS_AVAILABLE`, and raise an actionable
  `ImportError` from the constructor when it is false.
- Request construction is unchanged, so outgoing bodies, headers and URLs are
  byte-identical.

## Lead review

The PR closes the credential-echo seams found by successive rounds of independent
review at one boundary rather than site by site. The remaining risks are
stated in the PR body: a constructor that inlines a caller-passed secret into
a pre-registration message is a documented limit, and an exact-head review of
`681d28a5` (including the R-1846-7a delta) is pending. The 30 scanner findings
at `fce16051` are listed in the PR body with a disposition each; none is a
reachable credential leak. No findings block this documentation commit.

## Ticket-fitness exemption

The governing tickets below were written before the current evaluate-ticket
structure. #1398 is the parent epic and is context only. Each exemption covers
ticket structure only, not the Done-when content.

- **#1417** (retries, 429 handling, `$batch` failures). Reason: legacy
  Problem / Evidence / Done-when / Falsifier shape. Evidence:
  `tests/test_1417_crm_retry_idempotency.py`, 59 passed at `fce16051`; each
  Done-when item maps to a test in the PR body's Done-when table.
  Falsification: any of those tests fails at the head, or a Done-when item has
  no mapped test.
- **#1425** (missing values in `to_crm_*`). Reason: legacy shape. Evidence:
  `tests/test_1425_crm_missing_values.py`, 135 passed at `fce16051`.
  Falsification: a test fails at the head, or a Done-when item has no mapped
  test.
- **#1426** (canonical mapping: Zoho lookup ids, probability scale, Dynamics
  industry). Reason: legacy shape. Evidence:
  `tests/test_1426_crm_canonical_mapping.py`, 27 passed at `fce16051`.
  Falsification: as above.
- **#1427** (Dynamics `create_record` id). Reason: legacy shape. Evidence:
  `tests/test_1427_dynamics_create_record_id.py`, 34 passed at `fce16051`.
  Falsification: as above.
- **#1428** (Salesforce `get_objects` casing and relationship paths). Reason:
  legacy shape. Evidence: `tests/test_1428_salesforce_getobjects_casing.py`,
  19 passed at `fce16051`. Falsification: as above.
- **#1429** (pagination). Reason: legacy shape. Evidence:
  `tests/test_1429_crm_pagination.py`, 23 passed at `fce16051`.
  Falsification: as above.
- **#1431** (authorization URL encoding). Reason: legacy shape. Evidence:
  `tests/test_1431_crm_authorization_url.py`, 3 passed at `fce16051`.
  Falsification: as above.
- **#1436** (token lifecycle). Reason: legacy shape. Evidence:
  `tests/test_1436_crm_token_lifecycle.py`, 84 passed at `fce16051`.
  Falsification: as above.
- **#1463** (`SparkEngine.nearest`). Reason: legacy Problem / Evidence shape,
  and this PR does not implement it; the PR body mentions #1463 only because
  the develop CHANGELOG sync copies its entry. Evidence: the compare
  `develop...fce16051` lists no file under `siege_utilities/engines/`.
  Falsification: an `engines/` file appears in the PR diff, or the PR claims
  to close #1463.

## Test plan

- At `fce16051`, Python 3.11.11: `tests/test_1846_r6_hostile.py` (136),
  `tests/test_1846_r7a_retry_after.py` (16) and the eight ticket suites above
  (384) ran as 536 passed, 0 failed.
- `scan.sh --pr 1846` at `fce16051`: exit 1, 30 findings, each listed with a
  disposition in the PR body.
- This commit adds one Markdown file, so syntax, import and notebook gates are
  N/A.
