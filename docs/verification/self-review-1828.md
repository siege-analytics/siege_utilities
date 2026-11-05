# Self-review: PR #1828 MSAL in a `crm` extra and in CI (#1449), integration round

Review-Tier: C (CI workflow and packaging metadata).

## Assumptions
Working as: software engineer (Junior) and release-engineering tech lead (Lead).
Domain(s): software engineering (packaging extras, CI install, CRM connectors).
Geospatial cross-cut: no.
Goal source: the #1449 Done-when quoted in the PR #1828 body. Code at f930c182 was PASSed by an earlier local review. This round is integration only: develop sync, canonical CHANGELOG.md note, this artifact, exact-head CI. No library behavior changes.
Plan reference: docs/verification/self-review-1828.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1828.md#investigation
Investigate-artifact: docs/verification/self-review-1828.md
Pre-mortem-artifact: docs/verification/self-review-1828.md
Hostile-review-artifact: this file, section Lead review (hunk-by-hunk audit of the merged diff against develop). Independent re-review of the integration head is pending; this is NOT a pass of it.
Project-contribution: a user who installs `[crm]` or `[all]` gets a working Dynamics connector, and CI runs the Dynamics tests instead of skipping them.

## Investigation
- PR files (4): `.github/workflows/ci.yml`, `pyproject.toml`, `siege_utilities/connectors/dynamics.py`, `tests/test_1449_msal_extra.py`.
- At f930c182, `git grep 1449 -- CHANGELOG.md` found nothing, although the body said the existing 4.1.0 Fixed section documented the change. The note existed only in the body block.
- `dynamics.py` is shared with the CRM cluster, which reached develop through #1777. GitHub reported the branch MERGEABLE/UNSTABLE against develop dc7d3f76.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The merge silently alters `dynamics.py`, `ci.yml` or `pyproject.toml` beyond the PR's intent. Mitigation: the merged diff against develop was read hunk by hunk (Lead review).
2. Paper Tiger. Severity: P2. A positional CHANGELOG conflict. Mitigation: the entry is at the end of `[4.1.0]` / `### Fixed`; merge-tree is checked.
3. Paper Tiger. Severity: P2. The body's claim of an existing CHANGELOG section is false. Mitigation: entry added and sentence corrected.
4. Elephant. Severity: P3. Known DuckDB 2.0 CI failures until the pin lands (#1861/#1863). Labelled, not chased.

## Peer review (Junior: shelves, gates)
- Shelves: packaging rules (an extra declares a lower bound); release-note discipline.
- Gate 1 (syntax): no Python changed in this round; pytest imported every module -> 455 passed.
- Gate 2 (tests): pytest on the merged tree -> 455 passed, 2 skipped. Both skips are `tests/test_lazy_import_recovery.py` ordering skips ("No uncached lazy entries ..."), unrelated to Dynamics.
- Gate 3 (guards): lint ratchet phases 1 to 4 against develop dc7d3f76 (recorded in the PR body).
- Gate 4 (docs/notebooks): CHANGELOG.md only.

## Lead review (adversarial)
Merged diff against develop, hunk by hunk:
- `ci.yml`: `uv sync ... --extra crm`, plus `uv run python -c "import msal"`. Nothing else.
- `pyproject.toml`: a new `crm` extra (`msal>=1.24.0`, `pandas>=2.0.0,<3.0`) and `msal>=1.24.0` in `all`. Nothing else.
- `dynamics.py`: only the two `ImportError` message strings now name `siege-utilities[crm]`. The CRM cluster's sanitization code from develop is intact.
- `tests/test_1449_msal_extra.py`: unchanged from f930c182.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | Body claimed an existing CHANGELOG entry that was absent | entry added; body corrected |
| F2 | P3 | Branch behind develop with a positional CHANGELOG conflict | additive merge, develop entry kept |

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11), merged tree.
- `python -m pytest tests/test_1449_msal_extra.py tests/test_package_metadata_contract.py tests/test_wheel_contents.py tests/test_connectors_errors.py tests/test_lazy_import_recovery.py tests/test_lazy_introspection_contracts.py tests/test_connectors_dynamics_errors.py tests/test_connector_filter_escaping.py tests/test_connector_identifiers.py tests/test_connector_upsert_sanitization.py tests/test_connector_record_sanitizer.py tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py tests/test_release_process.py tests/test_user_config_export_changelog.py --no-cov -rs` -> 455 passed, 2 skipped.
- `git diff --stat origin/develop` -> the 4 PR files (98 insertions, 3 deletions).

## Rework ledger
Empty.
