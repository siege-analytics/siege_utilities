---
ticket_refs:
  - siege-analytics/siege_utilities#1462: comment posted
---

# Self-review: #1462 / PR #1803 (bivariate quantile classes dropped by ties)

## Assumptions
Domain(s): software engineering, cartographic classification, reporting
Goal source: #1462 (bivariate choropleth breaks on tied data) plus owner comment 6133698827 (second instance: reporting map engine)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1462#issuecomment-6651072711
Review being answered: https://github.com/siege-analytics/siege_utilities/issues/1462#issuecomment-6259624054 (exact-head review of a14179ec: F1 + process)
Pre-author-inventory: the Investigation section of the plan reference above
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1462#issuecomment-6767131380
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1462#issuecomment-6767132609
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1462#issuecomment-6769298437

## Scope of this round
F1: `MapChartMixin._apply_bivariate_colors` (reporting/engines/map_engine.py)
called `pd.qcut(..., 3, labels=[0, 1, 2], duplicates='drop')`, which raises
when ties drop a bin edge. It now calls `qcut(labels=False, duplicates='drop',
retbins=True)` and maps each variable's actual classes onto the 3-level matrix
with `np.rint(np.linspace(0, 2, count))`. That is the same low-to-high sampling
as `geo/choropleth._bivariate_color_grid`, so both palette ends survive. A
variable with fewer than 2 classes raises a clear `ValueError`. pandas returns
all-NaN codes for a constant series, so this check is what stops NaN codes
from being coloured silently. Colour assignment is vectorized. The per-row
`except (ValueError, IndexError): gray` default is removed: it was unreachable
for valid rows, and it would have hidden failures as gray (SU-1). NaN rows
stay gray.

Callers: `create_bivariate_choropleth_matplotlib` (wraps the error in
`RuntimeError("Bivariate Choropleth Error: ...")` with the cause chained) and
the folium `create_bivariate_choropleth`.

## Peer review (the Junior's checklist)

### writing-code
- Severe flake8 on the changed files -> no output.
- `scripts/check_exception_contracts.py` -> 207 flagged, 0 unlisted, 0 stale (the removed handler had no allowlist entry).
- `scripts/check_no_stub_docstrings.py` -> OK; `scripts/check_test_file_hygiene.py` -> PASS.

### writing-tests
- Red at 995aab86 (new tests, old map_engine): pytest -> 14 failed, 1 passed.
  The 9 tied-colour cases (3 schemes x 3 tie layouts), the NaN-gray case, the
  2 constant-axis cases, and the 2 end-to-end matplotlib cases fail. The untied
  exact 3x3 lookup passes before and after.
- After the fix: pytest -> 198 passed (new file, test_1462_bivariate_choropleth_ties,
  test_map_engine_errors, test_reporting_markup_escaping, smoke, runtime_guard, sql_safety).

### writing-claims
- The counts are pytest summary lines from this work cycle.

## Lead review
For untied data the sampling is the identity ([0, 1, 2]), and the exact-colour
test confirms that output is unchanged. The geo-path behavior is not touched.
No live notebook calls the map engine bivariate methods (grep over `notebooks/`).

## Rework ledger
- a14179ec/995aab86: the second ticket instance was left unfixed. F1 is fixed in this round.
- The 4.1.0 note is restored to CHANGELOG.md and names the map engine paths.
- Pre-flight (2026-11-10). Develop sync: `f87f3273` merges develop `71f02b0b` for a positional CHANGELOG conflict (the #1444 and #1462 Fixed entries). Both are kept, a diff against develop deletes 0 develop lines, and no merged develop behaviour disagrees with this PR. Classification follows the operator rule (2026-11-06): a change that alters v4.0.0 caller behaviour is BREAKING. On the v4.0.0 tag, `geo/choropleth.py` classified with `qcut(..., duplicates="drop")`. The #1462 probe (v4.0.0) records that the map rendered tied data with the top values in a middle colour and a mismatched legend, and that `verify_bivariate_classification` returned `valid: True`. `create_bivariate_crosstab` and `create_bivariate_analysis` raised `Length mismatch`. Now `_bivariate_color_grid` raises below two bins (unless `n_classes=1`), the map colours change, and verification reports the reduced count. Those are BREAKING; the crosstab and analysis crashes are plain fixes. So the geo part moves to 4.1.0 BREAKING with a **Migration:** line. (`f4d110c4` first said "smaller crosstabs"; that was wrong, because v4.0.0 crosstabs crashed. Corrected in the next commit.) The reporting map engine part stays under Fixed, because v4.0.0 crashed on tied data there and no caller could rely on that. No code changed.

- Review round on `24d3a03b` (5 automated review threads, 2026-11-10). Each was checked against the code at `24d3a03b`; no classification behaviour changed and `geo/classification.py` is untouched.
  - Thread at `geo/choropleth.py:251` (NaN rows): no defect; the requested contract test is added as `test_missing_values_stay_unclassified_with_tied_data` (rows missing a value keep a NaN `_bivar_class`, complete rows keep the row-major index on the reduced grid, verification reports `Unclassified units: 2 of 12`, the map draws 10 polygons with the top colour last).
  - Thread at `geo/choropleth.py:801` (monotonicity check called unreachable): not changed. The check predates this PR (v4.0.0 `choropleth.py:755-759`) and is reachable: for var1 `[1, 2, 3, inf, inf, inf]` the breaks are `[1, 2.667, nan]` and the check reports `a breakpoints are not monotonically increasing`.
  - Thread at `geo/choropleth.py:884` (companion maps): valid. `create_bivariate_companion_maps` classifies through `create_choropleth(scheme='quantiles')`, not `pandas.qcut`. For `[0] * 6 + [1, 2, 3, 4]` with 3 classes, qcut gives 2 bins (breaks `[0, 0.9999999999999982, 4]`) and mapclassify gives 3 classes (bins `[0, 1.0000000000000009, 4]`, value 1 alone in the middle class). Docstrings of the companion and analysis functions now say so; behaviour unchanged.
  - Thread at `reporting/engines/map_engine.py:345`: valid in part. The all-constant case was already tested, but nothing pinned the 2-class minimum: with `class_count < 1` every existing test passed. Added `test_single_class_axis_raises_value_error[a|b]` (`[0] * 9 + [1]` leaves 1 class) and a docstring precondition that `values` is NaN-free. The quoted annotation is left to match the module's existing style.
  - Thread at `tests/test_1462_bivariate_choropleth_ties.py:111` (PT006 tuple names): not changed. CI lints with flake8 only (`.github/workflows/ci.yml:260-263`); ruff and its PT rules are not configured, and comma-string names are the majority form in `tests/`.
  - Evidence. The new tests are controls on unchanged behaviour, so there is no red on `24d3a03b`; the library diff is docstring-only. Mutation checks, applied temporarily and reverted: `_bivar_class` filled with 0 fails `test_missing_values_stay_unclassified_with_tied_data` (`assert np.False_`, the NaN check); `class_count < 1` fails both `test_single_class_axis_raises_value_error` cases (`DID NOT RAISE`); the other 41 tests in the two 1462 files passed under both mutations. After revert: the two 1462 files plus `test_chart_generator.py`, `test_choropleth.py` and `test_map_engine_errors.py` gave 136 passed. Severe flake8 on the four changed Python files: no output; `scripts/check_test_file_hygiene.py`: PASS; `scripts/check_no_stub_docstrings.py`: OK.
  - Overlap. Without mapclassify, the companion maps classify through `classify_series` in `geo/classification.py`. #1801 changes `geo/classification.py` and `geo/choropleth.py`, including class assignment and boundary behaviour; #1764 changes reporting and legend presentation and does not change `geo/classification.py`. This round changes only docstrings in `geo/choropleth.py`; `geo/classification.py` is untouched.
  - Scanner. The implementer's own runs of the `detect-ai-fingerprints` scanner were refused by the local mutation gate both times it was invoked, in place, on the commit message:
    1. `bash scan.sh --commit-message-file <message file>` was refused with: "BLOCKED by universal-mutation-gate: Cannot resolve mutation targets: opaque inline execution has unbounded mutation targets".
    2. The same script invoked directly with the task binding was refused with: "BLOCKED by universal-mutation-gate: Unscoped mutation: open a task gate with scope_paths for this action. ... Task gate scope rejected: ... declares repo_root=<siege_utilities clone> (origin=git@github.com:siege-analytics/siege_utilities.git); expected target repo=<agent workspace> (origin=<none>). Set repo_root to the task's TARGET repository, not the session CWD/workspace repository."

    Local filesystem paths in both refusal texts are elided as `...` or `<...>`; the remaining wording is verbatim. The implementer did not attempt the staged-snapshot or `--pr` scan after those refusals. The repository operator then ran the published scanner (siege-analytics/claude-configs-public main `a0dc815f`, v3.5.87) independently against staged tree `ad8685cb` on base `24d3a03b`: the staged scan returned 1 with 96 findings (40 writing-code:8, 56 writing-tests:5), the same 96 normalized findings as a baseline scan with none added or removed; both changed production files have identical ASTs once docstrings are removed; the intended commit message (sha256 `fd2e4c97`) returned 0. This is not a clean staged scan; the 96 findings are pre-existing scanner debt, not introduced here. Record and disposition: https://github.com/siege-analytics/siege_utilities/pull/1803#issuecomment-6769428790. That scan predates the three artifact links under Assumptions and this paragraph, which are self-review prose only. A path and name leak grep over the commit message, this file and the reply drafts found no hits; that grep is not a scan.
- CI round on `5b79f631` (2026-11-10). The `geo without GDAL` job, which runs without reportlab, failed on `tests/test_1462_map_engine_bivariate_ties.py::test_matplotlib_bivariate_map_renders_tied_data` with `ModuleNotFoundError: No module named 'reportlab'`: job 129882318766 on `5b79f631` (1 failed, 10813 passed) and job 129671579644 on `24d3a03b` (1 failed, 10810 passed). The test imported `reportlab.platypus` before the `pytest.importorskip('reportlab')` inside `_tied_geodataframe`. Its first statement is now `pytest.importorskip('reportlab', reason='install reportlab to run the bivariate image rendering test')`; its assertions and the library are unchanged. Local run with reportlab present (Python 3.11): the file gives 17 passed, including `test_matplotlib_bivariate_map_renders_tied_data PASSED`. No reportlab-absent local run exists: an import-blocking simulation (a stub package on `PYTHONPATH`) was refused by the local mutation gate each time it was invoked. The absent-dependency evidence is the `geo without GDAL` job on the new head.

## Findings
F1 fixed. Pre-existing and out of scope: `create_bivariate_choropleth_matplotlib`
returns a placeholder image when matplotlib or geopandas is missing.

## Ticket-fitness exemption

Governing ticket: #1462. The #1398 epic is context only.

### #1462
Reason: #1462 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1462 states the dropped-class defect under "## Problem", the probe under "## Evidence (v4.0.0, CONFIRMED by probe)" (`geo/choropleth.py`), and the done-when criteria under "## Done when". The second instance (`reporting/engines/map_engine.py`) is in owner comment https://github.com/siege-analytics/siege_utilities/issues/1462#issuecomment-6133698827. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1462#issuecomment-6259624054.
Falsification: revert the implementation; `tests/test_1462_bivariate_choropleth_ties.py::test_map_high_values_and_legend_share_colors` goes red because the highest tied-data feature is no longer coloured with the palette's top colour, and `tests/test_1462_map_engine_bivariate_ties.py::test_tied_data_colours_use_both_palette_ends` goes red because `pd.qcut` raises "Bin labels must be one fewer than the number of bin edges".
Observed revert results (2026-11-05). Command, with `REV` set to the revert target:
`git checkout REV -- siege_utilities/geo/choropleth.py siege_utilities/reporting/engines/map_engine.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1462_bivariate_choropleth_ties.py::test_map_high_values_and_legend_share_colors test_1462_map_engine_bivariate_ties.py::test_tied_data_colours_use_both_palette_ends); git checkout HEAD -- <same files>`
- `REV=dc7d3f76` (develop): 12 failed, 0 passed (3 geo tie layouts + 9 map-engine scheme/layout cases).
- Current-head green: after the files were restored, the same command gave 12 passed. The worktree was clean. Earlier in this round, the whole 1462 selection gave 198 passed.
