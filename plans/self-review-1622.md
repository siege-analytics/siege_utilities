---
ticket_refs:
  - siege-analytics/siege_utilities#1622: comments posted https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6799914437 (investigation and pre-mortem), https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800163894 (independent Senior review)
---

# Self-review: develop integration for #1622 (PR #1752)

Ticket: siege-analytics/siege_utilities#1622

This is the evidence record for the current integration pass on PR #1752. It
was written on 2026-11-11, after the original implementation at `6d1923c0`
(2026-10-18). It does not backfill the original round: no investigation,
pre-mortem or hostile review was recorded before that implementation.

Review tier: B, by content. The local tooling classified this merge as tier C,
because develop-side workflow and release files are in the merge set, and the
pass was run under that stricter gate. The tier C fields follow.

## Assumptions

Working as: data engineer, data analyst

Domain(s): data engineering, data analysis

Geospatial cross-cut: yes (the regression module runs only against PostGIS)

Goal source: #1622 ("Done when")

Goal source verification: not run as a separate ticket check; the "Done when"
items were read from the ticket and compared with the code, and the "fails on
`v4.0.0`" item is recorded below as unmet.

Plan reference: the Junior task description and the response to the
independent Senior review (links below).

Pre-author-inventory: NONE

Trivial-against-state: docs-only
Reason: in this integration round the only authored files are `CHANGELOG.md`
and this record; the service and test are byte-identical to the original
implementation at `6d1923c0`, and every other file is byte-identical to
develop `79f37f4d`, so this round touches no data-shape, config-state,
topology, plan-shape or version-resolution contact point. No pre-author
inventory was recorded for the original 2026-10-18 implementation; that
absence is stated above and is not backfilled here.
Evidence: `git diff --name-only 79f37f4d HEAD` lists `CHANGELOG.md`,
`plans/self-review-1622.md`,
`siege_utilities/geo/django/services/timeseries_service.py` and
`tests/test_timeseries_cagr_moe.py`; the non-Markdown entries are only the
service and test, and `git diff 6d1923c0 HEAD` on those two paths is empty
(0 lines).
Falsification: if `git diff 6d1923c0 HEAD --
siege_utilities/geo/django/services/timeseries_service.py
tests/test_timeseries_cagr_moe.py` shows any change, or
`git diff --name-only 79f37f4d HEAD` lists any other non-Markdown file, this
declaration is wrong.

Project-contribution: stored `DemographicTimeSeries` growth rates mean per
calendar year and MOEs stay aligned with their years; this integration makes
the PR mergeable into develop with an accurate BREAKING and Migration record.

Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6799914437

Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800217762

The pre-mortem above is for the revised plan. The combined comment's
pre-mortem section is restated as its own entry in
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800307447.

Junior task description:
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6799995136

Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800163894

The hostile review above is the independent Senior adversarial review,
produced by a fresh-context reviewer. The item-by-item response is in
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800188053.
An earlier Senior checklist
(https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6799997178)
was written by the plan's author and is superseded by the independent review.

## Integration

- Base: `origin/develop` at `79f37f4d`. The PR head was `6d1923c0`, on merge
  base `ef2f3fc1`.
- Develop did not change any of these since the merge base:
  - `siege_utilities/geo/django/services/timeseries_service.py`;
  - `tests/test_timeseries_cagr_moe.py`;
  - `siege_utilities/geo/django/models/`;
  - `siege_utilities/geo/temporal/`.
  The service and test are byte-identical to `6d1923c0`.
- `CHANGELOG.md` was the only conflict. It is resolved as develop's file plus
  one bullet in the `## [5.0.0]` `### BREAKING` block that holds the
  GEOID-native key entry for `DemographicSnapshot` and `DemographicTimeSeries`.
  - The bullet has a Migration line.
  - The PR's earlier `[Unreleased]` `### Fixed` bullet is not kept.
  - Why BREAKING: stored CAGR values change for non-annual series, and
    `moe_values` can now hold `None` (a series with no MOEs stores a list of
    `None` instead of `[]`). 5.0.0 is the pending MAJOR release for breaking
    changes (see `docs/verification/self-review-1885.md`).

## Evidence status

- **Pre-fix control: NOT RUN.**
  - `tests/test_timeseries_cagr_moe.py` skips at module level unless
    `SIEGE_TEST_POSTGIS=1`, and needs a live PostGIS database with GDAL.
  - The supported environment for it is the CI `test-postgis` job, which tests
    the pull request's merge ref only. CI has no manual dispatch.
  - A run against the parent service would need a probe branch, a revert
    commit or a new CI path. None was used, and no local PostGIS database was
    available for this pass.
  - Expected on the pre-fix service, and not observed: a stored CAGR of 0.10
    instead of about 0.009577 for the 2000/2010/2020 case, and a compacted
    `moe_values` (`[50, 40]` instead of `[50, None, 40]`).
  - The ticket's "fails on `v4.0.0`" criterion is therefore unmet.
- **Fixed behavior in CI: PENDING.** The exact-head `test-postgis` log must
  show all 22 cases in `tests/test_timeseries_cagr_moe.py` PASSED and none
  skipped. This record is written before that run and claims no CI result.

## Verification (local Python 3.11.11)

Run on the merged working tree (develop `79f37f4d` plus this resolution)
before commit, with `python -m pytest -o addopts="" -p no:cacheprovider -rs`
from the worktree root (rootdir is the worktree, `configfile: pytest.ini`;
pytest 8.4.2, Django 5.2.14, `pytest-randomly` active). The run was done
twice, once with `-q` and once without (seed 3928869438), with the same
result each time: **206 passed, 25 skipped, 0 failed.**

Files run: `test_timeseries_cagr_moe.py`, `test_temporal_services.py`,
`test_temporal_store.py`, `test_temporal_query.py`, `test_timeseries.py`,
`test_timeseries_errors.py`, `test_timeseries_rollup_services.py`,
`test_demographic_schemas.py`, `test_1539_1550_bulk_sites.py`,
`test_exception_contracts.py`, `test_release_process.py`,
`test_package_metadata_contract.py`, `test_user_config_export_changelog.py`
and `test_smoke.py`. The release, metadata and CHANGELOG contract tests read
the resolved `CHANGELOG.md`.

Skipped, and not passes:

- `tests/test_timeseries_cagr_moe.py`: the whole module (22 cases), because
  `SIEGE_TEST_POSTGIS` is not set and there is no local PostGIS database. The
  changed behavior is therefore not exercised locally.
- `tests/test_1539_1550_bulk_sites.py`: the whole module, because GeoDjango
  (GDAL/GEOS) is not available locally.
- `tests/test_timeseries_rollup_services.py`: 23 cases, because
  GeoDjango/GDAL is not available locally.

Not run:

- The pre-fix control (see Evidence status).
- The full test suite. Only the files above were run.

Import provenance: the pytest header shows the worktree as rootdir, and
`python -m` puts the working directory first on `sys.path`. That is weaker
evidence than printing the imported module's `__file__`, which was not done
for this record.

## Peer review

- **CAGR:** the exponent at the PR head is `series_years[-1] - series_years[0]`.
  The ticket's decennial example gives 1.21^(1/20) - 1, about 0.009577, and
  the test expects 0.009576582776887.
- **MOEs:** stored without compaction on create and update. A series with no
  MOEs now stores a list of `None` instead of `[]`, and the CHANGELOG says so.
- **Reads:** GEOIDs are resolved once per call, and snapshots and existing
  series are read once per variable. Updates still save row by row.
- **Negative paths in the test file:**
  - fewer than two observations writes no series;
  - `_cagr` rejects zero periods;
  - a zero or negative start stores `cagr=None`;
  - out-of-state, other-dataset, other-level and other-interval rows are left
    alone.
  All of these are in the PostGIS module, were skipped locally, and must pass
  in the exact-final-head `test-postgis` job.
- **CHANGELOG fact check:** 0.0096 and 0.10 match the code and test. The
  Migration key (geography level, GEOID, variable, dataset, start and end
  years) matches the existing-series lookup. The affected-row selector follows
  from the old formula and the MOE compaction.
- **Syntax check:** `git diff --cached --check` against develop was clean
  before commit; no conflict markers remain; no Python source changed relative
  to the PR head.
- **Shelves checked:**
  - writing-releases:1: the change is breaking for stored series, so the
    CHANGELOG entry is under `### BREAKING` with a Migration line; the staged
    CHANGELOG diff against develop was +21/-0, the single entry.
  - writing-claims:1: before calling the CAGR fix complete, `git grep -n -i
    cagr` at develop found the two other implementations (temporal builder,
    `change_metrics`); both already use elapsed years, so the class is closed
    for the exponent. The unit difference is follow-up #1890.
  - writing-claims:8: the local counts come from the pytest summary line
    (206 passed, 25 skipped, 0 failed) and the 22-case count from the test
    file's parametrization.
  - writing-tests:1: NOT demonstrated in this pass. The regression test has
    not been shown to fail on the pre-fix service (pre-fix control NOT RUN).
  - writing-claims:10: import provenance rests on the pytest rootdir and
    `python -m` path ordering, which is weaker than printing the imported
    module's path.
- **Notebook API check:** N/A; no notebook calls `populate_timeseries` or
  `TimeseriesService` (`git grep` at develop).

## Lead review

- **Approach fit:** the fix is at the formula and the storage line, the right
  layer. The engine-agnostic temporal builder already used elapsed years and
  kept `None` MOEs, so this brings the Django service in line with it.
- **Blast radius:**
  - every `DemographicTimeSeries` row written after the merge;
  - consumers that sum, index or truth-test `moe_values`;
  - stored rows from earlier versions, until they are recomputed.
- **Evidence:** the evidence for the fix is CI-only. Local runs cannot exercise
  the database path, and the pre-fix control was not shown. A green job must
  be read case by case and is not red-on-revert.
- **Placement:** `[5.0.0]` is the pending, untagged MAJOR release. The two
  `[Unreleased]` entries predate the 4.1.0 to 5.0.0 renumber. The placement
  follows this round's review decision and is flagged for whole-PR review.
- **Findings:**
  - S1 (P1): the "fails on `v4.0.0`" criterion cannot be shown in the
    supported environment in this pass; recorded as unmet, and the ticket
    stays open.
  - S2 (P2): the CHANGELOG bullet was imprecise; fixed in the committed
    bullet.
  - S3 (P2): `[5.0.0]` versus `[Unreleased]` placement; kept, and flagged.
  - S4 (P3): CAGR units, the builder's per-boundary scan and Census sentinels
    are follow-ups (#1890, #1891, #1403), not part of this PR.
- **Ticket record:** the full self-review, including the rework ledger, is
  posted at
  https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800956235.

## Out of scope

- Census sentinels in `mean`, `std_dev` and `cagr` (#1403).
- CAGR units: this service and the temporal builder store a fraction, while
  `geo/timeseries/change_metrics.py` returns a percentage.
- The temporal builder's per-boundary scan.
