# Scripts

This directory contains maintenance and validation scripts for `siege_utilities`.

## Supported Scripts

These scripts are part of the expected contributor workflow and are maintained.

### Test execution

- `python scripts/check_test_file_hygiene.py`
  - Enforces tracked test naming/location conventions.
- `python scripts/check_lint_ratchet_phase1.py`
  - Phase 1 lint ratchet (`E722,F601,F403,F405`) on touched Python files.
- `python scripts/check_lint_ratchet.py --phase phase2`
  - Phase 2 lint ratchet (`F401,F841,F541`) on touched Python files.
- `python scripts/check_lint_ratchet.py --phase phase3`
  - Phase 3 lint ratchet (full-module checks when `config/geo/files` domains are touched).
- `python scripts/check_lint_ratchet.py --phase phase4`
  - Phase 4 full-repo ratchet against the committed baseline.

### Release support

- `python scripts/release_manager.py --help`
  - Release orchestration and release checks.

### API contract regression tools

- `python scripts/contracts/generate_public_api_contract.py --output /tmp/contract.json`
  - Generates a public API manifest for a package import surface.
- `python scripts/contracts/compare_public_api_contracts.py --baseline /tmp/base.json --candidate /tmp/candidate.json --release-impact patch --allowlist scripts/contracts/contract_allowlist.json`
  - Compares two manifests and enforces release-impact rules.
  - `--baseline` should come from a released package state (for example `siege-utilities==3.8.0`), and `--candidate` from the current branch output.

## Experimental / One-off Scripts

These scripts are useful for diagnostics or ad hoc local work, but are not part of the stable automation surface.

- `scripts/check_imports.py`
- `scripts/run_overnight_comprehensive.sh`
- `scripts/archive/diagnose_pyspark.py`
- `scripts/archive/verify_bivariate_choropleth.py`
- `scripts/archive/create_notebook.py`
- `scripts/archive/run_tests.py`

Use experimental scripts manually and verify outputs before relying on them in CI or release workflows.

## Contributing Rules for Scripts

- Keep new scripts narrowly scoped.
- Document whether a script is `Supported` or `Experimental` in this file.
- Avoid adding references to scripts that do not exist in the repository.
