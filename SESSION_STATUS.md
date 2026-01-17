# Siege Utilities - Session Status

**Last Updated:** January 17, 2026
**Branch:** `dheerajchand/sketch/siege-utilities-restoration`

---

## Library Purpose

Siege Utilities is a **data science and engineering utility library** designed to streamline analytical product creation (tables, reports, maps) for a consulting workflow where you switch between multiple clients.

### Core Use Case

An analyst working with multiple clients needs to:
1. Pull data from various sources (Census, Google Analytics, Facebook, databases)
2. Generate analytical products (choropleths, tables, reports)
3. Apply client-specific branding (colors, fonts, logos)
4. Switch seamlessly between clients

### Selling Points
- **Spatial data and maps** - Census boundaries, geocoding
- **Choropleth maps** - Standard and bivariate choropleths
- **Multi-client workflow** - Profile switching with branding

---

## Architecture Understanding

### Profile Hierarchy

```
USER PROFILE (Dheeraj)
├── user_credentials:
│   ├── FEC_API_KEY          ← Public APIs used for all clients
│   ├── CENSUS_API_KEY
│   └── NOMINATIM_API_KEY
│
└── clients:
    │
    ├── CLIENT A (Hillcrest)
    │   ├── branding: {colors, fonts, logo}
    │   ├── credentials:
    │   │   ├── GA_SERVICE_ACCOUNT    ← Client A's Google Analytics
    │   │   ├── FB_ACCESS_TOKEN       ← Client A's Facebook
    │   │   └── SNOWFLAKE_CONN        ← Client A's data warehouse
    │   └── db_connections: [postgres://clienta_db]
    │
    └── CLIENT B (Acme Corp)
        ├── branding: {colors, fonts, logo}
        ├── credentials:
        │   ├── GA_SERVICE_ACCOUNT    ← Client B's Google Analytics
        │   └── FB_ACCESS_TOKEN
        └── db_connections: [postgres://clientb_db]
```

### Credential Management

**CredentialManager** with fallback hierarchy:
1. Local files (credentials/*.json)
2. Environment variables
3. 1Password CLI (`op` command)
4. Apple Keychain (`security` command - macOS)
5. Interactive prompts (fallback)

Key integrations:
- `get_google_service_account_from_1password()` - GA service accounts
- `store_ga_credentials_from_file()` - Import OAuth JSON
- Apple Keychain support for macOS users

### Reporting System (ReportLab PDFs)

**Polling Report Template:**
```
┌─────────────────────────────────────┐
│         COVER SHEET                 │  ← Client branding
├─────────────────────────────────────┤
│      TABLE OF CONTENTS              │
├─────────────────────────────────────┤
│         SECTION 1                   │
│  ┌─────────────┬─────────────┐     │
│  │   TABLE     │    CHART    │     │  ← Always paired
│  │  (shaded,   │             │     │
│  │   totals,   │             │     │
│  │   %)        │             │     │
│  └─────────────┴─────────────┘     │
├─────────────────────────────────────┤
│         APPENDICES                  │
└─────────────────────────────────────┘
```

**Rules:**
1. Every table has an accompanying chart (always pairs)
2. Shaded tables when necessary
3. Total rows, percent columns as appropriate

### Module Architecture

```
                      SIEGE_UTILITIES (835 functions)
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
       CORE                 GEO                DISTRIBUTED
    (logging,            (census,              (spark,
    strings)            geocoding,              hdfs)
          │              spatial)                  │
          │                   │                    │
          └─────────┬─────────┴────────────────────┘
                    │
              ┌─────┴─────┐
              │           │
           CONFIG       DATA
        (profiles,    (synthetic,
        credentials,   samples)
         branding)        │
              │           │
              └─────┬─────┘
                    │
              ┌─────┴─────┐
              │           │
          REPORTING   ANALYTICS
         (charts,    (GA, FB,
          maps,      Snowflake,
         pptx)       data.world)
```

---

## Current State

### Test Results
- **418 tests passing**, 1 skipped
- **89 modules import successfully**

### What's Been Fixed (This Session)

1. **Import errors resolved:**
   - `create_choropleth_map()` - Added wrapper functions to chart_generator.py
   - `PollingAnalyzer` - Fixed import path (was `.reporting.polling_analyzer`, now `.reporting.analytics.polling_analyzer`)
   - Analytics connectors (GA, FB, Snowflake) - Now import correctly

2. **Code bugs fixed:**
   - O(n²) bug in `generate_synthetic_population()` - Moved nested loops outside
   - YAML tuple serialization - Convert tuples to lists before saving
   - `download_data()` wrapper - Now calls correct method
   - `get_optimal_year()` parameter order

3. **CI/CD modernization:**
   - Python 3.10+ minimum (was 3.8)
   - Replaced deprecated `safety` with `pip-audit`
   - Updated GitHub Actions to v4/v5

4. **Repository cleanup (28,396 lines removed):**
   - Removed `.idea/`, `dataspell_venv/` from tracking
   - Removed `purgatory/`, `overnight_results/`
   - Removed obsolete docs (INTERNAL_DOCUMENTATION.md, FUNCTION_STATUS_TRACKING.md, etc.)
   - Removed overnight testing scripts
   - Consolidated `examples/` into `notebooks/`
   - Updated `.gitignore`

### What's NOT Verified

**IMPORTANT:** Modules importing correctly does NOT mean they work correctly. A function can be syntactically correct but return wrong results. The following need end-to-end testing:

1. **Choropleth generation** - Does `create_choropleth_map()` actually produce a valid map?
2. **Bivariate choropleths** - Does the bivariate mapping work?
3. **Census data retrieval** - Does `get_census_boundaries()` return usable GeoDataFrames?
4. **Analytics connectors** - Do GA/FB connectors actually pull data with real credentials?
5. **Report generation** - Does ReportLab PDF generation work with table+chart pairs?
6. **Profile switching** - Does loading a client profile apply branding correctly?

---

## Remaining Tasks

### Immediate (This Session)

- [ ] Create notebook to test choropleth workflow end-to-end
- [ ] Verify spatial data functions actually work
- [ ] Test bivariate choropleth generation

### Short-term

- [ ] Review and update `wiki/` documentation
- [ ] Create notebooks matching wiki recipes:
  - Business-Intelligence-Site-Selection
  - Demographic-Analysis-Pipeline
  - Real-Estate-Market-Intelligence
  - Advanced-Census-Workflows
- [ ] Verify analytics connectors with real credentials
- [ ] Test ReportLab PDF generation

### Documentation Gap

**Wiki has recipes but no executable notebooks:**
- `wiki/Recipes/Business-Intelligence-Site-Selection.md`
- `wiki/Recipes/Demographic-Analysis-Pipeline.md`
- `wiki/Recipes/Real-Estate-Market-Intelligence.md`
- `wiki/Recipes/Advanced-Census-Workflows.md`

**Current notebooks only cover configuration:**
- `notebooks/01_Configuration_System_Demo.ipynb`
- `notebooks/02_Create_User_Client_Profiles.ipynb`
- `notebooks/03_Person_Actor_Architecture.ipynb`

Need notebooks that test the actual spatial/choropleth/reporting workflows.

---

## Key Files

### Configuration
- `siege_utilities/config/user_config.py` - User profile management
- `siege_utilities/config/credential_manager.py` - Credential retrieval (1Password, Keychain)
- `siege_utilities/config/models/person.py` - Person/Actor architecture
- `siege_utilities/config/models/credential.py` - Credential and OnePasswordCredential models

### Spatial/Geo
- `siege_utilities/geo/spatial_data.py` - Census boundaries, download functions
- `siege_utilities/geo/geocoding.py` - Address to coordinates
- `siege_utilities/geo/census_data_selector.py` - Census year/type selection

### Reporting
- `siege_utilities/reporting/chart_generator.py` - ChartGenerator class + wrapper functions
- `siege_utilities/reporting/analytics/polling_analyzer.py` - Cross-tabs, longitudinal analysis
- `siege_utilities/reporting/powerpoint_generator.py` - PPTX generation
- `siege_utilities/reporting/report_generator.py` - ReportLab PDF generation

### Analytics Connectors
- `siege_utilities/analytics/google_analytics.py` - GA connector
- `siege_utilities/analytics/facebook_business.py` - FB connector
- `siege_utilities/analytics/snowflake_connector.py` - Snowflake connector
- `siege_utilities/analytics/datadotworld_connector.py` - data.world connector

---

## Commits This Session

```
a2a3b80 - chore: Consolidate examples/ into notebooks/
376d9b2 - chore: Remove one-time development scripts
1e70fcf - chore: Remove overnight testing artifacts from scripts/
a5760f8 - chore: Repository cleanup and artifact removal
037f1db - fix: Add missing chart wrapper functions and fix import paths
fd29377 - docs: Add Session 3 progress and cleanup analysis
ed15fca - fix: Handle YAML serialization of tuples
0d92839 - fix: Update CI/CD for Python 3.10+, add function analysis
237b487 - fix: Fix critical code issues and CI/CD blockers
1dc2be1 - fix: Fix broken API calls and make census years dynamic
c496853 - fix: Rewrite config tests
```

---

## Next Session Startup

1. Read this file
2. Read `FUNCTION_ANALYSIS.md` for module details
3. Read `RESTORATION_PLAN.md` for full restoration context
4. Continue with: **Create notebook to test choropleth workflow end-to-end**
