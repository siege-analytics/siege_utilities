# Self-review: #1788 natural-language geometry notebook honesty (#1672)

Review-Tier: B (notebook fixtures and prose, regression tests and documentation; no library code change).

Scope: the PR as a whole at its current head. The diff against `develop` is `CHANGELOG.md`, `notebooks/spatial/07_natural_language_to_geometry.ipynb` and `tests/test_1672_gazetteer_notebook_truth.py`, plus these three verification documents.

## Assumptions
Working as: software engineer (implementing) and tech lead (adversarial review).
Domain(s): software engineering (notebook truthfulness) with a geospatial fixture.
Geospatial cross-cut: yes (illustrative Lausanne and Lake Geneva geometries, directional predicates).
Goal source: ticket #1672 and the exact-head reviews recorded on PR #1788.
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1788.md
Pre-mortem-artifact: docs/verification/pre-mortem-1788.md
Hostile-review-artifact: the pinned review on PR #1788 and the ticket #1672 review comment for the prior head (CHANGES REQUESTED on the unexecuted integration parameters, release-note placement, a stale description and a self-review that claimed a network job); the current head addresses those points and awaits a fresh exact-head review.
Project-contribution: keeps the natural-language geometry notebook truthful about its fixtures and keeps the evidence for the geo notebook group honest about what runs where.

## Test plan
- Offline cases: `python -m pytest test_1672_gazetteer_notebook_truth.py -m "not integration"` run from the `tests` directory -> 5 passed, 6 deselected in 2.11s (Python 3.11, repository pyproject as config).
- Integration parameters: `python -m pytest test_1672_gazetteer_notebook_truth.py -m integration -v -rs` on the tree after the develop sync -> `test_geo_notebook_group[04_redistricting]`, `[01_boundaries]`, `[05_multi_source_joins]`, `[07_natural_language_to_geometry]`, `[03_choropleth_maps]` and `[02_geocoding]` each PASSED; 6 passed, 5 deselected in 133.04s. These six executed; they were not only collected. The run is local, uses the network (real TIGER boundaries for `01_boundaries`) and ran with the marker enabled.
- What does not run: no workflow in `.github/workflows/ci.yml` runs the six integration-marked parameters (the main job uses `-m "not integration and not postgis"`; the only explicit integration command targets `tests/test_files_remote_tls.py`). Adding such a job is a separate change that this PR does not make.
- Hosted CI at the pushed head is recorded in the PR description once it finishes. Develop CI has known failures from the DuckDB 2.0 break (about 30) that are not attributable to this PR.

## Peer review
- writing-claims: no sentence claims a network job runs the geo group; the description and this document say what ran locally and what does not run in CI.
- writing-prose: the verification documents use ASCII punctuation only.
- Scope: one notebook, one test file, the changelog, and these documents; no library code changed.
- Gate evidence: pytest -> 5 passed, 6 deselected (offline) and 6 passed, 5 deselected (integration) as above.

## Ticket-fitness exemption

Governing ticket: #1672 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1672 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (the offline gazetteer returning one rectangle for every place name, so the Lake Geneva directional example used the wrong reference), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1672, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1672#issuecomment-6298384632.
- **Falsification:** revert the implementation (the notebook fixture and label edits of this PR); `tests/test_1672_gazetteer_notebook_truth.py::test_demo_names_resolve_to_distinct_geometries` goes red because Lausanne and Lake Geneva resolve to equal geometries again. The latest commit of this PR is process-only; that existing regression test guards the accepted fix.

## Lead review (adversarial)
Phase A coherence: the reviewer findings (unexecuted parameters, release-note placement, stale description, inaccurate self-review) map to the recorded run, the `[4.1.0]` entry, the refreshed description and this whole-PR artifact; no drift.
Phase B verification: did it fix or move the problem? Fixed for evidence: all six parameters were executed and passed. Not fixed, and said so: CI still does not run them; the offline geo coverage on `develop` through #1667 is separate.

Post-mortem applicability: N/A. This is a forward content fix, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F-1 | medium | No workflow job executes the six integration-marked parameters | Open by design: reported to the maintainers as a possible workflow change; this PR provides the local run |

## Quantified claims
- "5 passed, 6 deselected" and "6 passed, 5 deselected in 133.04s" are the two pytest runs above.

## Restoration note
The three `docs/verification` documents for this PR were removed by commit ac74e3f9 and are restored from its parent, a326d9d0233ca28f0f43368e8c3436cda7e57d72. They were not restored byte for byte: they were rewritten to cover the whole PR at the current head, and internal session names, absolute local paths, client names and non-ASCII punctuation were removed so that nothing internal is published.

## Evidence-predates-work
This artifact is committed in the PR branch at `docs/verification/self-review-1788.md`. The test results above were produced in the same work cycle that restored it, after the implementation commits.
