---
ticket_refs:
  - siege-analytics/siege_utilities#1125
---
## Self-Review: #1125 — Clear reportlab-missing error

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #1125
Goal source verification: ticket body describes cryptic TypeError from `float * NoneType` when reportlab absent
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1125#issuecomment-4836035231
Pre-author-inventory: investigate-gate.json (workspace)
Trivial-against-state: no authoring-against-state contact — changes are guard additions to reporting code, not domain content
Investigate-artifact: investigate-gate.json (ticket siege-analytics/siege_utilities#1125)
Pre-mortem-artifact: plans/pre-mortem-1125.md (workspace)

## Peer review

writing-code: all changes are guard insertions at method entry points in reporting engine/template files. No new features, no API changes, no domain logic.

### Syntax check
- `python3 -c "import ast; ast.parse(open('siege_utilities/reporting/engines/base_engine.py').read())"` → exit 0
- `python3 -c "import ast; ast.parse(open('siege_utilities/reporting/templates/base_template.py').read())"` → exit 0
- `python3 -c "import ast; ast.parse(open('siege_utilities/reporting/templates/content_page_template.py').read())"` → exit 0
- `python3 -c "import ast; ast.parse(open('siege_utilities/reporting/templates/table_of_contents_template.py').read())"` → exit 0

### Guard coverage verification
- `grep -rn '* inch' siege_utilities/reporting/` → 29 sites across 2 files (base_engine.py, base_template.py)
- All base_engine.py sites are in methods guarded by `_require_reportlab()` at entry
- All base_template.py sites are in `__init__` or methods reachable only from a constructed instance; `__init__` has the guard
- content_page_template.py and table_of_contents_template.py: guard in `__init__`
- Type annotations using `canvas.Canvas` changed to string form `"canvas.Canvas"` to avoid AttributeError when canvas=None

### Behavioral verification
- Simulated reportlab absence via `sys.modules` blocking
- `BaseChartEngine()._create_placeholder_chart(6, 4)` → `ImportError: reportlab is required for PDF chart generation but is not installed. Install it with: pip install reportlab`
- `BaseReportTemplate('test.pdf')` → `ImportError: reportlab is required for PDF report generation but is not installed. Install it with: pip install reportlab`
- Previously: `TypeError: unsupported operand type(s) for *: 'float' and 'NoneType'`

### Test results
- `pytest tests/test_reporting_config_exports.py tests/test_bar_engine_errors.py tests/test_chart_types.py` → 9 passed, 3 skipped, 0 failures

### Existing guards in sibling files
- `legend_manager.py:186`: returns `None` when `not REPORTLAB_AVAILABLE` (SU-1 violation — errors are not data — but out of scope for this ticket)
- `report_generator.py:544,639`: raises `ImportError` with clear message — same pattern we're adding

## Lead review

Four files modified, one class of bug fixed. The pattern is uniform: check `REPORTLAB_AVAILABLE` at method/constructor entry, raise `ImportError` with install instructions.

**Approach fit:** Method-entry guards (not import-time) preserve lazy loading. Per-file guards (not shared) because each file has its own `REPORTLAB_AVAILABLE` flag from its own conditional import block.

**Blast radius:** Minimal. Only code paths that previously crashed with TypeError now crash with ImportError. No behavioral change when reportlab IS installed.

**Sequencing assumption:** None — this is a standalone fix.

**legend_manager.py SU-1 violation:** `create_legend_table()` returns `None` on missing reportlab instead of raising. This is a separate bug (errors are not data), noted but not fixed here to keep scope tight.

Verdict: correct and minimal. The fix converts a class of cryptic runtime errors into actionable installation guidance.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P3 | legend_manager.py:186 returns None instead of raising — SU-1 violation | noted — separate ticket |

## Quantified claims
- "4 files changed, 31 insertions" — `git diff --stat` → `4 files changed, 31 insertions(+), 4 deletions(-)`
- "29 `* inch` sites" — `grep -c '* inch' siege_utilities/reporting/engines/base_engine.py siege_utilities/reporting/templates/base_template.py` → 9 + 20
- "9 passed, 3 skipped" — pytest output

## Rework ledger

No rework cycles occurred.

## Evidence-predates-work
Artifact: plans/self-review-1125.md
First-added commit: (same commit — artifact written after initial commit, will be in amend)
Work commit: (pending amend)
Verification: N/A — artifact and work in same commit
