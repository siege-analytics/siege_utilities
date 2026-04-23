# ADR 0001 — Chain → Argument pipeline ownership

**Status:** Accepted (supersedes prior "Proposed" draft)
**Date:** 2026-04-22 (revised 2026-04-23)
**Epic:** ELE-2415 (implemented under ELE-2441)

## Context

`survey.render.chain_to_argument(chain, ...)` and `Chain.to_argument(headline, narrative)` both produced an `Argument` from a `Chain`. The method delegated to the function. This was a dual-surface API with no compensating value — one behavior, two entry points.

## Decision

**Delete `Chain.to_argument()`. `chain_to_argument()` is the sole entry point.**

Chain is a `@dataclass` — its nature is *state*, not *behavior*. Rendering a Chain into an Argument is an operation *performed on* Chain by the render module, not a property of Chain itself.

## Consequences

**Positive:**
- Single rendering contract; no drift between method and function.
- Chain stays pure data — consistent with `View`, `Cluster`, `Stack` (none of which carry rendering methods either).
- `chain_to_argument` is the one place config kwargs (chart_generator, map_generator per ADR 0002) live.

**Negative:**
- Callers using `chain.to_argument(...)` must switch to `chain_to_argument(chain, ...)`. Small migration; the method was recent (added in PR #391).

## Alternatives considered

1. **Keep the method as a thin delegate.** Rejected. Dataclass purity wins — every data model in `survey/models.py` would eventually want its own `.to_X()` method and the model module would become a rendering module.
2. **Method canonical, function delegates.** Rejected on the same grounds.
3. **Keep both first-class.** Rejected. Guarantees drift.

## Migration

- Delete `Chain.to_argument` method on `survey/models.py`.
- Grep every caller using the method form; replace with the function form.
- CHANGELOG entry: `Chain.to_argument()` removed; use `survey.render.chain_to_argument(chain, ...)`.

## References

- `survey/render.py`
- `survey/models.py`
- `docs/INTENT.md` D8
- ELE-2441 (implements this decision + ADR 0002)
