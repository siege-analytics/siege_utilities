## Assumptions
Domain(s): configuration
Geospatial cross-cut: no
Goal source: ticket #1048
Goal source verification: Codex hostile review session 260619-apt-sequoia, finding S2-8
Plan reference: inline design (add warning log on coercion fallback)
Pre-author-inventory: siege_utilities/conf/__init__.py (existing file)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Single function `_coerce()` in `conf/__init__.py`. Called only by `__getattr__` in the same class. The fix adds `logger.warning()` calls on the fallback paths — no behavioral change, just observability.

## Trivial-pre-mortem declaration
Adding warning logs to exception handlers. The default value is still returned (existing behavior preserved). No API change. The only new behavior is a log line.

## Peer review

### Syntax check
Python: `ast.parse()` passes.

### Test suite
No behavioral change to test — only new log output.

### Build validation
No build changes.

## Lead review

### Phase A: Structural coherence
Added `import logging` and `_logger = logging.getLogger(__name__)`. Two `_logger.warning()` calls in the `except (ValueError, TypeError)` handlers for int and float coercion, logging the setting name, bad value, and default.

### Phase B: Did this close the gap?
- [x] Invalid int env vars now produce a warning
- [x] Invalid float env vars now produce a warning
- [x] Warning includes setting name, bad value, and default
- [x] Default still returned (no behavioral change)
- [x] AST parse clean

## Findings
No findings.

## Evidence-predates-work
Artifact: plans/self-review-1048.md
