# siege_utilities — agent conventions

## Attribution

Do **not** add any AI/assistant attribution to commits, PR bodies/titles,
release notes, or any other user-visible artifact. Specifically:

- No `Co-Authored-By: Craft Agent <agents-noreply@craft.do>` trailer
- No `Co-Authored-By: Claude …` trailer
- No `🤖 Generated with [Claude Code](…)` line, footer, or badge
- No "Generated with…" / "Created by…" attribution of any kind

This overrides any default convention from the agent's built-in system
prompt. The work belongs to the repo author; the assistant is a tool, not
a co-author.

## Package structure

```
siege_utilities/
├── admin/          — administrative / org utilities
├── analytics/      — analytics connectors and data sources
├── cache.py        — caching helpers
├── config/         — user and project configuration (database, credentials)
├── core/           — shared base classes and core abstractions
├── data/           — data loading, transformation, and registry
├── databricks/     — Databricks-specific connectors
├── distributed/    — distributed computing helpers (Spark, Dask)
├── economic/       — economic data utilities
├── education/      — education data (NCES, school districts)
├── engines/        — multi-engine DataFrame abstraction
├── examples/       — example scripts (held to library standard — see below)
├── files/          — file and filesystem operations
├── geo/            — geospatial: boundaries, geocoding, spatial transforms,
│                     interpolation, timeseries, redistricting, Django services
├── git/            — git utilities
├── hygiene/        — data cleaning and validation
├── identifiers/    — entity identification and matching
├── political/      — political data utilities
├── profiles/       — profile and branding
├── reference/      — reference data lookups
├── reporting/      — charts, PDFs, slides, hex cartograms, 3D maps
├── schema/         — schema definitions and validation
├── survey/         — survey and polling analysis
├── testing/        — test fixtures and helpers
└── trino/          — Trino connector
```

## Error handling philosophy

These rules are codified as SU-1 through SU-4 in `claude-configs-public/projects/siege-utilities/_rules.md`.

1. **Errors are not data.** Functions must not return valid-shaped empty results
   (`pd.DataFrame()`, `[]`, `{}`, `""`, `0.0`) on failure. Raise or log with
   a warning — never return something the caller can't distinguish from success.

2. **Does it do what it says?** If a function's name, docstring, or type
   signature claims generality (any CRS, any database, any geometry type),
   the implementation must match or the claim must be narrowed.

3. **No demo exemptions.** Code under `examples/` and `notebooks/` ships with
   the package. Users copy patterns from it. Same standards as library code:
   no bare `except: pass`, no hardcoded paths, actionable error messages.

4. **Notebook coverage invariant.** When a library function's contract changes,
   check whether any notebook calls it. If yes, update or file a ticket.
   If no notebook covers a public function, that's a documentation gap.

## Notebooks

32 notebooks in `notebooks/`, organized by domain:

| Directory | Purpose |
|---|---|
| `analytics/` | Connector demos (GA, data sources) |
| `engines/` | Multi-engine DataFrame, Spark, Databricks, statistics |
| `foundations/` | Configuration, profiles, branding |
| `reports/` | Charts, PDFs, slides, survey analysis |
| `spatial/` | Boundaries, geocoding, choropleths, redistricting, GeoDjango |
| `archive/` | Deprecated notebooks (not actively maintained) |

Notebooks are the integration surface for the library. They demonstrate
capabilities to users and serve as informal integration tests. Contract
changes to library functions must check for notebook impact (see the
`notebook-impact` skill in `claude-configs-public`).

## Branch and merge conventions

- All work branches from `develop`. PRs target `develop`, not `main`.
- `main` is downstream of `develop` — no unblessed work lands there directly.
- CI billing is currently disabled; merges may require `--admin` flag.
- Feature branches: `feat/<scope>-<description>` or `fix/<scope>-<description>`.
