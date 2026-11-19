---
ticket_refs:
  - siege-analytics/siege_utilities#1485: summarized in the self-review ticket comment
---

# Hostile review: #1485 / PR #1736 order-independent log test

Reviewer: a separate read-only reviewer, independent of the implementer. An independent exact-head re-review is still required and is requested after push.
Scope: the test-only diff on top of the develop merge `d106a3a0` (`tests/test_report_generator_renders_sections.py`).

## Findings and dispositions

1. No blocker: the logger name is correct. `report_generator.py:46` uses `logging.getLogger(__name__)`, and the missing-chart warning (`report_generator.py:573`) carries both "chart" and the file name.
2. No blocker: `caplog.set_level(..., logger=...)` restores the logger and handler levels at teardown.
3. FOLLOW-UP, fixed: `tests/django_project/settings.py:88` sets `disable_existing_loggers: True`. If Django logging were reconfigured after import, the logger would be disabled, and `set_level` does not clear that. The test now also resets `disabled` via `monkeypatch`, matching `tests/test_credential_url_leak.py:41-46`.
4. No blocker: this is the only log-capture test the PR adds.

Verdict: no blockers.
