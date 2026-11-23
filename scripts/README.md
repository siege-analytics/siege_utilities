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
  - Use `--release-impact minor` when intentionally adding public symbols and update `scripts/contracts/contract_allowlist.json` in the same PR.

### Source guards

`.github/workflows/ci.yml` runs every `scripts/check_*.py` guard except the
local-only tools listed below. Most run in the `static guards` job; the others
run in `test file hygiene`, `lint ratchet`, `notebook governance + pure
execution`, the `test` job (`check_test_litter.py`) and `api, security and
build` (`check_wheel_contents.py`).

### Local-only tools

CI does not run these. Each one is a report with no failing mode, duplicates
a check that CI already runs, or does not yet pass on the tree.

- `python scripts/check_broad_except.py`
  - Reports broad exception handlers without a reviewed entry. It delegates to
    `check_exception_contracts.py`, which CI runs, using the same rules and
    allow-list, so running it in CI as well would duplicate that step.
- `python scripts/check_symbol_test_coverage.py`
  - Per-symbol test and docstring coverage report (`--markdown`, `--json`,
    `--csv`). It always exits 0.
- `python scripts/check_social_review_fidelity.py`
  - Fidelity oracle for the offline social report against PR #1812's reviewed
    baseline. Run it with the repository on `PYTHONPATH`.
    `tests/test_1812_fidelity_oracle.py` loads it, so CI covers it through the
    test suite.
- `python scripts/check_imports.py`
  - Import diagnostic for `siege_utilities`. It prints what fails to import and
    why.
- `python scripts/check_hollow_work.py --strict`
  - Reports TODO/FIXME/HACK/XXX markers and `raise NotImplementedError`
    without a ticket reference, pass-only function bodies and tautology
    asserts (writing-code:19). Without `--strict` it always exits 0. It is not
    in CI yet because it reports 3 findings on develop (`c303621d`), all
    intentional `NotImplementedError` refusals whose ticket is not on the
    raise line or the 5 lines above it:
    - `siege_utilities/engines/dataframe_engine.py:2246`: Spark DataFrame
      pairwise distance (#1353);
    - `siege_utilities/engines/dataframe_engine.py:2448`: `SparkEngine.nearest`
      with `crs` (added in PR #1852);
    - `siege_utilities/reference/sample_data.py:297`: declared but
      unimplemented sample datasets (#1360, cited in the message two lines
      below the raise).

## Experimental / One-off Scripts

These scripts are useful for diagnostics or ad hoc local work, but are not part of the stable automation surface.

- `scripts/run_overnight_comprehensive.sh`
  - The `battle-test` job runs it, on manual (`workflow_dispatch`) CI runs only.
- `scripts/archive/diagnose_pyspark.py`
- `scripts/archive/verify_bivariate_choropleth.py`
- `scripts/archive/create_notebook.py`
- `scripts/archive/run_tests.py`
- `scripts/archive/verify_round6_hardening.py` through
  `scripts/archive/verify_round9_hardening.py`, and
  `scripts/archive/verify_batch1_1373.py`
  - One-off verifiers for earlier hardening rounds. The evidence transcripts
    under `docs/testing/` record them at their former `scripts/` paths.
- `scripts/archive/check_security.py`
  - Former bandit wrapper, archived as broken. Its baseline file
    `security_baselines/bandit_baseline.json` does not exist. It builds its
    severity flag as `-i` plus a letter (`-il`, `-im`, `-ih`), but `-i` is
    bandit's confidence flag, so `--severity` does not set the severity. It
    discards a bandit report that is not valid JSON and continues with no
    findings. It never checks bandit's exit code, so a bandit error with no
    report passes as a clean scan. The bandit step in the
    `api, security and build` CI job replaces it.

Use experimental scripts manually and verify outputs before relying on them in CI or release workflows.

## Contributing Rules for Scripts

- Keep new scripts narrowly scoped.
- Document whether a script is `Supported` or `Experimental` in this file.
- Avoid adding references to scripts that do not exist in the repository.
