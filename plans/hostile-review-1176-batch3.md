# Hostile review — #1176 batch 3 (databricks canonicals)

## Findings

### F1 — Under-promotion: `quote_ident` omitted despite being in submodule `__all__` (Major)

The audit promoted 18 of 19 public symbols in `siege_utilities.databricks.*`. The omitted symbol is `quote_ident` (defined at `siege_utilities/databricks/lakehouse_federation.py:35`, exported via that module's `__all__` at line 30, and re-exported by `unity_catalog.py`).

It sits alongside `build_foreign_table_sql` and `build_schema_and_table_sync_sql` — both of which WERE promoted — in the same module and same `__all__`. There is no plausible rationale for promoting the two SQL builders that CALL `quote_ident` while leaving `quote_ident` itself unpromoted, since a consumer building a foreign-table sync workflow will need to quote identifiers alongside the builder helpers.

Two acceptable resolutions:

1. Add `quote_ident` to the batch-3 promotion (19 symbols; extend `BATCH_3` list in the test). This is the low-risk option and matches the "if it's in a submodule `__all__` and its callers are promoted, promote it too" pattern used in batches 1/2.
2. Document the exclusion rationale in `docs/public-api-audit.md` (or wherever batch-3 was decided) — e.g., "internal helper; consumers should never need to hand-quote."

Given the symbol is a pure string helper with no dep-gate and no side effect, option 1 is the natural choice.

### F2 — Naming near-collision with pyspark idiom (Minor)

`spark_to_pandas` (top-level function) is one keystroke away from the widely-used `pyspark.sql.DataFrame.toPandas()` method. Runtime-collision check is clean (verified: `hasattr(pyspark.sql, 'spark_to_pandas') == False`), so this is not a defect — but a docstring note pointing users at `DataFrame.toPandas()` when they want the built-in path would reduce confusion. Non-blocking.

## Verifications performed

1. **Cross-module collision grep** — for each of the 18 names, `grep -rn "^def NAME\|^class NAME"` across `siege_utilities/`. Each name has exactly ONE definition, all under `siege_utilities/databricks/*.py`. Clean.
2. **Runtime resolution** — imported `siege_utilities` and confirmed all 18 resolve to `siege_utilities.databricks.<submodule>` module paths (18/18 OK).
3. **Extension-tier audit** — grepped all public `def`/`class` in `siege_utilities/databricks/*.py`; found 19 public symbols; 18 promoted, 1 omitted (`quote_ident`) — see F1.
4. **Batch 1 + 2 regression** — ran `pytest tests/test_public_api_surface.py`: 148 passed (coverage-gate failure unrelated).
5. **Dep-gate probe** — batch 3 leverages the existing lazy `__getattr__` shim (no changes); dep-gated symbols continue to raise on attribute access when deps missing, per the pattern established in batches 1/2.
6. **pyspark/pandas namespace collision** — verified `pandas_to_spark`, `spark_to_pandas`, `geopandas_to_spark`, `spark_to_geopandas` are absent from `pandas`, `pyspark.sql`, and `pyspark.sql.DataFrame` namespaces. No shadowing risk. See F2 for a naming-adjacency note.
7. **Diff hygiene** — working-tree change is 19 lines in `__init__.py` + 38 lines in test file; no incidental edits.

## Verdict

**SHIP WITH REVISIONS** — F1 is a real audit gap: `quote_ident` should be promoted alongside its two callers or the exclusion should be documented. F2 is advisory only.
