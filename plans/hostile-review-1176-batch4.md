# Hostile review — #1176 batch 4 config profile canonicals

## Scope reviewed

Batch 4 promotes 17 top-level canonical symbols from the stdlib-backed config profile helpers:

- `.config.clients`: 9 client profile helpers
- `.config.connections`: 8 connection profile helpers

## Findings

### F1 — Collision risk exists because enhanced config has similarly named helpers

`config.enhanced_config` also exposes enhanced client-profile helpers and uses lazy-import renames internally. This batch deliberately promotes the stdlib-backed `.config.clients` symbols already present in `_LAZY_IMPORTS`, not the pydantic-backed enhanced aliases.

Mitigation: `TestBatch4Promotions` asserts exact module resolution to `siege_utilities.config.clients` or `siege_utilities.config.connections` for every promoted symbol.

### F2 — Do not promote `verify_connection_profile` in this batch

`verify_connection_profile` sits next to the connection helpers but was not classified as canonical by `scripts/audit_public_api_surface.py`. Promoting it would be scope creep and would undermine the audit-driven batch process.

Mitigation: excluded from `__all__` and documented in the batch test docstring.

### F3 — Public API tests are contract tests, not behavioral tests

The batch regression tests prove `__all__` membership and lazy-resolution target. They do not test behavior of profile persistence/search/update functions.

Mitigation: this is acceptable for #1176. Behavioral gaps remain tracked by #1199 and its children.

### F4 — This PR should not mix unrelated modernization work

Nearby open work includes #1190 broader httpx migration, #1206 hollow-work triage, #1208 bivariate choropleth collision, and #1210 quote_ident decision. Mixing any of those here would make review harder and hide semantic changes inside an API-contract PR.

Mitigation: no runtime implementation changes beyond `__all__` except one tightly related metadata correction for already-migrated `geo.isochrones`; no issue-body edits; no unrelated scanner fixes.

### F5 — #1205 migrated `geo.isochrones` to httpx, but lazy metadata was stale

Top-level `_register_lazy` still declared `deps=['requests']` for `geo.isochrones`, while the implementation imports `httpx`. In an environment with `requests` installed but `httpx` missing, top-level access leaked raw `ModuleNotFoundError` instead of the documented dependency wrapper.

Mitigation: update the dependency metadata to `deps=['httpx']` and add `TestLazyDependencyMetadata.test_isochrones_lazy_metadata_requires_httpx`.

## Verdict

Proceed. The change is additive, audit-driven, and has exact-resolution guards for the primary collision risk. The extra #1190 metadata fix is justified because it removes a real import-resolution failure surfaced by the public API scanner without starting a broader httpx migration.
