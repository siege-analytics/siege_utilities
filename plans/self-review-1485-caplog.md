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

## Ticket-fitness exemption

### #1485

Reason: #1485 predates the canonical ticket template; it was filed before `evaluate-ticket.sh` gating.
Evidence: Problem, Evidence, Failure scenario, Done when, Assumptions and Falsifier sections live in https://github.com/siege-analytics/siege_utilities/issues/1485; the reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1485#issuecomment-6256395578.
Falsification: revert the implementation; `tests/test_report_generator_renders_sections.py::test_analytics_pdf_renders_sections` goes red because a chart list raises `AttributeError: 'list' object has no attribute 'get'` and the insight text is absent from the PDF.
Verified 2026-11-05: with `report_generator.py`, `templates/base_template.py` and `templates/content_page_template.py` checked out from `origin/develop`, `pytest tests/test_report_generator_renders_sections.py -k test_analytics_pdf_renders_sections` -> 2 failed (`report_generator.py:703: AttributeError: 'list' object has no attribute 'get'`; `assert 'X1' in ...`); after `git checkout HEAD --` on the same files -> 2 passed, worktree clean.

## Assumptions

1. The warning is emitted on `siege_utilities.reporting.report_generator` (module logger), so setting that logger's level is sufficient for `caplog`.
2. The test settings may disable existing loggers; resetting `disabled` through `monkeypatch` is restored at teardown.
3. Under the operator's standing rule (2026-11-06: an entry is BREAKING when code that worked on 4.0.0 now behaves differently), the #1485 contract entry moves from `[4.1.0]` `### Changed` to `### BREAKING` with a Migration line. Custom section types, a DataFrame appendix and non-string content now raise, and a titled report gains an automatic title page. The Migration's title-page sentence was checked against `report_generator.py:480-481`. The develop `71f02b0b` merge kept both `[4.1.0]` Fixed entries (a union); develop's lines are unchanged.

## Test plan

- Red before (at `6cc9f1a1`): `pytest tests/test_report_generator_renders_sections.py::test_missing_chart_warns` run alone -> 1 failed (`assert 'chart' in ''`).
- After the fix, alone -> 1 passed.
- Whole module with `pytest-randomly` seeds 37 and 102 (the seeds the reviewer saw fail) -> 24 passed each, after merging develop `dc7d3f76`.

## Peer review

- Shelves: writing-tests:3 (tests must not depend on order or on other tests' side effects), writing-claims:2 (counts carry `Verified-by:`).
- Syntax check: `py_compile` on 1 changed `.py` file -> parses clean (exit 0).
- Test suite: module 24 passed under each of seeds 37 and 102; the target test passes alone.
- Findings: test-only change; no library code touched. The two #1485 CHANGELOG entries are in `[4.1.0]` (`### BREAKING`, moved from `### Changed`, and `### Fixed`) after the develop `71f02b0b` merge.
- Notebook API: N/A (no library contract change). Doc build N/A.

## Lead review

- Fixes the cause the reviewer named (root at CRITICAL, no level on the logger under test), and also the latent `disable_existing_loggers` path the hostile review flagged.
- Post-mortem: not applicable. Caught in review before merge; no published version carried it.

## Quantified claims

- 1 red alone at `6cc9f1a1`; 1 passed alone after; 24 passed per seed (37, 102).

## Rework ledger

1 hostile-review follow-up applied (reset `disabled`).

## Develop integration (79f37f4d, 2026-11-11)

Reason for the merge: after #1812 landed, develop `79f37f4d` and this branch added entries at the same places in `CHANGELOG.md`, so the pull request reported a conflict.

Merge: `bbf88492b42f13848e6b4efcbecd40eff886a3f2` (first parent) + develop `79f37f4df28059a875c8dbf84cf77ce86812bdbb`, made with `--no-ff --no-commit`. One file conflicted, `CHANGELOG.md`, with two add/add hunks under `## [5.0.0]`. Both sides were kept verbatim, develop's entries first, and only the conflict markers were removed. No source, template or test file needed resolution.

- `### Fixed`: develop's #1882, #1458 and #1474 entries, then this PR's #1485 rendering entry.
- `### BREAKING`: develop's #1474/#1458, #1465/#1835 and #1812 entries with their Migration paragraphs, then this PR's `generate_pdf_report` entry with its Migration paragraph, unchanged.
- `CHANGELOG.md` against `79f37f4d`: 23 lines added, none removed (this PR's two entries). Against `bbf88492`: 116 added, 2 removed; the 2 are develop's own edits outside the conflict (the held section renamed to `[5.0.0]`, and the SSL entry's release number).
- Inventory against `79f37f4d`: only this PR's 7 files differ. Every imported develop file equals landed develop.
- Inventory against `bbf88492`: develop's 39 files differ, plus this section. This PR's source, template and test files equal `bbf88492`.
- The `[4.1.0]` references in Assumption 3 and Peer review above are historical; develop renamed that section to `[5.0.0]`.

Tests in the merged tree: Python 3.11.11, pytest 8.4.2, pytest-randomly 5.0.0, ReportLab 4.4.10 rendering real PDFs, PyPDF2 3.0.1 parsing their text.

- `pytest -p randomly --randomly-seed=1736` over `tests/test_report_generator_renders_sections.py tests/test_content_page_template_errors.py tests/test_reporting_errors.py tests/test_reporting_factory_contracts.py tests/test_reporting_markup_escaping.py tests/test_reporting_module.py tests/test_table_utils.py tests/test_backward_compat.py tests/test_public_api_surface.py tests/test_sprint_a_reliability.py tests/test_1812_fidelity_oracle.py tests/test_1812_null_policy_end_to_end.py tests/test_social_media_reports_nulls.py tests/test_social_media_reports_errors.py tests/guard/test_exception_contract_guard.py` -> 815 passed, 3 skipped. Two skips in `tests/test_sprint_a_reliability.py` need `weightipy`, which is not installed; `tests/test_reporting_module.py:616` runs only when `python-pptx` is absent. None is in the #1485 module.
- `tests/test_report_generator_renders_sections.py` alone under seeds 37 and 102 -> 24 passed each, no skips. These include the page-overflow, repeated-header and missing-chart log checks.
- `scripts/check_exception_contracts.py --list` -> 205 handlers flagged, 0 unlisted, 0 stale.
- Boundary: the rendered-PDF checks parse extracted text; they do not compare page images. The PostGIS and notebook jobs were not run locally; exact-head CI is the evidence for them.
