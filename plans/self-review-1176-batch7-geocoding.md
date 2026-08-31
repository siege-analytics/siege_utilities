# Self-review — #1176 batch 7 geo.geocoding

## Change summary

- Promoted six canonical geocoding helpers plus extension-tier `GeocodingError` to top-level `siege_utilities.__all__`.
- Corrected root lazy dependency metadata for `.geo.geocoding` from `geopandas` to `pandas` + `geopy`.
- Added `TestBatch7Promotions` to verify:
  - membership in `__all__`
  - exact lazy metadata
  - exact module resolution to `siege_utilities.geo.geocoding`

## Non-goals

- Did not invoke network geocoding paths.
- Did not migrate remaining `requests` users.
- Did not promote unrelated `geo` or census selector helpers.

## Validation

- AST parse passed for `siege_utilities/__init__.py` and `tests/test_public_api_surface.py`.
- `python3 scripts/check_lazy_imports.py` — passed.
- `python3 scripts/audit_public_api_surface.py` — passed; remaining outside `__all__` is 167, canonical is 41, extension is 8.
- `PYTEST_ADDOPTS='--override-ini addopts=' python3 -m pytest tests/test_public_api_surface.py -q` — 262 passed, 1 existing config warning.
- `PYTEST_ADDOPTS='--override-ini addopts=' python3 -m pytest tests/test_public_api_surface.py -q -k 'Batch7'` — 21 passed, 241 deselected, 1 existing config warning.
- Metadata smoke confirmed `get_coordinates` deps are `['pandas', 'geopy']` and `GeocodingError` is in `__all__`.
- `git diff --check` — passed.
