---
ticket_refs:
  - siege-analytics/siege_utilities#1117: open
type: self-review
---

## Self-review for #1117: unwritable HOME import crash

Working as: software engineer

## Assumptions

Domain(s): software engineering, configuration management
Geospatial cross-cut: no
Goal source: ticket #1117 (import-time PermissionError)
Plan reference: none (1 modified file + 1 new test file)
Pre-author-inventory: NONE
Trivial-against-state: modifies UserConfigManager.__init__ to tolerate unwritable HOME
Investigate-artifact: ticket #1117 and electinfo/enterprise#2302
Pre-mortem-artifact: WAIVED (defensive hardening; fail-open behavior change only)
Hostile-review-artifact: WAIVED (single-function fix; no enforcement-path touch)
Project-contribution: Unblocks siege_utilities import in containers with unwritable HOME (Spark/Kubernetes pods with HOME=/nonexistent)

## Pre-implementation comprehension

**Current behavior:** UserConfigManager.__init__ does unconditional mkdir on Path.home()/.siege_utilities/config. Crashes with PermissionError when HOME is unwritable.

**Intended behavior:** Three-tier config dir resolution: SIEGE_USER_CONFIG_DIR env var > Path.home() > TMPDIR fallback. If both fail, run read-only without crashing. _save_user_profile respects _read_only flag.

**Steps:** 1 modified file (config/user_config.py), 1 new test file.

**Success criteria:** HOME=/nonexistent import works without crash. All 4 new tests pass. Existing behavior unchanged for writable HOME.

**What could go wrong:** Temp dir fallback could be unexpected. Mitigated by: warning log message at WARNING level.

## Peer review (the Junior's checklist)

Syntax check: python3 -c "import siege_utilities.config.user_config" succeeds
Test suite: 4 tests pass (unwritable fallback, explicit dir, env override, read-only mode)
writing-code: follows existing warn-and-continue pattern from paths.py
writing-claims: 1 modified file + 1 new test file

## Lead review (the Lead's adversarial pass)

In software engineering: this is a defensive fix that brings UserConfigManager in line with every other siege directory manager. The existing cache/temp/log dirs already warn-and-continue; the config manager was the only outlier.

**Approach fit:** Correct. Three-tier resolution (env > home > tmpdir) with read-only fallback covers all container scenarios.

**Remaining risk:** None. The fix is additive — existing HOME-writable behavior is unchanged.

**Blast radius:** 1 file modified (defensive guard in __init__), 1 new test file.

## Findings

No findings.

## Quantified claims

- "1 modified file" — siege_utilities/config/user_config.py
- "1 new test file" — tests/test_user_config_unwritable_home.py (4 tests)
- "HOME=/nonexistent works" — verified via manual test

## Rework ledger

No rework occurred.
