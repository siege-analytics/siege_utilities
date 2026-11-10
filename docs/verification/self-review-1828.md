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

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket. The #1398 epic is context only.

### #1449
- **Reason:** #1449 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the problem (no extra declares `msal`), the evidence (`## Evidence (v4.0.0) — CONFIRMED by trace`) and the done-when criteria live in the #1449 body. The PR #1828 body quotes the Done-when and Falsifier. No public reviewer verdict for this PR exists yet; the earlier local PASS on code is recorded by the coordinator, not on GitHub. Investigation, pre-mortem and Junior/Senior records are on the ticket at issuecomment-6651155668 and issuecomment-6651205395.
- **Falsification:** revert the implementation (restore `pyproject.toml` and `siege_utilities/connectors/dynamics.py` from develop) and `tests/test_1449_msal_extra.py::test_msal_is_declared_in_an_extra_with_a_lower_bound` goes red with "msal is missing from every pyproject.toml extra". `test_dynamics_missing_dependency_names_crm_extra[MSAL_AVAILABLE]` goes red because the error no longer names `siege-utilities[crm]`. This was verified on 2026-11-05: all 5 tests fail against develop's files and pass again once they are restored.

## Pre-flight round on 723de64d (develop 71f02b0b)
- **Develop merge (df7653c0).** The PR was CONFLICTING. The only conflict was the CHANGELOG 4.1.0 Fixed position against the #1475, #1661 and #1439 entries from develop; every develop line is kept, with the #1449 entry after them. `pyproject.toml` and `.github/workflows/ci.yml` merged cleanly: against develop they differ only by this PR's own additions (the `crm` extra, `msal` in `[all]`, and the CI `--extra crm` install with its `import msal` check). The merged tree changes only the six PR files.
- **Review threads:** none unresolved for this PR (pre-flight list of 2026-11-10 03:25Z).
- **CHANGELOG classification:** the #1449 entry stays under Fixed. It adds a dependency to the `[crm]` and `[all]` extras and changes an error message's install hint; caller code that worked on 4.0.0 behaves the same, so the BREAKING rule does not apply.
- **Tests on the merged tree:** `tests/test_1449_msal_extra.py` with the changelog tests gives 30 passed.

## Rework ledger
Empty.
