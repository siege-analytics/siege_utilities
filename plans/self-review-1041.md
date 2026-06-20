## Assumptions
Domain(s): core, lazy loading
Geospatial cross-cut: yes (geo deps are in the lazy registry)
Goal source: ticket #1041
Goal source verification: Codex hostile review session 260619-apt-sequoia, findings S1-1 and S1-2
Plan reference: design note on #1041
Pre-author-inventory: siege_utilities/__init__.py, siege_utilities/config/__init__.py (existing files)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Two locations with the same pattern. Root `__init__.py:380-384` and `config/__init__.py:272-286`. Both catch ImportError and return dependency wrappers without checking if the dependency is actually missing. Fix: verify the root dependency package is genuinely uninstalled before returning the wrapper.

## Trivial-pre-mortem declaration
Risk surface: the lazy loader now re-raises ImportError when the dependency IS installed but an internal import within the module fails. This is strictly better — users see the real error instead of "install geopandas" when geopandas is already installed.

## Peer review

### Syntax check
Python: `ast.parse()` passes on both files.

### Test suite
Quick smoke test: `import siege_utilities` succeeds, eager imports work.

### Build validation
No build changes.

### Shelf: conventions
CLAUDE.md rule 6 restored: "Lazy loading defers when errors surface, not whether they surface: __getattr__ must never catch ImportError and return a stub — let it propagate."

## Lead review

### Phase A: Structural coherence
Root `__init__.py`:
- Added `_is_dep_missing(deps)` helper that extracts package names from dep specs (stripping version constraints via regex) and tries to import them
- `__getattr__` line 393: changed `if deps:` to `if deps and _is_dep_missing(deps):`

Config `__init__.py`:
- Added `_is_pkg_missing(pkg_name)` helper (simpler — single package check)
- `_resolve_with_fallback`: added `and _is_pkg_missing('pydantic')` and `and _is_pkg_missing('hydra')` guards

### Phase B: Did this close the gap?
- [x] Root lazy loader: ImportError with installed dep now propagates
- [x] Root lazy loader: ImportError with missing dep still returns wrapper
- [x] Config lazy loader: same fix for pydantic and hydra paths
- [x] Package name extraction handles version specifiers (>=, ==, etc.)
- [x] Package name extraction handles pip-to-import name conversion (- → _)
- [x] Both files AST parse clean
- [x] Smoke test: `import siege_utilities` works

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims
- "_is_dep_missing extracts package names from dep specs" — verified: regex `^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)` matches "pydantic" from "pydantic>=2.0", "pyspark" from "pyspark", etc. Correct.
- "hydra import name" — verified: `import hydra` is the correct import for hydra-core. Correct (tested: ModuleNotFoundError when not installed).

## Evidence-predates-work
Artifact: plans/self-review-1041.md
