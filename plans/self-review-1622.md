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

Updated on 2026-11-13 for the second review round:
- the develop `f22dce96` integration;
- the exact-head CI result at `3b1de990`;
- the negative-end CAGR fix the exact-head review found (S2-1, see "Round 2" below).

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

Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6799914437

The investigation linked above records the current behavior with file and
line evidence. No pre-author inventory was recorded for the original
2026-10-18 implementation; that absence is not backfilled.

The earlier integration rounds (`79f37f4d`, `f22dce96`) authored only
`CHANGELOG.md` and this record. Round 2 changes code (the CAGR helper), so
those rounds' docs-only declaration does not cover it. Before authoring the
round 2 fix, these states were measured:
- `_cagr` returned `(end / start) ** (1 / periods) - 1` and caught only
  `ZeroDivisionError` and `ValueError`; the caller caught only `ValueError`.
- `populate_timeseries` has no try or transaction around the per-GEOID loop.
- Raw Census sentinels stay in `DemographicSnapshot.values` by design (the
  summary columns map them to `None`, the JSON keeps the raw value).
- The unfixed helper failed all nine new negative-end cases (see Round 2).

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
- Second integration: develop `f22dce96` was merged on 2026-11-13 (merge
  `85c3a60b`, parents `3b1de990` and `f22dce96`). It had no conflicts. The
  PR's files were unchanged, and the CHANGELOG entry's added lines hashed the
  same before and after.
- A further merge of the live develop tip follows the round 2 fix commit; its
  SHA is in that merge commit.

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
- **Fixed behavior in CI:**
  - At head `3b1de990` (run 43352194897, pull_request), the `test-postgis`
    log showed all 22 cases in `tests/test_timeseries_cagr_moe.py` PASSED,
    with none skipped. This was read by the project coordinator, not by the
    author of this record.
  - Round 2 adds four cases (negative end, create and update), making 26.
    Those must pass in the next exact-head run; that result is PENDING.
- **Red-on-revert history:** the PR description reports a run of 15 failed and
  7 passed with the v4.0.0 service. The original author's ticket comment of
  2026-10-18 says the red-on-revert could not be reproduced locally, and no
  record of such a run exists. The exact-head reviewer derived the same 15/7
  by hand. A hand derivation is not a run, so the result stays NOT RUN.

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

## Round 2: negative-end CAGR (S2-1)

**Finding (exact-head review of `85c3a60b`):**
- With a positive start, a negative end and an exponent of two or more years,
  `(end / start) ** (1 / periods)` is a complex number.
- `_cagr` did not reject it. The value reached the `cagr` FloatField on
  `save()` or on the bulk insert. The resulting `TypeError` escaped
  `populate_timeseries` with no GEOID or variable named, and no transaction
  covers the loop.
- Elapsed calendar years made this reachable for two-observation series
  spanning two or more years. Before, those had an exponent of 1 and stored a
  meaningless negative rate.

**Fix:** `_cagr` raises `ValueError` for a negative end/start ratio; with a
positive start and a non-negative ratio the power is always real. The fix
commit also added a check for a non-real result. The independent review
showed that check could not be reached (a complex input fails earlier with
`TypeError`), so the correction commit removed it. The caller's existing
handler stores `cagr=None`, and the per-variable log line now counts these
series (`cagr_undefined`). A zero
end is still a real -100% rate. Only
`siege_utilities/geo/django/services/timeseries_service.py` changes.

**Tests:**
- `tests/test_timeseries_rollup_services.py`:
  - nine helper cases (ends -666666666, -999999999 and -1, periods 1, 2 and
    10) must raise `ValueError`;
  - one case pins a zero end at -1.0.
- `tests/test_timeseries_cagr_moe.py`: four PostGIS cases (ends -666666666
  and -999999999, create and update) assert that the series is written with
  `cagr` None.

**Red/green (local Python 3.11.11, `-p no:randomly`, `-k cagr` on
`tests/test_timeseries_rollup_services.py`):**
- RED, unfixed service: 9 failed ("DID NOT RAISE <class 'ValueError'>" for
  every negative-end case), 3 passed.
- GREEN, fixed service: 12 passed.
- The four PostGIS cases skip locally, and their red on the unfixed service
  is NOT RUN. A local PostgreSQL 14 service exists, but using it for the
  suite was not authorized in this pass. They must pass in the next
  exact-head `test-postgis` run.

**Local targeted run after the fix** (15 files, including develop's soupsieve
marker test): 273 passed, 1 skipped, 10 failed.
- The skip is the PostGIS module.
- The 10 failures are all in `tests/test_temporal_store.py`, a local pyarrow
  error that the scheme 'file' is already registered. That code and test are
  unchanged by this PR, and they passed on the 79f37f4d integration. The
  cause is in the local environment and is unverified.

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
  before each commit, and no conflict markers remain. The integration merges
  changed no Python source relative to the PR. Round 2 changes the service and
  two test files; `ruff check` on them passed.
- **Shelves checked:**
  - writing-releases:1: the change is breaking for stored series, so the
    CHANGELOG entry is under `### BREAKING` with a Migration line. The staged
    CHANGELOG diff against develop was +21/-0 in the integration rounds and
    +25/-0 after round 2, the single entry in each case.
  - writing-claims:1: before calling the CAGR fix complete, `git grep -n -i
    cagr` at develop found the two other implementations (temporal builder,
    `change_metrics`). Both already use elapsed years, so the class is closed
    for the exponent. It is NOT closed for negative ends: the temporal
    builder's `_cagr` still returns a complex value for a negative end, which
    its schema rejects. That is drafted as a follow-up and is outside the
    files this round may change. The unit difference is follow-up #1890.
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
  kept `None` MOEs, so this brings the Django service in line with it for
  those two points. For a negative end the two now differ: the Django service
  stores `None`, while the temporal builder still produces a complex value
  (follow-up).
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
    in the mean and standard deviation are follow-ups (#1890, #1891, #1403),
    not part of this PR. #1891's builder scan has since been fixed on develop.
  - Round 2 (S2-1): a negative end gave a complex CAGR; fixed. The
    independent review of the staged merge
    (https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6851470468)
    found it acceptable, with corrections that the following commit makes.
    Its other findings are drafted as a follow-up: the temporal builder's
    negative-end CAGR, and string values that can still stop the run.
- **Ticket record:** the full self-review, including the rework ledger, is
  posted at
  https://github.com/siege-analytics/siege_utilities/issues/1622#issuecomment-6800956235.

## Out of scope

- Census sentinels in `mean` and `std_dev`, and a sentinel start value
  (#1403). A sentinel end value is now handled in `cagr` (round 2).
- CAGR units: this service and the temporal builder store a fraction, while
  `geo/timeseries/change_metrics.py` returns a percentage (#1890).
- The temporal builder's per-boundary scan (#1891, fixed on develop).
- The temporal builder's negative-end CAGR, the loader's M-suffixed MOE key
  that this service does not read, and string values in snapshots that can
  still stop `populate_timeseries` (drafted follow-up).
