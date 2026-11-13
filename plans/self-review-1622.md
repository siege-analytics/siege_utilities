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

Working as: data engineer, data analyst

Goal source: #1622 ("Done when")

Investigate-artifact:
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6799914437

Pre-mortem-artifact: the pre-mortem for the revised plan is in
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800217762.
The combined comment's pre-mortem section is restated as its own entry in
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800307447.

Junior task description:
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6799995136

Hostile-review-artifact: the independent Senior adversarial review, produced
by a fresh-context reviewer, is in
https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800163894.
The item-by-item response is in
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

## Out of scope

- Census sentinels in `mean`, `std_dev` and `cagr` (#1403).
- CAGR units: this service and the temporal builder store a fraction, while
  `geo/timeseries/change_metrics.py` returns a percentage.
- The temporal builder's per-boundary scan.
