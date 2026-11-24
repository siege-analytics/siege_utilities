# Self-review: PR #1743 chart wrapper and dispatcher argument binding (#1517)

Review-Tier: C (public reporting API; pre-flight round with a develop merge and a BREAKING classification).

## Assumptions
Working as: software engineer (Junior) and reporting tech lead (Lead).
Domain(s): software engineering (chart wrapper/engine dispatch, ReportLab images, bundled examples).
Geospatial cross-cut: light (choropleth/bivariate `geo_data` forwarding only; no CRS logic changed).
Goal source: #1517 (wrappers and dispatchers pass arguments positionally, so titles, columns and geometry land on the wrong engine parameters). This round is a pre-flight of the existing implementation at `2874052f`: resolve the develop conflict, classify the CHANGELOG entry against the v4.0.0 tag, fix one dangling documentation pointer, and re-run red/green evidence. No library code changed in this round.
Plan reference: docs/verification/self-review-1743.md#pre-mortem
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1517#issuecomment-6758611714
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1517#issuecomment-6758611714
Project-contribution: chart wrappers produce the chart the caller asked for, and the shipped reporting examples run.

## Investigation
- GitHub reported PR #1743 CONFLICTING with develop `71f02b0b` (1 ahead, 112 behind). Merge base `a6e84550`. Develop changed `CHANGELOG.md` and `siege_utilities/reporting/templates/base_template.py`; only `CHANGELOG.md` overlaps the PR, and the conflict was the `[4.1.0] ### Fixed` list.
- v4.0.0 `base_engine.py:373` builds figures with `plt.subplots(figsize=(width, height), dpi=150)`, so the wrappers' `800`/`600` defaults were already inches to matplotlib; the "pixels" docstrings were wrong. The CHANGELOG entry says this rather than suggesting a pixel conversion.
- `git grep comprehensive_mapping_example` on the merged tree found one remaining pointer, in `docs/archive/examples/README_Streamlit_Demo_2026.md`, listing the removed file under "For active examples". It predates the merge (present at v4.0.0 and on the PR head). Removed in this round.
- REST: 0 inline review comments and 0 reviews on PR #1743.

## Pre-mortem
1. Tiger. Severity: P1. The CHANGELOG union drops a develop line. Mitigation: develop's side of the only hunk kept verbatim; post-merge `git diff origin/develop -- CHANGELOG.md` empty; after the BREAKING entry, 0 removed lines.
2. Tiger. Severity: P2. A develop change references the removed example. Mitigation: repository-wide `git grep`; the only hit was the pre-existing archive pointer, now removed.
3. Paper Tiger. Severity: P2. Migration text invents a unit conversion. Mitigation: checked v4.0.0 `figsize` usage; Migration says to pass inches explicitly.
4. Paper Tiger. Severity: P3. Develop's `base_template.py` change interacts with wrappers. Mitigation: merged unchanged; the 273-test reporting set passes.

## Peer review (Junior: shelves, gates)
- Shelves: SU-2 (wrapper signatures and docstrings now match what reaches the engine); SU-3 (bundled examples run end to end).
- Gate 1 (syntax): no Python file changed in this round.
- Gate 2 (tests): on the merged tree, the 15 `tests/test_chart*.py` and `tests/test_reporting*.py` files -> 273 passed, 1 skipped (`test_reporting_module.py:616` runs only when python-pptx is missing).

## Lead review (adversarial)
Phase A coherence: CHANGELOG, PR body and tests describe keyword forwarding, keyword-only `geo_data`, the new defaults and the example removal.
Phase B verification (red/green): `tests/test_chart_generator_wrapper_kwargs.py` copied into a detached v4.0.0 worktree (`9c3463b1`) -> 33 failed, 1 passed; failures are at the engine boundary (`assert 800 == 'T'` for the scatter title, `KeyError: 'y_columns'`, `unexpected keyword argument 'geo_data'`). On the merged branch -> 34 passed. Import paths were checked to resolve to each worktree's package.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | Branch CONFLICTING with develop (CHANGELOG only) | additive merge `8c190b18`; develop side kept verbatim |
| F2 | P2 | Caller-visible changes listed under Fixed, not BREAKING | entry under `[4.1.0] ### BREAKING` with Migration |
| F3 | P3 | Archived README points to the removed example as active | line removed |
| F4 | P3 | Tip lacked review trailers | this commit carries them |
