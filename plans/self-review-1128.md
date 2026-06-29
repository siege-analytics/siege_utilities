---
ticket_refs:
  - siege-analytics/siege_utilities#1128
---
## Self-Review: #1128 — legend_manager SU-1 fix

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #1128
Goal source verification: ticket body describes SU-1 violation (return None instead of raising)
Plan reference: #1128 ticket body
Pre-author-inventory: #1125 self-review Finding #1
Investigate-artifact: investigate-gate.json (ticket siege-analytics/siege_utilities#1128)
Pre-mortem-artifact: plans/pre-mortem-1128.md (workspace)

## Peer review

writing-code: one-line change — replace `return None` with `raise ImportError(...)` in legend_manager.py.

### Syntax check
- `python3 -c "import ast; ast.parse(open('siege_utilities/reporting/legend_manager.py').read())"` → exit 0

### Caller verification
- `grep -rn 'create_legend_table' siege_utilities/` → 0 callers (function is defined but uncalled in library)
- No code depends on the None return value

### Docstring update
- Changed "ReportLab Table object or None if ReportLab not available" → "ReportLab Table object"

### Test results
- 9 passed, 2 skipped, 0 failures

## Lead review

Single-line fix, identical pattern to report_generator.py:544,639. No callers to break. Docstring updated to match new contract.

Verdict: correct and trivial.

## Findings

No findings.

## Quantified claims
- "1 file changed" — `git diff --stat` confirms
- "0 callers" — grep for create_legend_table found 0 call sites in library code

## Rework ledger

No rework cycles.

## Evidence-predates-work
Artifact: plans/self-review-1128.md
First-added commit: (same commit)
Work commit: (pending)
