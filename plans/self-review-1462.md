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
