---
ticket: "#1176"
scope: "siege_utilities/__init__.py, tests/test_public_api_surface.py"
---

# Self-Review — #1176 batch 3: promote databricks canonicals

## Assumptions

Working as: Software Engineer
Goal source: #1176 body — "Public API categorization: 283 lazy symbols not in __all__". Batch 3 continues the per-subpackage promotion template from batches 1 (#1207) and 2 (#1209).
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: plans/hostile-review-1176-batch3.md
Pre-author-inventory: `scripts/audit_public_api_surface.py --markdown --report` output filtered to `.databricks*` (18 canonicals, all registered in a single `_register_lazy` call at `__init__.py:290-298`).

Assumed:
- Batch 3 stacks on batch 2 (PR #1209), which stacks on batch 1 (PR #1207). Merge order: #1207 → #1209 → this → develop.
- All 18 batch-3 names are registered as lazy imports from `.databricks` (deps=['pyspark']).
- Test env has pyspark available via SZSH (`ZSH_FORCE_FULL_INIT=1 zsh -ic`), so runtime resolution succeeds. If pyspark is absent, the dep-wrapper returns a stub that raises `ImportError` on call — this is the intended graceful-degradation path.

## Peer review

- **writing-code:16 (migration completeness):** N/A — metadata addition.
- **writing-releases:1 (BREAKING when public surface changes):** ADDITIVE only. 18 names added, none removed. Not BREAKING.
- **writing-claims:8 (specific counts must cite command):**
  - "18 canonical databricks symbols" — `python scripts/audit_public_api_surface.py --markdown --report 2>&1 | grep -E '\`\.databricks' | awk -F'\`' '{print $2}' | sort -u | wc -l` → 18.
  - "canonical tier drops 103 → 85 (approx)" — verified post-diff `audit_public_api_surface.py` output; delta ≥ 18 (some names dedup across audit passes).
  - "`__all__` length: 105 → 123" — runtime-verified.
- **writing-tests:1 (tests must fail on revert):** `TestBatch3Promotions` (36 tests) would go red if any batch-3 name removed from `__all__` or rebound outside `.databricks.*`.
- **SU-5 (parse verification):** OK.

## Lead review

Working as: Tech Lead

Affirmative:
- The template pattern held for the third batch — additive edit, extended test class, hostile-review + follow-up ticket for scope-creep candidates. No structural changes to the `__all__` block layout across three batches.
- 148 tests passing (60 + 52 + 36 = 148). Baseline GDAL/Django failures unchanged.
- The audit tool's feedback loop remains reliable: canonical tier tracks the promotion delta batch-over-batch.

Deferred:
- `quote_ident` (peer helper to two promoted SQL builders) is not in `_LAZY_IMPORTS` and was not audit-classified. Follow-up ticket #1210 documents the promotion decision for a future PR.
- The Spark interop helpers (`spark_to_pandas`, `pandas_to_spark`, etc.) are one keystroke from pyspark's built-in `DataFrame.toPandas()`. Docstring pointers are polish, tracked as a v-next follow-up if needed.

## Hostile review responses

Hostile review artifact: `plans/hostile-review-1176-batch3.md` (SHIP WITH REVISIONS verdict).

**F1 (Major, `quote_ident` under-promotion):** Deferred to follow-up ticket #1210. `quote_ident` is not currently in `_LAZY_IMPORTS`, so promoting it would require scope expansion beyond audit-classified canonicals. The template pattern is "batch promotes what the audit classifies; discovered peer-helper gaps get follow-up tickets" — this preserves the audit's authority as the classification source of truth. Inline NOTE in `__all__` cross-references #1210 so the deferral is discoverable.

**F2 (Minor, `spark_to_pandas` naming adjacency to pyspark builtin):** Not-a-defect confirmed by the review itself; a docstring pointer is polish and tracked separately if operator wants it.

## Trivial-investigation declaration

Category: descriptive-docstring-fix
Cannot produce error: Additive metadata edit + additive test cases. Runtime-verified all 18 names resolve to `siege_utilities.databricks.*`.
Evidence: `pytest tests/test_public_api_surface.py --no-cov` → 148 passed. `python -c "import ast; ast.parse(open('siege_utilities/__init__.py').read())"` → OK.
Falsification: If any batch-3 name fails to resolve OR resolves outside `.databricks.*` OR is silently missing from `__all__`.

## Trivial pre-mortem declaration

Third additive metadata batch following the proven template. No behaviour modified. Risk surface is bounded by the runtime-verification loop and the F1 deferral (documented + ticketed).
