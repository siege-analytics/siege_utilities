# Siege Utilities Coding Style

This document defines contribution standards for code quality, review consistency, and maintainability.

## Scope

Applies to all Python code under `siege_utilities/`, tests under `tests/`, and supporting scripts under `scripts/`.

## Core Principles

- Prefer clear, predictable code over clever code.
- Prefer small, composable functions over large multi-purpose functions.
- Prefer explicit behavior over hidden side effects.
- Prefer deterministic behavior and typed interfaces over implicit conventions.

## Functional vs OOP

- Default to functional style for stateless transformations, adapters, and data processing steps.
- Use classes only when they provide clear value: lifecycle state, cohesive domain behavior, plugin boundaries, or protocol implementations.
- Do not introduce classes as namespaces for unrelated functions.
- Keep object state minimal and explicit; avoid mutation-heavy flows.

## Iterative vs Recursive

- Prefer iterative implementations for production paths.
- Use recursion only when the domain is naturally recursive and depth is bounded and tested.
- If recursion is used, include explicit guardrails for depth and failure behavior.

## Naming Conventions

- Modules and files: `snake_case.py`.
- Functions and variables: `snake_case`.
- Classes and exceptions: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Booleans should read as predicates: `is_valid`, `has_geometry`, `should_retry`.
- Avoid one-letter names except in local numeric loops (`i`, `j`) with tight scope.
- Avoid ambiguous abbreviations unless they are domain-standard (`gdf`, `srid`, `fips`, `geoid`).

## Function and Method Signatures

- Every public function must include type hints for parameters and return type.
- Keep signatures stable and explicit; avoid positional-only surprises.
- Prefer keyword arguments for optional behavior toggles.
- Keep required parameters first, optional parameters after.
- Avoid long boolean argument lists; use small config objects/dataclasses when options grow.
- Avoid `*args`/`**kwargs` in public APIs unless forwarding is the core purpose.
- Prefer returning structured results (`dataclass`, typed dict, model) over overloaded tuple shapes.

## Error Handling

- Never use bare `except:` blocks.
- Catch specific exceptions and preserve context.
- Do not swallow exceptions silently; log and re-raise or return an explicit failure object.
- Use `ValueError` for invalid user input, `RuntimeError` for runtime contract violations, and domain-specific exceptions where useful.
- Avoid returning `None` for failure in functions that can return valid empty values; use explicit result types.

## Imports and Dependency Boundaries

- Keep imports at module top-level by default.
- Use lazy imports only for optional heavy dependencies or cycle avoidance, and document why.
- Separate optional dependency paths clearly with actionable `ImportError` messages.
- Do not trigger network/package-install side effects at import time.
- Star imports (`from x import *`) are allowed only in intentional API-aggregation surfaces where convenience is the goal and the exported surface is documented.
- For non-aggregation modules, avoid star imports; use explicit imports to preserve static analyzability and reduce namespace collisions.

### Ergonomics vs Analyzability Decision Rule

Use convenience/broad imports only when all conditions are true:

- The module is an explicit public API boundary (for example package facade).
- The exported surface is explicit and stable (`__all__`, contract tests, docs).
- Static tooling can still trace symbol ownership.
- The convenience materially improves caller ergonomics.

If any condition is false, prefer explicit imports and analyzability.

## Data and State Management

- Prefer immutable inputs and return new objects where practical.
- Avoid hidden global state and cross-module mutation.
- Cache behavior must be explicit: key, TTL, invalidation, and backend contract should be test-covered.
- Any environment-variable fallback must have deterministic precedence and safe defaults.

## Logging

- Use structured, actionable log messages with context.
- Do not log secrets, tokens, credentials, or PII.
- Use `debug` for internals, `info` for major lifecycle events, `warning` for recoverable anomalies, `error` for user-visible failures.

## Django and GeoDjango Expectations

- Django + GDAL are required for full test execution in this repository.
- Tests requiring this stack must be clearly marked and fail with actionable setup guidance when prerequisites are missing.
- Keep import-time side effects minimal; surface missing dependency errors early and clearly.

## Testing Standards

- New or changed behavior requires tests.
- Unit tests should validate success, edge cases, and failure paths.
- Integration tests should verify cross-module contracts and dependency-boundary behavior.
- Fixes for regressions must include a targeted regression test.
- Test file naming must be deterministic and clean (`test_<feature>.py`); avoid duplicate ad hoc files.

## Documentation Standards

- Public APIs require docstrings with parameters, return values, and failure behavior.
- Behavior involving fallback order, caching, or dependency gates must be documented.
- Keep docs synchronized with API signatures.
- Any behavior, API, or workflow change must include documentation updates in the same PR.
- Notebook-facing workflow changes must include notebook updates in the same PR so external contributors can see working examples.

## Review Checklist

- API: Signature is typed, explicit, and stable.
- Behavior: No hidden side effects; precedence and defaults are deterministic.
- Errors: No bare `except`; no silent failure.
- Dependencies: Optional imports handled correctly; required stack declared.
- Tests: Added/updated and meaningful.
- Docs: Updated for user-visible behavior.

## Recommended Enforcement

- Lint: `ruff check siege_utilities tests`
- Tests: `python -m pytest -q --no-cov`
- Focused gate for critical paths: `python -m pytest -q --no-cov tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py`
