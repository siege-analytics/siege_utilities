---
ticket_refs:
  - siege-analytics/siege_utilities#1476: summarized in the self-review ticket comment
---

# Hostile review: #1476 / PR #1738 public signature restore

Reviewer: a separate read-only review agent (same model family as the implementer). The cross-family exact-head re-review by the independent PR reviewer is still required and is requested after push.
Scope: the uncommitted diff on top of the develop merge `ad39229a` (`siege_utilities/config/databases.py`, `tests/test_databases_config_roundtrip.py`, `CHANGELOG.md`).

## Findings and dispositions

1. No blocker: the only public signature the PR changes against `v4.0.0` is `create_database_config`, and with this change it matches 4.0.0 exactly (`databases.py:105`). No package `__init__` re-export changed. `_validate_host` and `_validate_port` are private and not in `__all__`.
2. No blocker (SU-2): the `int` annotation claims less than the runtime accepts, and the docstring (`databases.py:114-117`) states the digit-string allowance and the `ValueError`, matching `_validate_port` (`databases.py:92-102`).
3. No blocker: the signature test fails on `89e8d749` (`port: int | str`) and passes after the change.
4. FOLLOW-UP, accepted: `test_digit_string_port_is_still_accepted_at_runtime` overlaps the `"5432"` case in `tests/test_1476_port_host_injection.py`. It is kept because it pins the exact JDBC URL next to the signature test that narrowed the annotation.
5. No blocker: the #1476 entry sits fully inside `[4.1.0]` → Fixed and matches its previous text word for word, plus one clause about the annotation. The other `[Unreleased]` entries survived the merge resolution.
6. Nit, accepted: an uneven line wrap at `CHANGELOG.md:135-136`; it renders correctly.

Verdict: no blockers.
