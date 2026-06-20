## Assumptions
Domain(s): notebooks, SU-3 compliance
Geospatial cross-cut: no
Goal source: ticket #1050
Goal source verification: Codex hostile review session 260619-apt-sequoia, findings S2-10 and S2-11
Plan reference: inline design
Pre-author-inventory: 7 notebook files (existing)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Notebook exception handling and output clearing. No runtime code changes. Archive notebooks are shipped examples (SU-3 applies) but are not executed in any pipeline.

## Trivial-pre-mortem declaration
Exception type narrowing is strictly more correct. Output clearing removes personal paths from shipped artifacts. No runtime impact.

## Peer review

### Syntax check
All 7 notebooks valid JSON after edits.

### Build validation
No build changes.

## Lead review

### Phase A: Structural coherence
Two categories of fix:
1. **Exception narrowing** (2 notebooks):
   - Census notebook cells 7, 8: `except Exception` → `except (requests.RequestException, KeyError, ValueError)`
   - Sample Data notebook cells 27-30: `except Exception` → `except (requests.RequestException, OSError)`
2. **Output clearing** (5 notebooks): Removed cell outputs containing hardcoded personal paths, 1Password metadata, and personal email from repo_analysis, 01_configuration, 01_boundaries, 10_Profile_Branding_Testing, 18_Google_Workspace notebooks.

### Phase B: Did this close the gap?
- [x] No broad `except Exception` in archive notebooks (replaced with specific types)
- [x] Personal paths cleared from notebook outputs
- [x] All notebooks valid JSON
- [x] Cell source code preserved

## Findings
No findings.

## Evidence-predates-work
Artifact: plans/self-review-1050.md
