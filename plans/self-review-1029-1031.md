---
ticket: "#1029, #1030, #1031"
scope: "connectors/_adapters.py, connectors/_dedup.py, connectors/__init__.py, reporting/chart_types.py"
---

# Self-Review — #1029/#1030/#1031 CRM adapters, pipeline chart, dedup

## Junior Assessment

**#1029 — Adapters:** Added `connectors/_adapters.py` with four pure functions:
- `pipeline_adapter()` — opportunity stages → pipeline chart input
- `timeseries_adapter()` — activity timestamps → time-series chart input
- `geographic_adapter()` — addresses → geocoding-ready DataFrame
- `tabular_adapter()` — any CRM data → presentation-ready table

**#1030 — Pipeline chart:** Registered `sales_pipeline` chart type in
`ChartTypeRegistry._register_default_chart_types()` with stage_column,
value_column, stage_order, orientation, and color coding by stage
category (open/won/lost).

**#1031 — Dedup:** Added `connectors/_dedup.py` with `crm_dedup_pipeline()`.
Composes `normalize_name_v1` and `uuid5_from_seed` with CRM DataFrames
to produce a merge table with canonical IDs.

## Lead Assessment

**Adapter purity:** All four adapters are DataFrame-in, DataFrame-out
with no side effects. Empty inputs return empty DataFrames with correct
columns. `pipeline_adapter()` uses CategoricalDtype for stage ordering.

**Pipeline chart:** Registered as `statistical` category alongside
bar/line/scatter. Stage ordering is configurable (not alphabetical).
Color map supports open/won/lost stage categories. Works with any
CRM's opportunity data via the adapter.

**Dedup pipeline:**
- CRM_NAMESPACE is a fixed UUID for deterministic cross-session results
- normalizer parameter defaults to normalize_name_v1 but accepts any
  str→str callable for future v2
- "Last, First" limitation is documented in the docstring — not
  silently mishandled
- match_confidence is 1.0 for exact normalized match (v1)
- Log output reports canonical ID count and cross-system match count
- SU-1: empty inputs return empty DataFrames with correct columns

## Trivial-investigation declaration

Adapters are thin transforms. Pipeline chart follows existing
ChartType registration pattern. Dedup composes existing identifiers/
functions.

## Trivial pre-mortem declaration

Two new files (adapters, dedup) + one chart type registration in
existing file. No existing behavior modified.
