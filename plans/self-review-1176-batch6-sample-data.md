# Self-review — #1176 batch 6 / #1213 sample-data canonicals

## Change summary

- Retargeted root sample-data lazy registration from `.data.sample_data` to `.reference.sample_data`.
- Promoted 8 safe sample-data symbols to top-level `siege_utilities.__all__`.
- Added `TestBatch6Promotions` to verify:
  - symbols are in `__all__`
  - lazy metadata targets `.reference.sample_data`
  - function symbols resolve to `siege_utilities.reference.sample_data`
  - top-level access does not import the deprecated `siege_utilities.data.sample_data` shim
  - top-level access does not emit the shim's `DeprecationWarning`

## Non-goals

- Did not promote `create_sample_dataset`.
- Did not promote `join_boundaries_and_data`.
- Did not alter the deprecated `siege_utilities.data.sample_data` shim itself; existing direct shim imports still warn as intended.

## Validation

- `python3 - <<'PY' ... ast.parse(...)` — passed for touched Python files
- `python3 scripts/check_lazy_imports.py` — passed
- `python3 scripts/audit_public_api_surface.py` — passed; remaining outside `__all__` is 174, canonical is 47
- `python3 scripts/check_symbol_test_coverage.py --tier canonical --json` — passed; unresolvable remains 0
- `PYTEST_ADDOPTS='--override-ini addopts=' python3 -m pytest tests/test_public_api_surface.py -q` — 241 passed, 1 existing config warning
- `PYTEST_ADDOPTS='--override-ini addopts=' python3 -m pytest tests/test_public_api_surface.py -q -k 'Batch5 or Batch6 or LazyDependencyMetadata'` — 59 passed, 182 deselected, 1 existing config warning
- Metadata smoke: `run_command` absent from `__all__` but still lazy-backed; `get_isochrone` requires `httpx`; `load_sample_data` targets `.reference.sample_data`
- `git diff --check` — passed
