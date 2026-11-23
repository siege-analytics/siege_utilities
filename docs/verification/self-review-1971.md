# Self-review: #1971 one SU-1 authority for broad exception handlers

Review-Tier: C (guard tooling; no library code changes).

## Assumptions
- Goal source: #1971. `scripts/check_broad_except.py` reported 34 SU-1 violations on develop and CI never ran it. `scripts/check_exception_contracts.py` runs in CI (`.github/workflows/ci.yml:44`), has guard tests and a justified, digest-bound allow-list, and reported 0 unlisted.
- Measured on develop `45ea8d15`, the base of the reviewed design: `check_broad_except.py` reported 34 violations (89 broad handlers, 55 exempt), and `check_exception_contracts.py --list` reported 208 flagged, 0 unlisted, 0 stale.
- Base of this tree: develop `d2c15b13`, the 6.0.0 release preparation. Under `siege_utilities/` it changes only the version fallback in `siege_utilities/__init__.py`; outside the library it changes release files and `scripts/release_manager.py`, but no guard script, allow-list or guard test. The four handler files that gain allow-list entries have the same blobs on both bases, and the allow-list is byte-identical, so the measurements and the justifications carry over. The change was first staged on `45ea8d15`. It was carried onto `d2c15b13` by a three-way tree merge (base `45ea8d15`), which reported no conflict, and then reworked after two review rounds (see Findings F7 to F9).
- Design reviewed before implementation: 31 of the 34 already had a justified BROAD entry. The other 3 each contain a conditional raise, which the contract guard accepted because it exempted any handler with a raise anywhere. No handler was an untracked swallow: the 7 partial-result handlers belong to #1708, #1408 and #1410/#1411.
- The SU-1 rule text in the project overlay names `check_broad_except.py` as the Tier 1 tool, so the file is kept as a wrapper. The rule text lives in another repository and is not changed here.
- Out of scope: narrowing any handler; the same tightening for DEFAULT and LOGONLY, drafted as a follow-up issue because its size is unmeasured; `siege_utilities/reporting/`, which #1461 covers.

## Changes
`scripts/check_exception_contracts.py`:
- New `unconditional_reraise(body)`. It is true only when the last statement is a `raise` and nothing in the handler's own scope returns, breaks, continues or yields. That includes inside `if`, `for`, `while`, `try`, `with` and `finally` blocks, and covers `yield` and `yield from` used as a statement, assigned, or inside `await`.
- The scan uses a dedicated walker, `escape_nodes`, built on `definition_time_expressions`. Like `walk_body`, it does not enter the body of a nested `def`, `async def`, `lambda` or `class`. It does visit what those definitions evaluate in the handler's scope when they run: decorators, argument defaults and keyword-only defaults, argument and return annotations, and class bases and keywords. `walk_body` itself is unchanged, so raise detection, the DEFAULT rule and the data-function test behave exactly as on develop.
- BROAD: a bare, `Exception` or `BaseException` handler is flagged unless `unconditional_reraise(handler.body)`. A raise reached on only some paths no longer exempts it.
- DEFAULT and LOGONLY: unchanged. They are still skipped for a handler with a raise anywhere in its body.
- New `load_allowlist(root, allowlist=None)`: the single allow-list loader. It rejects a non-mapping or any entry whose justification is not a nonempty string by raising `ValueError(ALLOWLIST_ERROR)`. `main` reports that through `parser.error`, as before.
- Existing keys keep their digests and rule order, so no existing allow-list entry became stale. The docstring states both rules.

`scripts/exception_contracts_allowlist.json`: four BROAD entries with justifications, one per handler the tighter rule lists:
- `analytics/google_slides.py:421` `_delete_figure_file`: best-effort cleanup; logs ERROR and re-raises unless an insert error is already propagating;
- `connectors/_protocol.py:502` `_wrap_callable.boundary`: `except BaseException` forwarding to the inner async generator with `athrow`;
- `geo/providers/nominatim_batch.py:171` `_nominatim_request`: retries, then re-raises;
- `geo/timeseries/longitudinal_data.py:189` `get_longitudinal_data`: re-raises unless the caller passes `strict_years=False`.

`scripts/check_broad_except.py`: replaced by a wrapper. It loads the contract guard, reads the allow-list through the guard's `load_allowlist`, and has no validator of its own; an invalid allow-list ends in `parser.error` with the same message as the guard. It reports BROAD findings without an entry, exiting 0 or 1. Its docstring says it delegates and why. Options: `--root` and `--allowlist`. The former `--report` and `--json` options are gone; no CI step, test or document used them.

`tests/guard/test_exception_contract_guard.py`: `run_wrapper` and `WRAPPER`, plus 27 tests:
- a conditional raise does not exempt a broad handler: 3 cases (a raise inside `if`; `except BaseException` with a raise inside an inner `try`, the `_protocol.py:502` shape; a bare `except` that raises or returns);
- an escape before the final raise does not exempt a broad handler: 6 cases (`if flag: return {...}` then `raise`; `return` inside a nested `finally`; a conditional `break` and a conditional `continue` in a loop handler; a conditional `return` in an `async def`; an assigned `yield`);
- a `yield` in definition-time code is an escape: 7 cases (a function default, a keyword-only default, an `async def` default, a `lambda` default, a class base, a class keyword, a decorator), each followed by a final `raise`;
- a `return` inside a nested `def` body and a `yield` inside a nested `lambda` body do not count as escapes;
- a broad handler ending in `raise ... from exc` after logging and cleanup is accepted;
- a narrow handler with a conditional raise and `continue` stays exempt from DEFAULT and LOGONLY;
- a broad data handler with a conditional raise and `continue` reports BROAD only, not DEFAULT;
- the wrapper passes on the repository, fails on an unreviewed broad handler, passes once the handler is allow-listed, and ignores narrow DEFAULT findings, which the guard still reports;
- a custom allow-list of `{K: ""}`, `{K: 17}` or `[K]` makes both the guard and the wrapper exit 2 with the guard's message: 3 cases.

`CHANGELOG.md`: one `### Changed` entry under the empty `[Unreleased]`, above `## [6.0.0] - 2026-11-22`. Develop's text is unchanged.

## Test plan
New findings. With the tighter BROAD rule (first version) and before the allow-list edit, on `45ea8d15`: "handlers flagged: 212; unlisted: 4; stale allow-list: 0":
- `siege_utilities/analytics/google_slides.py::_delete_figure_file::BROAD::7aa9259c91de0b5f::1`
- `siege_utilities/connectors/_protocol.py::_SecretRedactionMixin._wrap_callable.boundary::BROAD::3244774dd728a94d::1`
- `siege_utilities/geo/providers/nominatim_batch.py::NominatimBatchGeocoder._nominatim_request::BROAD::ffe7c03aef39a730::1`
- `siege_utilities/geo/timeseries/longitudinal_data.py::get_longitudinal_data::BROAD::0904c12671e35981::1`

After adding the escape check, on `d2c15b13` and before touching the allow-list, it reported 212 flagged, 0 unlisted, 0 stale. It reported the same after the definition-time scan was added, again before touching the allow-list. Neither step finds a further handler in the library.

Wrapper coverage, compared by key. With a non-existent allow-list inside the worktree, the wrapper printed every BROAD finding: 35 locations with their keys. These are exactly the 34 file:line locations the former `check_broad_except.py` reported on the same library code, plus `connectors/_protocol.py:502`. That one is an `except BaseException`, which the former script did not scan. No location was missing and none was added. Run on both bases with the same result; nothing was created. With the real allow-list: "broad handlers flagged: 35; unreviewed: 0".

Mutations. Each was applied in the working tree with the real change staged, then restored; after every restore, `git diff` was empty and `git hash-object` of the file equalled its staged blob. The test command was `python -m pytest -o addopts="" -p no:cacheprovider -q -p no:randomly --tb=no tests/guard/test_exception_contract_guard.py`.

| Mutant | Change | Result |
|--------|--------|--------|
| A | remove the `google_slides` allow-list entry | `scripts/check_exception_contracts.py --list`: "unlisted: 1" naming that key, exit 1. `scripts/check_broad_except.py`: "unreviewed: 1", exit 1 |
| B | BROAD condition reverted to develop's `not raises` | 19 failed: `test_converted_tree_has_zero_unlisted`; `test_conditional_raise_does_not_exempt_a_broad_handler` [raise-in-if, raise-in-inner-try, bare-then-return]; `test_an_escape_before_the_final_raise_does_not_exempt_a_broad_handler` [if-return-then-raise, finally-return, break-in-loop, continue-in-loop, async-return, assigned-yield]; `test_a_yield_in_definition_time_code_is_an_escape` [function-default, keyword-only-default, async-function-default, lambda-default, class-base, class-keyword, decorator]; `test_conditional_raise_in_a_broad_data_handler_reports_only_broad`; `test_broad_except_wrapper_fails_on_an_unreviewed_broad_handler` |
| C | escape check dropped (`unconditional_reraise` returns True once the last statement is a raise) | 13 failed: the 6 `test_an_escape_before_the_final_raise_does_not_exempt_a_broad_handler` cases and the 7 `test_a_yield_in_definition_time_code_is_an_escape` cases |
| C2 | escape check scans nested bodies too (`ast.walk` instead of `escape_nodes`) | 1 failed: `test_a_return_inside_a_nested_definition_does_not_count_as_an_escape` |
| D | wrapper reads the allow-list itself with `json.loads`, without the guard's loader | 3 failed: `test_malformed_allowlist_is_rejected_by_guard_and_wrapper_alike` [empty-justification, non-string-justification, list-not-mapping] |
| E | `escape_nodes` skips nested definitions entirely (no definition-time scan), as the first rework did | 7 failed: `test_a_yield_in_definition_time_code_is_an_escape` [function-default, keyword-only-default, async-function-default, lambda-default, class-base, class-keyword, decorator] |

On the first version of the tests, the inner-`try` case had no raise. Develop's rule therefore flagged it too, and it passed under mutant B. It was changed to carry a raise in the inner `except`, as `_protocol.py:502` does, and it fails under B in the table above.

Results on the staged tree:
- `tests/guard/test_exception_contract_guard.py` with `tests/test_exception_contract_review.py`: 106 passed (79 existing and 27 new). With all of `tests/guard/`, `tests/test_release_process.py` (which the 6.0.0 preparation extended) and `tests/test_atomic_write_guard.py`: 173 passed.
- `ruff check` with F, E9 and the lint ratchet rules on the three changed Python files: no findings.
- `scripts/check_exception_contracts.py`: 212 flagged, 0 unlisted, 0 stale. `scripts/check_broad_except.py`: exit 0.
- `scripts/check_atomic_writes.py`: 0 unlisted, 0 stale, 40 reviewed. `check_secure_writes.py`, `check_secret_literals.py`, `check_secret_repr.py`, `check_subprocess_safety.py`: 0 violations. `check_credential_urls.py`: 0 unreviewed sites. `check_test_file_hygiene.py`: pass. `check_no_stub_docstrings.py`: no markers. `check_unbounded_io.py` on non-test code and on the tests: 0 violations. `check_error_path_coverage.py`: 0 failing modules.
- `check_hollow_work.py`: 3 findings, all in files this change does not touch (`engines/dataframe_engine.py:2246` and `:2448`, `reference/sample_data.py:297`). They are present on develop.
- `CHANGELOG.md` has exactly one `#1971` entry, inside `[Unreleased]` and above `## [6.0.0]`.
- `git ls-files tests/guard/test_exception_contract_guard.py` lists the file, and no ignore rule matches it.

Not run locally:
- Lint ratchet phases 1, 2 and 4 need `flake8`, which is not installed here; the `ruff` run uses the same rules, as supporting evidence only. Phase 3 compares base and head commits and runs after the commit.
- `check_test_litter.py` needs a snapshot before a pytest run and a comparison after; CI runs it that way.
- `check_lazy_imports.py` stops on a Django `ImproperlyConfigured` error in `geo/django/services`, which is untouched.
- `check_security.py` (bandit), the notebook checks and `check_wheel_contents.py` concern files and artefacts this change does not touch.

## Findings
| ID | Priority | Description | Outcome |
|----|----------|-------------|---------|
| F1 | P2 | Two SU-1 checkers with different raise rules; the one named in the rule text was not in CI and failed on 34 reviewed handlers | fixed: one rule set in the CI guard; the named script delegates to it |
| F2 | P2 | The CI guard exempted a broad handler that raises on only some paths, so a future swallow of that shape needed no review | fixed: BROAD requires a final raise with no escape in the handler's scope; the 4 existing handlers of that shape are reviewed and listed |
| F3 | P3 | The same conditional-raise exemption remains for DEFAULT and LOGONLY | not changed; follow-up issue drafted, size unmeasured |
| F4 | P3 | The design note's table swapped two names: `geo/spatial_transformations.py:264` is `PostGISConnector.close` and `:552` is `DuckDBConnector.close` (the keyed wrapper output shows this) | corrected here; both are allow-listed teardown handlers, so the classification is unchanged |
| F5 | P3 | The wrapper dropped the former `--report` and `--json` options | recorded; nothing in CI, tests or docs used them |
| F6 | P3 | `NominatimBatchGeocoder._nominatim_request` retries on any `Exception` | not changed; it re-raises after the last attempt, and narrowing belongs to #1410/#1411 |
| F7 | S2 (review) | The first version checked only top-level statements before the final raise, so `if flag: return {...}` then `raise`, a `return` in a nested `finally`, a conditional `break` or `continue`, an `async` return and an assigned or conditional `yield` stayed exempt | fixed: the escape check covers the handler's whole own scope; six escape tests and a nested-scope negative; mutants C and C2 |
| F8 | S2 (review) | The first wrapper checked only key membership, so a custom allow-list of `{K: ""}`, `{K: 17}` or `[K]` passed as reviewed | fixed: the wrapper uses the guard's `load_allowlist`; three malformed-allow-list tests run both scripts; mutant D |
| F9 | S2 (review) | The first rework skipped nested definitions entirely, including the decorators, defaults, annotations, bases and keywords they evaluate in the handler's scope, so `def nested(value=(yield ...))`, a lambda default, a class base or keyword, or a decorator with a `yield`, followed by `raise`, stayed exempt | fixed: `escape_nodes` visits definition-time expressions without entering bodies; seven witness tests; mutant E |
| F10 | S3 (review) | An earlier version of this file said the release preparation changed no library file; it changed the version fallback in `siege_utilities/__init__.py` | corrected under Assumptions: the four handler files and the allow-list are identical on both bases |

## Independent review
The first exact-tree review failed an earlier tree with findings F7 and F8, and the delta review of the next tree failed it with F9 and F10. The delta review of this tree is routed separately; the commit cites its record.
