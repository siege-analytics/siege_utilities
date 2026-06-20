## Assumptions
Domain(s): security, shell utilities
Geospatial cross-cut: no
Goal source: ticket #1042
Goal source verification: Codex hostile review session 260619-apt-sequoia, finding S1-3
Plan reference: design note on #1042
Pre-author-inventory: siege_utilities/files/shell.py (existing file)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Dead code deletion. `_run_subprocess_unrestricted()` has zero callers — verified via `grep -r '_run_subprocess_unrestricted' siege_utilities/`. Only hits: the function definition itself. The function's own docstring says "should be removed in future versions." No imports, no test references, no notebook references.

## Trivial-pre-mortem declaration
Risk surface: deletion of a single private function from `siege_utilities/files/shell.py`. The function is unused (zero callers). No public API changes. No downstream impact. Rollback: `git revert`.

## Peer review

### Syntax check
Python: `ast.parse()` passes on `shell.py` after deletion.

### Test suite
No tests reference `_run_subprocess_unrestricted`. Verified via grep.

### Build validation
No build changes.

### Shelf: conventions
SU-1 compliance: removing a function that returns stderr output on non-zero exit (line 257) instead of raising — an SU-1 violation that no longer matters because the function is gone.

## Lead review

### Phase A: Structural coherence
Single deletion of lines 199-265 from `shell.py`. The `__all__` list at line 268 (now 199) is unchanged — the deleted function was never exported. The `shlex` import remains needed by `run_subprocess()` at line 72.

### Phase B: Did this close the gap?
- [x] `_run_subprocess_unrestricted()` removed from the codebase
- [x] No callers broken (zero callers existed)
- [x] `shlex` import still needed (used by `run_subprocess`)
- [x] `__all__` unchanged (function was never exported)
- [x] AST parse clean

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims
- "Zero callers" — verified: grep across entire siege_utilities/ directory returns only the definition. Correct.
- "shlex still needed" — verified: used at shell.py:72 by run_subprocess(). Correct.

## Evidence-predates-work
Artifact: plans/self-review-1042.md
