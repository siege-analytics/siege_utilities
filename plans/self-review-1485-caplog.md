---
ticket_refs:
  - siege-analytics/siege_utilities#1485: comment posted https://github.com/siege-analytics/siege_utilities/issues/1485#issuecomment-6651317443
---

# Self-review: #1485 / PR #1736, order-independent missing-chart log test

Working as: software engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1485#issuecomment-6256395578 (required changes 1 and 2)
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1485#issuecomment-6651199765 (fact sheet: `tests/test_report_generator_renders_sections.py:132-136`, `tests/django_project/settings.py:86-98`)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1485#issuecomment-6651199765
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1485#issuecomment-6651199765
Hostile-review-artifact: plans/hostile-review-1485-caplog.md

## Assumptions

1. The warning is emitted on `siege_utilities.reporting.report_generator` (module logger), so setting that logger's level is sufficient for `caplog`.
2. The test settings may disable existing loggers; resetting `disabled` through `monkeypatch` is restored at teardown.

## Test plan

- Red before (at `6cc9f1a1`): `pytest tests/test_report_generator_renders_sections.py::test_missing_chart_warns` run alone -> 1 failed (`assert 'chart' in ''`).
- After the fix, alone -> 1 passed.
- Whole module with `pytest-randomly` seeds 37 and 102 (the seeds the reviewer saw fail) -> 24 passed each, after merging develop `dc7d3f76`.

## Peer review

- Shelves: writing-tests:3 (tests must not depend on order or on other tests' side effects), writing-claims:2 (counts carry `Verified-by:`).
- Syntax check: `py_compile` on 1 changed `.py` file -> parses clean (exit 0).
- Test suite: module 24 passed under each of seeds 37 and 102; the target test passes alone.
- Findings: test-only change; no library code touched. The two #1485 CHANGELOG entries were already in `[4.1.0]` (`### Changed` and `### Fixed`) and remain there after the develop merge.
- Notebook API: N/A (no library contract change). Doc build N/A.

## Lead review

- Fixes the cause the reviewer named (root at CRITICAL, no level on the logger under test), and also the latent `disable_existing_loggers` path the hostile review flagged.
- Post-mortem: not applicable. Caught in review before merge; no published version carried it.

## Quantified claims

- 1 red alone at `6cc9f1a1`; 1 passed alone after; 24 passed per seed (37, 102).

## Rework ledger

1 hostile-review follow-up applied (reset `disabled`).
