---
ticket_refs:
  - siege-analytics/siege_utilities#1882: pre-implementation record https://github.com/siege-analytics/siege_utilities/issues/1882#issuecomment-6761203101
---

# Self-review: #1882, package introspection recurses only into package submodules and never evaluates lazy objects

Working as: software engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1882 (root cause, CI evidence, done-when)
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1882#issuecomment-6761203101
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1882
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1882#issuecomment-6761203101

## Ticket-fitness exemption (writing-rules:4)

### #1882

`evaluate-ticket.sh siege-analytics/siege_utilities#1882` returns BLOCK (exit 2). The ticket has no literal Context / Goal / Acceptance sections, no `/think` design reference or inline `## Design`, and no `## Assumptions`. The exemption covers ticket shape only. The acceptance criteria are not rewritten, and nothing below changes them.

Reason: #1882 was filed mid-incident, from a CI root-cause analysis, as a Problem / Evidence / Failure scenario / Done when / Notes ticket. That is the shape of the #1398-era hostile-review tickets, not the canonical template. The content each missing section asks for exists, under other headings or in linked records:

- Context: the ticket's `## Problem` (the two combined defects, with line references) and `## Evidence` (CI run 42766691710, traceback, local reproduction).
- Goal and Acceptance: the ticket's `## Done when`, four criteria, unchanged:
  - recursion by module name;
  - no lazy-object evaluation in attribute classification;
  - regression tests that fail on the old code;
  - package output unchanged.
- Design: the "Plan" section of the pre-implementation record, https://github.com/siege-analytics/siege_utilities/issues/1882#issuecomment-6761203101. Per the GitHub API it was created 2026-11-10T07:00:49Z, after the ticket (created 06:49:22Z) and before the first implementation commit `af5056db` (committed 07:11:21Z, UTC).
- Assumptions: the "Pre-mortem" section of that record, plus `## Assumptions` in this file.

Evidence: the four Done-when criteria map one-to-one onto the six regression tests in `tests/test_1882_architecture_module_walk.py` and the package-output equivalence check below. The review-round class-attribute case comes from independent review on #1883 (issuecomment-6762079633).

Falsification: the exemption is wrong if the tests do not pin the Done-when criteria, i.e. if reverting the implementation leaves them passing. Verified 2026-11-10: with `siege_utilities/development/architecture.py` checked out from develop `2deb6a1f`, `pytest tests/test_1882_architecture_module_walk.py` gave 6 failed:

- third-party module walked;
- lazy stand-in evaluated, in a module and at top level;
- CI's `ImproperlyConfigured` STATIC_URL error;
- the class-attribute sentinel escaped;
- real `SimpleLazyObject` set up.

With the implementation restored (`git checkout HEAD --` plus the uncommitted docstring edits re-applied, diff hash verified), 6 passed.

## Change

`siege_utilities/development/architecture.py`:

- `_attribute_kind(item)` classifies an attribute as function, class or module from `type(item)`.
  - `type()` never reads `item.__class__`, so a Django `LazyObject` is not set up.
  - The previous `inspect.isfunction`/`isclass`/`ismodule` calls are `isinstance` checks, which read `__class__` when it differs from `type(item)`. That read forced `staticfiles_storage` to set itself up and raise `ImproperlyConfigured`.
  - Used at the package top level (`analyze_package_structure`) and inside `_analyze_module`.
- `_is_package_module(module)` decides recursion by module name: `siege_utilities`, or a name starting `siege_utilities.`. This is the recursive boundary only. `analyze_package_structure` still analyzes every module attribute of the top-level package, as before; the preserved output shows that.
  - The previous test, `'siege_utilities' in str(item.__file__)`, matched every installed package on CI, where the virtualenv is under `.../siege_utilities/siege_utilities/.venv`.
- `analyze_class` now classifies class members by actual type as well: `issubclass(type(member), (types.FunctionType, types.MethodType))` replaces `inspect.isfunction`/`inspect.ismethod`. This was added after independent review (https://github.com/siege-analytics/siege_utilities/pull/1883#issuecomment-6762079633).
  - The reviewer found that a real `SimpleLazyObject` held as a public attribute of a package class (`Holder.storage`) was still set up through that path. That was pre-existing on develop `2deb6a1f` and remained on `af5056db`.
  - Ordinary methods, staticmethods (functions on the class) and bound classmethods are still discovered.
  - Nothing is caught or suppressed, class analysis is kept, and the lazy value is never pre-initialised.
- `inspect.signature`/`getdoc`/`getfile` in `analyze_function` and `analyze_class` are unchanged. They only run on objects already classified as real functions, methods or classes.

`tests/test_architecture.py::TestAnalyzeModule::test_submodule_detection` built its fake package child as a module named `child`, counted as package-owned only because its fake path contained `siege_utilities`, which is the rule this ticket replaces. Its fakes now carry real package names (`siege_utilities.parent`, `siege_utilities.parent.child`). The intent, that a package submodule is detected, is unchanged, and the test passes on both the old and new code.

## Assumptions

1. Every `siege_utilities` submodule's `__name__` is `siege_utilities` or starts with `siege_utilities.`. The import system sets it, so this holds for any real import.
2. For objects that do not override `__class__`, `issubclass(type(x), T)` equals `isinstance(x, T)`. So classification of ordinary package members is unchanged, as the fingerprint below confirms.
3. The CHANGELOG entry is a `[4.1.0]` Fixed entry, not BREAKING: output for package modules is unchanged. The only behaviour difference is that third-party modules are no longer recursed into as submodules on machines whose path contains `siege_utilities`, and that recursion was the bug.

## Test plan

- **Red on develop `2deb6a1f`:** `pytest tests/test_1882_architecture_module_walk.py` gave 5 failed, each for the intended reason:
  - third-party module walked (`AssertionError: a third-party module was walked`);
  - lazy stand-in evaluated in a module, and at package top level (`RuntimeError: lazy object was evaluated`, twice);
  - the CI case: Django's real `staticfiles_storage` held by a module under a `/home/runner/work/siege_utilities/...` path raised `ImproperlyConfigured: You're using the staticfiles app without having set the required STATIC_URL setting.`;
  - real `SimpleLazyObject` set up (`RuntimeError: SimpleLazyObject was set up`).
- **After the fix:** the same file gave 5 passed. The new tests plus `tests/test_architecture.py`, `tests/test_development_runtime_introspection_contracts.py`, `tests/test_public_api_surface.py` and `tests/guard/test_exception_contract_guard.py` gave 384 passed.
- **Output equivalence:** a fingerprint of `analyze_package_structure()` was taken in a fresh process, with memory addresses and the checkout root normalised. Develop's `architecture.py` and the fixed one give equal results under that normalisation (structured-field equality, not raw byte identity), measured in this local environment (another environment gives other absolute counts): 7 modules, 58 functions, 33 classes, 12 walked modules, walked-set hash `cdc09513adef0621`, normalised output hash `61a799bb048eb0c6`. Without normalisation the output hash varies between runs of the same code, because default-value reprs embed addresses, so the raw hash is not usable.
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
- Ordering:
  - The known trigger is #1791's new test file, whose pytest-django `settings` fixture fires Django's `setting_changed`. This was reproduced locally with CI-path emulation and GeoDjango (CI run 42766691710).
  - A static search of develop's `tests/` found no other test that changes Django settings. That is a static search only.
  - A paired full-suite baseline on develop (with and without #1791) was not performed. So it is not established that develop alone never triggers the failure.
  - This fix should land before #1791.
- Post-mortem: not performed. Whether any released version's users hit this failure has not been investigated.

## Review round: lazy class attribute

- **Red on `af5056db`:** `tests/test_1882_architecture_module_walk.py::test_real_django_lazy_class_attribute_is_never_set_up` gave 1 failed. The test's sentinel `RuntimeError` subclass ("SimpleLazyObject on a class was set up") escaped `analyze_module` -> `analyze_class`.
- **After:** that test passes. Its positive control holds: `Holder`'s `run`, `build` (bound classmethod) and `helper` (staticmethod) are all discovered, with `method_count` 3.
- **Wider set:** the new file plus `tests/test_architecture.py`, `tests/test_development_runtime_introspection_contracts.py`, `tests/test_public_api_surface.py` and `tests/guard/test_exception_contract_guard.py` gave 385 passed.
- **Package output unchanged:** the fresh-process fingerprint still equals develop's under the same normalisation, in this local environment: 7 modules, 58 functions, 33 classes, 12 walked; walked-set hash `cdc09513adef0621`; normalised output hash `61a799bb048eb0c6`.

## Scanner lead disposition (34 leads)

Source: the reviewer's full `--pr` scan of `c603a0fd` (log `pr1883-c603-full-scanner.log`, exit 1, "violations: 34"), read verbatim. A local re-run was refused by the mutation gate:

- `scan.sh --pr 1883`: "Cannot resolve mutation targets: opaque inline execution has unbounded mutation targets";
- `scan_ast.py` on the changed files: "Unscoped mutation ... expected target repo=.../claude-configs-public".

The scan of the tip commit message exits 0.

Every flagged handler body at `c603a0fd` is byte-identical to its develop `2deb6a1f` body (`git show 2deb6a1f:...` vs `c603a0fd:...`). Only the line numbers moved, by the added helpers. This PR changes no `except` clause, error return or log call.

"No direct test" below means no test was found that reaches that handler. It is not a claim of a coverage defect. Where the handler converts the error into a return value, `pytest.raises` is not the applicable assertion.

| c603 line (develop line) | Rule, leads | Handler body (identical on develop) | Existing tests | Disposition |
|---|---|---|---|---|
| 16 (15) | writing-tests-5 ×1 | `except ImportError:` defines no-op `log_*` fallbacks | no direct test (it would need `siege_utilities.core.logging` to fail to import) | pre-existing, unchanged |
| 121 (89) | writing-tests-5 ×1 | `except ImportError` -> `{"error": "Could not import package ..."}` | `test_architecture.py::TestAnalyzePackageStructure::test_nonexistent_package`; `test_development_runtime_introspection_contracts.py::...::test_unknown_package_reports_error_not_raises` (asserts the error dict names the package) | converted-error contract covered by these tests |
| 123 (91) | writing-tests-5 ×3 | `except (AttributeError, TypeError, ValueError)` -> error dict | no direct test for these three types. `TestAnalyzePackageStructure::test_generic_exception` pins that an exception outside the tuple (`RuntimeError`) propagates | pre-existing, unchanged |
| 186 (152) | writing-tests-5 ×4 | `except (AttributeError, TypeError, ValueError, ImportError)` -> `module_info["error"]` | no direct test | pre-existing, unchanged |
| 213 (179) | writing-tests-5 ×4 | `except (ValueError, TypeError, AttributeError, OSError)` in `analyze_function` -> error dict | `TestAnalyzeFunction::test_builtin_function_error_handling` calls `analyze_function(len)`, but `inspect.signature(len)` succeeds on Python 3.11 (`len(obj, /)`), so that test is not shown to reach the handler. No direct test | pre-existing, unchanged |
| 252 (214) | writing-tests-5 ×4 | `except (ValueError, TypeError, AttributeError, OSError)` in `analyze_class` -> error dict | no direct test | pre-existing, unchanged |
| 296 (258) | writing-tests-5 ×1 | `except OSError` -> `log_warning`, diagram still returned | `TestGenerateArchitectureDiagram::test_output_file_bad_path` (writes to a nonexistent directory and asserts the diagram is returned). Allowlisted as `LOGONLY` "needs-tracing #1708" in `scripts/exception_contracts_allowlist.json` | covered; already tracked by #1708 |
| 502 (464) | writing-code-7 ×1, writing-tests-5 ×4 | `except (OSError, SyntaxError, ValueError, AttributeError)` in `generate_requirements_txt` -> `log_error`, `return False` | `TestGenerateRequirementsTxt::test_missing_setup_py` covers the separate "not found -> False" precondition branch, not this `except`. No direct test of the `except` | pre-existing, unchanged (see note) |
| 623 (585) | writing-code-7 ×1, writing-tests-5 ×4 | same shape in `generate_pyproject_toml` | `TestGeneratePyprojectToml::test_missing_setup_py` (precondition branch only). No direct test of the `except` | pre-existing, unchanged (see note) |
| 736 (698) | writing-code-7 ×1, writing-tests-5 ×4 | same shape in `generate_poetry_toml` | `TestGeneratePoetryToml::test_missing_setup_py` (precondition branch only). No direct test of the `except` | pre-existing, unchanged (see note) |
| tests/test_architecture.py:43 | writing-code-9 ×1 | `_sample_function(x: int, y: str = "hello")`: `y` is never referenced | `TestAnalyzeFunction::test_basic_info` asserts `"y" in result["signature"]` | intentional signature-introspection fixture; line unchanged from develop |

Totals: 3 writing-code-7 + 30 writing-tests-5 + 1 writing-code-9 = 34.

Note on the three `generate_*` handlers:
- On develop, their docstrings document `Returns: bool ... False if there was an error`, which matches the `log_error` + `return False` body. The same docstrings also list `Raises: FileNotFoundError` and `SyntaxError`, which the bodies never raise; those cases are logged and return `False`.
- That docstring/behaviour mismatch is pre-existing and unchanged here. It is outside #1882's scope and not fixed in this PR. Whether to ticket it is the reviewer's call; no ticket has been filed.

## Quantified claims

- Red: 5 failed at `2deb6a1f`. After: 5 passed in the new file, 384 passed in the 5-module set. Fingerprint identical before and after.
