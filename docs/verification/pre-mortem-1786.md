---
propagation-deferred: "Repo-resident pre-mortem for PR #1786 (#1671); travels with the PR."
---

# Pre-mortem: #1786 GeoDjango notebook honesty (#1671)

## What / Context
The GeoDjango notebook advertised a copy-pasteable recipe that cannot run, and the notebook guide and notebook test module did not distinguish markdown-only schematics from execution groups. PR #1784 edits the same guide lines for the Spark notebook and is still open.

## Approach
Label the notebook a schematic, document the missing loader and setup, correct the guide, track markdown-only schematics separately in `tests/test_notebooks.py`, add a documentation-contract test, and place the release note in `[4.1.0]`.

## Risks
### R1: overlap with #1784
Severity: medium. Both PRs edit the same guide lines. The shared paragraph and table row are textually identical in both, so a merge of either leaves the other free of a guide conflict. The changelog bullets are adjacent additions and need a trivial additive resolution by whichever PR lands second.
### R2: punctuation regressions
Severity: low. The notebook text uses ASCII punctuation only, and the verification documents do too.
### R3: understating the diff
Severity: low. The self-review lists all five changed files.

## Severity
Overall: low. Documentation, one notebook prose edit and tests; no library behavior change.

## Launch readiness
The documentation-contract test file passes (4 passed) and the geodjango hygiene selection passes (12 passed with the contract tests) on the synced tree. No tiger.
