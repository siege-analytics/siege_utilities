# Self-Review: release v3.18.0

## Assumptions

Working as: software engineer
Goal source: release task — accumulation of SU#381, SU#527, SU#533, SU#534, SU#535, SU#545, SU#546, SU#547, SU#548, SU#551, SU#552
Goal source verification: all tickets merged to develop via reviewed PRs

- Version bump 3.17.2 → 3.18.0 (minor: new features, no breaking changes)
- Both pyproject.toml and __init__.py fallback updated
- No API removals; all changes are additive

## Peer review

Shelf: writing-releases:1 (version bump matches change scope)

### Shelf checks

1. **Version consistency**: pyproject.toml and __init__.py both say 3.18.0
2. **Scope**: new features (boundary models, plan_status, economic/education lifts, CRS detection, data_reception, swmaps_reader) + 1 bugfix (migration 0006) = minor bump
3. **No breaking changes**: all exports are additive; no removals in __all__

## Lead review

- **[Correctness]** Version bump is correct for the scope of changes
- **[Sequencing]** All feature PRs merged to develop before promote branch created
