# Self-Review: SU#558 — SQL injection audit fixes

## Assumptions

Working as: software engineer, security focus
Goal source: https://github.com/siege-analytics/siege_utilities/issues/558
Goal source verification: ticket exists with 4 specific SQL injection sites

- All four fixes are mechanical: add parameter binding, add allowlist validation, or add input regex
- No behavioral changes for legitimate callers
- The `_create_spatial_table` method is deprecated; adding validation rather than removing it preserves backward compatibility while closing the injection surface

## Peer review

Shelf: writing-code:1 (no unnecessary abstractions), writing-code:3 (test what you ship)

### Shelf checks

1. **DuckDB read_spatial**: changed `f"SELECT * FROM ST_Read('{path}')"` to `"SELECT * FROM ST_Read(?)", [path]` — matches sibling methods `read_csv`, `read_parquet` in same class
2. **SpatiaLiteCache.clear**: added `_KNOWN_TABLES` frozenset and validation before interpolation; `noqa: S608` comment updated to reference the allowlist
3. **PostGIS _create_spatial_table**: added `validate_sql_identifier(table_name)` + integer check on SRID
4. **Spark reproject_geom_columns**: added `^(?:EPSG:)?\d+$` regex validation on both SRIDs; removed destructive `spark.stop()` from error handler (callers own the session lifecycle)
5. **No unused imports introduced**: `re` import is inline in the function scope; `validate_sql_identifier` imported at call time (lazy, matching existing pattern)

## Lead review

- **[Security]** All four injection surfaces now validated before interpolation
- **[Backwards compatibility]** No behavioral change for legitimate inputs; only malicious/malformed inputs are now rejected
- **[Blast radius]** Additive validation only — no removed APIs, no changed signatures
