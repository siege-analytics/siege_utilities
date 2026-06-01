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

## Strategic intent

siege_utilities is a thesaurus of space-time composition tools. Every piece
exists to serve one question: what happened, where, when, and what does
proximity imply?

The library ties events to coordinates in space-time, then extrapolates
significances and meanings from placement. Domain packages (political,
economic, education, survey, analytics) produce events. Geo locates them.
Engines scale them. Reporting presents them. The canonical composition chain
is: address → geocoder → GEOID → boundary provider → demographic overlay →
choropleth or report.

Domain packages are primitives, not applications. `political/` provides DDL
and entities. `education/` downloads NCES data. These are building blocks
consumed by downstream projects (LegiNation, socialwarehouse, electinfo).
The library encodes domain expertise — what data exists, where it lives, how
to access it — not domain analysis.

Temporal awareness is first-class. Redistricting plans have effective dates.
Congressional districts depend on congress number matching vintage year.
Census data has vintages. Survey data has waves. Not just "where" but
"where-when."

## Architectural decisions

1. **Geo is the gravitational center.** All domain modules produce events
   that need space-time location before they become analytically useful.
   Changes to geo propagate everywhere.

2. **Engine-agnostic DataFrame.** Same analysis at different scales without
   rewriting: pandas for exploration, DuckDB for medium scale, Spark for
   distribution, PostGIS for persistence. The abstraction serves the general
   case; when you must drop to native (Spark SQL, raw pandas), use that
   engine's idioms. Do not create single-consumer abstractions.

3. **OSGeo preferred, alternatives when constrained.** GDAL/OGR, PROJ, GEOS
   via Shapely, Fiona, rasterio are the default geospatial stack. When the
   deployment target cannot run C libraries (Databricks, Lambda, serverless),
   use Sedona, DuckDB-spatial, or pure-Python paths. The constraint must be
   explicit, not a silent fallback. A missing non-GDAL path is a gap to fill,
   not a design choice to accept.

4. **Databricks and Snowflake are first-class targets.** Azure Databricks
   cannot install GDAL. The `databricks/` bridge pattern (Spark → driver-side
   GeoPandas → back to Spark) is an architectural choice. Snowflake's
   geography type and Trino federation are parallel vendor paths.

5. **Pluggable providers with shared contracts.** Boundary providers (Census
   TIGER, GADM, RDH), geocoders, data sources — all pluggable so callers
   compose without knowing which provider is active. Provider contracts must
   be consistent: same failure mode, same return shape, same column names.

6. **Lazy loading by design.** PEP 562 `__getattr__` because the dependency
   tree is enormous. You must be able to import one piece in a Lambda or
   notebook without pulling the whole library. Lazy loading defers when errors
   surface, not whether they surface: `__getattr__` must never catch
   ImportError and return a stub — let it propagate (SU-1 applies).

7. **Credential management via external tools.** 1Password CLI (`op`),
   environment variables, Databricks secret scopes. `siege_zsh` sets up the
   shell environment that siege_utilities expects. `siege_zsh` is a reference
   architecture — it shows the frameworks and tooling we build for. Code
   should detect and leverage `siege_zsh` conventions but not hard-fail
   without them.

8. **Fuzzy matching at seams is expected.** Precinct names from three vendors
   with different conventions. The library provides the fuzzy-matching
   mechanism (canonicalization, normalization, scoring); heavy entity
   resolution belongs in downstream applications.

## Tactical principles

1. **Pythonic patterns.** Scala is a far-off dream; the library is
   Python-first. Use Python idioms, not Java-in-Python. Protocols over
   abstract base classes when feasible. Type hints everywhere.

2. **Technology-appropriate implementation.** A PostgreSQL query has different
   constraints than pandas, even for the same goal. Write SQL that uses SQL
   strengths (window functions, CTEs, lateral joins). Write pandas that uses
   pandas strengths (vectorized ops, groupby-apply). Do not transliterate one
   into the other.

3. **Logging is a primary concern.** Every side-effecting process must produce
   observable output. Progress indicators for long-running operations. The
   operator must always be able to see what is happening.

4. **Functional approaches preferred.** Prefer composition and immutability
   over mutation, not strict purity (logging wraps pure cores). Legibility
   over elegance within a function (each case obvious to a cold reader);
   elegance across modules (minimal, orthogonal protocols). The boundary is
   the module boundary.

5. **Notebooks demonstrate intent; foundations are not negotiable.** Notebooks
   demonstrate current library capabilities and should be rewritten when
   functions change. The foundations (user architecture, Spark Connect,
   credential management, engine abstraction) must be solid because everything
   composes on top of them.

6. **Reuse siege_zsh when available.** Shell environment setup should leverage
   `siege_zsh` conventions. Code should detect and use them but not hard-fail
   without them. The graceful degradation path must actually work and be
   tested.

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
