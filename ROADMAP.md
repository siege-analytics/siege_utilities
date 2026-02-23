# Siege Utilities - Roadmap

**Last Updated:** January 21, 2026

---

## Completed Work

### Session 10 (January 21, 2026)
- [x] **Google Analytics Reporting** - Professional PDF reports with KPI cards, sparklines, traffic analysis
- [x] **Geographic Integration** - State choropleths, city heatmaps, Census demographic joins
- [x] **ReportGenerator Enhancements** - Support for matplotlib figures, PIL images, BytesIO data

### Session 9 (January 21, 2026)
- [x] **GeoDjango Integration** - Full Django models for Census boundaries
- [x] **Boundary Models** - State, County, Tract, BlockGroup, Block, Place, ZCTA, CongressionalDistrict
- [x] **Spatial Query Managers** - `containing_point()`, `intersecting()`, `for_state()`, `for_year()`
- [x] **Demographic Storage** - DemographicSnapshot, DemographicVariable, DemographicTimeSeries models
- [x] **Boundary Crosswalks** - BoundaryCrosswalk and CrosswalkDataset models
- [x] **Management Commands** - `populate_boundaries`, `populate_demographics`, `populate_crosswalks`
- [x] **DRF Serializers** - GeoJSON serializers for REST API integration

### Session 8 (January 20, 2026)
- [x] **Census API Client** - ACS 1-year, 5-year, Decennial survey fetching
- [x] **GEOID Utilities** - Normalization, construction, parsing, validation
- [x] **Predefined Variable Groups** - `total_population`, `demographics_basic`, `race_ethnicity`, `income`, `education`, `poverty`, `housing`
- [x] **Shape-Demographics Joining** - `get_census_data_with_geometry()` function

### Earlier Sessions
- [x] **Core Library Restoration** - 260+ functions across 12 categories
- [x] **Census Data Intelligence** - Dataset selection and relationship mapping
- [x] **Hydra + Pydantic Configuration** - Type-safe configuration management
- [x] **Profile/Branding System** - Multi-client support with credential management
- [x] **14 Demo Notebooks** - Comprehensive usage examples

---

## Priority 1: Census Longitudinal Analysis (Partial)

### Completed
- [x] **#13 Census API Demographic Data Fetching** - CensusAPIClient with caching
- [x] **#14 Shape and Demographics Joining** - GEOID utilities for joining

### Remaining
- [ ] **#15 Census Boundary Crosswalk Support** - 2010-2020 boundary changes
  - Models exist (BoundaryCrosswalk, CrosswalkDataset)
  - Need service layer to load NHGIS/Census crosswalk files
  - Need interpolation functions for time-series analysis

- [ ] **#16 Time-Series Analysis and Trends** - Multi-year analysis functions
  - Build on crosswalk support
  - Tract-level change detection
  - Demographic trend visualization

---

## Priority 2: E2E Testing and Documentation

### Issue #29-#36: E2E Testing Epic
- [ ] **#29** End-to-end Census data pipeline test
- [ ] **#30** End-to-end reporting pipeline test
- [ ] **#31** End-to-end analytics connector test
- [ ] **#32** End-to-end GeoDjango integration test
- [ ] **#33** CI/CD pipeline improvements
- [ ] **#34** Coverage threshold adjustment (currently 60%)
- [ ] **#35** Network call mocking for flaky tests
- [ ] **#36** Documentation sync with current API

### Wiki Updates
- [ ] **#9 Wiki Documentation** - Sync recipes with current API
- [ ] Update `wiki/Recipes/` with GeoDjango examples
- [ ] Update `wiki/Recipes/` with GA reporting examples
- [ ] Create executable notebooks for each recipe

---

## Priority 3: Integration with pure-translation

- [ ] Add siege_utilities as dependency in pure-translation
- [ ] Create `fec enrich` CLI command for geographic enrichment
- [ ] Implement address-to-district lookup using Census boundaries
- [ ] Add VTD/Congressional district assignment to contributions
- [ ] Create FEC report templates using reporting module
- [ ] Implement `fec report` CLI command

---

## Priority 4: Analytics Connector Verification

- [ ] **#4 Analytics Connectors** - Test with real credentials
  - [ ] GoogleAnalyticsConnector (GA4 API)
  - [ ] FacebookBusinessConnector (Marketing API)
  - [ ] SnowflakeConnector
  - [ ] DatadotworldConnector

---

## Future Enhancements

### Geospatial
- [ ] Add OpenStreetMap boundary support
- [ ] Add international Census data support (UK, Canada)
- [ ] Add real-time geocoding rate limiting

### Reporting
- [ ] Add Word document generation (python-docx)
- [ ] Add HTML report templates
- [ ] Add email report distribution

### Performance
- [ ] Add DuckDB as local query engine option
- [ ] Add Polars DataFrame support
- [ ] Optimize large boundary file loading

---

## Technical Debt

- [ ] Remove deprecated `wiki_fresh/` and `wiki_debug/` directories
- [ ] Consolidate SESSION_*.md files into changelog
- [ ] Add type stubs for better IDE support
- [ ] Improve error messages for missing dependencies

---

## Notes for Next Session

1. Consider implementing **#15 Census Boundary Crosswalk Support** next
   - Load NHGIS crosswalk CSV files
   - Implement interpolation for changed tract boundaries

2. Or implement **#16 Time-Series Analysis** if crosswalks not needed immediately
   - Simple year-over-year comparison
   - Trend visualization functions

3. Check if user wants to run integration tests with Census API key

4. The GeoDjango module requires PostGIS database - verify deployment setup
