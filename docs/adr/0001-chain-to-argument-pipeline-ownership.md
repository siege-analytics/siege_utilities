# ADR 0001 — Chain → Argument pipeline ownership

**Status:** Proposed
**Date:** 2026-04-22
**Epic:** ELE-2415 (sub-issue ELE-2417)

## Context

The `Chain → Argument` pipeline has two entry points today:

1. `survey.render.chain_to_argument(chain, headline, narrative, ...)` — module-level function
2. `Chain.to_argument(headline, narrative)` — instance method that internally calls (1)

Both do the same thing; the method is a thin convenience. With two entry points, future changes to the pipeline (adding kwargs, changing default behavior) risk drift where one path behaves differently from the other.

## Decision

**The module-level function `survey.render.chain_to_argument` is canonical. `Chain.to_argument` is a thin delegate that takes no additional arguments beyond `headline` and `narrative` and forwards everything to the module function.**

`Chain.to_argument` stays because the fluent form reads nicely in notebooks:

```python
arg = chain.to_argument("Headline", "Narrative prose")
# vs
arg = chain_to_argument(chain, "Headline", "Narrative prose")
```

All configuration knobs (chart_generator, map_generator once unblocked by ADR 0002) live on the module function. The method does not expose them.

## Consequences

**Positive:**
- One place to change pipeline defaults
- Method-vs-function choice is ergonomic, not architectural
- Tests cover both paths with a single fake (`monkeypatch.setattr(render_mod, 'chain_to_argument', fake)`)

**Negative:**
- Minor: callers who want to inject a custom chart_generator MUST use the module function, not the method
- Acceptable: documented in `Chain.to_argument` docstring

## Alternatives considered

1. **Method is canonical** — rejected. Methods on data classes should be thin; complex multi-arg rendering doesn't belong on `Chain`.
2. **Remove the method** — rejected. The fluent form is too useful in notebooks to drop.
3. **Keep both as first-class siblings** — rejected. Two canonical APIs guarantees drift.

## Migration

- Current code already reflects the decision. Confirm no callers pass config-like kwargs via `chain.to_argument(...)`.
- Add a note to `Chain.to_argument` docstring: "for full control use `render.chain_to_argument`."

## References

- `survey/render.py`
- `survey/models.py::Chain.to_argument`
- `docs/INTENT.md` D9 (dual entry points divergence)
