# Hostile review: PR #1176 batch 1 (geo.spatial_data promotion)

## Findings

**F1 (Minor / latent trap): Three promoted names have sibling definitions in unrelated modules.**
Runtime resolution is correct today (all three resolve to `geo.spatial_data`, verified via `__module__`), but the names collide with functions defined elsewhere in the tree:

- `get_census_boundaries` — also defined at `siege_utilities/reference/sample_data.py:271`
- `get_census_data` — also defined at `siege_utilities/reference/sample_data.py:325`
- `get_available_years` — also defined at `siege_utilities/geo/timeseries/longitudinal_data.py:484`

Neither `reference/sample_data.py` nor `geo/timeseries/longitudinal_data.py` is currently registered in `_LAZY_IMPORTS`, so today there is no shadowing conflict. However: (a) once these modules get promoted in a future batch, `_register_lazy` order will silently pick a winner and the explicit `__all__` entry will bind to whichever loses the race, with no error raised; (b) `help(su.get_census_boundaries)` / IDE go-to-definition already lie by omission — there are two implementations with the same name and consumers cannot tell. Recommend: (i) file a follow-up ticket to reconcile (rename losers or delete stale copies) before the next promotion batch, or (ii) add an assertion in `_register_lazy` that raises on duplicate name registration to make the trap fail loudly the moment a collision would activate.

**F2 (Minor): No test coverage of `__all__` contents.**
`grep -rn 'siege_utilities\.__all__\|from siege_utilities import \*' tests/` returns empty. A regression test asserting `set(su.__all__) >= EXPECTED_MINIMUM` and `all(getattr(su, n) for n in su.__all__)` would catch accidental removal, name typos in future batches, and cross-module registration collisions. Cheap to add; batch 1 is the moment to introduce the scaffold. Cross-references SU-4b (error-path coverage) and the general concern that a public-API declaration with no test is speculation.

## Verifications performed

- `git diff develop..HEAD -- siege_utilities/__init__.py` — reviewed full diff, 74 lines added, no other edits.
- `python -c "diff(distributed.__all__, preserved_set)"` — exit 0; both sets have exactly 39 members, symmetric difference empty. Preserved surface is complete.
- `python -c "[getattr(su, n) for n in su.__all__]"` — exit 0, no AttributeError. All 79 names resolve.
- `set(su.__all__).count` duplicate check — 0 duplicates within `__all__`.
- `python -c "print(getattr(su, n).__module__ for n in promoted)"` — all 27 resolve to `siege_utilities.geo.spatial_data`.
- `grep -rn "^def <27 names>" siege_utilities/` — surfaced F1 collisions in `reference/sample_data.py` and `geo/timeseries/longitudinal_data.py`.
- Comment / grouping structure re-read against block contents: eager core (11), metadata (3), preserved distributed (39), promoted geo.spatial_data (27) = 80 declared. Actual `len(__all__) = 79`. **Discrepancy is one item**: `settings` counted as one but list literal is correct; recount: 1 (settings) + 5 (log_*) + 3 (init/get/configure) + 1 (remove_wrapping) = 10 eager core, not 11. Comment says "11 items" in the review brief but code and my count agree at 10. Not a defect in the diff; noting in case the PR body / self-review artifact repeats the "11" miscount.

## Verdict

**SHIP WITH REVISIONS.** F1 is latent, not active — no runtime breakage today — but the collision surface expands with every promotion batch. Either add the duplicate-registration assertion or file the reconciliation follow-up before batch 2 lands. F2 (no `__all__` test) is a cheap add and this PR is the natural home. Neither finding blocks merge on its own; together they warrant one revision cycle.
