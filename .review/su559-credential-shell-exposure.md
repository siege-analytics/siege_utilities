# Self-Review: SU#559 — credential exposure and shell injection fixes

## Assumptions

Working as: software engineer, security focus
Goal source: https://github.com/siege-analytics/siege_utilities/issues/559
Goal source verification: ticket exists with 4 specific exposure sites

- `run_subprocess_unrestricted` has no callers in the codebase (grep confirmed)
- 1Password CLI `op item edit` supports `[password]` field type annotation with stdin for value
- Snowflake connector config keys are well-known; an allowlist doesn't break legitimate configs

## Peer review

Shelf: writing-code:1, writing-code:3

### Shelf checks

1. **shell.py**: renamed to `_run_subprocess_unrestricted`, removed from `__all__`. No callers found in codebase.
2. **credential_manager.py**: changed `f'{field}={value}'` to `f'{field}[password]'` with `input=value` to pipe secret via stdin
3. **snowflake_connector.py**: replaced `hasattr(self, key)` check with explicit `_ALLOWED_CONFIG_KEYS` frozenset
4. **No unused imports introduced**

## Lead review

- **[Security]** No credentials in process arguments; unrestricted shell removed from public API
- **[Backwards compatibility]** `_run_subprocess_unrestricted` has zero callers; Snowflake allowlist covers all documented connection params
