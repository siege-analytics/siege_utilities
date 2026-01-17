# Siege Utilities - Function Relationship Analysis

**Generated:** January 17, 2026
**Branch:** `dheerajchand/sketch/siege-utilities-restoration`

---

## Package Overview

| Metric | Value |
|--------|-------|
| Total Functions | ~835 across 25 modules |
| Overall Status | ~90% WORKING, ~10% BROKEN/DEGRADED |
| Tests Passing | 418 |

**Key Finding:** Core functionality is solid, but reporting/analytics modules are non-functional.

---

## Module Architecture

```
                      SIEGE_UTILITIES (835 functions)
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
      WORKING (90%)      DEGRADED (5%)      BROKEN (5%)
          │                   │                   │
    ┌─────┴─────┐        ┌────┴────┐        ┌─────┴─────┐
    │           │        │         │        │           │
  CORE       GEO      Census    User     Reporting  Analytics
  DATA      FILES    Discovery  Config   Charts     Connectors
  CONFIG  DISTRIBUTED           YAML     PowerPoint Facebook
  ADMIN      GIT                Parse    Choropleth Google
  TESTING                                Polling    Snowflake
```

---

## Working Modules (90% of codebase)

### Core Layer (9 functions)
| Function | Purpose | Status |
|----------|---------|--------|
| `log_debug()` | Debug logging | WORKING |
| `log_info()` | Info logging | WORKING |
| `log_warning()` | Warning logging | WORKING |
| `log_error()` | Error logging | WORKING |
| `log_critical()` | Critical logging | WORKING |

All logging uses singleton pattern, shared across modules.

### Geo/Spatial Layer (43 functions)

#### Census Data
| Function | Purpose | Status |
|----------|---------|--------|
| `get_available_years()` | Discover Census years | WORKING (with fallback) |
| `discover_boundary_types()` | Find boundary types for year | WORKING |
| `get_census_boundaries()` | Download Census boundaries | WORKING |
| `get_geographic_boundaries()` | Generic boundary fetch | WORKING |
| `download_data()` | Convenience wrapper | WORKING (fixed) |

#### State Lookups
| Function | Purpose | Status |
|----------|---------|--------|
| `get_state_by_abbreviation()` | CA → California | WORKING |
| `get_state_by_name()` | California → CA | WORKING |
| `normalize_state_identifier()` | Any format → FIPS | WORKING |
| `get_state_fips()` | Abbreviation → FIPS code | WORKING |

#### Geocoding
| Function | Purpose | Status |
|----------|---------|--------|
| `get_coordinates()` | Address → lat/lon | WORKING |
| `use_nominatim_geocoder()` | OSM geocoding | WORKING |
| `concatenate_addresses()` | Build address strings | WORKING |

### Data Layer (8 functions)
| Function | Purpose | Status |
|----------|---------|--------|
| `load_sample_data()` | Load bundled datasets | WORKING |
| `list_available_datasets()` | List sample datasets | WORKING |
| `generate_synthetic_population()` | Create fake population | WORKING (fixed O(n²) bug) |
| `generate_synthetic_businesses()` | Create fake businesses | WORKING |
| `generate_synthetic_housing()` | Create fake housing | WORKING |

### Config Layer (46 functions)

#### Database Configuration
| Function | Purpose | Status |
|----------|---------|--------|
| `create_database_config()` | Create DB config | WORKING |
| `save_database_config()` | Persist DB config | WORKING |
| `load_database_config()` | Load DB config | WORKING |

#### Client Profiles
| Function | Purpose | Status |
|----------|---------|--------|
| `create_client_profile()` | Create client profile | WORKING |
| `save_client_profile()` | Persist client profile | WORKING |
| `load_client_profile()` | Load client profile | WORKING |

#### Connection Management
| Function | Purpose | Status |
|----------|---------|--------|
| `create_connection_profile()` | Create connection | WORKING |
| `verify_connection_profile()` | Test connection | WORKING |

### File Utilities (23 functions)
| Function | Purpose | Status |
|----------|---------|--------|
| `file_exists()` | Check file existence | WORKING |
| `copy_file()` | Copy files | WORKING |
| `download_file()` | HTTP download | WORKING |
| `calculate_file_hash()` | SHA256 hash | WORKING |
| `get_file_type()` | Detect file type | WORKING |
| `create_unique_staging_directory()` | Temp directories | WORKING |

### Distributed Layer (530 functions!)
| Category | Count | Status |
|----------|-------|--------|
| Spark utilities | 519 | WORKING |
| HDFS operations | 11 | WORKING |

### Git Operations (15 functions)
| Function | Purpose | Status |
|----------|---------|--------|
| `analyze_branch()` | Branch analysis | WORKING |
| `create_feature_branch()` | Create branches | WORKING |
| `get_git_status()` | Status info | WORKING |

---

## Broken Modules (10% of codebase)

### Reporting Module - CRITICAL FAILURE

**Root Cause:** Cannot import chart generation functions

| Function | Error | Impact |
|----------|-------|--------|
| `create_bar_chart()` | ImportError | Non-functional |
| `create_line_chart()` | ImportError | Non-functional |
| `create_pie_chart()` | ImportError | Non-functional |
| `create_choropleth_map()` | Function missing | Non-functional |
| `ChartGenerator` | Error wrapper | Non-functional |
| `PowerPointGenerator` | Error wrapper | Non-functional |
| `AnalyticsReportGenerator` | Error wrapper | Non-functional |

**Fallback behavior:** All chart functions return error wrappers that raise ImportError when called.

### Analytics Module - COMPLETE FAILURE

**Root Cause:** Missing or broken connector implementations

| Connector | Error | Impact |
|-----------|-------|--------|
| `GoogleAnalyticsConnector` | ImportError | Non-functional |
| `FacebookBusinessConnector` | ImportError | Non-functional |
| `SnowflakeConnector` | ImportError | Non-functional |
| `DatadotworldConnector` | ImportError | Non-functional |

### Polling Analyzer - MODULE NOT FOUND

**Issue:** `reporting/polling_analyzer.py` referenced but doesn't exist

---

## Degraded Modules (Partial Functionality)

### Census Discovery
| Issue | Impact | Workaround |
|-------|--------|------------|
| 45-second timeout on Census.gov | Slow startup | Uses cached years 2010-present |

### User Config YAML Parsing
| Issue | Impact | Workaround |
|-------|--------|------------|
| Python tuple serialization fails | Config not loaded | Uses defaults |

**Error:** `could not determine constructor for tag:yaml.org,2002:python/tuple`

---

## Critical Call Chains

### Census Data Path (WORKING)
```
get_census_boundaries('06', 'county')
  └─> normalize_state_identifier('06')
      └─> CensusDataSource.get_geographic_boundaries()
          ├─> CensusDirectoryDiscovery.get_optimal_year()
          │   └─> [TIMEOUT 45s] requests.get(census.gov)
          │       └─> fallback: cached years
          ├─> construct_download_url()
          ├─> download_file()
          └─> gpd.read_file() → GeoDataFrame
```

### Geocoding Path (WORKING)
```
get_coordinates('123 Main St, SF, CA')
  └─> use_nominatim_geocoder()
      ├─> Nominatim(user_agent='siege_utilities')
      ├─> rate_limit: sleep(1)
      └─> [NETWORK] geocoder.geocode()
          └─> {'lat': 37.7749, 'lon': -122.4194}
```

### Sample Data Path (WORKING - FIXED)
```
generate_synthetic_population(size=1000)
  └─> for ethnicity in demographics:
      └─> for _ in range(ethnic_count):
          └─> _generate_synthetic_person()
  └─> [OUTSIDE LOOP] add tract_info  # Fixed O(n²) bug
  └─> [OUTSIDE LOOP] add categories
  └─> pd.DataFrame(population_data)
```

### Broken Call Chains
```
create_bar_chart(data)
  └─> from .chart_generator import create_bar_chart
      └─> ImportError: cannot import 'create_choropleth_map'
          └─> RAISES ERROR

create_report_generator()
  └─> ImportError
      └─> RAISES ERROR
```

---

## Module Dependency Matrix

| Module | pandas | geopandas | requests | geopy | faker | pyspark |
|--------|:------:|:---------:|:--------:|:-----:|:-----:|:-------:|
| core/ | - | - | - | - | - | - |
| geo/ | Y | Y | Y | Y | - | - |
| data/ | Y | Y | - | - | Y | - |
| config/ | - | - | - | - | - | - |
| files/ | - | - | Y | - | - | - |
| distributed/ | Y | - | - | - | - | Y |
| reporting/ | Y | Y | - | - | - | - |

---

## Recommendations

### Priority 1: Critical Fixes
1. **Fix Reporting Module** - Implement missing `create_choropleth_map()` or remove dependency
2. **Fix User Config YAML** - Use JSON or clean YAML instead of Python object serialization

### Priority 2: Performance
3. **Optimize Census Discovery** - Reduce 45s timeout, implement async with caching
4. **Add connection pooling** - For repeated Census/geocoding requests

### Priority 3: Cleanup
5. **Remove broken analytics** - Either implement connectors or remove from exports
6. **Add polling_analyzer.py** - Or remove from imports

---

## Test Coverage Summary

| Module | Tests | Passing | Coverage |
|--------|-------|---------|----------|
| config/ | 57 | 57 | High |
| geo/ | 45 | 45 | High |
| core/ | 30 | 30 | High |
| files/ | 25 | 25 | High |
| data/ | 20 | 20 | Medium |
| distributed/ | 150+ | 150+ | Medium |
| reporting/ | 15 | 15 | Low (mocked) |
| analytics/ | 10 | 10 | Low (mocked) |

**Total: 418 passing, 1 skipped**

---

*Generated by Claude Code during siege_utilities restoration*
