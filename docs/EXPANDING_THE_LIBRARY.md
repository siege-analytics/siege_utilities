# Expanding the library

This guide is for contributors adding a new capability across one of
siege_utilities' harder seams: a new optional extra, a new DataFrame
engine backend, a new lazily-imported symbol, a new data or boundary
provider, or a new governed notebook. The basic "add a function, export
it, test it" flow is in [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#adding-new-functions);
this document covers the extension points where the library's invariants
are easy to break.

Read [ARCHITECTURE.md](ARCHITECTURE.md) first. The single invariant that
governs every extension is **imports go DOWN**: Foundation
(`core/`, `config/`, `files/`, `testing/`) depends on nothing else,
Ingestion (`data/`, `geo/`, `distributed/`, `databricks/`) depends only on
Foundation, and Analysis/output (`reporting/`, `survey/`, `analytics/`,
`hygiene/`) depends on both. If your new code would create an upward edge,
it belongs in a lower layer, or the lower layer grows the abstraction.

## Choosing where a capability goes

| If the capability ... | It belongs in ... |
|---|---|
| produces events that need space-time location | a domain package (`political/`, `economic/`, `education/`), located later through `geo/` |
| locates, buffers, interpolates, or crosswalks geometry | `geo/` |
| scales the same analysis to another compute backend | `engines/` (a new `DataFrameEngine` subclass) |
| reads from an external warehouse or API | `analytics/` (connector) or `data/` (loader), as an optional extra |
| renders a chart, map, slide, or report | `reporting/` |
| cleans or validates tabular input | `hygiene/` |

When two consumer modules share a helper, it lives in whichever consumer
owns the larger half of the surface, never pushed down into Foundation
just because it looks generic (that pulls heavy extras into a layer meant
to install on a bare Spark worker). See the upward-import trap in
[ARCHITECTURE.md](ARCHITECTURE.md#consumer-extras-and-the-upward-import-trap).

## Adding a new optional extra

Every heavy dependency surface is an optional extra so that
`pip install "siege-utilities[geo]"` stays lean. Adding one has three
synchronized parts; skipping any one produces a lying public surface.

1. **Declare the extra** in `pyproject.toml` under
   `[project.optional-dependencies]`. Use lower-bound pins (`>=`), not
   exact pins, and respect the version-support policy below (for example,
   anything pulling pandas must honor the `pandas>=2.0.0,<3.0` cap).

2. **Gate the imports** with the optional-import pattern (next section) so
   importing the package without the extra does not crash at module load.

3. **Keep the introspection contract honest.** `get_package_info()` must
   report a symbol with missing extras under `unavailable_functions` and
   `optional_dependency_symbols` (with `required_dependencies`,
   `missing_dependencies`, `module`, `attribute`, `category`), and must not
   count a dependency-wrapper stub as an available function. Verify with:

   ```bash
   python -c "import siege_utilities as su; import json; print(json.dumps(su.get_package_info(), indent=2, default=str))"
   ```

The `[all]` extra is end-user convenience. No internal module may assume
`[all]` is installed.

## Adding a lazily-imported symbol

The dependency tree is large, so top-level packages defer heavy submodules
through PEP 562 `__getattr__`. The contract (ADR 0005):

```python
# siege_utilities/some_package/__init__.py
def __getattr__(name: str):
    if name == "heavy_module":
        from . import heavy_module
        return heavy_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

Rules that keep lazy loading honest:

- **Never catch `ImportError` and return a stub, print, or `None`** (SU-1).
  Lazy loading defers *when* a missing dependency surfaces, not *whether*.
  Let the error propagate with a message naming the install extra.
- **`import pkg.sub as x` binds a function, not a module**, under PEP 562
  `__getattr__`. In tests and tools that need the actual submodule, use
  `importlib.import_module("pkg.sub")`.
- **Shadow-audit before adding a public symbol** on a shared import path.
  If more than one installation of the package can sit on the same
  `sys.path`, confirm which copy the runtime resolves
  (`python -c "import pkg.mod as m; print(m.__file__)"`) so a new symbol is
  not silently shadowed by a sibling copy.
- **Keep the lazy registry in sync** with the real module layout; a stale
  entry that points at a renamed or removed module is a broken public API,
  and the registry is checked in CI.

## Adding a DataFrame engine backend

`engines/` gives the same analysis at four scales (pandas, DuckDB, Spark,
PostGIS) behind one `DataFrameEngine` interface. A new backend subclasses
`DataFrameEngine` and implements the same contract. The contract below was
hardened across an extended cross-model review of the DuckDB backend; a new
engine that violates any clause will fail the same way the DuckDB backend
did before it was fixed.

**Result materialization**

- `query()` returns an **eager, materialized** frame. The result must
  survive the producing engine going out of scope and must not change when
  the source is mutated afterward (stable snapshot and lifetime). Returning
  a lazy relation leaks connection ownership and loses snapshot semantics.
- Apply geometry conversion by **column position**, not by name, so a
  result with duplicate column names keeps each column's distinct value.
- Convert native geometry to WKB for **every result-producing statement**,
  including a DML `... RETURNING` clause, not only plain `SELECT`.

**Engine capability loading**

- Load an optional engine capability (for example a spatial extension) only
  when a result actually needs it. Ordinary non-spatial queries must run
  under a restricted configuration that cannot load that capability, and a
  failed capability load must not break later ordinary queries.

**Statements and identifiers**

- Preserve the affected-row count for `INSERT` / `UPDATE` / `DELETE`, and
  run each mutation exactly once (no retry that replays a prior statement).
- Quote identifiers by doubling embedded quotes (`a"b` becomes `"a""b"`).
- Extract statement and object names on the engine's own token boundaries,
  not Python's `\s` whitespace class, and compare stored names with a
  binary (case- and accent-exact) collation so session collation settings
  cannot conflate two distinct names.

**Conversion boundaries**

- `to_pandas()` returns the materialized frame with geometry already
  WKB-encoded and decodable; `to_geodataframe()` decodes it. Any internal
  consumer (`spatial_join`, `buffer`, `index_points`, aggregations) must
  keep working through that boundary.

Every clause above has an executable regression test under
`tests/` (see the `test_round*_class_hardening.py` and
`test_final_hardening_consensus.py` suites, plus the per-round evidence in
[docs/testing/](testing/)). A new engine should add parallel tests that are
red-on-revert: each test must fail against an implementation missing the
clause and pass against the correct one.

## Adding geospatial transforms: crosswalk and areal rules

Geometry-aware aggregation has its own invariants, also hardened under
review:

- **Intensive variables** (rates, densities, per-capita values) area-weight
  by **true overlap area**: use an `overlap_area` column when present, else
  reconstruct it as `source_area * area_weight`. Weighting by whole-source
  area ignores partial overlap and produces a wrong mean. A merge the
  crosswalk cannot express (only an allocation factor, no absolute area)
  raises rather than returning a wrong number; `LongitudinalAligner` then
  falls back to real areal interpolation.
- **Missing values** are excluded per variable from both the numerator and
  the denominator, so `[0.2, NaN]` yields `0.2`, not `0.1`.
- **Zero-overlap sources contribute nothing** and must not trigger a false
  merge rejection.
- **A target with no valid contributing source stays undefined (NaN)**,
  never fabricated to `0.0`, even when a disjoint source exists.
- **Extensive variables** (counts, totals) are allocated, not
  subset-normalized; keep them distinct from the intensive path.

## Adding a data or boundary provider

Providers locate or enrich events. The geo center means every domain entity
eventually needs a GEOID and a boundary, so a provider encodes
*where-when*, not just *where*:

- Pin the vintage. Geography, districts, and census variables all have an
  implicit year; a join without a pinned vintage is a latent bug (see the
  data-trust rules).
- Default to OSGeo (GDAL/OGR, PROJ, Shapely). Where the target cannot run C
  libraries (Databricks, Lambda), provide a Sedona / DuckDB-spatial /
  pure-Python path and document the constraint.
- For an external endpoint, validate the base URL against the real host
  (not a substring), decode percent-encoded path components before
  validating structure, and fail loud on an unexpected shape rather than
  building a malformed request.

## Adding a governed notebook

Notebooks demonstrate intent and must reflect current behavior (SU-4a). A
new notebook is held to library standard (SU-3, no demo exemptions):

- Show the real API, including at least one error-path cell for a new
  public surface.
- No committed output that encodes stale results; the notebook-output
  policy test enforces this.

```bash
python -m pytest -q --no-cov tests/test_notebooks_output_policy.py
```

When a library function's contract changes, check whether any notebook
calls it and update the notebook or file a follow-up (SU-4a).

## Version-support policy

| Runtime | Status |
|---|---|
| Python 3.11 - 3.13 | Supported; blocking CI gate |
| Python 3.14 | Tested as a non-blocking matrix entry while its native stack stabilizes |
| pandas | `>=2.0.0,<3.0` across every extra that declares pandas |

The pandas cap exists because pandas 3.0 makes the default string dtype
Arrow-backed, so `.str` operations dispatch into `pyarrow.compute` and
segfault on 3.13 with the current native stack. Lift the cap only once
pandas 3.x plus pyarrow string interop is verified green across the CI
matrix; update every extra that pins pandas in the same change, and record
it in the changelog.

When you drop or raise a supported runtime, update `requires-python` and
the affected dependency bounds in `pyproject.toml` in the same commit, and
note it under the changelog's version-support entry.

## Expansion checklist

- [ ] New code respects the layer invariant (imports go DOWN); no upward edge.
- [ ] Heavy dependencies are an optional extra with `>=` bounds honoring the version policy.
- [ ] Optional imports are gated; `ImportError` propagates with an install hint (SU-1).
- [ ] `get_package_info()` reports the new surface honestly; lazy registry is in sync.
- [ ] A new engine honors the full `DataFrameEngine` contract with red-on-revert tests.
- [ ] Geospatial aggregation honors the intensive/extensive and NaN/overlap rules.
- [ ] A provider pins vintage and documents any non-OSGeo fallback.
- [ ] A new notebook shows the real API with an error-path cell and passes the output policy.
- [ ] Tests cover normal and error paths; every `except`/`raise` is exercised (SU-4b).
- [ ] CHANGELOG updated; PR targets `develop`.

See also: [ARCHITECTURE.md](ARCHITECTURE.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [NOTEBOOKS.md](NOTEBOOKS.md) · [adr/](adr/)
