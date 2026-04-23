# ADR 0005 — Lazy-import convention

**Status:** Proposed
**Date:** 2026-04-22
**Epic:** ELE-2415 (sub-issue ELE-2417)

## Context

Heavy optional dependencies (`geopandas`, `shapely`, `pyproj`, `pyspark`, `reportlab`, `weightipy`, `snowflake-connector-python`, …) cause ImportError cascades in slim environments. Today's codebase uses several patterns, inconsistently:

| Pattern | Example | Problem |
|---|---|---|
| Module-top `try: import X / except: HAS_X = False` | `data/redistricting_data_hub.py` | OK for bool gating; bad when paired with stub functions that silently no-op |
| PEP 562 `__getattr__` at package `__init__.py` | `core/__init__.py`, `geo/__init__.py`, `distributed/__init__.py` | Good; on first access pulls the submodule |
| Function-level import | Various | Good for truly-lazy paths |
| Bare module-top import | `reporting/analytics/polling_analyzer.py::import ChartGenerator` | Cascades — module can't be imported without reportlab |

PR #389 surfaced the polling_analyzer case: `pytest.importorskip('reportlab')` fixed tests but runtime still raises ImportError on import.

## Decision

**Three rules.**

### Rule 1. Package `__init__.py` uses PEP 562 `__getattr__` for submodules with heavy deps

```python
# siege_utilities/reporting/__init__.py
import importlib, sys
_LAZY_IMPORTS = {'ChartGenerator': 'chart_generator', 'PDFReportGenerator': 'report_generator'}

def __getattr__(name):
    if name in _LAZY_IMPORTS:
        module = importlib.import_module(f".{_LAZY_IMPORTS[name]}", __package__)
        return getattr(module, name)
    raise AttributeError(name)
```

`from siege_utilities.reporting import ChartGenerator` only pulls `reportlab` when `ChartGenerator` is actually accessed. The module itself stays importable without heavy deps.

### Rule 2. Module body uses function-level imports for heavy deps when they're used rarely

```python
def generate_pdf(report):
    """Build a PDF — needs reportlab."""
    from reportlab.platypus import SimpleDocTemplate
    ...
```

Only incur the import cost when the function is called, not when its module is first imported.

### Rule 3. Module-top `try/except ImportError` with `HAS_X = False` is OK for feature-gating booleans ONLY

```python
try:
    import scipy
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    scipy = None

def significance_test(data, alpha):
    if HAS_SCIPY:
        return scipy.stats.norm.ppf(1 - alpha / 2)
    if alpha in _FALLBACK_Z_CRIT:
        return _FALLBACK_Z_CRIT[alpha]
    raise SignificanceError(...)  # explicit — no silent no-op
```

**Anti-pattern** to avoid: the same construct but with stub functions that silently return `None` / `pass`. That's category (b) silent-swallow per `docs/FAILURE_MODES.md`. If the dep is missing and the function is called, it MUST raise — never return a lie.

## Consequences

**Positive:**
- Slim-install users can import siege_utilities without heavy deps
- Heavy-dep code paths stay discoverable (not hidden behind import-time try/except)
- Consistent rule for new contributors

**Negative:**
- Every `__init__.py` with heavy deps needs a `_LAZY_IMPORTS` table (one-time cost)
- Some `from pkg import Thing` patterns become slightly slower on first call (one-time; cached thereafter)

## Alternatives considered

1. **Eager imports everywhere** — rejected. Breaks slim envs.
2. **Runtime feature detection via `importlib.util.find_spec`** — rejected. Adds complexity without clearer semantics.
3. **Optional-deps as hard deps** — rejected. Install size and CI speed matter.

## Migration

Priority sites surfaced by ELE-2418 / ELE-2419:
1. `reporting/analytics/polling_analyzer.py` — move `ChartGenerator` import inside methods OR move the class into a lazy-loaded subpackage
2. Audit every `try: import X / except: def stub...` — confirm stubs RAISE on call rather than silently return
3. Add `_LAZY_IMPORTS` to `reporting/__init__.py` if it doesn't have one already

Full audit is a follow-up PR under ELE-2420.

## References

- `core/__init__.py`, `geo/__init__.py`, `distributed/__init__.py` — existing good examples
- `reporting/analytics/polling_analyzer.py` — known violation
- `data/redistricting_data_hub.py` — mixed-pattern example
- PR #389 — fixed the tests but not the runtime
- `docs/FAILURE_MODES.md` CC4 — ImportError cascade pattern
