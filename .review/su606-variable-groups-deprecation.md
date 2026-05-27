# Self-Review: SU#606 — VARIABLE_GROUPS Deprecation

**Domain:** software engineering
**Geospatial cross-cut:** no
**Trivial-against-state:** yes — behavioral change is warning-only, no functional change

## Assumptions

1. `_DeprecatedDict` wrapper emits warning on first access only (not every access).
2. Internal `VariableRegistry` uses `_VARIABLE_GROUPS_DATA` directly, avoiding the warning.
3. External callers accessing `VARIABLE_GROUPS` get a clear deprecation message pointing to `CensusCatalog`.

## Peer Review (Junior)

- 6 tests: warning emission, warn-once, data accessibility, iteration, get, registry-no-warn.
- `_DeprecatedDict` is minimal — subclasses `dict`, overrides access methods.
- Existing code continues to work; only the warning is new.

## Lead Review (Adversarial)

- **Q: Why not `__getattr__` module-level?** A: Module-level `__getattr__` wouldn't work for an already-defined name. The dict wrapper is cleaner and more explicit.
- **Q: `_warned` is class-level — thread-safe?** A: Boolean assignment is atomic in CPython. Worst case: two threads both see `False` and both warn once. Acceptable.

## Quantified Claims

- 6 tests, all passing
- 0 functional changes to existing behavior
