# Scripts

This directory contains maintenance and validation scripts for `siege_utilities`.

## Supported Scripts

These scripts are part of the expected contributor workflow and are maintained.

### Test execution

- `python scripts/run_tests.py`
  - Wrapper for project test runs.

### Release support

- `python scripts/release_manager.py --help`
  - Release orchestration and release checks.

### API contract regression tools

- `python scripts/contracts/generate_public_api_contract.py --output /tmp/contract.json`
  - Generates a public API manifest for a package import surface.
- `python scripts/contracts/compare_public_api_contracts.py --baseline /tmp/base.json --candidate /tmp/candidate.json --release-impact patch --allowlist scripts/contracts/contract_allowlist.json`
  - Compares two manifests and enforces release-impact rules.

## Experimental / One-off Scripts

These scripts are useful for diagnostics or ad hoc local work, but are not part of the stable automation surface.

- `scripts/check_imports.py`
- `scripts/diagnose_pyspark.py`
- `scripts/verify_bivariate_choropleth.py`
- `scripts/create_notebook.py`
- `scripts/run_overnight_comprehensive.sh`

Use experimental scripts manually and verify outputs before relying on them in CI or release workflows.

## Contributing Rules for Scripts

- Keep new scripts narrowly scoped.
- Document whether a script is `Supported` or `Experimental` in this file.
- Avoid adding references to scripts that do not exist in the repository.
