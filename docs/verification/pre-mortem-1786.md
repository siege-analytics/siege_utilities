---
propagation-deferred: "Repo-resident pre-mortem for PR #1786 (#1671) prose fix; travels with the PR."
---

# Pre-mortem — #1786 prose-scanner fix (#1671)

## What / Context
spatial/06_geodjango.ipynb used em-dashes (U+2014), a prose-scanner violation
(line 22 per the review).

## Approach
Rewrite the em-dashes to ASCII punctuation via NotebookEdit; preserve the
markdown-only (0 code cells) schematic content.

## Risks
### R1: semantic change
Severity: low — only punctuation changed; meaning preserved; 0 code cells kept.

## Severity
Overall: low. Prose-only; no code behavior change.

## Launch readiness
Red-first grep 3 em-dashes; green 0, notebook valid, test_1671 4 passed. No tiger.
