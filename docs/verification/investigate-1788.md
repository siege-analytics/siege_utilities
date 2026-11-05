---
propagation-deferred: "Repo-resident investigation for PR #1788 (#1672); travels with the PR."
---

# Investigation: #1788 natural-language geometry notebook honesty (#1672)

Sources of record: the exact-head reviews recorded on PR #1788 and ticket #1672, the regression tests in `tests/test_1672_gazetteer_notebook_truth.py`, and a local run of the geo notebook group.

### Verified Shapes
- PROBED: `notebooks/spatial/07_natural_language_to_geometry.ipynb` did not tie place resolution and directional labels to the queried fixture; the regression tests guard distinct geometries and the Lake Geneva reference. The notebook now resolves the two names to distinct illustrative fixtures, rejects unknown place names, and labels directional results against the queried fixture's centroid. The Lake Geneva fixture joins Grand Lac and Petit Lac boxes so the south-shore towns fall south of its centroid.
- PROBED: `tests/test_1672_gazetteer_notebook_truth.py` has 11 collected cases. Five run offline (`-m "not integration"`): distinct geometries, unknown-name rejection, two south-shore town checks, and the directional reference check. Six are the parameters of `test_geo_notebook_group`, one per notebook in the geo group (`01_boundaries`, `02_geocoding`, `03_choropleth_maps`, `04_redistricting`, `05_multi_source_joins`, `07_natural_language_to_geometry`), marked `integration` and `requires_gdal` because `01_boundaries` fetches real TIGER boundaries over the network.
- PROBED: in `.github/workflows/ci.yml` the main test job runs `-m "not integration and not postgis"`, and the only explicit integration command targets `tests/test_files_remote_tls.py`. So no workflow job executes the six integration-marked parameters. Offline, network-mocked coverage of the geo group exists on `develop` through the #1667 change.
- PROBED: running the six parameters with `-m integration -v` on the synced tree executed all six and each reported PASSED (details in the self-review).
- ATTESTED: the independent reviews flagged the release-note placement, a stale description, a self-review that claimed a network job runs the group, and the unexecuted parameters.

### Findings
- F-1788a (high): six collected is not six executed. This PR provides a local run of all six; a workflow that runs them would be a separate change and is not made here.
- F-1788b (medium): the `#1672` release note belongs in the `[4.1.0]` section of `CHANGELOG.md`.
- F-1788c (medium): the description and self-review must not claim a network job runs the group.
