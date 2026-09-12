# Hostile review — #1176 batch 7 geo.geocoding

## Scope reviewed

Promotes the geocoding public surface:

- `GeocodingError` (extension-tier error type)
- `concatenate_addresses`
- `get_coordinates`
- `get_country_code`
- `get_country_name`
- `list_countries`
- `use_nominatim_geocoder`

Also corrects top-level lazy dependency metadata for `.geo.geocoding` from `geopandas` to `pandas` + `geopy`.

## Findings

### F1 — Dependency metadata was wrong

`geo/geocoding.py` imports `pandas` and `geopy`, not `geopandas`. Declaring `deps=['geopandas']` makes missing-dependency wrappers misleading and may force a heavy optional dependency for plain geocoding helpers.

Mitigation: update root lazy metadata to `deps=['pandas', 'geopy']`; add tests asserting metadata for each promoted symbol.

### F2 — `GeocodingError` is extension-tier, not canonical

The audit classifies `GeocodingError` as extension-tier. Promoting it is still appropriate because users need stable exception types to catch public geocoding failures.

Mitigation: comment says “6 canonical + 1 extension”; tests include the error type explicitly.

### F3 — Network behavior is not exercised

`use_nominatim_geocoder` / `get_coordinates` can hit geocoding services when called. Public API tests only resolve symbols and do not invoke network paths.

Mitigation: keep this as a contract PR; behavioral/network tests belong under existing geocoding test coverage and broader #1199 work.

## Verdict

Proceed. This is a narrow public API contract batch plus a dependency metadata correction that makes the lazy wrapper more truthful and lighter-weight.
