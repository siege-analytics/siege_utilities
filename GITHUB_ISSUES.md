# siege_utilities GitHub Issues

These issues should be created in `siege-analytics/siege_utilities` repository.

---

## Parent Issue

### [EPIC] siege_utilities Full Restoration and Testing

**Labels:** `enhancement`, `documentation`, `testing`

**Description:**

Complete restoration of siege_utilities library to production-ready state. This library provides core infrastructure for:

- **Spatial Data & Census** - TIGER/Line boundary downloads, state FIPS normalization
- **Geocoding** - Address to coordinate conversion using Nominatim
- **Reporting** - ReportLab PDF generation, PowerPoint slides
- **Charting** - Matplotlib/Folium visualizations, choropleths
- **Spark/Distributed** - 530 Spark utility functions
- **Configuration** - Client profiles, branding, credential management
- **Analytics Connectors** - Google Analytics, Facebook, Snowflake, data.world

**Current State:**
- 418 tests passing
- Core functionality verified working
- 8 demo notebooks created

**Remaining Work:**
See linked sub-issues below.

---

## Sub-Issues

### Issue 1: Verify and Document Analytics Connectors

**Labels:** `enhancement`, `testing`, `analytics`

**Description:**

Test analytics connectors with real credentials to verify they work end-to-end.

**Connectors to Test:**
- [ ] `GoogleAnalyticsConnector` - GA4 API integration
- [ ] `FacebookBusinessConnector` - Facebook Marketing API
- [ ] `SnowflakeConnector` - Snowflake data warehouse
- [ ] `DatadotworldConnector` - data.world API

**Files:**
- `siege_utilities/analytics/google_analytics.py`
- `siege_utilities/analytics/facebook_business.py`
- `siege_utilities/analytics/snowflake_connector.py`
- `siege_utilities/analytics/datadotworld_connector.py`

**Acceptance Criteria:**
- [ ] Each connector tested with valid credentials
- [ ] Error handling verified for invalid credentials
- [ ] Documentation updated with working examples
- [ ] Notebook created demonstrating each connector

---

### Issue 2: Profile/Branding System End-to-End Testing

**Labels:** `enhancement`, `testing`, `config`

**Description:**

Verify the profile and branding system works correctly for multi-client workflows.

**Features to Test:**
- [ ] User profile creation and persistence
- [ ] Client profile creation with branding config
- [ ] Credential management (1Password, Keychain, env vars)
- [ ] Profile switching between clients
- [ ] Branding application to reports

**Files:**
- `siege_utilities/config/user_config.py`
- `siege_utilities/config/credential_manager.py`
- `siege_utilities/config/models/client_profile.py`
- `siege_utilities/reporting/client_branding.py`

**Acceptance Criteria:**
- [ ] Create user profile, save, reload - data intact
- [ ] Create client with branding, apply to report
- [ ] Switch between 2 clients, verify correct branding
- [ ] Update existing notebooks or create new one demonstrating workflow

---

### Issue 3: ReportLab PDF Generation with Charts and Tables

**Labels:** `enhancement`, `testing`, `reporting`

**Description:**

Verify ReportLab PDF generation works with the full feature set including charts, tables, and client branding.

**Features to Test:**
- [ ] BaseReportTemplate with custom branding
- [ ] Table generation with styling
- [ ] Chart embedding (matplotlib figures)
- [ ] Multi-page reports with sections
- [ ] Cover page with client logo
- [ ] Table of contents generation

**Files:**
- `siege_utilities/reporting/templates/base_template.py`
- `siege_utilities/reporting/templates/title_page_template.py`
- `siege_utilities/reporting/templates/content_page_template.py`
- `siege_utilities/reporting/report_generator.py`

**Acceptance Criteria:**
- [ ] Generate multi-page PDF with ToC, tables, and charts
- [ ] Apply client branding (colors, fonts, logo)
- [ ] Notebook 06 updated with full feature demonstration

---

### Issue 4: PowerPoint Generation Testing

**Labels:** `enhancement`, `testing`, `reporting`

**Description:**

Verify PowerPointGenerator creates valid PPTX files with charts and data.

**Features to Test:**
- [ ] Slide creation with title/content layouts
- [ ] Table insertion
- [ ] Chart/image insertion
- [ ] Branding application (colors, fonts)
- [ ] Multi-slide decks

**Files:**
- `siege_utilities/reporting/powerpoint_generator.py`

**Acceptance Criteria:**
- [ ] Generate PPTX that opens in PowerPoint/LibreOffice
- [ ] Tables render correctly
- [ ] Charts/images display properly
- [ ] Create notebook demonstrating PowerPoint generation

---

### Issue 5: Spark Utilities Verification

**Labels:** `enhancement`, `testing`, `distributed`

**Description:**

Verify the 530 Spark utility functions work correctly with PySpark.

**Areas to Test:**
- [ ] DataFrame creation and manipulation
- [ ] UDF registration
- [ ] Window functions
- [ ] Aggregations
- [ ] Delta Lake integration (if available)

**Files:**
- `siege_utilities/distributed/spark_utils.py`
- `siege_utilities/distributed/hdfs_operations.py`

**Acceptance Criteria:**
- [ ] Key Spark functions tested in Spark environment
- [ ] HDFS functions documented (may require Hadoop)
- [ ] Notebook created for Spark workflows

**Note:** This requires a Spark environment. Consider testing in Docker or on the cluster.

---

### Issue 6: Update Wiki Documentation

**Labels:** `documentation`

**Description:**

Update wiki recipes to match current API and create executable versions.

**Wiki Files to Review:**
- `wiki/Recipes/Business-Intelligence-Site-Selection.md`
- `wiki/Recipes/Demographic-Analysis-Pipeline.md`
- `wiki/Recipes/Real-Estate-Market-Intelligence.md`
- `wiki/Recipes/Advanced-Census-Workflows.md`
- `wiki/Recipes/Census-Data-Intelligence-Guide.md`

**Acceptance Criteria:**
- [ ] Each recipe reviewed for API accuracy
- [ ] Deprecated function calls updated
- [ ] Executable notebook created for each recipe
- [ ] Cross-reference with demo notebooks 04-08

---

### Issue 7: CI/CD Pipeline Fixes

**Labels:** `ci/cd`, `bug`

**Description:**

Fix GitHub Actions CI/CD pipeline to pass on all supported Python versions.

**Current Issues:**
- Coverage threshold at 60% (may need adjustment)
- Some tests may be flaky due to network calls

**Tasks:**
- [ ] Review GitHub Actions workflow
- [ ] Fix any remaining test failures
- [ ] Ensure coverage reporting works
- [ ] Add caching for dependencies

**Files:**
- `.github/workflows/ci.yml`
- `pytest.ini`

**Acceptance Criteria:**
- [ ] CI passes on Python 3.10, 3.11, 3.12
- [ ] Coverage report generated
- [ ] Badge shows passing status

---

## pure-translation Integration Issues

These should be created in the pure-translation GitLab repo and link back to siege_utilities issues.

### pure-translation Issue: Census/TIGER Integration

**Description:**

Integrate siege_utilities Census data retrieval into pure-translation's geographic enrichment pipeline.

**Dependencies:**
- siege-analytics/siege_utilities#[Issue 1 number]

**Tasks:**
- [ ] Add siege_utilities to pure-translation dependencies
- [ ] Create enrichment command in `fec enrich` CLI
- [ ] Implement address-to-district lookup using Census boundaries
- [ ] Add VTD/Congressional district assignment to contributions

---

### pure-translation Issue: Report Generation for FEC Data

**Description:**

Use siege_utilities reporting for FEC data exports and analysis reports.

**Dependencies:**
- siege-analytics/siege_utilities#[Issue 3 number]
- siege-analytics/siege_utilities#[Issue 4 number]

**Tasks:**
- [ ] Create FEC report templates
- [ ] Implement `fec report` CLI command
- [ ] Generate candidate/committee summary PDFs
- [ ] Create contribution analysis charts

---

## Commands to Create Issues

Once `gh` CLI is available, use these commands:

```bash
# Create parent issue
gh issue create --repo siege-analytics/siege_utilities \
  --title "[EPIC] siege_utilities Full Restoration and Testing" \
  --body-file /path/to/parent-body.md \
  --label "enhancement,documentation,testing"

# Create sub-issues and link
gh issue create --repo siege-analytics/siege_utilities \
  --title "Verify and Document Analytics Connectors" \
  --body-file /path/to/issue1-body.md \
  --label "enhancement,testing,analytics"

# Link issues using GitHub's sub-issue API (requires GraphQL)
```

---

*Generated by Claude Code on 2026-01-17*
