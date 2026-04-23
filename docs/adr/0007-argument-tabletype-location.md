# ADR 0007 — Argument + TableType location

**Status:** Proposed
**Date:** 2026-04-22
**Epic:** ELE-2415 (sub-issue ELE-2417)

## Context

`Argument` (dataclass) and `TableType` (enum) live in `siege_utilities/reporting/pages/page_models.py`. Consumers:

- `reporting/pages/` — their home
- `survey/models.py` — `Chain.table_type: TableType` field
- `survey/crosstab.py` — `TableType` enum values drive dispatch
- `survey/render.py` — returns `Argument` objects
- `analytics/google_slides.py` — consumes `Argument` to render slides

Five consumers across three modules — these types are cross-cutting, not reporting-internal. The `page_models` filename also suggests "one of many page types" which is no longer accurate after `Argument` moved in.

`docs/INTENT.md` flagged this as divergence D8.

## Decision

**Move `Argument` and `TableType` to `siege_utilities/reporting/models.py`. Keep `reporting/pages/page_models.py` for actual Page subclasses (`TitlePage`, `TableOfContentsPage`, `ContentPage`).**

Why `reporting/models.py` and not `core/models.py`:
- Only 3 modules consume these types; promotion to `core/` is premature
- They're conceptually reporting-domain (a "table type" and an "argument" are both reporting concepts, even if survey and analytics also use them)
- Keeps the import graph honest: survey and analytics depend on reporting, not the other way around

## Consequences

**Positive:**
- Filename matches content (`reporting/models.py` instead of `pages/page_models.py` for things that aren't pages)
- Single source of truth per-type
- Lower risk of future divergence (no more "is this a page concern or not?")

**Negative:**
- Existing imports `from siege_utilities.reporting.pages.page_models import Argument, TableType` need to change. Fix: re-export from old path with `DeprecationWarning` for one minor version.
- Mild increase in module count.

## Alternatives considered

1. **Keep in `page_models.py`** — rejected. Filename lies about contents.
2. **Move to `core/models.py`** — rejected. Promotion without enough cross-cutting users; circular-dependency risk if `core/` grows to include domain types.
3. **Move to a new `siege_utilities/models/` top-level package** — rejected. Over-indexes on "shared types" when we have only two cross-cutting types today. If the count grows to 5+, revisit.

## Migration

- Phase M2 (per ARCHITECTURE.md): create `reporting/models.py` with the new canonical location.
- Old `reporting/pages/page_models.py` re-exports with `DeprecationWarning` for one minor version.
- Update `survey/*.py` and `analytics/google_slides.py` imports in the same PR.
- Existing notebooks and external callers have one release to migrate.

## References

- `docs/INTENT.md` D8
- `reporting/pages/page_models.py` (current location)
- `survey/models.py`, `survey/crosstab.py`, `survey/render.py`, `analytics/google_slides.py` (consumers)
