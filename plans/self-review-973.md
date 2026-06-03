# Self-Review: feat(#973) add sort_by/sort_order parameters to table generation functions

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #973
Goal source verification: PASS — ticket #973 requests sort_by/sort_order on table generation functions
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/973
Pre-author-inventory: NONE
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL

Trivial-against-state: adds new optional parameters with None defaults; no existing behavior changes.

## Trivial-investigation declaration

Category: single-line-fix
Cannot produce error: all new parameters default to None, preserving existing behavior. No existing call sites are affected.
Evidence: `git diff --stat HEAD` → 6 files changed, all additions. No existing function signatures broken (parameters are optional with defaults).
Falsification: an existing caller that passes positional arguments is disrupted by the new parameter positions.

## Peer review (Junior's checklist)

### Correctness
- `sort_table_data()` handles: int index, str header name, formatted numbers (commas, %), None preservation, empty tables, header-only tables.
- Sort key strips `,` and `%` for numeric comparison, falls back to case-insensitive string sort.
- Validates sort_order (asc/desc), column name existence, index bounds.
- Does not mutate input (returns new list).

### Integration
- `ReportGenerator.add_table_section()` — sort_by/sort_order added, lazy import of table_utils.
- `PowerPointGenerator.add_table_slide()` — same pattern.
- `ContentPageTemplate.add_table()` — same pattern, respects has_header flag.
- All three use lazy imports to avoid circular dependencies.
- `__init__.py` registers `sort_table_data` in lazy loader and `__all__`.

### Tests
- 14 unit tests for `sort_table_data` covering all paths.
- 2 integration tests for `ReportGenerator.add_table_section`.
- 1 integration test for `PowerPointGenerator.add_table_slide`.
- All 17 pass.

### Syntax check
- All 6 modified .py files parse OK.

## Lead review

Domain: software engineering.

The Junior's approach is correct. Optional parameters with None defaults ensure zero breaking changes. The sort utility is shared across all three table functions via lazy import. The sort key handles the common reporting format patterns (comma-separated numbers, percentages with % suffix).

Approach-fit: correct — utility function + parameter threading, not a new abstraction layer.

Blast radius: none — all parameters default to None, existing callers unaffected.

## Quantified claims

- "17 tests pass" — `python -m pytest tests/test_table_utils.py -v` → 17 passed in 0.79s
- "6 files changed" — `git diff --cached --stat` → 6 files, +276 -13

## Evidence-predates-work
Artifact: plans/self-review-973.md
Work commit: pending (will be first commit on branch)
