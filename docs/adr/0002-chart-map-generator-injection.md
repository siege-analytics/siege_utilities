# ADR 0002 — Chart / map generator injection

**Status:** Proposed
**Date:** 2026-04-22
**Epic:** ELE-2415 (sub-issue ELE-2417)

## Context

`chain_to_argument(chain, headline, narrative, *, chart_generator=None, map_generator=None)` accepts two optional generator kwargs. Neither is honored at runtime — as of PR #391 both raise `NotImplementedError` if set, so callers don't silently lose customizations they thought they were providing.

The kwargs exist because earlier design imagined plugin-style chart theming via dependency injection. In practice no caller has asked for this, and chart theming today is handled through `reporting.client_branding` (which configures a singleton `ChartGenerator`).

## Decision

**Remove the `chart_generator` and `map_generator` kwargs from `chain_to_argument` in the next major version. Until then, keep the `NotImplementedError` guard so callers get a loud signal rather than silent no-op.**

Chart theming stays in `reporting.client_branding`. A client that wants different chart styling sets the branding config, not injects a different generator.

## Consequences

**Positive:**
- One less dead knob in the public API
- `chain_to_argument` signature gets simpler
- Removes the bait — interface-integrity violation (ADR follows `coding/python-patterns/SKILL.md`)

**Negative:**
- A future caller who genuinely wants to inject a pre-configured generator has to rebuild that path deliberately
- Acceptable because we'd re-introduce with a plan at that point, not speculatively

## Alternatives considered

1. **Wire the kwargs through** — rejected. No caller today uses them; speculative feature.
2. **Keep raising NotImplementedError indefinitely** — rejected. Leaving broken optional kwargs in a signature is worse than removing them.
3. **Replace with a `branding: BrandingConfig | None = None` kwarg** — deferred. If the branding path grows, this ADR can be superseded by a new one that adds per-call branding explicitly.

## Migration

- Next minor release: emit `DeprecationWarning` when either kwarg is passed (replacing `NotImplementedError`).
- Next major release: remove the kwargs from the signature.
- CHANGELOG entry for both steps.

## References

- `survey/render.py::chain_to_argument`
- PR #391 (introduced the NotImplementedError guard)
- `coding/python-patterns/SKILL.md` — "Interface integrity" section
