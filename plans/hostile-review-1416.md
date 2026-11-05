---
ticket_refs:
  - siege-analytics/siege_utilities#1416: summarized in the self-review comment https://github.com/siege-analytics/siege_utilities/issues/1416#issuecomment-6650792304
---

# Hostile review: #1416 / PR #1776 uncorroborated-namesake fix

Reviewer: a separate read-only review agent (same model family as the implementer; read-only, no edits). The cross-family exact-head re-review by the independent PR reviewer is still required and is requested after push.
Scope: the uncommitted diff on top of `df2faba0` (`_dedup.py`, `tests/test_crm_dedup.py`, `tests/test_1416_crm_notebook_truth.py`, `notebooks/analytics/04_crm_pipeline.ipynb`, `CHANGELOG.md`).

## Findings and dispositions

1. BLOCKER, fixed: the null/blank source-key fallback seed used the frame index label. Labels repeat after `pd.concat` without `ignore_index`, and the seed omits the name, so two different people (Maria Garcia, John Smith) with null `source_id` in one frame would share a `canonical_id`. Fix: seed from the row position (`enumerate(df.iterrows())`). Regression `test_missing_source_key_rows_with_duplicate_index_labels_stay_distinct`: red with the label seed (`assert 1 == 2`), green with the position seed.
2. BLOCKER claimed, rejected with evidence: "the #1416 note is filed under 4.1.0, which already shipped." `git ls-remote --tags origin 'v4.1*'` returns nothing, and no local `v4.1*` tag exists. `origin/main` carries `version = "4.1.0"` from re-sync `cf00f68d`, but the 4.1.0 tag and publication are on hold pending operator GO. The PR reviewer's register asks for this note in the held `[4.1.0]` section, so the placement and the "differs from 4.0.0" migration baseline (the last published release) stand.
3. FOLLOW-UP, accepted as pre-existing: list- or array-valued source keys or identifiers make `pd.isna` ambiguous. The name loop had the same shape before this change, so it is not a regression; candidate for a separate hardening ticket.
4. FOLLOW-UP, conservative: `str()` coercion can split the same record across frames (`1` vs `1.0` after a null upcasts an int column; unstripped keys). This splits rather than merges, so it does not violate the ticket.
5. FOLLOW-UP, documented: the `source_record` seed omits the name, so rows with the same (system, id) and different names share an ID. The docstring states this; a test pins the repeated-record case.
6. Informational: the three seed shapes cannot collide (different JSON arity and types; `json.dumps` escapes quotes). The log counts match the docstring and are tested. The tests are order-independent under pytest-randomly. The notebook matches the code.
7. Nit, fixed: the notebook lost its trailing newline after the cell edit; restored.

Verdict after dispositions: no open blockers from this pass.

## Second pass: gaps A and B (normalized phone and address, one key suffices)

Scope: the A+B change on top of `f71e3cd9` (`identifiers/normalize.py`, `connectors/_dedup.py`, tests, CHANGELOG, notebook), reviewed against `plans/design-1416-identifier-graph.md`.

1. BLOCKER raised, resolved by operator ruling: the per-component conflict guard covers every column, so a pair that merged at `f71e3cd9` on an equal email is split when its phone differs or its address is partial on one side. Escalated to the hub. The ruling keeps the guard on every column ("as written"). The trade-off is now stated in the docstring, CHANGELOG, design note and PR body. Callers who want email-only corroboration pass `identifier_columns=["email"], address_columns=[]`, pinned by `test_email_only_migration_setting_restores_email_corroboration`.
2. FOLLOW-UP, fixed: each key linked members only to its first (smallest-seed) member, so one conflicting record kept two compatible ones apart. Now every earlier member is tried; covered by `test_conflicting_member_does_not_block_two_compatible_members`.
3. FOLLOW-UP, documented: when one record matches two others that conflict with each other, it joins the smaller-seed side. That is deterministic and row-order independent.
4. FOLLOW-UP, fixed before freezing v1: the address normalizer now works per component. State names map only in the state field, so "West Virginia Ave" is no longer rewritten. ZIP rules apply only to the postal field, so house numbers are not read as ZIPs and numeric ZIPs are zero-padded. Unit designators (`#`, apt, suite, unit) are unified. The phone normalizer drops extensions. The court/connecticut and floor/florida collisions are gone with the shared table.
5. FOLLOW-UP, fixed: `identifier_normalizers` now adds to the phone default instead of replacing it, and non-callable values raise `ValueError`.
6. FOLLOW-UP, open question to operator: unmerged namesakes that each carry their own identifier show `match_confidence` 1.0 (each record's own evidence). Asked whether candidates should show < 1.0.
7. FOLLOW-UP, fixed: tests that also pass at `f71e3cd9` are labeled as controls in the self-review; the design note no longer claims every test fails at the prior head.
8. FOLLOW-UP, documented: CRMContact has no suffix field, so a Sr/Jr pair sharing a household phone or address can merge if no identifier conflicts. Stated as the residual risk in the docstring and design note.
9. FOLLOW-UP, documented: `canonical_id` can change when a smaller-seed member joins; the docstring says to regenerate merge tables rather than append.
10. FOLLOW-UP, fixed: notebook section 2 and the CHANGELOG now describe email, phone and address defaults, the widened defaults and the email-only Migration line.
