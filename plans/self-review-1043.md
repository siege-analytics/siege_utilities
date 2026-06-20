## Assumptions
Domain(s): analytics, Google Analytics connector
Geospatial cross-cut: no
Goal source: ticket #1043
Goal source verification: Codex hostile review session 260619-apt-sequoia, findings S1-4 and S1-5
Plan reference: design note on #1043
Pre-author-inventory: siege_utilities/analytics/google_analytics.py (existing file)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Two functions in a single module. `batch_retrieve_ga_data` has no callers within siege_utilities (top-level convenience API). `GoogleAnalyticsConnector.__init__` is called by `create_ga_connector_with_service_account()` and `batch_retrieve_ga_data()` — both in the same file. No cross-module impact.

## Trivial-pre-mortem declaration
Risk surface: constructor now raises RuntimeError instead of silently continuing with None credentials. Any caller that caught and retried was already using a broken connector. The success flag fix is additive — existing callers that checked `results['success']` were getting a lie; now they get truth.

## Peer review

### Syntax check
Python: `ast.parse()` passes on `google_analytics.py`.

### Test suite
No test files for google_analytics.py found. Verified via grep.

### Build validation
No build changes.

### Shelf: conventions
SU-1 restored: constructor raises on auth failure instead of silently producing unusable object. Batch retrieval's success flag now reflects actual outcome.

## Lead review

### Phase A: Structural coherence
Two changes:
1. Constructor (lines 115-129): `except ImportError` and `except CalledProcessError` now raise `RuntimeError` with actionable messages instead of logging warnings and continuing.
2. `batch_retrieve_ga_data` (line 646): `results['success'] = not results['errors']` set before return, overriding the initial `True`.

### Phase B: Did this close the gap?
- [x] Constructor raises on 1Password ImportError (was: log warning, continue)
- [x] Constructor raises on 1Password CalledProcessError (was: log warning, continue)
- [x] Success message at line 130 only reached when auth actually succeeded
- [x] batch_retrieve_ga_data success flag reflects actual error state
- [x] AST parse clean

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims
- "Constructor raises instead of silently continuing" — verified: both except blocks now raise RuntimeError. Correct.
- "Success flag set before return" — verified: `results['success'] = not results['errors']` at line 646. Correct.

## Evidence-predates-work
Artifact: plans/self-review-1043.md
