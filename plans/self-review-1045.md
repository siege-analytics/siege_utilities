## Assumptions
Domain(s): geo, overlay registry
Geospatial cross-cut: yes
Goal source: ticket #1045
Goal source verification: Codex hostile review session 260619-apt-sequoia, finding S2-4
Plan reference: inline design (let constructor exceptions propagate)
Pre-author-inventory: siege_utilities/geo/overlay_registry.py (existing file)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Single method `OverlayRegistry.get()`. The broad `except Exception` swallowed constructor failures and returned None — making a broken registered overlay indistinguishable from an unregistered one. Fix: remove the try/except and let constructor exceptions propagate.

## Trivial-pre-mortem declaration
Risk: callers that relied on `get()` returning None for broken overlays will now see exceptions. But that's the correct behavior — a registered overlay that can't be instantiated is an error, not an absence. Callers should handle it explicitly.

## Peer review

### Syntax check
Python: `ast.parse()` passes.

### Build validation
No build changes.

## Lead review

### Phase A: Structural coherence
Removed `try/except Exception` wrapper around `self._classes[name]()`. Updated docstring to document the Raises section.

### Phase B: Did this close the gap?
- [x] Constructor exceptions now propagate
- [x] Docstring updated with Raises section
- [x] None still returned for genuinely unregistered overlays
- [x] AST parse clean

## Findings
No findings.

## Evidence-predates-work
Artifact: plans/self-review-1045.md
