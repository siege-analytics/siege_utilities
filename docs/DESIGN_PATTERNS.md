# siege_utilities Design Patterns

**Goal:** name the recurring design patterns in siege_utilities so that human
contributors and coding agents can extend the library *in the grain of the
existing code* rather than inventing a parallel style.

**How to read this:** each pattern is stated as *Intent, Forces, Structure,
Minimal shape, Consequences, Extend it*. The "Extend it" line links to the
concrete how-to in [EXPANDING_THE_LIBRARY.md](EXPANDING_THE_LIBRARY.md); this
document explains the *why* those how-tos assume. Pair it with
[ARCHITECTURE.md](ARCHITECTURE.md) (the layer model) and
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) (setup and conventions).

**For agents:** every pattern below names the governing rules (`SU-1`,
`writing-code:*`, `writing-tests:*`) from the project rule bundle. These are not
advisory: a PR that violates them fails hostile review. Where a pattern has a
worked failure history it is cited, so you do not reintroduce a closed bug
class.

---

## 1. Layered monolith, imports go DOWN

**Intent.** Keep a single installable package navigable by forbidding upward
dependencies, so a reader can predict where any capability lives.

**Forces.** A monolith accretes cross-references until every module imports
every other and nothing can be understood in isolation. A hard directional
rule is cheaper to enforce than taste.

**Structure.** Three layers: Foundation (`core/`, `config/`, `files/`,
`testing/`, `exceptions.py`), Ingestion (`data/`, `geo/`, `distributed/`,
`databricks/`, `git/`), and Analysis plus output (`reporting/`, `survey/`,
`analytics/`, `admin/`, `hygiene/`). Imports only ever point from a higher layer
to a lower one. A utility that would create an upward edge belongs in a lower
layer.

**Consequences.** `core/` cannot import `reporting/`; shared helpers sink to the
lowest layer that needs them. The dependency diagram in ARCHITECTURE.md is the
authoritative map.

**Extend it.** [EXPANDING_THE_LIBRARY.md, "Choosing where a capability goes"](EXPANDING_THE_LIBRARY.md).

---

## 2. Deferred public surface, PEP 562 lazy loading

**Intent.** Expose a flat, discoverable public API from the top-level package
without paying the import cost (and optional-dependency cost) of every submodule
at `import siege_utilities`.

**Forces.** Geospatial and distributed submodules pull in heavy optional
dependencies such as GDAL, Spark, and DuckDB. Eagerly importing them makes a
trivial import slow and brittle in environments missing those extras.

**Structure.** A package `__init__.py` declares a `_LAZY_IMPORTS` registry
mapping public name to submodule path and implements module-level `__getattr__`
(PEP 562) to import on first access. `from pkg import symbol` works identically
whether the import is eager or lazy.

**Minimal shape.**
```python
# siege_utilities/some_package/__init__.py
_LAZY_IMPORTS = {"fetch_boundaries": ".boundaries", "GeocodeResult": ".geocode"}

def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib
        module = importlib.import_module(_LAZY_IMPORTS[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Consequences.** The registry is a second source of truth and must stay in sync
with the actual module paths; a stale entry is a broken public API. CI checks the
registry via `scripts/check_lazy_imports.py` (Scientific Python SPEC 6).

**Extend it.** [EXPANDING_THE_LIBRARY.md, "Adding a lazily-imported symbol"](EXPANDING_THE_LIBRARY.md).

---

## 3. Optional-dependency gating

**Intent.** Let a module reference a heavy optional dependency while still
importing cleanly when that dependency is absent, and fail with an actionable
message at the point of use rather than a bare `NameError`.

**Forces.** `import shapely` at module top crashes the whole module when shapely
is not installed, even for code paths that never touch shapely.

**Structure.** A `try/except ImportError` sets an availability flag; every call
site checks the flag first and raises a message naming the package and the
install command.

**Minimal shape.**
```python
try:
    import shapely
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

def build_polygon(coords):
    if not SHAPELY_AVAILABLE:
        raise RuntimeError("shapely required; install with: pip install 'siege_utilities[geo]'")
    return shapely.geometry.Polygon(coords)
```

**Consequences.** Every public call site of the gated symbol must check the flag
(`writing-code:8`). A bare `if not X_AVAILABLE: return None` is allowed only when
a no-op is the documented contract; otherwise it is an `SU-1` violation. Worked
failure: gazetteer geometry call sites once used `shapely.geometry.Polygon(...)`
without the guard and raised `NameError` instead of the intended `RuntimeError`.

**Extend it.** [EXPANDING_THE_LIBRARY.md, "Adding a new optional extra"](EXPANDING_THE_LIBRARY.md).

---

## 4. Errors are not data (SU-1)

**Intent.** Make failure impossible to mistake for an empty-but-valid result.

**Forces.** Returning `pd.DataFrame()`, `[]`, `{}`, `0.0`, or an undocumented
`None` on an error path lets a caller consume a failure as if it were "no data
found." The corruption surfaces far downstream, where it is expensive to trace.

**Structure.** On an error path a function does exactly one of: raise an
exception; return a *documented* sentinel the caller pattern-matches (an
`Optional[T]` whose docstring states that `None` means failure); or best-effort
cleanup in `finally`. Never a valid-shaped empty value standing in for an error.

**Minimal shape.**
```python
demographics = tract_lookup.get(tract_id)
if demographics is None:
    raise CensusAPIError(f"unknown tract_id={tract_id!r}")   # not: return {}
```

**Consequences.** A single function uses one failure-indication mechanism, and
sibling methods share it (`writing-code:13`). Every `except` block is exercised
by a test that forces it (`writing-tests:5`). The Summary File reader in
pattern 10 is a worked example: a corrupt record raises, it never returns a
misaligned or NaN row.

**Extend it.** [DEVELOPER_GUIDE.md, "Error handling rules"](DEVELOPER_GUIDE.md);
project rules `SU-1` and `SU-2`.

---

## 5. Engine-agnostic DataFrame, protocol plus backend dispatch

**Intent.** Write one analysis API that runs on pandas, DuckDB, Spark, or
PostGIS, choosing the backend by data scale and deployment without changing
caller code.

**Forces.** Binding analysis logic to one engine forces a rewrite when data
outgrows memory or moves to a cluster. Inlining `if engine == "spark"` branches
everywhere scatters the dispatch.

**Structure.** A backend-neutral operation surface (aggregations, joins, spatial
ops) dispatches to a per-engine implementation. The caller selects an engine;
the operation set is identical across engines, and the capability registry that
gates which operations are legal must match what each backend actually
implements.

**Consequences.** A capability the validator advertises must be implemented by
every backend it gates, or the validator lies and the caller hits a runtime
error after passing validation (`writing-code:10`). Aggregation-name support,
for instance, is validated against one registry; a backend missing a name must
either implement it or the registry must narrow.

**Extend it.** [EXPANDING_THE_LIBRARY.md, "Adding a DataFrame engine backend"](EXPANDING_THE_LIBRARY.md);
[docs/engines/](engines/).

---

## 6. Provider pattern, pluggable external sources

**Intent.** Add a new boundary or data source (Census TIGER, GADM, and others)
without touching the code that consumes boundaries.

**Forces.** Each upstream has its own URL scheme, vintage discovery, and
availability constraints; callers should not know which one served a request.

**Structure.** An abstract base (`BoundaryProvider`) declares `name`,
`is_available`, `list_levels`, and `get_boundary`; concrete providers implement
it; a manager or registry resolves a request to a provider. `is_available`
reflects whether the provider's optional dependency is installed (pattern 3).

**Consequences.** Providers return domain objects, not raw upstream payloads; the
boundary layer translates at the edge. A provider that cannot serve a request
raises rather than returning empty (`SU-1`).

**Extend it.** [EXPANDING_THE_LIBRARY.md, "Adding a data or boundary provider"](EXPANDING_THE_LIBRARY.md).

---

## 7. Catalog plus populator, searchable metadata over a provider

**Intent.** Let callers discover *what* is available (datasets, variables,
vintages) separately from *fetching* it.

**Forces.** Hard-coding dataset lists rots; querying upstream on every lookup is
slow and fragile.

**Structure.** A catalog holds searchable metadata with a cache backend; a
populator refreshes the catalog from the live source. Lookups hit the catalog;
the populator is the only component that talks upstream to rebuild it. A lookup
miss raises or returns a documented sentinel, it never fabricates an entry.

**Consequences.** The catalog and the thing it describes can drift; the populator
plus a freshness check is how drift is bounded. Catalog reads are the hot path
and must not silently return stale-as-fresh data without signalling.

**Extend it.** [MULTI_SOURCE_TABULATION_GUIDE.md](MULTI_SOURCE_TABULATION_GUIDE.md);
the census catalog and populator modules.

---

## 8. Spatial transform backend dispatch, crosswalk and areal

**Intent.** Offer one crosswalk and areal-interpolation API that reports which
backend actually ran, with correct missing-data semantics.

**Forces.** Areal interpolation of extensive versus intensive variables has
different correctness rules; a silent wrong default corrupts totals.

**Structure.** The transform selects a backend by input shape and CRS, performs
the operation, and returns a result object that names the backend used. Extensive
(count) and intensive (rate) variables are handled distinctly; a CRS mismatch
warns or raises rather than silently reprojecting.

**Consequences.** The result carries provenance (which backend ran). NaN after a
join is logged with the drop count, per the data-trust rules. Worked history: an
empty-areal short-circuit and extensive/intensive NaN handling were hardened in
#1373.

**Extend it.** [EXPANDING_THE_LIBRARY.md, "Adding geospatial transforms"](EXPANDING_THE_LIBRARY.md);
the data-trust rules.

---

## 9. Dual-source fallback with provenance

**Intent.** Serve the same tabular result from a primary source (the Census API)
and transparently fall back to a secondary (the bulk Summary File FTP service)
when the primary is rate-limited or degraded, and tell the caller which source
answered.

**Forces.** The API has rate limits and outages; the bulk files are always
available but slower and shaped differently. Callers need one result shape and an
honest record of how it was obtained.

**Structure.** A `CensusDataSource` protocol (`fetch(**request)` returns a
DataFrame and a `Provenance`); concrete `ApiSource` and `BulkFileSource`; an
`AlternationPolicy` describing which errors trigger fallback and how many
attempts each source gets; and a `DualSourceCensusClient` that tries the primary,
then the secondary, and returns the first success with a `Provenance(source,
url_or_path, attempts, degraded)` record. Every success returns the source's
unchanged frame plus provenance; if no source succeeds, the last error propagates
(`SU-1`, no empty-frame-on-failure).

**Minimal shape.**
```python
client = DualSourceCensusClient(
    ApiSource(api), BulkFileSource(cache_dir), AlternationPolicy(...)
)
frame, prov = client.fetch(variables=["B01003_001E"], year=2022,
                           dataset="acs5", geography="county", state_fips="06")
# prov.source is "api" or "bulk"; prov.degraded is True when fallback fired.
```

**Consequences.** The two sources must produce the same frame shape (GEOID, NAME,
estimate and MOE columns) so the fallback is invisible to callers; the bulk
source does the translation work to match the API shape. Provenance is not
optional decoration, it is how a caller detects it was served degraded data.
Added across #1374 (timeseries), #1375 (framework and API source), and #1385
(bulk Summary File source).

**Extend it.** Add a third source by implementing the `CensusDataSource` protocol
and inserting it into the client's alternation order; keep the output frame shape
identical.

---

## 10. Validate at the ingestion boundary

**Intent.** Treat every externally-sourced byte as hostile until proven
well-formed, so corruption raises at ingestion rather than surfacing as
misaligned or NaN analysis output.

**Forces.** Parsers are lenient by default: pandas' `usecols` silently drops
surplus fields, its python engine shifts columns on width drift, `to_numeric`
coerces garbage to NaN and accepts `inf`, quote characters absorb delimiters,
duplicate headers get silently renamed, and a leading BOM shifts the first
column. Each leniency is a silent-data (`SU-1`) hole.

**Structure.** Before trusting parsed data, validate the raw input against the
format's own contract: record width against the header, reject embedded control
bytes that the parser treats as boundaries, reject duplicate and BOM-masked
header names, disable quote handling when the format is unquoted, and parse
numerics strictly (`errors="raise"`) after masking only the *documented*
missing-value sentinels, rejecting non-finite tokens.

**Minimal shape (from the Summary File reader).**
```python
# width and control-byte validation against the file's own header
expected = header_body.removeprefix(b"\xef\xbb\xbf").count(b"|")
if b"\x00" in body or b"\r" in body: raise ValueError("embedded control character")
if body.count(b"|") != expected:     raise ValueError("record width mismatch")
# strict numeric parse: sentinels become NaN, everything else must be finite
parsed = pd.to_numeric(raw.where(~is_sentinel), errors="raise")
if (~is_sentinel & ~np.isfinite(parsed)).any(): raise ValueError("non-finite value")
```

**Consequences.** Validation must see the same record boundaries the parser does;
a naive line check diverges from pandas on `\r`, NUL, quotes, and BOM. This
pattern was hardened across five adversarial review rounds on #1385; every listed
leniency was a reproduced bypass before it was closed. Tie-in: the data-trust
rules (validate at boundaries, log join loss) and `writing-tests:5` (every reject
path has a red-on-revert test).

**Extend it.** When adding any file or API ingestion, write the boundary
validation first and give each reject path a test that fails if the guard is
removed.

---

## 11. Configuration, Hydra plus Pydantic

**Intent.** Compose runtime configuration (clients, connections, credentials)
from layered sources with typed validation.

**Structure.** Pydantic models define the typed shape and enforce invariants at
construction; Hydra composes config groups. Credentials resolve through a
provider (environment variable, then 1Password), never hard-coded.

**Extend it.** [HYDRA_PYDANTIC_CONFIGURATION.md](HYDRA_PYDANTIC_CONFIGURATION.md),
[CLIENT_AND_CONNECTION_CONFIG.md](CLIENT_AND_CONNECTION_CONFIG.md),
[DEVELOPER_GUIDE.md, "Credential management"](DEVELOPER_GUIDE.md).

---

## Pattern-to-rule map (for agents)

| Pattern | Primary rules |
|---|---|
| 2 Lazy loading | SPEC 6; lazy-registry CI check |
| 3 Optional-dependency gating | `writing-code:8` |
| 4 Errors are not data | `SU-1`, `SU-2`, `writing-code:7`/`:13`, `writing-tests:5` |
| 5 Engine-agnostic | `writing-code:10` (capability/impl parity) |
| 6 Provider, 7 Catalog | `SU-1` (no empty-on-miss), data-trust |
| 8 Spatial dispatch | data-trust rules, extensive/intensive correctness |
| 9 Dual-source | `SU-1` (last error propagates), provenance honesty |
| 10 Boundary validation | data-trust rules, `writing-tests:5`, `writing-code:15` |
| all | no AI attribution, tests mandatory (definition-of-done) |
