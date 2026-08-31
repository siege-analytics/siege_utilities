# Hostile review — #1176 batch 5 file utility canonicals

## Scope reviewed

Batch 5 promotes 13 top-level canonical symbols from file utility modules:

- `.files.hashing`: `calculate_file_hash`, `generate_sha256_hash_for_file`, `get_file_hash`, `get_quick_file_signature`, `verify_file_integrity`
- `.files.operations`: `copy_file`, `file_exists`, `move_file`
- `.files.remote`: `download_file`, `download_file_with_retry`, `get_file_info`, `is_downloadable`
- `.files.paths`: `ensure_path_exists`

## Findings

### F1 — `run_command` is ambiguous; do not canonize it here

Promotion would not newly expose `run_command`; it is already addressable via top-level `__getattr__`. However hostile review found another shipped helper, `siege_utilities.testing.runner.run_command`, with a different signature and a docstring example advertising `siege_utilities.run_command(...)`.

Mitigation: remove `run_command` from batch 5 `__all__` promotion while preserving lazy compatibility through `_LAZY_IMPORTS`. Add a regression guard proving it stays lazy-addressable but non-canonical. Filed #1215 for the API decision.

### F2 — Remote helpers may perform network I/O when called

`download_file`, `download_file_with_retry`, `get_file_info`, and `is_downloadable` can perform remote operations, but this batch does not invoke them or alter timeout semantics.

Mitigation: regression tests only resolve the symbol object and assert the source module. Network behavior remains a separate concern under broader library-health/httpx work.

### F3 — Do not mix behavioral file utility tests into #1176

Several file utility symbols remain documented-but-untested in #1199. Adding behavioral coverage would be useful, but it is a different ticket lane.

Mitigation: limit tests to public API contract shape; leave behavioral coverage to #1199 children.

### F4 — Skip `data.sample_data` despite a similar remaining canonical count

`data.sample_data` is a deprecation shim that resolves functions from `reference.sample_data` and emits a deprecation warning on import. Blindly promoting it could bless a moved module path.

Mitigation: prefer file utilities for batch 5; leave sample-data promotion/alias policy to a separate design pass. Filed follow-up #1213.

## Verdict

Proceed. The batch is additive, cohesive, and avoids deprecation-alias and optional-dependency traps.
