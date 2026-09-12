# Self-review — PR #1217 CI baseline unblock

## Scope

This branch fixes three develop-baseline CI blockers that were preventing unrelated PRs from merging:

- #1216 — pydantic-v1 compatibility job fails during third-party pytest plugin startup
- #1218 — no-GDAL geo job imports Django GIS migrations in a supposedly static test
- #1219 — siege_geo models and migrations are out of sync

## Changes

### #1216

- Set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` only for the pydantic-v1 compatibility job.
- Clear pytest addopts with `-o addopts=` because pytest-cov is intentionally unavailable when plugin autoload is disabled.
- Kept `uv run --no-sync` so the forced pydantic 1.x downgrade is preserved.

### #1218

- Rewrote `tests/test_geo_migration_graph.py` to parse migration files with `ast` rather than importing Django migration modules.
- Preserved the duplicate `AddField` / `RemoveField` logic and support for `SeparateDatabaseAndState.state_operations`.

### #1219

- Restored explicit historical index names in models where the model shape matched existing migrations, avoiding needless `RenameIndex` churn.
- Generated `0012_bargainingunit_electionresult_nlrbcase_ulpcharge_and_more.py` for real model drift:
  - NLRB models and relationships
  - special-district/base-field changes
  - RedistrictingPlan `enacted_date` change and new temporal indexes
  - OtherSpecialDistrict index changed to include `function_code`

## Validation

- Workflow YAML parsed; pydantic job env/command assertions passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --no-sync pytest -o addopts= tests/test_pydantic_v1_compat.py -q` — 14 passed, 6 skipped.
- `python3 -m pytest -o addopts= tests/test_geo_migration_graph.py -q` — 1 passed.
- Subprocess import guard confirmed `test_geo_migration_graph.py` does not import `django`.
- AST parse passed for touched Python files and generated migration.
- With explicit local `GDAL_LIBRARY_PATH` and `GEOS_LIBRARY_PATH`: `django-admin makemigrations siege_geo --check --dry-run` — No changes detected.
- `git diff --check` — passed.

## CI observation

After the first #1217 version, `pydantic v1 compat` passed in CI. After adding #1218/#1219, the PR needs fresh CI to confirm all baseline blockers are green together.
