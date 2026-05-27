# Self-Review: SU#608 — Overlay Registry

**Domain:** software engineering
**Geospatial cross-cut:** yes (extensible overlay system for place history)
**Trivial-against-state:** partially — standard registry pattern, but correctly integrated with ABC

## Assumptions

1. `PlaceHistoryOverlay` is the ABC — subclasses implement `name` and `fetch()`.
2. `OverlayRegistry` supports both decorator and imperative registration.
3. Class-registered overlays are lazily instantiated on first `get()`.
4. Instance registration takes priority over class registration for same name.
5. Failed instantiation returns None (logged, not raised).
6. Global `overlay_registry` singleton is the default for place_history().

## Peer Review (Junior)

- ABC: 4 tests (cannot instantiate, concrete, fetch, is_available override)
- Registry: 15 tests (empty, instance reg, type checks, decorator, lazy init, list, unregister ×3, clear, unknown, init failure, instance override)
- Global: 1 test
- 20 total tests passing

## Lead Review (Adversarial)

- **Q: Why lazy instantiation for decorated classes?** A: Overlays may import heavy dependencies (Django, geopandas). Deferring construction until `get()` avoids import-time failures when overlays are registered but not used.
- **Q: Why instance overrides class?** A: Allows test code to inject mock overlays without modifying class registration. The instance is already constructed, so it's preferred.

## Quantified Claims

- 20 new tests, all passing
- ~160 lines of implementation (ABC + registry)
- ~180 lines of tests
