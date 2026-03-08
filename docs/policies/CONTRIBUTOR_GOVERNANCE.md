# Contributor Governance

This document defines branch protections, merge policy, release permissions, and required validation for `siege_utilities`.

## Branching and Merge Policy

- `develop` is the integration branch for all feature and bugfix work.
- `main` is the release branch.
- Contributor branches must be created from `develop` and merged back to `develop` via PR.
- Releases are produced from `develop` and merged to `main` through the release workflow.

## Protected Branch Rules

`main` and `develop` are governed by an active repository ruleset:

- Pull request required for merges.
- 1 approving review required.
- Review threads must be resolved.
- Stale approvals dismissed on new pushes.
- Non-fast-forward pushes blocked.
- Branch deletion blocked.
- Required status checks enforced and up-to-date with base required.

Required checks include:

- `CodeRabbit`
- `lint ratchet phase1`
- `lint ratchet phases2-4`
- `test file hygiene`
- `api contract regression`
- `core-only (no heavy deps)`
- `geo without GDAL`
- `smoke tests (fast, no GDAL)`
- `test (3.11)`
- `test (3.12)`
- `pydantic v1 compat`
- `security`
- `databricks SDK tests`

## Bypass Policy (Direct Push Authority)

Direct push/bypass is intentionally restricted to:

- `release-admins` team (designated release maintainers)
- Organization admins (super admins)

All other contributors are expected to use PR-based flow.

Direct pushes are for urgent operational cases (for example: release repair). Normal development still goes through PRs.

## External Contributor Workflow

1. Fork repository and clone your fork.
2. Add upstream remote to `siege-analytics/siege_utilities`.
3. Create a feature branch from `upstream/develop`.
4. Install in virtual environment from cloned repo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

5. Implement changes and run required checks.
6. Open PR targeting `develop`.
7. Link related issue and include verification evidence.

## Required Pre-PR Validation

At minimum:

```bash
python scripts/check_test_file_hygiene.py
python scripts/check_lint_ratchet_phase1.py
python scripts/check_lint_ratchet.py --phase phase2
python scripts/check_lint_ratchet.py --phase phase3
python scripts/check_lint_ratchet.py --phase phase4
python scripts/contracts/generate_public_api_contract.py --output /tmp/contract_candidate.json
python scripts/contracts/compare_public_api_contracts.py \
  --baseline /tmp/contract_baseline.json \
  --candidate /tmp/contract_candidate.json \
  --release-impact <patch|minor|major> \
  --allowlist scripts/contracts/contract_allowlist.json
python -m pytest -q --no-cov tests/test_api_contract_tools.py
```

API release-impact practice:

- `patch`: no new public symbols.
- `minor`: new public symbols are allowed; add intentional additions to `scripts/contracts/contract_allowlist.json` in the same PR.
- `major`: breaking API changes require explicit migration notes and allowlist updates for intentional signature/kind/removal changes.

When applicable:

- Run targeted tests for changed modules.
- Update and validate impacted notebooks.
- Ensure `notebooks/output/` artifacts remain reviewable for notebook-driven workflows.

## Documentation and Notebook Change Policy

For user-visible behavior changes:

- Documentation updates are required in the same PR.
- Notebook updates are required in the same PR when the workflow/API examples change.

## Change Classification and Release

Use canonical policies for release impact:

- `docs/policies/CHANGE_CLASSIFICATION_AND_RELEASE_POLICY.md`
- `docs/policies/CODING_STYLE.md`
- `docs/policies/PR_REVIEW_RUBRIC.md`

Release execution uses:

```bash
python scripts/release_manager.py --release --target-version X.Y.Z --release-notes "..."
```

Release flow:

- run on `develop`
- commit release metadata on `develop`
- merge `develop` -> `main`
- tag release on `main`
- publish GitHub release (and PyPI when enabled)
