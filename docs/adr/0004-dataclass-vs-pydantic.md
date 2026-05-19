# ADR 0004 — Dataclass vs Pydantic boundary

**Status:** Proposed
**Date:** 2026-04-22
**Epic:** ELE-2415 (sub-issue ELE-2417)

## Context

The library uses both patterns:
- `survey.models` (`Chain`, `Cluster`, `Stack`, `View`, `WeightScheme`) — `@dataclass`
- `config.models` (`UserProfile`, `ClientProfile`, `ContactInfo`, `BrandingConfig`, `ReportPreferences`) — Pydantic `BaseModel`

No written rule says which to use where. New contributors default to whichever they saw last.

Pydantic's strengths are runtime validation, JSON schema generation, and strict field discipline. Its costs are import-time overhead (~50ms), a dependency on Pydantic v2, and harder interop with `numpy` / `pandas` types.

Dataclasses are lighter but offer no validation — mistyped fields silently work until they don't.

## Decision

**New external-facing types (user config, API request/response shapes, serialized outputs, CLI args) use Pydantic `BaseModel`. Internal computation types (pipeline intermediates) use `@dataclass`.**

A type is "external-facing" if it crosses a trust boundary: read from or written to disk, loaded from YAML/JSON/TOML, returned to notebooks as a published API, deserialized from an HTTP response.

A type is "internal" if it exists only during a function's execution — passed between helpers, never persisted, not part of the published surface.

| Type | Kind | Reason |
|---|---|---|
| `UserProfile`, `ClientProfile` | Pydantic | Loaded from YAML, validates fields at read time |
| `Chain`, `Cluster`, `Stack`, `View` | Dataclass | Pipeline intermediates, never serialized |
| `Argument`, `TableType` | **Dataclass** (current) — likely promote one level, see ADR 0007 | Intermediate between survey and reporting |
| `BoundaryFetchResult` (geo) | Dataclass | Internal |
| `RDHDataset` (data/RDH) | Dataclass today; **candidate for Pydantic** because it's deserialized from the RDH API | Migrate under future work |
| Future `SiegeConfig` type | Pydantic | User-facing config |

## Consequences

**Positive:**
- Clear rule for new contributors
- Pydantic overhead isolated to types that benefit from validation
- Dataclass stays for hot computation

**Negative:**
- Some types (e.g. `RDHDataset`) currently in the "internal" category are really "boundary" and should migrate. One-off migration cost.
- Mixed codebase is slightly more friction for readers who have to remember which rule applies.

## Alternatives considered

1. **All-Pydantic** — rejected. Overkill for intermediate types that never cross a boundary.
2. **All-dataclass** — rejected. Loses validation at trust boundaries where it matters most.
3. **attrs instead of either** — rejected. Adds a third pattern; existing code commits to dataclass OR Pydantic, not attrs.

## Migration

- Document the rule in `coding/python-patterns/` if not already covered
- Audit `data/redistricting_data_hub.py::RDHDataset` for Pydantic candidacy (ELE-2418 notes this under D3)
- Do not rewrite existing dataclass types that fit the internal-only rule

## References

- `survey/models.py` (dataclass family)
- `config/models/*.py` (Pydantic family)
- `data/redistricting_data_hub.py::RDHDataset` (current dataclass; migration candidate)
