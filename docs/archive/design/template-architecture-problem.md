# The Template Architecture Problem: SW, GST, and Enterprise

**Date**: 2026-02-24
**Status**: Discussion Draft
**Participants**: Dheeraj Chand
**Epics**: 13 (SW/DSTK Foundation), en#166 (SW template rewrite)
**Affects**: socialwarehouse, geodjango_simple_template, pure-translation (enterprise), siege_utilities

---

## 1. History and Motivation

### How We Got Here

The current architecture is the result of three projects that were each created to solve a different problem at a different time. They grew organically and became entangled.

**geodjango_simple_template (GST)** came first. Dheeraj built it because spinning up GeoDjango projects is painful — the PostGIS plumbing, the spatial reference system configuration, the GDAL dependency management. GST is a **project template** (a `startproject` template or cookiecutter-style scaffold) that generates a working GeoDjango project with sensible defaults.

**socialwarehouse (SW)** came next. The concept: a **framework for building longitudinal data warehouses** about demographic, econometric, and electoral data. When SW needed a web application layer, Dheeraj reached for GST as a dependency — "I'll need a GeoDjango project, and I already have a template for that." So SW includes GST as a nested template. SW is itself a template — it generates project instances.

**siege_utilities (SU)** happened because Dheeraj had a `utilities/` folder he was copying between projects. It's a **library** (now on PyPI as `siege-utilities`) that provides shared functions: spatial data helpers, choropleth generators, string/file utilities, SQL safety, logging configuration.

**enterprise (pure-translation)** is an **instance** of the socialwarehouse template. It's the FEC campaign finance data pipeline — Hydra configs, Delta Lake, Django API. Enterprise is where the actual work happens.

### The Dependency Chain

```
siege_utilities (library)
    ^
    |  (pip install)
    |
geodjango_simple_template (project template)
    ^
    |  (nested template inclusion)
    |
socialwarehouse (framework template)
    ^
    |  (template instantiation)
    |
enterprise / pure-translation (instance)
```

### The Problems

**Problem A: Nested templates are fragile.**
SW includes GST as a sub-template. When GST changes, SW doesn't automatically pick up those changes. When SW is instantiated into enterprise, the GST layer is frozen at whatever version SW had when enterprise was created. There's no upgrade path — changes to GST have to be manually propagated through SW into enterprise.

**Problem B: Template vs library confusion.**
GST and SW are templates (generate code), but siege_utilities is a library (imported at runtime). When you need to share behavior, a library is maintainable (upgrade the dependency, all consumers benefit). A template is a one-shot copy — once instantiated, the generated code diverges from the template. This means bug fixes in the template don't reach existing instances.

**Problem C: Where does shared domain logic live?**
The PersonAddress model (linking persons to addresses with temporal metadata) exists in enterprise because that's where FEC data lives. But the concept of "an actor at an address over time" is universal to SW's mission. Should it be in:
- siege_utilities? (It's reusable domain logic)
- SW template? (It's specific to longitudinal warehouse instances)
- Enterprise? (It's only needed for FEC right now)

The user's insight: **solving A and B (flattening the template chain and converting to a library/generator model) will resolve C**, because the right ownership boundary will become obvious once the architecture is clean.

---

## 2. Current State of Each Project

### geodjango_simple_template (GST)
- **What it provides**: A working GeoDjango project scaffold with:
  - PostGIS-ready settings
  - GDAL/GEOS configuration
  - Basic geographic models (varies by version)
  - Docker and docker-compose setup
  - Test configuration
- **How it's used**: As a nested template inside SW
- **Problem**: Not independently installable as a library. Its value is in the initial scaffold, not ongoing runtime behavior.

### socialwarehouse (SW)
- **What it provides**: A framework template for longitudinal data warehouses:
  - Geographic data models (Census TIGER, GADM, intersections)
  - Data ingestion patterns for demographic/econometric sources
  - Django REST API scaffolding
  - ETL pipeline structure
- **How it's used**: Instantiated once to create enterprise
- **Problem**: After instantiation, it's dead code. Enterprise has diverged significantly. No way to pull SW improvements into an existing instance.

### siege_utilities (SU)
- **Current modules**: `geo.django.models`, `geo.schemas`, spatial helpers, choropleths, string/file ops, SQL safety, logging
- **Version**: 2.1.0 on PyPI
- **Design direction**: The user suspects "we can build a lot of the intelligence and orchestration into siege_utilities" — making it the runtime brain, not just a helper library.

### enterprise (pure-translation)
- **Status**: Active, production-bound FEC pipeline
- **Has diverged from SW template**: Extensively — Epic 12 alone rewrote config inheritance, semantic mappings, path resolution
- **Contains domain logic that could be shared**: PersonAddress, FEC-specific models, geographic intersections

---

## 3. The Generator Idea

The user proposed rethinking both GST and SW as **generators** rather than templates:

> "I think that we should design the generator, maybe, but it should inform the way we do the rest of the work."

### Template vs Generator vs Library

| Approach | When Code Runs | Upgrade Path | Shared Behavior |
|----------|---------------|--------------|-----------------|
| **Template** (current GST/SW) | At project creation only | None — manual copy | None — code is forked |
| **Library** (current SU) | At runtime | `pip install --upgrade` | Full — all consumers share |
| **Generator** (proposed) | At project creation AND on demand | Re-run generator for new components | Partial — generated code + library imports |

A generator combines the best of both:
1. **Scaffolding** (like a template): Creates project structure, settings, Docker configs
2. **Code generation** (beyond a template): Can add new models, views, API endpoints to an existing project
3. **Library dependency** (like SU): Generated code imports from siege_utilities at runtime

### What the Generator Would Do

```
siege-generate geodjango       # → Create a new GeoDjango project (replaces GST)
siege-generate warehouse       # → Add SW warehouse layer to an existing GeoDjango project
siege-generate census-models   # → Add Census TIGER geographic models
siege-generate gadm-models     # → Add GADM international boundary models
siege-generate fec-pipeline    # → Add FEC-specific models and parsers
siege-generate api             # → Add Django REST API for warehouse data
```

Each generator command:
- Inspects the existing project (reads `pyproject.toml`, Django settings)
- Generates code that imports from siege_utilities
- Is idempotent (can be re-run safely)
- Produces code that's customizable without forking

### What siege_utilities Would Provide

The "intelligence and orchestration" the user mentioned. SU becomes the runtime backbone:

| Module | Purpose | Used By |
|--------|---------|---------|
| `siege_utilities.geo.django.models` | TemporalBoundary, CensusTIGER, GADM, intersections | All generated projects |
| `siege_utilities.geo.schemas` | Pydantic schemas for boundary data | Validation layer |
| `siege_utilities.geo.loaders` | LayerMapping dicts, bulk import logic | ETL pipelines |
| `siege_utilities.warehouse.config` | Warehouse DB router, dual-database setup | Django settings |
| `siege_utilities.warehouse.dimensions` | Dimension table management (SCD Type 2) | Star schema maintenance |
| `siege_utilities.warehouse.facts` | Fact table base classes, partitioning logic | Data warehouse |
| `siege_utilities.etl.provenance` | Data lineage tracking (cf. en#162) | All pipelines |
| `siege_utilities.etl.quality` | Data quality checks, anomaly detection | Pipeline monitoring |
| `siege_utilities.templates` | Jinja2 templates for code generation | Generator CLI |

---

## 4. What Data Should SW Take In (and Why)

The user asked: "What data should the SW take in, and why?"

### Core Data Categories for a Longitudinal Demographic/Electoral Warehouse

**Tier 1: Geographic Boundaries (the skeleton)**
- Census TIGER (states, counties, tracts, block groups, blocks, CDs, SLDs, VTDs, places, ZCTAs)
- GADM (international administrative boundaries, levels 0-5)
- Special districts (NLRB regions, NCES school districts, federal judicial districts)
- Why: Everything else is attached to geography. You can't analyze anything without knowing where it is.

**Tier 2: Demographics (who lives there)**
- ACS 5-year estimates (population, income, education, housing, commuting)
- Decennial Census (PL 94-171 redistricting data, demographic profile)
- ACS 1-year estimates (larger geographies only)
- Why: The "about whom" of every analysis. Required for normalization (per-capita, per-household).

**Tier 3: Elections (what they decided)**
- FEC federal campaign finance (contributions, expenditures, committees, candidates, filings)
- State-level SOS data (voter files, election results, ballot measures)
- Why: Core mission of the SW — connecting money, people, and outcomes.

**Tier 4: Economic Indicators (what happened to them)**
- BLS employment/unemployment by county/MSA
- BEA GDP and personal income by state/county
- Census County Business Patterns (establishments by NAICS, employment, payroll)
- USDA ERS rural-urban classifications
- Why: Economic conditions drive electoral behavior. Required for regression models.

**Tier 5: Institutional Boundaries (who governs them)**
- NCES school districts (with performance data)
- NLRB regions (with case data — union elections, ULP filings)
- Federal judicial districts (with caseload data)
- Why: Governance structures that overlay geographic boundaries. Critical for policy analysis.

### The Star Schema Connection

The [warehouse-star-schema.md](./warehouse-star-schema.md) design doc separates the webapp database (Django models, boundary dimensions) from the analytical warehouse (fact tables, materialized views). The data categories above map to this:

- **Dimension tables** (webapp DB): Geographic boundaries (Tier 1)
- **Fact tables** (warehouse DB): Demographics (Tier 2), elections (Tier 3), economics (Tier 4), institutional data (Tier 5)
- **Materialized views**: Cross-boundary aggregations, temporal comparisons

### What This Means for the Generator

The generator doesn't need to know about ALL of this data. It needs to:
1. Set up the dual-database architecture (webapp + warehouse)
2. Generate the boundary dimension models (via siege_utilities)
3. Provide a pattern for adding fact tables (base class + partitioning)
4. Wire the ETL pipeline structure (Bronze → Silver → Gold)

The actual data sources (FEC, ACS, BLS, etc.) are instance-specific. Enterprise adds FEC. Another instance might add only ACS + BLS. The generator provides the framework; the library provides the shared logic; the instance provides the domain-specific configuration.

---

## 5. Open Questions

### Architecture Questions
1. **Should the generator be a CLI in siege_utilities, or a separate package?**
   - Pro SU: Single install, shared versioning
   - Pro separate: Keeps SU lightweight, generator is only needed once
   - Recommendation: CLI command in SU (`siege-utilities generate ...`)

2. **How do we handle enterprise's divergence from the SW template?**
   - Enterprise has significant FEC-specific code that can't be generated
   - The geographic models CAN be migrated to siege_utilities.geo.django
   - The warehouse architecture CAN be standardized
   - The FEC parsers/configs stay enterprise-specific

3. **What happens to GST as a standalone project?**
   - GST still has value as a simple "spin up GeoDjango" tool
   - But it becomes `siege-utilities generate geodjango` instead of a separate repo
   - The GST GitHub repo could become an archive pointing to siege_utilities

4. **Where does PersonAddress live?**
   - It's a through-table linking Person to Address with temporal metadata
   - The concept is universal (any longitudinal warehouse tracks actor addresses)
   - The FEC-specific fields (filing_count, contribution_count, total_amount) are NOT universal
   - **Possible split**: Base `TemporalAssociation` in SU, FEC-specific subclass in enterprise

### Data Questions
5. **How many database vintages do we support simultaneously?**
   - Census TIGER data changes every year. Do we keep all vintages loaded, or just current + decennial?
   - Affects storage costs and query complexity

6. **How do we handle cross-vintage comparisons?**
   - Tracts change boundaries between decennials
   - The intersection model (area-weighted overlap) handles this, but it's expensive to compute
   - Pre-compute or compute on demand?

7. **What's the MVP data scope for a non-FEC SW instance?**
   - Minimum: Census TIGER boundaries + ACS demographics
   - That alone enables per-capita analysis at tract level
   - Everything else is additive

---

## 6. Proposed Sequence

Based on the Epic schedule and the user's prioritization:

1. **Migrate geographic models to siege_utilities** (Epic 13, Phase 4)
   - Move TemporalBoundary, CensusTIGER, GADM from enterprise to SU
   - Enterprise becomes a consumer of SU geo models
   - This is the "flattening" that resolves the nested template problem for geo

2. **Design the warehouse base classes** (Epic 13, Phase 4-5)
   - Dual-database router
   - Fact table base class with temporal partitioning
   - Dimension management (SCD Type 2)

3. **Build the generator CLI** (Phase 5-6)
   - `siege-utilities generate geodjango`
   - `siege-utilities generate warehouse`
   - `siege-utilities generate census-models`
   - These inform the rest of the work by forcing clean interfaces

4. **Retire GST and SW as separate templates** (Phase 6)
   - GST → archive, redirect to SU generator
   - SW → archive, redirect to SU generator + SU library
   - Enterprise stands alone with SU as its foundation library

---

## 7. Related Design Documents

- [unified-geo-model-schema.md](./unified-geo-model-schema.md) — Concentric circles model for geographic boundaries
- [warehouse-star-schema.md](./warehouse-star-schema.md) — Star schema separating webapp and warehouse databases
- [MASTER_PLAN.md](https://github.com/electinfo/enterprise/blob/main/docs/MASTER_PLAN.md) — Overall project roadmap with epic schedule
