---
ticket: "#1017"
scope: "connectors/salesforce.py, connectors/__init__.py"
---

# Self-Review — #1017 Salesforce SOQL query builder

## Junior Assessment

Added `SOQLQuery` fluent builder class and `soql()` escape-hatch method:
- `SOQLQuery`: `select()`, `from_()`, `where()`, `where_raw()`, `order_by()`,
  `limit()`, `offset()`, `build()`
- `where()` supports: eq, ne, gt, gte, lt, lte, in_, not_in, like, is_null
- `_soql_literal()` module-level helper for value→SOQL conversion
- `soql()` method on SalesforceConnector accepts raw strings or SOQLQuery objects
- Registered `SOQLQuery` in `connectors/__init__.py` lazy loader

## Lead Assessment

**Sentinel pattern:** `_UNSET = object()` at module level. Comparison via
`is not _UNSET` — correct identity check, not equality. This allows
`where("field", eq=None)` to produce `field = null` (the value IS set, to
None) while omitting the condition entirely when `eq` is not passed.

**Type coercion in `_soql_literal()`:** bool before int/float (Python
`isinstance(True, int)` is True). None→null, str→escaped single-quoted.
Matches the existing `_soql_condition()` from #1016.

**Relationship queries:** Supported naturally — `select("Account.Name")`
just includes the dotted field in the SELECT clause. SOQL handles the
rest.

**Order and validation:** `build()` raises ValueError for missing
`from_()` or empty `select()`. ORDER BY before LIMIT before OFFSET
matches SOQL syntax.

**`soql()` method:** Accepts `str | SOQLQuery`. Raw strings pass through
unchanged. SOQLQuery objects call `.build()`. Results go through
`_query_all()` for pagination. Empty results return empty DataFrame
with warning (SU-1).

**`where_raw()`:** Escape hatch for conditions the builder can't express
(subqueries, INCLUDES/EXCLUDES, date literals like `LAST_N_DAYS:30`).

## Trivial-investigation declaration

SOQL syntax follows Salesforce SOQL reference. Fluent builder pattern
is standard (no external dependencies).

## Trivial pre-mortem declaration

New class + one new method on existing connector + one-line init change.
Existing `_build_soql()` and `_soql_condition()` from #1016 unchanged.
