---
ticket_refs:
  - siege-analytics/siege_utilities#1416: comment posted https://github.com/siege-analytics/siege_utilities/issues/1416#issuecomment-6650792304
---

# Self-review: #1416 / PR #1776, uncorroborated namesakes never share a canonical ID

Working as: software engineer, data engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1416 (acceptance criteria) and the exact-head review https://github.com/siege-analytics/siege_utilities/issues/1416#issuecomment-6257104805
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1416#issuecomment-6650523718 (fact sheet: seed site `_dedup.py:132`, callers `connectors/__init__.py`, `notebooks/analytics/04_crm_pipeline.ipynb`, `tests/test_crm_dedup.py`)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1416#issuecomment-6650523718
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1416#issuecomment-6650523718
Hostile-review-artifact: plans/hostile-review-1416.md

## Ticket-fitness exemption

### #1416

Reason: #1416 predates the canonical ticket template. Its body carries Problem, Failure scenario, Done when and Falsifier sections, but not the canonical Evidence and Assumptions sections.
Evidence: problem, failure scenario, done-when and falsifier live in https://github.com/siege-analytics/siege_utilities/issues/1416; the exact-head reviewer verdict with reproducer is https://github.com/siege-analytics/siege_utilities/issues/1416#issuecomment-6257104805.
Falsification: revert the implementation; `tests/test_crm_dedup.py::test_uncorroborated_namesakes_stay_distinct_final_entities` goes red because two no-email `Maria Garcia` rows group into one `canonical_id` (`[['a', 'b']]`).
Verified 2026-11-05: with `siege_utilities/connectors/_dedup.py` checked out from the previous PR head `af0c6df7` (this fix reverted), the test -> 2 failed, `test_crm_dedup.py:303: assert [['a', 'b']] == [['a'], ['b']]`. With `_dedup.py` from `origin/develop` (the whole PR reverted) -> 2 failed with `TypeError: crm_dedup_pipeline() got an unexpected keyword argument 'identifier_columns'`. After `git checkout HEAD --` -> 2 passed, worktree clean.

## Assumptions

1. The ticket's acceptance criteria ("a merge requires at least one corroborating key, or it is emitted as a candidate pair for review with a confidence below 1.0") mean a consumer that groups by `canonical_id` must not coalesce uncorroborated namesakes. The reviewer's probe used exactly that consumer.
2. `source_system` + `source_id` identify one source record, so an uncorroborated record's own entity is seeded from them. When either is null or blank there is no stable record key. The fallback seed (frame position, row position) is deterministic only for identical input, and the docstring says so.
3. Callers persisting 4.0.0 merge tables need a join key. `name_candidate_id` is byte-identical to the 4.0.0 name-only `canonical_id` (`uuid5_from_seed(CRM_NAMESPACE, normalized_name)`).
4. Adding a trailing output column is additive for name-based consumers. Positional consumers of exactly five columns would break; the [4.1.0] note documents the new column.

## Test plan

- Red before: `tests/test_crm_dedup.py::test_uncorroborated_namesakes_stay_distinct_final_entities` (both parametrizations) at `af0c6df7` -> 2 failed, `assert [['a', 'b']] == [['a'], ['b']]`. This reproduces the reviewer's probe.
- After the fix: the same module -> 57 passed. The new notebook-truth module -> 2 passed.
- Hostile-review regression: `test_missing_source_key_rows_with_duplicate_index_labels_stay_distinct` -> 1 failed with the index-label seed (`assert 1 == 2`), passed with the row-position seed.
- Edge paths: null/NaN/NA/blank/whitespace source keys stay distinct and deterministic (5 cases); a corroborated pair plus an uncorroborated namesake share only `name_candidate_id`; a repeated source record keeps one identity; `identifier_columns=[]` with equal emails does not merge; textual-null identifiers do not merge (5 cases); the log separates corroborated matches from unmerged review groups.
- Notebook: `tests/test_notebooks.py::test_pure_python_notebook[04_crm_pipeline]` executes the edited notebook (1 passed). `tests/test_1416_crm_notebook_truth.py` pins that Ada Lovelace merges (same email, different case) and that Grace Hopper stays two entities with one candidate key.

## Peer review

- Shelves: writing-tests:1 (red before, green after, on the consumer-visible `groupby("canonical_id")`), writing-tests:2 (negative and edge paths for null, blank and duplicate-label keys), writing-claims:2 (counted results carry a `Verified-by:` trailer), writing-code:1 (seed shapes stay structured JSON, so no delimiter collisions); siege-utilities SU-1, SU-2, SU-4a and SU-4b as listed below.
- Syntax check: `py_compile` on 3 changed `.py` files (`_dedup.py`, `test_crm_dedup.py`, `test_1416_crm_notebook_truth.py`) -> all parse clean (exit 0).
- Test suite: after merging develop `dc7d3f76`, `pytest -p no:randomly tests/test_crm_dedup.py tests/test_1416_crm_notebook_truth.py tests/test_notebook_hygiene.py tests/test_notebooks.py tests/test_connector_record_sanitizer.py tests/test_connector_upsert_sanitization.py tests/test_connectors_errors.py -k "not spark and not databricks and not django"` -> 444 passed, 1 skipped, 27 deselected (exit 0). After the hostile-review fix: `pytest tests/test_crm_dedup.py tests/test_1416_crm_notebook_truth.py tests/test_notebooks.py -k "dedup or crm"` -> 61 passed (exit 0).
- Notebook API: the only notebook caller, `04_crm_pipeline.ipynb`, was updated. Its old markdown said Ada Lovelace mapped to one canonical ID, but the fixture gave her two different emails, so the claim was already false at `af0c6df7`. The fixture now uses a case- and whitespace-variant email for her and adds an email-less Grace Hopper namesake to show the review path (SU-4a error-path cell).
- Doc build: N/A (no Sphinx sources changed).
- SU-1: no new except/return-empty paths. `_empty_result` keeps the documented empty schema for "no valid rows" and gains the new column.
- SU-2: the docstring and module header now describe the code: no name-only merging. The `identifier_columns=[]` doc changed from "name-only matching" to "disable identifier matching".
- Findings: the identifier seed path is byte-unchanged (`json.dumps([normalized, identifiers], sort_keys=True)`). Existing identifier tests pass unmodified.

## Lead review

- Finding or only the probe? Both. The probe yields two groups, and the name-only paths (missing identifier values, `[]`, textual nulls, surname-only rows) are covered.
- Hidden collision caught before commit: seeding only from source keys would collapse every null-source-id row in one system into one entity regardless of name. Fixed with a frame position fallback (5 parametrized cases). The hostile review then showed the index label repeats after `pd.concat`; the seed now uses the row position (plans/hostile-review-1416.md, finding 1).
- Log accuracy: the corroborated-match count excludes repeated source rows, and a test asserts it.
- Migration: every canonical ID differs from 4.0.0 (identifier IDs already changed earlier in this PR). The note says to regenerate and names `name_candidate_id` as the old-key join.
- Post-mortem: not applicable. The defect was caught by exact-head review before merge, so no shipped implementation contradicts the ticket and no release carried it.
- Release classification: BREAKING for 4.1.0 by operator sign-off (2026-11-05). The CHANGELOG entry is a `**BREAKING (#1416):**` bullet under `[4.1.0]` → `### Changed` with its Migration paragraph; no code changed for the classification.
- Residual: callers that relied on name-only merging lose it on purpose. The library offers no opt-in, matching the architecture note that heavy entity resolution belongs downstream.

## Gaps A and B (operator ruling 2026-11-05: do not ship debt)

Design note: `plans/design-1416-identifier-graph.md` (written before the code, revised after hostile review).

- **A, normalized phone and address keys.** No reusable normalizer existed: `geo/providers/batch_geocoder.normalize_addresses` only reshapes geocoder input. So frozen, versioned `normalize_phone_v1` and `normalize_address_v1` were added beside `normalize_name_v1`. Phone and the composed address now corroborate by default; the widened defaults are listed in the CHANGELOG with an email-only Migration setting.
- **B, one corroborating key suffices.** Union-find over edges that require an equal normalized name and at least one equal identifier, with a per-component conflict guard and `canonical_id = uuid5(min member seed)`. The operator approved keeping the guard on every column. Its cost is that the same person with a different phone, or a fuller or partial address, in another CRM is split; this is stated in the docstring, CHANGELOG and PR body.
- **C, accepted.** Review candidates are exposed through the shared `name_candidate_id` grouping key, not a candidate-pair table. The operator accepted this as meeting "emitted as a candidate pair for review with a confidence below 1.0": every pair of rows sharing a `name_candidate_id` but differing in `canonical_id` is a review candidate pair.
- **Residual risk, stated:** two same-name people sharing one identifier with no conflicting identifier merge. This is the same standard as name plus an equal email. CRMContact has no suffix field, so a Sr/Jr pair sharing a household phone or address is the realistic case.
- **Red first** (prior head `f71e3cd9`): see the receipt under Quantified claims. Controls that also pass at `f71e3cd9`: `test_identities_do_not_depend_on_row_order`, `test_distinct_addresses_do_not_corroborate`, `test_address_without_street_is_not_identity_evidence`, `test_namesakes_sharing_nothing_stay_split`, `test_unmerged_identifier_record_keeps_its_own_seed_id`, `test_different_names_sharing_a_household_email_stay_split`.
- Hostile review second pass: `plans/hostile-review-1416.md`. One blocker went to an operator ruling; follow-ups were fixed or documented.

## Quantified claims

- Gaps A and B, red first (2026-11-05): with `connectors/_dedup.py`, `identifiers/normalize.py` and `identifiers/__init__.py` checked out from `f71e3cd9`, `pytest tests/test_crm_dedup.py` -> 14 failed, 63 passed (the 63 include the labeled controls), and `tests/test_identifiers_contact_normalizers.py` -> collection error (`normalize_address_v1` absent). After `git checkout HEAD --` on the same files, `pytest tests/test_crm_dedup.py tests/test_identifiers_contact_normalizers.py tests/test_1416_crm_notebook_truth.py` -> 110 passed (current-head green), worktree clean. Broader set (dedup, normalizers, notebook hygiene and execution, connector and identifier errors, public API surface) -> 543 passed, 1 skipped.

- 57 tests in `tests/test_crm_dedup.py` pass (46 at `af0c6df7` plus 11 new cases); 2 in `tests/test_1416_crm_notebook_truth.py`.
- Red before: 2 failed at `af0c6df7` for the new regression.
- Post-merge targeted suite: 444 passed, 1 skipped.

## Rework ledger

2 self-caught defects before commit (null-key collision, log count), plus 1 hostile-review blocker fixed (duplicate index label) and 1 rejected with tag evidence (4.1.0 placement).
