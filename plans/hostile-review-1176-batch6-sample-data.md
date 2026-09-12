# Hostile review — #1176 batch 6 / #1213 sample-data canonicals

## Scope reviewed

Batch 6 retargets root lazy sample-data symbols from the deprecated `siege_utilities.data.sample_data` shim to the canonical implementation module `siege_utilities.reference.sample_data`, then promotes 8 safe sample-data symbols:

- `CENSUS_SAMPLES`
- `SAMPLE_DATASETS`
- `SYNTHETIC_SAMPLES`
- `generate_synthetic_businesses`
- `generate_synthetic_housing`
- `generate_synthetic_population`
- `list_available_datasets`
- `load_sample_data`

## Findings

### F1 — Promoting through the deprecated shim would bless the wrong module path

`data.sample_data` emits a `DeprecationWarning` and re-exports from `reference.sample_data`. If top-level lazy loading continues to target `.data.sample_data`, users can see a deprecation warning from a supposedly canonical top-level access.

Mitigation: retarget root `_register_lazy` for sample-data symbols to `.reference.sample_data` before promotion. Add tests proving top-level access does not import `siege_utilities.data.sample_data` or emit its deprecation warning.

### F2 — Do not promote unimplemented or audit-internal helpers

`create_sample_dataset` and `join_boundaries_and_data` are lazy-addressable but not part of this promotion. `create_sample_dataset()` may route into not-yet-implemented census sample paths; `join_boundaries_and_data` was not classified as canonical.

Mitigation: promote only the 8 audit-canonical constants/loading/synthetic helpers recommended by the #1213 hostile review.

### F3 — Constants do not have `__module__`

Function module-resolution guards work for callable helpers, but list/dict constants do not carry `__module__`.

Mitigation: constants are covered by lazy metadata assertions and no-shim/no-warning access tests.

## Verdict

Proceed. This resolves #1213's deprecation-shim hazard while keeping the promoted contract narrow and tested.
