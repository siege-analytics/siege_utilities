# Connector live-API credentials

Sprint B (issue #453) adds connector test coverage in two phases:

- **Phase 1 — mock unit tests.** No credentials required. Run on every CI build.
- **Phase 2 — live-API smoke tests.** Marked `@pytest.mark.requires_api_key`. Skipped by default. Run manually when you want to prove the real API contract still holds.

This document covers Phase 2 only.

## Strategy

Developer-local credentials in **`~/.siege-test-credentials.yaml`** (or the path in `SIEGE_TEST_CREDENTIALS`). The file is **not** read by CI; CI runs the mock path only. If/when external contributors land, we may layer GitHub Actions secrets + a gated `live-api` environment on top — see #453 for context.

The file is gitignored at the repo root; the test fixture skips when it's absent. **Never commit a credentials file**, even partially redacted.

## Schema

```yaml
snowflake:
  account: xy12345.us-east-1
  user: TESTUSER
  password: ...           # or use private_key_file
  warehouse: COMPUTE_WH
  database: TEST_DB
  schema: TEST_SCHEMA
  role: TEST_ROLE

facebook_business:
  access_token: ...
  app_id: ...
  app_secret: ...
  ad_account_id: act_...

datadotworld:
  api_token: ...
  dataset_owner: my-org
  dataset_id: test-dataset

google_analytics:
  property_id: "12345678"
  # Auth comes from a service-account JSON; set GOOGLE_APPLICATION_CREDENTIALS
  # or point at it explicitly:
  service_account_json: /path/to/sa.json

google_workspace:
  customer_id: C0123abcd
  admin_email: admin@example.com
  service_account_json: /path/to/sa.json

google_search:
  api_key: ...
  search_engine_id: ...

vista_social:
  api_token: ...
  account_id: ...

polling_analyzer:
  # No external credentials — polling_analyzer is data-only.
  # Listed here for completeness; tests will not consume this fixture.
```

## Running the live-API tests

```bash
# All connectors with creds available
pytest -m requires_api_key

# A specific connector
pytest -m requires_api_key tests/test_snowflake_connector.py

# Combined with the standard mock suite (full coverage):
pytest -m "not requires_api_key or requires_api_key"  # not how -m works; see note below
```

Note: `requires_api_key` is the **only** marker that disables the test by default. Standard `pytest` (no `-m`) skips it via the fixture's `pytest.skip()`, not via `-m "not requires_api_key"`. This means the test still appears in the report as `SKIPPED` with the reason "no credentials file at X" — which is the signal you want when you're trying to figure out why a connector isn't being exercised.

## Failure modes

- **Credentials file missing** → `SKIPPED` with the path it expected. Create the file.
- **Section missing** → the per-connector test sub-skips with which key is missing.
- **Credentials wrong / expired** → real API error from the connector. Fix the value and re-run.
- **Test passes locally but fails on someone else's machine** → schemas drift. Re-read this doc; if the schema has changed, update both this doc AND the relevant tests in the same commit.
