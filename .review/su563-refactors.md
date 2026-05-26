# Self-Review: SU#563 (Group 2) — code deduplication refactors

## Assumptions

Working as: software engineer, architecture focus
Goal source: https://github.com/siege-analytics/siege_utilities/issues/563
Goal source verification: ticket exists as sub-issue of epic #557

- `run_git_command` was byte-identical in all 4 git modules; safe to extract
- `ADMIN_LEVEL_AVG_AREA_KM2` and `_ADMIN_LEVEL_ALIASES` were identical in h3_utils and s2_utils
- `UserProfile` collision in config/__init__.py is already handled via aliasing (`EnhancedUserProfile`, `PydanticUserProfile`); no change needed

## Peer review

Shelf: writing-code:1, writing-code:3

### Shelf checks

1. **git/_utils.py**: new file with canonical `run_git_command`; uses same `subprocess` + `GitError` pattern as originals
2. **git/git_status.py, git_operations.py, branch_analyzer.py, git_workflow.py**: replaced inline definitions with `from ._utils import run_git_command`; removed now-unused `import subprocess`
3. **geo/_admin_areas.py**: new file with canonical `ADMIN_LEVEL_AVG_AREA_KM2` and `ADMIN_LEVEL_ALIASES`
4. **geo/h3_utils.py, geo/s2_utils.py**: replaced inline dicts with `from ._admin_areas import ...`
5. **config/__init__.py UserProfile**: no change — aliasing already resolves the collision
6. **Import smoke test passed** for both new modules

## Lead review

- **[Backwards compatibility]** `ADMIN_LEVEL_AVG_AREA_KM2` is re-exported at the same module path via the import; existing `from siege_utilities.geo.h3_utils import ADMIN_LEVEL_AVG_AREA_KM2` still works
- **[run_git_command]** not in any `__all__`; internal-only. Callers within the git package now share one definition
