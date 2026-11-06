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
