---
ticket_refs:
  - siege-analytics/siege_utilities#1882: pre-implementation record https://github.com/siege-analytics/siege_utilities/issues/1882#issuecomment-6761203101
---

# Self-review: #1882, package introspection walks package modules only and never evaluates lazy objects

Working as: software engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1882 (root cause, CI evidence, done-when)
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1882#issuecomment-6761203101
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1882
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1882#issuecomment-6761203101

## Change

`siege_utilities/development/architecture.py`:

- `_attribute_kind(item)` classifies an attribute as function, class or module from `type(item)`.
  - `type()` never reads `item.__class__`, so a Django `LazyObject` is not set up.
  - The previous `inspect.isfunction`/`isclass`/`ismodule` calls are `isinstance` checks, which read `__class__` when it differs from `type(item)`. That read forced `staticfiles_storage` to set itself up and raise `ImproperlyConfigured`.
  - Used at the package top level (`analyze_package_structure`) and inside `_analyze_module`.
- `_is_package_module(module)` decides recursion by module name: `siege_utilities`, or a name starting `siege_utilities.`.
  - The previous test, `'siege_utilities' in str(item.__file__)`, matched every installed package on CI, where the virtualenv is under `.../siege_utilities/siege_utilities/.venv`.
- The `inspect` helpers inside `analyze_function`/`analyze_class` are unchanged. They only run on objects already classified as real functions or classes.

`tests/test_architecture.py::TestAnalyzeModule::test_submodule_detection` built its fake package child as a module named `child`, counted as package-owned only because its fake path contained `siege_utilities`, which is the rule this ticket replaces. Its fakes now carry real package names (`siege_utilities.parent`, `siege_utilities.parent.child`). The intent, that a package submodule is detected, is unchanged, and the test passes on both the old and new code.

## Assumptions

1. Every `siege_utilities` submodule's `__name__` is `siege_utilities` or starts with `siege_utilities.`. The import system sets it, so this holds for any real import.
2. For objects that do not override `__class__`, `issubclass(type(x), T)` equals `isinstance(x, T)`. So classification of ordinary package members is unchanged, as the fingerprint below confirms.
3. The CHANGELOG entry is a `[4.1.0]` Fixed entry, not BREAKING: output for package modules is unchanged. The only behaviour difference is that third-party modules are no longer walked on machines whose path contains `siege_utilities`, and that walk was the bug.

## Test plan

- **Red on develop `2deb6a1f`:** `pytest tests/test_1882_architecture_module_walk.py` gave 5 failed, each for the intended reason:
  - third-party module walked (`AssertionError: a third-party module was walked`);
  - lazy stand-in evaluated in a module, and at package top level (`RuntimeError: lazy object was evaluated`, twice);
  - the CI case: Django's real `staticfiles_storage` held by a module under a `/home/runner/work/siege_utilities/...` path raised `ImproperlyConfigured: You're using the staticfiles app without having set the required STATIC_URL setting.`;
  - real `SimpleLazyObject` set up (`RuntimeError: SimpleLazyObject was set up`).
- **After the fix:** the same file gave 5 passed. The new tests plus `tests/test_architecture.py`, `tests/test_development_runtime_introspection_contracts.py`, `tests/test_public_api_surface.py` and `tests/guard/test_exception_contract_guard.py` gave 384 passed.
- **Output equivalence:** a fingerprint of `analyze_package_structure()` was taken in a fresh process, with memory addresses and the checkout root normalised. Develop's `architecture.py` and the fixed one give identical results: 7 modules, 58 functions, 33 classes, 12 walked modules, walked-set hash `cdc09513adef0621`, normalised output hash `61a799bb048eb0c6`. Without normalisation the output hash varies between runs of the same code, because default-value reprs embed addresses, so the raw hash is not usable.
- `scripts/check_exception_contracts.py --list`: 0 unlisted, 0 stale.

## Peer review

- Shelves:
  - writing-tests:1: each regression fails on the old code for the stated reason, not on setup.
  - writing-tests:2: negative and positive controls (a package submodule is still walked; a third-party module is not).
  - writing-tests:3: no shared state (`monkeypatch.setitem` for `sys.modules`).
  - writing-claims:2: counts carry `Verified-by:`.
  - siege-utilities SU-2: docstrings state the name rule and why `type()` is used.
- Gate evidence: pytest -> 384 passed (exit 0); `ruff check` on the changed source and test files -> all checks passed; exception contracts 0/0.
- Notebook API: only the archived `notebooks/archive/17_Developer_Tooling.ipynb` calls the introspection functions. It is archived and output is unchanged, so no edit. Doc build N/A.

## Lead review

- The fix addresses both causes named in the ticket: the path-based recursion and the evaluation of lazy objects. Either one alone would leave a way to hit the failure (a lazy object held directly by a package module; any third-party walk).
- Ordering: #1791's test file is the only test on develop that changes Django settings, so it would arm this bug for every later run. This fix has to land before #1791.
- Post-mortem: not applicable. The bug was caught on a PR's CI before reaching a release; no published version failed because of it.

## Quantified claims

- Red: 5 failed at `2deb6a1f`. After: 5 passed in the new file, 384 passed in the 5-module set. Fingerprint identical before and after.
