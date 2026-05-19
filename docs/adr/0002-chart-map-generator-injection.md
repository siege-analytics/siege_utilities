# ADR 0002 — Chart / map generator injection

**Status:** Accepted (supersedes prior "Proposed" draft with reversed conclusion)
**Date:** 2026-04-22 (revised 2026-04-23)
**Epic:** ELE-2415 (implemented under ELE-2441)

## Context

`chain_to_argument(..., chart_generator=None, map_generator=None)` accepts generator kwargs that are not honored at runtime — they either raise `NotImplementedError` on non-None, or silently no-op, depending on which code path you land on. Inconsistency is itself a bug.

The kwargs point at real use cases:

1. **Ad hoc charts without branding configured.** Users running a one-off script shouldn't need a `ClientBrandingManager` setup to render a figure.
2. **Override branding on a one-off basis.** A user with branding configured occasionally wants a chart rendered differently without mutating global state.
3. **Swap the whole render backend** (matplotlib → Plotly, etc.) without monkeypatching.

An earlier draft of this ADR proposed dropping the kwargs on YAGNI grounds. That was wrong: the kwargs are already in the signature, callers expect them to work, and the use cases are concrete — not speculative.

## Decision

**Honor `chart_generator` and `map_generator` on `chain_to_argument`. Drop them from `ChartTypeRegistry.create_chart`.**

- `chart_generator=None` → construct a default `ChartGenerator()` (picks up active profile branding if present; otherwise library defaults). No branding required for sensible output.
- `chart_generator=<instance>` → use the caller's generator as-is. Caller controls style: differently-branded, un-branded, alternative backend.
- Same pattern for `map_generator`.
- `ChartTypeRegistry.create_chart` is an internal dispatcher — generators should be resolved before we reach it. Drop the kwargs from there.

**Type discipline:** duck type the generator interface for now. Document the expected methods (`create_bar_chart`, `create_heatmap`, etc.) in `chain_to_argument`'s docstring. Formalize as a `Protocol` only when a second backend (e.g., Plotly) lands — adding the Protocol is additive and won't break duck-typed callers.

## Consequences

**Positive:**
- Kwargs do what their names say.
- Ad hoc use is possible without branding setup.
- Override path is real; no monkeypatching needed.
- Room to grow into alternative backends without redesigning the signature.

**Negative:**
- Slightly more wiring in `chain_to_argument` (resolve generator, dispatch).
- Docstring becomes load-bearing — callers rely on it for the interface. Acceptable in a small library.

## Alternatives considered

1. **Drop the kwargs entirely.** Rejected after reconsideration. Dropping removes real capability (ad hoc / override / backend swap) that the audience actually uses.
2. **Define a formal `ChartGeneratorProtocol` now.** Rejected for this pass. Premature formalization without a second backend. Revisit when Plotly or another renderer lands.
3. **Replace with a `branding: BrandingConfig | None = None` kwarg.** Rejected — conflates branding with rendering backend.

## Migration

- Implement the dispatch in `chain_to_argument`: if generator is None, construct a default; otherwise use as-is.
- Remove `chart_generator` / `map_generator` from `ChartTypeRegistry.create_chart` signature.
- Update `chain_to_argument` docstring with the interface contract and examples (no-branding, override, custom backend).
- Add tests for all three paths.

## References

- `survey/render.py::chain_to_argument`
- `reporting/chart_types.py::ChartTypeRegistry`
- `docs/INTENT.md` D9
- ELE-2441 (implements this decision + ADR 0001)
