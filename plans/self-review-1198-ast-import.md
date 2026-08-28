---
ticket: "#1178"
scope: "scripts/check_symbol_test_coverage.py"
---

# Self-Review — #1178 drop unused ast import (PR #1198 lint unblock)

## Assumptions

Working as: Software Engineer
Goal source: PR #1198 CI job `lint ratchet phases2-4` reports `scripts/check_symbol_test_coverage.py::F401::'ast' imported but unused`. Merging #1198 requires that check green or admin-bypassed; the finding is legitimate (dead import) so the honest fix is to remove it, not bypass.
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: plans/hostile-review-1198-ast-import.md
Pre-author-inventory: `grep '\bast\.' scripts/check_symbol_test_coverage.py` → 0 matches (no attribute access anywhere). `grep 'ast\.parse\|ast\.walk\|ast\.NodeVisitor'` → 0. Scanner discovery is regex + `tomllib` (`_LAZY_IMPORTS` reflection at line 184–188), never AST-based. Import is dead code.

Assumed:
- The `ast` import is genuinely unreferenced (verified by dual grep).
- The scanner's behavior is unchanged by removing the import (Python parses fine, no runtime path exercises `ast`).
- No downstream code re-exports `ast` via `from scripts.check_symbol_test_coverage import *` (scripts/ modules are entry points, not library modules).

## Peer review

- **writing-code:04 (imports are load-bearing):** confirmed no usage; removing cannot change behavior.
- **writing-releases:1 (BREAKING when public API changes):** N/A — `scripts/` is not part of the `siege_utilities` public surface.
- **writing-claims:8 (specific counts must cite command):**
  - "0 usages of `ast`" — `grep '\bast\.' scripts/check_symbol_test_coverage.py` → exit 1 (no matches).
- **SU-5 (parse verification):** `python -c "import ast; ast.parse(open('scripts/check_symbol_test_coverage.py').read())"` → OK.
- **Lint ratchet (F401):** the finding this PR resolves; a repeat lint-ratchet run post-fix would report 0 F401 on this file.

## Lead review

Working as: Tech Lead

Affirmative:
- The fix is exactly the reported finding, no collateral edits, no scope creep.
- Preferred over `--admin` bypass because the finding is real and the fix is 1 line.
- Preserves the scanner's original commit (`ac17dd6c`) as-is on the branch; the fix rides on top as a separate commit for a clean review trail.

Deferred: none.

## Trivial-investigation declaration

Category: dead-code-removal (unused import)
Cannot produce error: Removing a Python import that is never referenced cannot change program behavior. Verified by dual grep for both attribute access and common AST-visitor patterns.
Evidence: `grep '\bast\.' scripts/check_symbol_test_coverage.py` → 0 matches. `python -c "import ast; ast.parse(open(...).read())"` → OK.
Falsification: If any code path (including `getattr`, `hasattr`, or `sys.modules['ast']` runtime lookup) referenced `ast`, removing the import would surface as NameError or ModuleNotFoundError on the first run through that path.

## Trivial pre-mortem declaration

Category: dead-code-removal
Cannot produce error: Same as investigation — no behavior change possible from removing an unreferenced import.
Evidence: dual grep + parse check.
Falsification: See investigation Falsification.

## Hostile-review response

Verdict: SHIP (no findings). Reviewer independently confirmed `ast` is orphaned via `\bast\b` grep (only occurrence is inside the word "least" in a docstring), no dynamic imports exist, no tests reference the script, and `import ast` has no import-time side effects. See `plans/hostile-review-1198-ast-import.md` for the full artifact.

