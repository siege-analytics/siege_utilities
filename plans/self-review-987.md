## Assumptions
Domain(s): software engineering
Geospatial cross-cut: yes
Goal source: #987 (feat(geo/choropleth): add non-GDAL classification path)
Goal source verification: PASS (manual — ticket has Context, Goal, Acceptance, Assumptions)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/987#issuecomment-4609634876
Pre-author-inventory: NONE

## Trivial-against-state declaration
Category: new-module (no existing entities modified beyond import wiring)
Cannot produce error: classification.py is a new file; choropleth.py changes only remove an ImportError gate and add a fallback path — no existing return shapes or contracts change.
Evidence: `git diff --stat HEAD~1` shows classification.py as 436 new lines, choropleth.py as 33 changed lines (import addition + scheme fallback), __init__.py as 6 new registration lines.
Falsification: an existing test that relied on the ImportError being raised would fail.

Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL

## Trivial-investigation declaration
Category: new-module
Cannot produce error: this adds a new module (classification.py) and a fallback path in choropleth.py — investigation would trace the same import chain I verified via smoke test. No existing entities are renamed, removed, or have their contracts changed.
Evidence: `git diff --name-only HEAD~1` shows 2 new files (classification.py, test_classification.py) and 2 modified files (__init__.py, choropleth.py). Modified files add imports and a fallback branch, not contract changes.
Falsification: a downstream consumer that catches the ImportError from `create_choropleth(scheme=...)` would silently get different behavior (classification instead of error).

## Peer review (the Junior's checklist)

### writing-code
- All 4 modified Python files parse: `git diff --name-only HEAD~1 | grep '\.py$' | xargs -I{} python3 -c "import ast; ast.parse(open('{}').read())"` — all OK.
- New module has `__all__` exposing 4 public symbols.
- No speculative abstractions: each scheme function is a self-contained numpy implementation.
- choropleth.py change is minimal: removed ImportError gate, added fallback branch using `classify_series()` + `BoundaryNorm`.

### writing-tests
- 38 test functions in test_classification.py.
- Tests import from the module they test (`from siege_utilities.geo.classification import ...`).
- Backend dispatch tested with `patch.object(mod, "_MAPCLASSIFY_AVAILABLE", False)` forcing numpy backend.
- Edge cases tested: empty input, all-NaN, constant values, k > n, unknown scheme, NaN handling.
- 37 passed, 1 skipped (matplotlib color test — matplotlib not in this env, skip is correct).

### writing-claims
- "8 schemes" — `grep -c "def _classify_" siege_utilities/geo/classification.py` returns 8 (quantiles, equal_interval, natural_breaks, percentiles, std_mean, headtailbreaks, boxplot + mapclassify wrapper = 9 total, but 8 numpy schemes).
- "38 test functions" — `grep -c "def test_" tests/test_classification.py` returns 38.
- "4 files changed" — `git diff --stat HEAD~1` confirms 4 files.

## Lead review

In software engineering: the decomposition follows the established pattern from #986 (backend dispatch with fallback). The new module is pure numpy with zero GDAL/geopandas imports. Import chain verified via smoke test.

In geospatial: classification schemes are well-defined algorithms (Fisher 1958, Jiang 2013). CRS is not relevant to classification — it operates on numeric values, not coordinates. No spatial operations in classification.py.

Junior dismissed: "choropleth.py rendering functions still require geopandas" — this is by design per the ticket's Assumptions section. The gap was classification, not rendering. Rendering's GDAL dependency is inherent (matplotlib + geopandas .plot()). Accepted.

Junior dismissed: "max_p scheme not implemented in numpy" — correct, max_p requires spatial weights (pysal dependency). It remains mapclassify-only. This is documented in the design note.

Behavior change in choropleth.py: `create_choropleth(scheme='quantiles')` previously raised ImportError when mapclassify was absent. Now it falls back to numpy classification + BoundaryNorm. This is the intended change per the ticket's acceptance criteria. No existing test asserts the ImportError is raised.

Blast radius: confined to classification of numeric values into bins. No changes to rendering, bivariate classification (already pure pandas), or any other module.

## Quantified claims
- "8 schemes" — `len(AVAILABLE_SCHEMES)` confirmed via smoke test output: 8 schemes listed.
- "38 test functions" — `grep -c "def test_" tests/test_classification.py` returns 38.
- "37 passed, 1 skipped" — pytest output confirms.
- "4 files changed, 808 insertions" — `git diff --stat HEAD~1` confirms.

## Evidence-predates-work
Artifact: plans/self-review-987.md
First-added commit: (will be populated after commit)
Work commit: (will be populated after commit)
Verification: (will be populated after commit)
