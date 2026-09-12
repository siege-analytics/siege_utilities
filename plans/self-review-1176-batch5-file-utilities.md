# Self-review — #1176 batch 5 file utility canonicals

## Change summary

Promoted 13 canonical file utility symbols to top-level `siege_utilities.__all__`:

- 5 from `siege_utilities.files.hashing`
- 3 from `siege_utilities.files.operations`
- 4 from `siege_utilities.files.remote`
- 1 from `siege_utilities.files.paths`

`run_command` remains lazy-addressable for backward compatibility but is intentionally not promoted pending #1215.

Added `TestBatch5Promotions` in `tests/test_public_api_surface.py` to verify:

- every batch-5 symbol is present in `siege_utilities.__all__`
- every symbol resolves exactly to its expected file utility module

## Risk notes

- `run_command` is already top-level lazy-loadable but has a testing-runner collision; it was excluded from canonical promotion and tracked in #1215.
- Remote helpers are not invoked by the tests, avoiding network I/O.
- `data.sample_data` was intentionally skipped because it is a deprecation shim resolving to `reference.sample_data`; follow-up filed as #1213.

## Validation

- `python3 - <<'PY' ... ast.parse(...)` — passed for touched Python files
- `python3 scripts/check_lazy_imports.py` — passed
- `python3 scripts/audit_public_api_surface.py` — passed; remaining outside `__all__` dropped from 195 to 181, canonical dropped from 68 to 54
- `python3 scripts/check_symbol_test_coverage.py --tier canonical --json` — passed; unresolvable remains 0
- `PYTEST_ADDOPTS='--override-ini addopts=' python3 -m pytest tests/test_public_api_surface.py -q` — 213 passed, 1 existing config warning
- `git diff --check` — passed

The normal pytest command still requires a local `pytest-cov` install because `pytest.ini` injects coverage options.
