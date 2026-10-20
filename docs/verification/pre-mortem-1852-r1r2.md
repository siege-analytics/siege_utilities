---
propagation-deferred: "Repo-resident pre-mortem for PR #1852 re-review R1/R2; travels with the PR."
---

# Pre-mortem — PR #1852 scoped re-review R1/R2 (#1398)

## What / Context
snug-coral re-review FAIL @46f4b882: R1 the B1 helper relabeled a geometry join
key's CRS from the right input (last-writer-wins); R2 the B2 cleanup left the
first temp view registered when the second registration failed.

## Approach
R1: in `_merge_geometry_crs`, a column in `on_cols` takes only the LEFT CRS; the
right is skipped. R2: register views inside the try, track them in `registered`,
and drop every registered view on any exception before re-raising.

## Risks
### R1a: dropping the right key CRS loses legitimate metadata
Severity: low -- for a coalesced join key the surviving value is the left key
(develop parity); non-key right geometry keeps its CRS under the suffix.
### R2a: the success path double-drops or loses views
Severity: low -- views are dropped only on the exception path; the success path
returns the lazy frame with its views (16 retained views are the #1854 follow-up).

## Severity
Overall: medium. Shared engine abstraction; CRS provenance + resource lifecycle. No
credentials/branch/deploy.

## Launch readiness
R1 direct check green (left CRS kept for right=3857/None); R2 native-Sedona SZSH
test_1479 14 passed; test_1497 33 passed. Reviewer red @46f4b882 documented. No tiger.
