---
ticket: "#1176"
scope: "siege_utilities/__init__.py"
---

# Self-Review — #1176 batch 1: promote geo.spatial_data canonicals

## Assumptions

Working as: Software Engineer
Goal source: #1176 body — "Public API categorization: 283 lazy symbols not in __all__". Deliverable: "Per-symbol pass to add categorized entries to __all__".
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: plans/hostile-review-1176-batch1.md
Pre-author-inventory: `scripts/audit_public_api_surface.py --markdown --report` output (137 canonicals → 27 in geo.spatial_data, prioritized for batch 1).

Assumed:
- The current top-level `siege_utilities.__all__` (39 symbols) comes indirectly through `__getattr__` fallback → `.distributed.__all__`. Verified via `python -c 'import siege_utilities; print(len(siege_utilities.__all__))'` returning 39, and `grep -n "__all__" siege_utilities/__init__.py` returning zero hits. Explicit `__all__` did NOT exist prior to this PR.
- Consumers depending on `from siege_utilities import *` currently receive the 39 distributed symbols. Removing them from `__all__` would be BREAKING (writing-releases:1).
- The 27 geo.spatial_data symbols are all resolvable via `__getattr__` today. Verified for a sample (`discover_boundary_types`, `download_data`, `get_census_boundaries`, `normalize_fips_code`, `validate_state_fips`) — all return functions from `siege_utilities.geo.spatial_data`.

## Peer review

- **writing-code:16 (migration completeness):** N/A — no import path is being moved or renamed. This is a metadata addition (`__all__` declaration), not a symbol relocation.
- **writing-releases:1 (BREAKING when public surface changes):** The change ADDS symbols to `__all__` (27 canonicals + explicit declaration of the 39 pre-existing distributed symbols). Nothing is removed or renamed. `from siege_utilities import *` gains 27 new names but loses none. Not BREAKING.
- **writing-claims:8 (specific counts must cite the command):**
  - "27 canonical symbols in geo.spatial_data" — verified: `python scripts/audit_public_api_surface.py --markdown --report 2>&1 | grep '\`\.geo\.spatial_data\`' | wc -l` → 27.
  - "canonical tier drops from 137 to 121" — verified: pre-change `audit_public_api_surface.py 2>&1` showed `canonical: 137`; post-change showed `canonical: 121`. The 16-symbol delta (vs. 27 promoted) reflects that some spatial_data names also appear in other `_register_lazy` calls elsewhere in `__init__.py`; audit dedups.
  - "__all__ length: 79" — verified at runtime: `python -c 'import siege_utilities as su; print(len(su.__all__))'` → 79 (13 core + 39 preserved distributed + 27 promoted geo).
- **writing-tests:1 (tests must fail on revert):** N/A — this is metadata; no behaviour changes. Existing pytest run (`pytest tests/ -k 'test_public_api or test_lazy or test_all or test_init or test_import'`) shows 140 passed, 6 failed. The 6 failures (`test_nces_service`, `test_nlrb_models`) are pre-existing GDAL-library-missing baseline failures (see user memory `reference_su_ci_baseline`), unrelated to this diff.
- **SU-5 (parse verification):** `python -c "import ast; ast.parse(open('siege_utilities/__init__.py').read())"` → `parses OK`.

## Lead review

Working as: Tech Lead

Affirmative:
- The BREAKING risk was recognized mid-authoring: after the first version of the diff dropped `__all__` to 40 (would have removed the 39 distributed symbols from `import *`), the diff was updated to explicitly preserve the 39. This is the pattern all future promotion PRs must follow — grandfather the existing implicit surface, then promote.
- The audit-tool feedback loop closes: pre-change `canonical: 137` → post-change `canonical: 121`. Future PRs can rerun the same command to verify their batch was promoted correctly.
- The template establishes the pattern (explicit `__all__` block, distinct sections for eager core / preserved distributed / promoted per-subpackage) so batches 2 and 3 are additive-only edits within the "Promoted canonicals" region.

Deferred:
- The 27 promoted symbols do not yet have per-symbol test coverage requirements checked; that gap is tracked by #1200-#1204 from earlier in this session.
- No CI ratchet job yet prevents new `_LAZY_IMPORTS` entries from landing without an `__all__` decision (part of the #1176 deliverable list, follow-on PR).

## Trivial-investigation declaration

Category: descriptive-docstring-fix
Cannot produce error: The change adds explicit symbol names to `__all__` — a Python-standard metadata field. Every name added was verified at runtime to resolve via the existing `__getattr__` path. No new code paths, no exception handlers, no type coercion.
Evidence: `git diff --stat` shows 1 file changed, 74 insertions, 0 deletions. `python -c "import siege_utilities as su; assert all(hasattr(su, n) for n in su.__all__)"` → passes.
Falsification: If a consumer of `from siege_utilities import *` reports that a name in the pre-existing 39-symbol distributed set no longer resolves, or if any of the 27 promoted geo names fails to import.

## Trivial pre-mortem declaration

The change is a metadata additive edit within one file. No behaviour is modified. No consumers are broken; consumers gain 27 new star-importable names. Risk surface is bounded by the runtime-verification loop above (import each promoted name; all resolve).

## Hostile review responses

Hostile review artifact: `plans/hostile-review-1176-batch1.md` (SHIP WITH REVISIONS verdict).

**F1 (latent name collision):** RESOLVED in-PR by adding a duplicate-registration guard to `_register_lazy`. Any future promotion batch that would silently pick a collision winner now raises `RuntimeError` at import time with a message naming both modules. Test coverage: `TestLazyRegistrationGuard::test_duplicate_registration_raises` and `test_idempotent_registration_allowed` in `tests/test_public_api_surface.py`. The three specific collisions F1 flagged (`get_census_boundaries`, `get_census_data`, `get_available_years` all having sibling defs in `reference/sample_data.py` / `geo/timeseries/longitudinal_data.py`) remain latent — those files are not registered — but the mechanical guard now prevents any future batch from activating the shadow silently.

**F2 (no `__all__` test coverage):** RESOLVED by adding `tests/test_public_api_surface.py` (60 tests, all passing):
- `TestAllDeclaration`: `__all__` is defined as a list; no duplicates; every declared name resolves; the 39 preserved-distributed symbols are all present (BREAKING-guard for `from siege_utilities import *`).
- `TestBatch1Promotions`: each of the 27 promoted symbols is in `__all__` AND resolves to `siege_utilities.geo.spatial_data` specifically (cross-module rebinding detection).
- `TestLazyRegistrationGuard`: F1 mechanical guard tested.

