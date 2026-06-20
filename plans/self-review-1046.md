## Assumptions
Domain(s): reporting
Geospatial cross-cut: no
Goal source: ticket #1046
Goal source verification: Codex hostile review session 260619-apt-sequoia, findings S2-5 and S2-6
Plan reference: inline design
Pre-author-inventory: siege_utilities/reporting/report_generator.py, siege_utilities/reporting/__init__.py (existing files)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Three functions in two files. `_process_charts` and `_build_section_content` are private methods on ReportGenerator — callers are within the same class. `get_report_output_directory` is a convenience function called by `create_report_generator` in the same file.

## Trivial-pre-mortem declaration
`_process_charts` and `_build_section_content` now raise ImportError instead of returning []. Any caller that reached these methods without ReportLab was already getting silently broken reports — raising is strictly better. The output directory fallback is unchanged but now logs a warning.

## Peer review

### Syntax check
Python: `ast.parse()` passes on both files.

### Build validation
No build changes.

## Lead review

### Phase A: Structural coherence
- `_process_charts` (line 544): `return []` → `raise ImportError(...)`
- `_build_section_content` (line 636): `log.error + return []` → `raise ImportError(...)`
- `get_report_output_directory` (line 135): added `logging.warning()` before CWD fallback

### Phase B: Did this close the gap?
- [x] Missing ReportLab now raises instead of producing silently incomplete reports
- [x] Output directory fallback now logs a warning
- [x] Both files AST parse clean

## Findings
No findings.

## Evidence-predates-work
Artifact: plans/self-review-1046.md
