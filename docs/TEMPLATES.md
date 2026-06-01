# siege_utilities — Canonical Templates

Derived from forensic review of the codebase (2026-06-01). These templates
describe how functions, modules, and providers **should** be written based
on the best existing examples. New code must follow these patterns;
existing code should converge toward them over time.

Source of truth for *why*: [CLAUDE.md](../CLAUDE.md) (principles) and
[ARCHITECTURE.md](ARCHITECTURE.md) (layer model + tensions).

---

## A. Function template

```python
def function_name(
    required_param: ExplicitType,
    second_param: Union[str, int],
    *,                                    # keyword-only after this
    optional_kwarg: Optional[str] = None,
    on_error: OnErrorStrategy = "raise",  # if failure mode is caller-configurable
) -> ReturnType:
    """One-line summary in imperative mood.

    Longer explanation if behavior has non-obvious aspects — edge cases,
    axis order, temporal semantics, CRS assumptions.

    Args:
        required_param: What it is and what forms are accepted.
        second_param: Constraints (e.g. "must be > 0").
        optional_kwarg: What happens when None (e.g. "uses get_default_crs()").

    Returns:
        What the shape/type is and what it represents.

    Raises:
        ValueError: When inputs violate constraints (with actionable message).
        ImportError: When optional dep is missing (with install instructions).
        DomainError: When the operation itself fails after validation passes.

    Example:
        >>> function_name("06037", "county")
        '06037'
    """
    # 1. Input validation — fail fast with actionable messages
    if not required_param:
        raise ValueError(
            f"required_param must be non-empty; got {required_param!r}"
        )

    # 2. Lazy import of heavy/optional dependencies
    try:
        from pyproj import CRS
    except ImportError as exc:
        raise ImportError(
            "pyproj is required for function_name. "
            "Install with: pip install 'siege-utilities[geo]'"
        ) from exc

    # 3. Core logic — log for side effects, pure for computation
    log.info("Starting operation on %s", required_param)
    result = _do_the_work(required_param, second_param)

    # 4. Return typed result — NEVER return empty on failure (SU-1)
    return result
```

### Conventions

| Concern | Rule |
|---|---|
| **Type hints** | Every parameter and return. `Union` / `Optional` explicit. No `Any` without justification. |
| **Keyword-only** | Use `*` separator for optional parameters to prevent positional ambiguity. |
| **Validation** | First thing in the body. Message names the constraint AND the bad value. |
| **Lazy imports** | `try/except ImportError as exc: raise ImportError("...install with...") from exc` — always chain with `from exc`. |
| **Logging** | `log.info` for side effects, `log.debug` for diagnostic detail. Never `print()`. |
| **Return on failure** | Raise an exception. Never `return []`, `return {}`, `return None` as error signal (SU-1). |
| **Docstring** | NumPy-style (Args/Returns/Raises/Example). Imperative mood for the one-liner. |
| **Error strategy** | Use `OnErrorStrategy` parameter when callers legitimately need different failure modes. |

### Positive examples

| File | Function | Why it's good |
|---|---|---|
| `geo/crs.py` | `reproject_geom()` | Explicit dep guards with `from exc`, axis-order docs, None only when input is None |
| `geo/grids.py` | `infer_grid()` | Pure function, exhaustive validation, actionable messages for every contradiction |
| `geo/geoid_utils.py` | `normalize_geoid()` | Clean signature, ValueError with exact constraint, docstring examples |
| `cache.py` | `ensure_sample_dataset()` | NumPy-style docstring, domain exception on failure, atomic file ops |

---

## B. Module template

### `__init__.py` — PEP 562 lazy loading

```python
"""One-sentence module purpose.

Submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import sys

_LAZY_IMPORTS: dict[str, str] = {}


def _register(names: list[str], module: str) -> None:
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- submodule_a ---
_register([
    "PublicClass",
    "public_function",
], ".submodule_a")

# --- submodule_b ---
_register([
    "AnotherThing",
], ".submodule_b")

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))
```

### Conventions

| Concern | Rule |
|---|---|
| **Lazy loading** | Every package uses `_register()` + `__getattr__`. No `from .sub import *` at module level. |
| **`__all__`** | Derived from the lazy registry. |
| **`__dir__()`** | Includes lazy names for IDE/tab-completion. |
| **ImportError** | Never caught in `__getattr__`. Let it propagate (SU-1, principle 6). |
| **Logging** | Every leaf module: `log = logging.getLogger(__name__)` at module level. |
| **`__all__` in leaf modules** | Every leaf `.py` file defines `__all__` listing its public API. |

### Positive examples

| File | Why it's good |
|---|---|
| `core/__init__.py` | Minimal (49 lines), textbook PEP 562 |
| `geo/__init__.py` | Scales to ~300 registered names across 30+ submodules, same pattern |

### Anti-pattern

`engines/__init__.py` — uses `from .dataframe_engine import *` (star-import, no lazy
loading). Works only because it's a single-file module but breaks the convention.

---

## C. Provider template

Providers follow a three-part contract: ABC, concrete implementations, factory/resolver.

### Interface

```python
from abc import ABC, abstractmethod
from typing import Any


class ProviderBase(ABC):
    """Abstract base class for <domain> providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for this provider."""

    @abstractmethod
    def fetch(self, key: str, **kwargs: Any) -> ResultType:
        """Primary operation — same signature across all providers.

        Args:
            key: The canonical lookup key.
            **kwargs: Provider-specific options.

        Returns:
            Always the same shape (e.g., GeoDataFrame, GeocodingResult).

        Raises:
            ProviderError: On failure (never returns empty silently).
        """

    @abstractmethod
    def list_capabilities(self) -> list[str]:
        """Return what this provider can serve."""

    def is_available(self) -> bool:
        """Return True if deps are installed and service is reachable."""
        return True
```

### Factory/resolver

```python
def resolve_provider(hint: str, **kwargs) -> ProviderBase:
    """Select the appropriate provider based on hint.

    Args:
        hint: Selector (e.g., country code, service name).

    Returns:
        Configured provider instance.

    Raises:
        ValueError: If no provider matches hint.
    """
    ...
```

### Contract consistency rules

| Rule | What it means |
|---|---|
| **Same return shape** | All providers in a family return the same type (e.g., all boundary providers return GeoDataFrame). |
| **Same failure mode** | Raise a typed exception inheriting from the domain base (`BoundaryFetchError`, `IsochroneError`). Never return None/empty. |
| **Same column names** | All providers in a family produce the same column names (e.g., geocoders: `lat`, `lon`, `state_geoid`, `tract_geoid`, `match_quality`). |
| **`is_available()`** | Runtime capability detection — allows composite/fallback patterns. |
| **Typed results** | Use a dataclass with `.success`/`.matched` properties and typed failure stages when the result carries metadata beyond the primary data. |

### Positive examples

| File | Why it's good |
|---|---|
| `geo/providers/batch_geocoder.py` | `BatchGeocoder` ABC + `GeocodingResult` dataclass + `MatchQuality` enum. Clean contract with shared result type. |
| `geo/isochrones.py` | `IsochroneProvider` ABC with typed exceptions, retry with backoff. Never returns empty on failure. |
| `geo/providers/boundary_providers.py` | `BoundaryProvider` ABC with `get_boundary()`, `list_levels()`, `is_available()`, factory via `resolve_boundary_provider()`. |

### Anti-pattern

`CensusTIGERProvider.get_boundary()` (boundary_providers.py:118) — returns `None` on
failure after `log.warning`. Should raise `BoundaryFetchError`. Return type annotation
missing `Optional[...]` making it SU-1 + SU-2 violation.

---

## Cross-cutting conventions

| Concern | Canonical approach | Reference |
|---|---|---|
| **Logging** | `log = logging.getLogger(__name__)` at module top | Every `geo/` module |
| **Credentials** | Env var first, 1Password CLI fallback, never hardcoded | `config/credential_manager.py` |
| **Optional deps** | `try/import/except ImportError as exc: raise ImportError("...") from exc` | `geo/crs.py:243-257` |
| **Exception hierarchy** | All inherit `SiegeError`; domain subtypes (`SiegeGeoError`, `SiegeDataError`) | `exceptions.py` |
| **Error strategy** | `OnErrorStrategy` type + `handle_error()` for caller-configurable behavior | `exceptions.py:81-119` |
| **Typed results** | Dataclass with `.success`/`.matched` properties and typed failure stages | `boundary_result.py`, `batch_geocoder.py` |
| **Validation** | Early, actionable message naming the constraint and the bad value | `grids.py:58-81`, `geoid_utils.py:178-193` |
| **Temporal awareness** | Enum for vintages, threshold-based selection | `census_geocoder.py:103-130` |
