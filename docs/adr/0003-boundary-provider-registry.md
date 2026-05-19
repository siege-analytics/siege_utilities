# ADR 0003 — BoundaryProvider registry pattern

**Status:** Proposed
**Date:** 2026-04-22
**Epic:** ELE-2415 (sub-issue ELE-2417)

## Context

Today `resolve_boundary_provider(country='US', **kwargs)` hardcodes a country-code set:

```python
_US_CODES = frozenset({'US', 'USA', 'PR', 'PRI', 'GU', 'GUM', 'VI', 'VIR', 'AS', 'ASM', 'MP', 'MNP'})

def resolve_boundary_provider(country: str = 'US', **kwargs):
    if country.upper() in _US_CODES:
        return CensusTIGERProvider()
    return GADMProvider(**kwargs)
```

This works for the current two providers but:
- Adding a third provider (e.g. the new `RDHProvider` from #386) requires modifying `resolve_boundary_provider` AND possibly `_US_CODES`
- Client-specific providers (e.g. a custom state-level source) can't be plugged in without forking
- The factory can't express "which provider handles best for X" — it's binary US vs. not

## Decision

**Adopt a registry pattern. Each `BoundaryProvider` subclass declares which countries/levels it accepts; `resolve_boundary_provider` iterates registered providers.**

```python
class BoundaryProvider(ABC):
    # ... existing abstract methods ...

    @classmethod
    @abstractmethod
    def accepts(cls, country: str, level: str) -> bool:
        """Return True if this provider can satisfy a request for the given country + level."""


_REGISTRY: list[type[BoundaryProvider]] = []

def register_provider(cls: type[BoundaryProvider]) -> type[BoundaryProvider]:
    """Decorator; adds the class to the dispatch registry."""
    _REGISTRY.append(cls)
    return cls


@register_provider
class CensusTIGERProvider(BoundaryProvider):
    @classmethod
    def accepts(cls, country: str, level: str) -> bool:
        return country.upper() in {'US', 'USA', 'PR', 'PRI', ...}
    ...

@register_provider
class GADMProvider(BoundaryProvider):
    @classmethod
    def accepts(cls, country: str, level: str) -> bool:
        return level in ('country', 'admin1', 'admin2', 'admin3')
    ...


def resolve_boundary_provider(country: str = 'US', level: str = 'county', **kwargs) -> BoundaryProvider:
    for cls in _REGISTRY:
        if cls.accepts(country, level):
            return cls(**_filter_kwargs(cls, kwargs))
    raise NoProviderError(
        f"no registered BoundaryProvider accepts country={country!r} level={level!r}; "
        f"registered: {[c.__name__ for c in _REGISTRY]}"
    )
```

External callers (e.g. siege-analytics client configs) can register their own providers at import time:

```python
from siege_utilities.geo.boundary_providers import register_provider, BoundaryProvider

@register_provider
class MyCustomStateProvider(BoundaryProvider):
    ...
```

## Consequences

**Positive:**
- Adding a provider is self-contained (one class, one decorator)
- External providers are a first-class extension point
- `resolve_boundary_provider` becomes the only dispatch point; no more scattered country-code lists
- The dispatch function can also be used by the test suite to assert "every provider is callable"

**Negative:**
- Registration happens at import time; provider classes must be imported before dispatch to be registered. OK for core providers (always imported); requires callers who add custom providers to import their module before calling resolve.
- Ambiguity if two providers accept the same country/level — handled by registration order (first-registered wins) OR by adding a `priority` attribute. Pick at implementation time.

## Alternatives considered

1. **Keep the factory, extend `_US_CODES`** — rejected. Doesn't scale past 3-4 providers.
2. **Configuration-file driven dispatch** — rejected. Over-engineered; registration-by-decorator is more Pythonic.
3. **Protocol-based, no registry; caller passes provider** — rejected. Loses the convenience of `resolve_boundary_provider('US')`.

## Migration

- Add `BoundaryProvider.accepts` as abstract in a minor release; default implementations preserve current behavior for `CensusTIGERProvider` and `GADMProvider`
- Migrate `resolve_boundary_provider` to iterate the registry
- Register `RDHProvider` explicitly — confirms the pattern
- Add a test that asserts `resolve_boundary_provider("US", "county")` returns a CensusTIGER provider (behavior preservation)

## References

- `geo/boundary_providers.py::resolve_boundary_provider`
- `geo/boundary_providers.py::_US_CODES`
- PR #386 (added `RDHProvider` — exercises the "how do we add a provider" question)
- `coding/python-patterns/SKILL.md` — "Interface integrity" section
