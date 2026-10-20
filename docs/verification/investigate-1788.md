---
propagation-deferred: "Repo-resident investigation for PR #1788 (#1672) CI fix; travels with the PR."
---

# Investigation — #1788 test-scope CI fix (#1672)

Source of record: the fair-bobcat exact-head review (#1788 TEST-SCOPE FAIL) plus
local collection-only reproduction.

### Verified Shapes
- PROBED: test_1672_gazetteer_notebook_truth.py::test_geo_notebook_group
  parametrizes over notebook_runner.NOTEBOOK_GROUPS['geo'] under only
  @pytest.mark.requires_gdal. `pytest --collect-only` in the default lane
  (pytest.ini addopts `-m "not integration"`) selects all 6 geo-group params,
  including 01_boundaries, whose cell runs a real TIGER get_boundary('state').
  Offline that raises BoundaryFetchError.
- ATTESTED: the fair-bobcat review reproduced BoundaryFetchError (1 failed, 10
  passed) in a network-disabled exact-head run at a1752350.

### Findings
- F-1788 (high): mark test_geo_notebook_group @pytest.mark.integration so the
  ordinary offline lane excludes it; it still runs under -m integration. The
  offline mocked geo-group run is provided separately by #1783.
