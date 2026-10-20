# Self-review — #1787 test-portability CI fix (#1673) (Tier B)

Review-Tier: B (test-only change to CI lane behavior; adds a skip-guard, no library or notebook change).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering (test portability / CI lanes).
Geospatial cross-cut: no.
Goal source: fair-bobcat exact-head review of PR #1787 (TEST/CI FAIL) + hub item-4 queue.
Plan reference: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/plans/pre-mortem-1673.md
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1787.md
Pre-mortem-artifact: docs/verification/pre-mortem-1787.md
Hostile-review-artifact: sessions/261019-fair-bobcat/data/notebook-pr-reviews.md (#1787 TEST/CI FAIL @5a3c4b01; this commit addresses it; exact-head re-review pending).
Project-contribution: keeps the reports/01 units regression test runnable across CI lanes, so the minimal (no-GDAL/no-ReportLab) lane stays green without dropping coverage where ReportLab is present.

## Test plan
- Red-first: force report_generator.Table = None and evaluate the failing class statement; expect `TypeError: NoneType takes no arguments` (the exact CI lane error). Observed: reproduced.
- Green (ReportLab present): run tests/test_1673_reports01_units_notebook_truth.py; expect all pass with the Spy subclass exercised. Observed: 3 passed.
- Green (minimal lane): with report_generator.Table = None, the guard must raise Skipped (not TypeError) before the class statement. Observed: clean Skipped.

## Peer review (Junior)
- writing-tests:3 (actionable skip): the skip message names ReportLab, the lane, and the install hint.
- No coverage loss: where ReportLab is installed the guard is inert and the Spy still asserts the rendered table.
- Gate 1 Syntax: the edited test file parses (pytest collected and ran it, 3 passed).
- Scope: only the test function changed; no library, notebook, or other test touched.

## Lead review (adversarial)
Phase A coherence: the fair-bobcat finding (Table=None subclass TypeError in the minimal lane) maps directly to the skip-guard; no drift.
Phase B verification: did it fix or move the problem? Fixed: red-first proves the TypeError pre-fix; green proves a clean skip when Table is None and full pass when present. The guard keys on the exact cause (Table is None), so it cannot mask an unrelated failure. No assertion was loosened.

Post-mortem applicability: N/A — forward test-portability fix closing a reviewer FAIL, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| (none) | - | - | - |

## Quantified claims
- "3 passed" — tests/test_1673_reports01_units_notebook_truth.py with ReportLab 4.4.10 present.
- "TypeError reproduced" / "clean Skipped" — targeted runs forcing report_generator.Table = None.

## r2 guard correction (fair-bobcat FAIL @0b5a98fc)

The first guard (`if report_generator.Table is None: pytest.skip(...)`) was wrong:
it skips whenever Table is None, which masks a renderer/module regression in a
lane where ReportLab IS installed (the reviewer forced Table=None with reportlab
present and the test falsely skipped). Corrected to
`pytest.importorskip("reportlab")` (skip only when the package is genuinely
absent) plus `assert report_generator.Table is not None, "ReportLab installed but
Table unavailable"` (a present-but-None Table now fails, not skips).

- Gate 2 (r2) Test suite: `pytest tests/test_1673_reports01_units_notebook_truth.py` with ReportLab 4.4.10 present -> 3 passed (the file has exactly three test functions: test_signups_use_counts_in_chart_table_and_report, test_growth_matches_counts_on_every_report_surface, test_pdf_table_renders_counts). The r2 FINAL anticipated "4 passed"; the head has 3 test functions, so the observed and reported count is 3.
- Forced Table=None with reportlab present -> AssertionError "ReportLab installed but Table unavailable" (fails, not skips).
- Package genuinely absent -> importorskip skips only test_pdf_table_renders_counts (1 skipped); the other two run.
- The rendered-table 51->52 mutation assertion is unchanged and still fails under mutation.

## Evidence-predates-work
Artifact: docs/verification/self-review-1787.md, committed in the same never-pushed work commit (self-ancestor). Written post-implementation, pre-push.
