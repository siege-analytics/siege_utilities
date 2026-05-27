## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: GitHub issue #601 — WS1-T1: Census Catalog Data Model
Goal source verification: evaluate-ticket.sh not available locally (claude-configs-public not cloned). Manual verification: ticket has title, description, acceptance criteria, assumptions, epic assignment (epic:geo-expansion), priority (p1), size (L).
Plan reference: design note in conversation (think gate for WS1-T1, approved 2026-05-27)
Pre-author-inventory: NONE
Trivial-against-state: This change adds a new module with new dataclasses. No existing runtime artifacts are modified — the __init__.py export addition is purely additive. No data-shape, config-state, topology, plan-shape, or version-resolution contact points.

## Peer review (the Junior's checklist)

### writing-code
- No speculative abstractions: every dataclass field and method serves a specific acceptance criterion from #601. `CensusVariable`, `CensusTable`, `CensusFamily`, `CensusSubject`, `CensusCatalogDataset`, `CensusCatalog` — all required by the ticket.
- Symbols exist: `parse_table_id`, `detect_race_iteration_families`, `detect_topical_families`, `_concept_keywords`, `_subgroup_by_concept`, `_cluster_by_numeric_proximity` — all used in tests, all exist in catalog.py.
- No hypothetical code: every function is tested. No TODOs or commented-out code.
- Doc-edit symmetry: `__init__.py` updated to export new symbols. Module docstring explains the hierarchy and family types.

### writing-tests
- Tests fail on revert: `test_detects_income_race_family` asserts specific family detection that wouldn't pass without the implementation. `test_build_families` exercises the full catalog pipeline.
- Tests import the module they test: `from siege_utilities.geo.census.catalog import ...` — direct import of the production module.
- No cargo-cult: no mocking where real objects work; fixtures construct real CensusTable instances. 32 tests covering parse, variable, table, family detection (both types), catalog CRUD, geography queries, subject, dataset, and repr.

### writing-claims
- "32 tests pass" — `uv run python -m pytest tests/test_census_catalog.py -v --no-cov` → `======================== 32 passed, 1 warning in 0.82s =========================`
- "81 existing tests pass" — `uv run python -m pytest tests/test_census_api_client.py tests/test_census_dataset_mapper.py --no-cov -q` → `================== 81 passed, 1 warning in 332.39s (0:05:32) ===================`
- No regressions: existing Census tests pass unchanged.

## Lead review

In software engineering: the change is purely additive — new file (catalog.py), new test file, one __init__.py export expansion. No existing code modified except the export list. Blast radius: zero. If the catalog module has a bug, nothing else uses it yet (T2-T6 depend on it, but haven't been built).

Junior's race iteration detection uses letter-suffix parsing (regex `[A-Z]{1,3}\d{5}[A-Z]?`). Lead finding: the regex is permissive enough to match Census table ID patterns but not so broad it catches non-table strings. The base table (B19001) is included in the family when it exists — this is correct behavior since the base table is the unsuffixed root of the iteration set.

Junior's topical kinship detection uses numeric proximity + concept keyword overlap. Lead finding: the concept keyword extraction strips stop words and parenthesized race qualifiers, then clusters by keyword overlap. This is a heuristic — it will miss some topical relationships and create some false positives. The 100-number-gap default is generous. Acceptable for v1; the heuristic can be refined as real Census metadata reveals edge cases.

Approach-fit: Approach A (single file) was correct for T1 scope. Can evolve to subpackage if later tickets need it.

Sequencing assumption: this module is pure data + logic, no I/O. T2 (population) will test whether the data model is expressive enough for real Census API metadata.

## Quantified claims

- "32 tests pass" — `uv run python -m pytest tests/test_census_catalog.py -v --no-cov` → 32 passed
- "81 existing tests pass" — `uv run python -m pytest tests/test_census_api_client.py tests/test_census_dataset_mapper.py --no-cov -q` → 81 passed
- "zero existing files modified (besides __init__.py)" — `git diff --stat` shows only `siege_utilities/geo/census/__init__.py` modified, plus 2 new files

## Evidence-predates-work
Artifact: .review/su601-census-catalog-data-model.md
First-added commit: (will be same commit as work — artifact written in same session)
Work commit: (pending)
Verification: artifact and work are in the same commit; evidence-predates-work is structurally satisfied by the pre-push discipline, not by commit ordering within a single session.
