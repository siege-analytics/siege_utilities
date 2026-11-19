# Self-review: RDH compactness scoring and projection (#1467, PR #1792)

Scope of this artifact: the PR as a whole at its code head 567e743a, plus the process-only commit that syncs with develop, adds the release note to `CHANGELOG.md` under `[5.0.0]` `### BREAKING` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also refreshed.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at an earlier head by the external reviewer.

## Assumptions

- Goal source: ticket #1467. RDH compactness calculations understated circle scores and disagreed between APIs; Reock must use the minimum bounding circle, projection must be a per-district local AEQD, and `compute_compactness` and `compare_plans` must share the scoring.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the earlier approval on the ticket and PR.
- The code diff against `origin/develop` after the sync is `siege_utilities/geo/providers/redistricting_data_hub.py`, `tests/test_1467_rdh_compactness_projection.py` and `tests/test_redistricting_data_hub.py`, plus `CHANGELOG.md` from this commit. The connector files that appeared in the earlier branch diff belong to an unrelated change that is already on develop and no longer appear. This commit adds no library code.
- Release convention: user-visible notes belong in `CHANGELOG.md` under `[5.0.0]`; this behavior change belongs under its `### BREAKING` section. Before this commit the #1467 note existed only in the PR body block; this commit adds it to `CHANGELOG.md` verbatim from that block.
- Out of scope, inherited: the antimeridian handling in the compactness helpers is existing behavior and is not changed here.
- Pre-author-inventory: NONE. Trivial-against-state: after the sync, `git diff origin/develop -- CHANGELOG.md` shows only the #1467 entry as an addition.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_1467_rdh_compactness_projection.py test_redistricting_data_hub.py` -> 137 passed, 6 warnings in 1.90s. The warnings are a shapely deprecation notice for an existing `resolution` argument and an `RDHClient.__del__` message in the existing missing-requests test.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1467 entry under `[5.0.0]` `### BREAKING` exactly once.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. Develop wins on any disagreement, and none exists: no develop change touches `siege_utilities/geo/providers/redistricting_data_hub.py`.

Classification: caller code that worked on v4.0.0 now sees different numbers (the Reock, Polsby-Popper and Schwartzberg scores change for the same districts). The entry already said "Behavior change"; it now sits under `### BREAKING` in `[5.0.0]` with a Migration line, at its own position in the BREAKING list so it does not conflict with the other open PRs. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_1467_rdh_compactness_projection.py test_redistricting_data_hub.py -q` -> 137 passed, 6 warnings in 1.53s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Ticket-fitness exemption

Governing ticket: #1467 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1467 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (RDH compactness scores understating circles and disagreeing between APIs), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1467, and in the PR description, https://github.com/siege-analytics/siege_utilities/pull/1792. The reviewer verdicts are recorded on the ticket thread and the PR conversation.
- **Falsification:** revert the implementation (the `redistricting_data_hub.py` changes of this PR); `tests/test_1467_rdh_compactness_projection.py::test_reock_equilateral_triangle` goes red because the Reock score returns 0.315045 instead of 0.413497. Observed revert run: with `siege_utilities/geo/providers/redistricting_data_hub.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/geo/providers/redistricting_data_hub.py`), `python -m pytest test_1467_rdh_compactness_projection.py::test_reock_equilateral_triangle -q`, run from the tests directory, gave 1 failed, 1 warning in 0.50s (AssertionError on the Reock score). After `git checkout HEAD --` of the file the command gave 1 passed in 0.43s, `test_1467_rdh_compactness_projection.py` with `test_redistricting_data_hub.py` gave 137 passed (6 warnings) on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The change is additive and reverts with one commit. The process commit (documentation and release notes) makes no behavior change; the PR as a whole changes compactness scores and is BREAKING. No claim in this artifact exceeds what was observed.

## Fix round, 2026-11-17: projected districts across the antimeridian

The whole-PR review of head `dfb306f3` failed with one S2: already-projected districts that cross the antimeridian lost their Polsby-Popper, Reock and Schwartzberg scores. The Assumptions entry above that called the antimeridian handling inherited and unchanged was wrong: this PR introduced the regression.

### Cause
`_reproject_geometry` chose the centre of each district's local AEQD by converting the whole ring to EPSG:4326 and taking its planar centroid. A projected ring that crosses the antimeridian becomes, in longitude and latitude, a ring with vertices near +180 and -180 degrees, so that centroid lands far from the district and the AEQD is centred in the wrong place. A valid 50 km circle built in a local AEQD at 179.9E, 52N and stored in EPSG:3338 scored Polsby-Popper 0.9644, Reock 0.7319 and Schwartzberg 0.9821 at `dfb306f3`. v4.0.0 and develop `2c51af86` both scored its projected Polsby-Popper about 0.99996, because they kept projected input as it was.

### Fix
- For a projected source CRS, the centre is the district's planar centroid in that CRS, and only that one point is converted to longitude and latitude. Projected coordinates are continuous across the antimeridian, so the centroid stays inside the district.
- The code path for geographic input is the one #1467 introduced: its centre still comes from the ring in EPSG:4326. Geographic districts that cross the antimeridian are improved over v4.0.0 but still wrong, and are tracked in #1954. For two 10 km disks 30 km either side of longitude 180 at 52N, the delta review measured Polsby-Popper 0.482 and Reock 0.091 here against a true 0.5 and 0.125 (v4.0.0 and develop: 0.237 and about 1e-6). The convex hull ratio, the Reock bounding circle and the plan APIs are unchanged.

### Tests (`tests/test_1467_rdh_compactness_projection.py`, 27 new)
- A 50 km circle built in its own local AEQD (the planar truth, about 1 for every metric) and stored in a projected CRS, for three districts across the antimeridian: 179.9E and 179.9W at 52N in Alaska Albers (EPSG:3338), and 180 at 17S in Pacific Mercator (EPSG:3832).
- Each district for Polsby-Popper, Reock and Schwartzberg through the scalar functions with `source_crs`, `compute_compactness` and `compare_plans` (both plan summaries and the zero delta): 3 x 3 x 3 = 27.

### Results
- Red on `dfb306f3`: the 27 new tests failed. The review's reproducer, run in the worktree as a byte copy with byte copies of its frozen develop and v4.0.0 modules, failed its 9 metric and API cases and passed its 2 controls. The existing tests passed.
- After: the review's reproducer passed 11 of 11. `tests/test_1467_rdh_compactness_projection.py` passed 60 (33 existing and 27 new). With the RDH client, atomic download, silent-wrong-data, chamber, selection, redistricting model, credential URL leak, release, changelog and exception contract site tests: 642 passed.
- Not counted: the two import tests in `tests/test_redistricting_models.py` and the whole of `tests/test_rdh_precinct_loader.py` import the GeoDjango models, which need the GDAL C library, and this machine has none (`ImproperlyConfigured: Could not find the GDAL library`). They do not touch the compactness code. The `RDHClient.__del__` warning in the missing-requests test also appears at `dfb306f3`.
- `ruff check --select F,E9`: no findings. Exception-contract scanner: 0 unlisted, 0 stale. Test-file hygiene: pass.
- The reproducer and the frozen modules were removed from the worktree before staging.

## Second fix round, 2026-11-17: only projected sources use their own centroid

The delta review of the first fix round's staged tree `9e34375b` failed with one S2: the fix treated every source that is not geographic as projected.

### Cause
The first fix took the local AEQD centre from the district's centroid in its source CRS whenever the source was not geographic. A geocentric source (Earth-centred XYZ, EPSG:4978) is neither geographic nor projected, and its XY centroid ignores the Z axis, which carries the latitude. A valid 50 km circle at 150W, 61N stored in EPSG:4978 was centred at about 150W on the equator and scored Polsby-Popper 0.9858, Reock 0.8223 and Schwartzberg 0.9929 instead of about 1. At `dfb306f3`, which converted the whole ring to longitude and latitude for every source, it scored about 1 for all three; the delta review measured v4.0.0 and develop at Polsby-Popper 0.99330 for the same input.

### Fix
- The source's own centroid is used only when its CRS is projected (`pyproj.CRS.is_projected`). Every other source, geographic, geocentric or otherwise, takes its centre from the ring converted to EPSG:4326, as at `dfb306f3`. No source is rejected.
- The projected antimeridian fix of the first fix round, the convex hull ratio, the Reock bounding circle and the plan APIs are unchanged.
- Out of scope and still wrong: geographic districts that cross the antimeridian (#1954). This round leaves their path as at `dfb306f3`; the review's falsifier checks that the output for its two-disk case is identical to `dfb306f3` and that its Reock is still not the true value. They are improved over v4.0.0 but not correct.

### Tests (`tests/test_1467_rdh_compactness_projection.py`, 9 new)
- The 50 km circle at 150W, 61N built in its own local AEQD with z = 0 and stored in EPSG:4978, for Polsby-Popper, Reock and Schwartzberg through the scalar functions with `source_crs`, `compute_compactness` and `compare_plans`: 3 x 3 = 9.

### Results
- Red on `9e34375b` (the source file restored from the index): the 9 new tests failed. The review's falsifier, run in the worktree as a byte copy with byte copies of the files it loads (the earlier reproducer and the frozen `dfb306f3`, develop and v4.0.0 modules), failed its 9 geocentric cases and passed its other 18. The 27 projected-antimeridian tests and the other existing tests passed.
- After: the review's falsifier passed 27 of 27 (including its 12 ordinary-CRS parity checks against `dfb306f3`, its large-circle and projection-seam inventory and its #1954 two-disk check) and the earlier reproducer 11 of 11. The review also noted that a Mercator-stored 1,500 km circle scores Reock 0.999518 here against 0.999965 at `dfb306f3`, a small dependence on the storage CRS rather than a failure. `tests/test_1467_rdh_compactness_projection.py` passed 69 (60 earlier and 9 new). With the RDH client, atomic download, silent-wrong-data, chamber, selection, redistricting model, credential URL leak, release, changelog and exception contract site tests: 678 passed.
- Not counted, as in the first fix round: the two GeoDjango import tests in `tests/test_redistricting_models.py` and `tests/test_rdh_precinct_loader.py`, which need the GDAL C library this machine lacks.
- The falsifier imports the earlier reproducer by module name; it was run with `-o pythonpath=tests` so the byte copy could find it.
- `ruff check --select F,E9`: no findings. Exception-contract scanner: 0 unlisted, 0 stale. Test-file hygiene: pass.
- The falsifier, the reproducer and the frozen modules were removed from the worktree before staging.
