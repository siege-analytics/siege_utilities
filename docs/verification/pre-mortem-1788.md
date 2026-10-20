---
propagation-deferred: "Repo-resident pre-mortem for PR #1788 (#1672) CI fix; travels with the PR."
---

# Pre-mortem — #1788 test-scope CI fix (#1672)

## What / Context
test_geo_notebook_group ran under only requires_gdal, so the ordinary offline lane
executed the unmocked geo group and 01_boundaries hit real TIGER -> BoundaryFetchError.

## Approach
Add @pytest.mark.integration so the ordinary lane excludes it; it still runs under
-m integration. Offline mocked coverage is provided separately by #1783.

## Risks
### R1: default-lane geo-group coverage removed
Severity: low — intended; the group needs network, and #1783 covers it offline with mocks.

## Severity
Overall: low. Test-only; no library/notebook behavior change.

## Launch readiness
Red-first: default lane selects 6 geo-group params. Green: default 0, integration 6,
content tests 5 passed. No tiger.
