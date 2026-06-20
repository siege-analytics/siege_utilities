## Assumptions
Domain(s): packaging, build
Geospatial cross-cut: no
Goal source: ticket #1049
Goal source verification: Codex hostile review session 260619-apt-sequoia, finding S2-9. Related to #1040.
Plan reference: inline design (add exclude-package-data to pyproject.toml)
Pre-author-inventory: pyproject.toml (existing file)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
314 Finder-duplicate files (`* 2.py`) exist on disk but are gitignored. The fix adds `[tool.setuptools.exclude-package-data]` to prevent them from entering wheel builds from dirty working trees.

## Trivial-pre-mortem declaration
Config-only change to pyproject.toml. No runtime code affected. Rollback: `git revert`.

## Peer review

### Syntax check
TOML: valid (pyproject.toml is not executable).

### Build validation
`[tool.setuptools.exclude-package-data]` is the standard setuptools mechanism for excluding files from package data.

## Lead review

### Phase A: Structural coherence
Added `[tool.setuptools.exclude-package-data]` section after `[tool.setuptools.packages.find]`. Glob patterns `"* [0-9].py"` and `"* [0-9][0-9].py"` match Finder's copy naming convention.

### Phase B: Did this close the gap?
- [x] Finder duplicates excluded from wheel builds
- [x] Comments reference both #1040 and #1049 for context
- [x] Existing git-tracked files unaffected (none of these patterns match tracked files)

## Findings
No findings.

## Evidence-predates-work
Artifact: plans/self-review-1049.md
