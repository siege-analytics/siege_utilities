# Contributing to Siege Utilities

## Quick Start (Fork → Clone → Install → Test)

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/<your-user>/siege_utilities.git
cd siege_utilities
git remote add upstream https://github.com/siege-analytics/siege_utilities.git
```

### 2. Set Up Your Python Environment

Siege Utilities requires **Python 3.11+**. We recommend using `pyenv` to manage Python versions.

```bash
# Install Python 3.11 (if not already installed)
pyenv install 3.11.11

# Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Verify
python --version  # Should show 3.11.x
```

### 3. Install the Package Locally

```bash
# Core + dev tools (minimal — enough to run tests)
pip install -e ".[dev]"

# Full install (all extras — geo, analytics, reporting, etc.)
pip install -e ".[all,dev]"

# Geospatial work (requires system GDAL libraries)
# macOS: brew install gdal
# Ubuntu: sudo apt-get install gdal-bin libgdal-dev libgeos-dev libproj-dev
pip install -e ".[geo,dev]"
```

The `-e` flag installs in **editable mode** — your code changes take effect immediately without reinstalling.

### 4. Run the Tests

```bash
# Full test suite
python -m pytest tests/ -v

# Quick smoke test (no network, no GDAL)
python -m pytest tests/ -m smoke -v --no-cov

# Core-only tests (no heavy dependencies)
python -m pytest tests/test_backward_compat.py tests/test_pydantic_v1_compat.py tests/test_sql_safety.py -v --no-cov

# By marker
python -m pytest tests/ -m core          # Core modules only
python -m pytest tests/ -m geo           # Geospatial tests
python -m pytest tests/ -m "not requires_gdal"  # Skip GDAL-dependent tests

# With coverage
python -m pytest tests/ -v --cov=siege_utilities --cov-report=term-missing
```

### 5. Using UV (Alternative)

If you prefer [UV](https://docs.astral.sh/uv/) for faster dependency resolution:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --extra all --extra dev
uv run pytest tests/ -v
```

## Development Workflow

### Branch Strategy (Gitflow)

We use **gitflow**: `develop` is the integration branch, `main` is release-only.

```bash
# Start from develop
git checkout develop
git pull upstream develop

# Create your feature branch
git checkout -b feature/my-change

# ... make changes, commit ...

# Push to your fork
git push origin feature/my-change
```

### Pre-PR Validation

Run these before opening a pull request:

```bash
# 1. Tests pass
python -m pytest tests/ -v --no-cov

# 2. Test file hygiene (naming/location conventions)
python scripts/check_test_file_hygiene.py

# 3. Lint — phase 1 (runtime-safety errors)
flake8 siege_utilities --count --select=E9,F63,F7,F82 --show-source --statistics

# 4. Lint — phases 2-4 (hygiene + module ratchet + full-repo fingerprint)
#    This is what CI's "lint ratchet phases2-4" job runs. Skipping it is the
#    most common reason a PR passes locally but fails CI lint.
python scripts/check_lint_ratchet.py --phase all

# 4. API contract check (if you changed public API)
python -m venv /tmp/.venv_baseline
/tmp/.venv_baseline/bin/pip install siege-utilities==3.8.0
/tmp/.venv_baseline/bin/python scripts/contracts/generate_public_api_contract.py \
  --output /tmp/contract_baseline.json

python scripts/contracts/generate_public_api_contract.py \
  --output /tmp/contract_candidate.json

# Infer the impact level automatically
IMPACT=$(python scripts/release_manager.py --infer-impact --baseline-version 3.8.0)
python scripts/contracts/compare_public_api_contracts.py \
  --baseline /tmp/contract_baseline.json \
  --candidate /tmp/contract_candidate.json \
  --release-impact "$IMPACT" \
  --allowlist scripts/contracts/contract_allowlist.json
```

### Notebooks

Notebooks in `notebooks/` demonstrate real-world usage. If your change affects user-facing workflows or APIs, update the impacted notebooks.

```bash
# Validate notebook output policy
python -m pytest -q --no-cov tests/test_notebooks_output_policy.py

# Run a specific notebook headlessly (requires papermill)
pip install papermill
papermill notebooks/01_Getting_Started.ipynb /tmp/nb01_output.ipynb --execution-timeout 300
```

## CI Pipeline

Every push and PR triggers the full CI pipeline (`.github/workflows/ci.yml`):

| Job | What it checks |
|-----|----------------|
| **test** | Full test suite on Python 3.11, 3.12, 3.13 |
| **test-core** | Core-only install (no heavy deps) |
| **test-geo-no-gdal** | Geospatial tests without GDAL system libraries |
| **test-smoke** | Fast validation tests (no network, no GDAL) |
| **test-pydantic-v1** | Backward compatibility with Pydantic v1 |
| **test-databricks** | Databricks SDK integration |
| **battle-test** | Comprehensive overnight suite (30min timeout) |
| **api-contract-regression** | Public API compatibility vs. baseline |
| **lint-ratchet** | Lint quality gate (violations can only go down) |
| **test-file-hygiene** | Test naming and location conventions |
| **security** | pip-audit + bandit vulnerability scan |
| **build** | Package build + twine validation |

The **build** job gates on `test`, `battle-test`, and `api-contract-regression`. The **release** job (PyPI upload) runs only on GitHub release events.

### API Contract Policy

The contract regression check enforces semver compatibility:

- **Patch** releases: no new symbols, no signature changes, no removals
- **Minor** releases: new symbols OK, no signature changes or removals (unless allowlisted)
- **Major** releases: anything goes (removals require allowlist entry)

The impact level is **inferred automatically** from the version delta between the baseline and the candidate. If your PR adds public API symbols, classify it as `minor` and update `scripts/contracts/contract_allowlist.json` in the same PR.

### Lint Ratchet

The lint ratchet is a one-way quality gate — the total violation count can only go **down**, never up. If you touch a file, clean up any existing lint violations in that file before submitting.

See [docs/policies/LINT_POLICY.md](docs/policies/LINT_POLICY.md) for root-cause analysis of common CI lint failures, baseline update procedures, and the full rule reference.

## Pull Request Guidelines

1. Branch from `develop`, not `main`
2. Include tests for new functionality
3. Run the pre-PR validation commands above
4. Keep PRs focused — one logical change per PR
5. Update notebooks and documentation if you changed user-facing behavior
6. If you add public API symbols, update the contract allowlist

## Project Structure

```
siege_utilities/
├── config/              # Census registry, Hydra/Pydantic configs, client management
├── geo/                 # Census API, GEOID utils, geocoding, spatial ops
│   ├── census_files/    # PL 94-171, TIGER/Line downloaders
│   └── django/          # GeoDjango models, services, management commands
├── distributed/         # Spark, HDFS, Databricks utilities
├── reporting/           # PDF, PowerPoint, choropleth, GA reports
├── analytics/           # GA4, Google Workspace, Snowflake connectors
├── data/                # Data sources (Redistricting Data Hub, NLRB, etc.)
├── files/               # File operations, hashing, remote downloads
├── core/                # Logging, string utilities
├── testing/             # Test environment helpers
└── development/         # Architecture analysis, package management

scripts/
├── release_manager.py   # Release workflow (version bump, build, publish)
├── contracts/           # API contract generation and comparison
└── check_*.py           # Lint and hygiene validation scripts

tests/                   # 3058+ tests across all modules
notebooks/               # 20 Jupyter notebooks demonstrating features
docs/                    # Sphinx documentation + policy docs
```

## Policy Documents

- [`docs/policies/CODING_STYLE.md`](docs/policies/CODING_STYLE.md)
- [`docs/policies/PR_REVIEW_RUBRIC.md`](docs/policies/PR_REVIEW_RUBRIC.md)
- [`docs/policies/CHANGE_CLASSIFICATION_AND_RELEASE_POLICY.md`](docs/policies/CHANGE_CLASSIFICATION_AND_RELEASE_POLICY.md)
- [`docs/policies/CONTRIBUTOR_GOVERNANCE.md`](docs/policies/CONTRIBUTOR_GOVERNANCE.md)

## License

Dual license (AGPL-3.0-only OR commercial). See [LICENSE](LICENSE) for details. Attribution is required in both paths.
