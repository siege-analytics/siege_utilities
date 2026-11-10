# Self-review: PR #1765 Census API sentinels and identifiers (#1403), pre-flight

Review-Tier: C (the checkout's path floor; this commit changes `siege_utilities/geo/census/api.py` and its tests).

## Assumptions
Working as: software engineer (Junior) and data-integrity tech lead (Lead).
Domain(s): Census API response normalization (ACS, decennial PL, PEP).
Geospatial cross-cut: no (identifier strings only).
Goal source: the #1403 Problem / Done when / Falsifier sections; ruling to fix the PR's own non-ACS regression on this PR.
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1403#issuecomment-6761131641
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1403#issuecomment-6761131641
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1403#issuecomment-6761131641
Hostile-review-artifact: none yet. An independent exact-head review of the pushed commit is pending; this is NOT a pass.
Project-contribution: suppressed ACS cells become NaN in both sources, identifiers keep leading zeros, and decennial/PEP counts stay numeric.

## Investigation
- PR head `72dd7b88` converted only columns matching `[BC][0-9]{5}[A-Z]*_[0-9]{3}[EM]`. `CensusAPI.fetch_data` also serves `dataset='dec'` (`{year}/dec/pl`) and `dataset='pep'` (`{year}/pep/population`) per `DatasetSelector.get_dataset_path`, so `P1_001N` and `POP_2020` came back as strings; on `v4.0.0` every non-`GEOID`/`NAME` column passed through `pd.to_numeric(errors='coerce')`.
- The PR body called this intentional, "as required by #1403". #1403 bounds the protected set: "Identifier columns, geography components and annotation columns are never numerically coerced". Decennial and PEP counts are none of those.
- `tests/test_census_api_client.py::test_nonmatching_columns_are_untouched` asserted that `P1_001N` and `DP05_0001E` stay strings, encoding the regression.
- The Census API names requested variables by their uppercase codes and geography components in lowercase (`'state'`, `'us'`, `'zip code tabulation area'`, `'congressional district'`).
- Develop `2deb6a1f` changed none of the PR's files since merge-base `7f534f6c`.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. Decennial/PEP counts returned as strings. Mitigation: every uppercase variable column converts; tests for `P1_001N` and `POP_2020` through `_process_response`.
2. Tiger (launch-blocking). Severity: P1. Sentinel masking spreads to non-ACS columns. Mitigation: masking stays limited to the ACS estimate/MOE pattern; `test_non_acs_variables_are_numeric_without_sentinel_masking` keeps `-666666666` as a number outside that pattern.
3. Tiger (launch-blocking). Severity: P1. Identifiers or annotations get coerced. Mitigation: lowercase names, `GEOID`/`NAME`/`GEO_ID`/`ucgid` and `_NNN[P]EA`/`_NNN[P]MA` annotation codes are skipped; the existing identifier and annotation tests pass, plus `test_non_variable_columns_are_untouched`.
4. Tiger (launch-blocking for release notes). Severity: P1. Non-breaking mislabel. Mitigation: `### BREAKING` + Migration in the PR body.
5. Elephant. Severity: P3. The optional annotation-provenance column is not implemented (optional in #1403).

## Peer review (Junior: shelves, gates)
- Shelves: SU-2 (the docstring now states which columns convert, which are preserved and where jam values are masked; the PR body's "intentional" claim is corrected against the #1403 wording); data trust: no silent change to the meaning of a value beyond the ticket.
- Gate 1 (syntax/lint): flake8 on `api.py` is clean; the ratchet rule set on the test file is clean; `scripts/check_test_file_hygiene.py`: PASS.
- Gate 2 (tests): census-related files (`test_geo_alignment`, `test_census_api_key_warning`, `test_census_api_integration`, `test_census_api_client`, `test_credential_url_guard`, `test_round5_class_hardening`, `test_final_hardening_consensus`, `test_credential_url_leak`, `test_review_fixes`, `test_census_cache_backend`, `test_summary_file_1385`, `test_dual_source_1375`) plus smoke/runtime-guard/SQL-safety, `--no-cov -p no:randomly`: 806 passed, 29 deselected. `test_census_cache_django_roundtrip.py` needs the database and was not run locally.
- Gate 3 (docs): `_convert_numeric_columns` docstring; PR body CHANGELOG block.
- Notebook impact (SU-4a): `notebooks/archive/15_Census_Demographics_Integration.ipynb` fetches `acs5` variables, which stay numeric with masking. `notebooks/spatial/01_boundaries.ipynb` uses `CensusAPIClient`, a different module.

## Lead review (adversarial)
Phase A coherence: the regression maps to `_is_census_variable_column`; ACS masking stays bound to `_ACS_ESTIMATE_OR_MOE`.
Phase B verification (normalization class):
- Against PR head `72dd7b88`'s `api.py`: 9 failed / 27 passed. The 9 are the new conversion tests (7 non-ACS variables, `dec-pl`, `pep`).
- Against `v4.0.0`'s `api.py`, `dual_source.py` and `variable_registry.py` (new tests only): 7 failed / 7 passed. The 7 passes are the non-ACS conversion cases, where this commit restores v4.0.0 behaviour; the failures are the mixed dec/pep/ACS tests (no masking, annotations coerced) and the untouched-column tests.
- After: 98 passed in `tests/test_census_api_client.py`.
- Changed test: `test_nonmatching_columns_are_untouched` is replaced by `test_non_acs_variables_are_numeric_without_sentinel_masking` (uppercase codes outside the ACS pattern) and `test_non_variable_columns_are_untouched` (lowercase/mixed-case names, plus `ucgid`). The previous assertion encoded the regression.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | `dec`/`pep` variables returned as strings (regression vs v4.0.0) | convert every variable column |
| F2 | P2 | A test asserted the regression | replaced by two tests that state the intended rule |
| F3 | P2 | PR body: "intentional ... as required by #1403" | corrected with the #1403 quote; BREAKING + Migration; hygiene |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1403
- **Reason:** #1403 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections.
- **Evidence:** the sentinel and identifier defects, the evidence and the acceptance criteria are in the #1403 body. The investigation, pre-mortem and Junior/Senior review are at https://github.com/siege-analytics/siege_utilities/issues/1403#issuecomment-6761131641.
- **Falsification:** restore `siege_utilities/geo/census/api.py` from `72dd7b88`; `test_process_response_converts_every_dataset_and_masks_only_acs[dec-pl]` then fails because `P1_001N` stays a string. Restore the three census files from `v4.0.0`; the same test fails because `-666666666` is returned as a number and the annotation is coerced. Verified on 2026-11-10.

## Test plan / Quantified claims
Interpreter: local Python 3.11.11, run from the repository root.
- Census-related run as in Gate 2: 806 passed, 29 deselected.
- Normalization class: 9 failed / 27 passed on `72dd7b88`; new tests 7 failed / 7 passed on `v4.0.0`; 98 passed after in the client test file.

## Rework ledger
- Pre-flight round, 2026-11-10: non-ACS conversion restored; a test that encoded the regression replaced; body classification, correction and hygiene.
