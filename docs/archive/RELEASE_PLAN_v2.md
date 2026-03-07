# Release Plan: siege_utilities v2.0.0

## Summary

v2.0.0 is the first major release since the siege_utilities restoration effort began in January 2026. It represents a ground-up rebuild of the package with:

- **Person/Actor architecture** — unified domain model for people across contexts
- **Geographic reconciliation** — canonical naming with alias resolution (20 levels)
- **Census API client** — with retry/fallback and boundary type catalog
- **GeoDjango integration** — spatial data processing and choropleth generation
- **OAuth2 credential wiring** — 1Password integration for secure API access
- **GA4 multi-client reporter** — Google Analytics 4 data fetching
- **17 Jupyter notebooks** — complete data science workflow suite
- **724 tests** — comprehensive coverage across unit, E2E, and pipeline tests
- **Release infrastructure** — consolidated release manager with PyPI support

See `CHANGELOG.md` for the complete list of additions, changes, fixes, deprecations, and removals.

## Pre-Release Checklist

### Notebook Verification (GUI machine required)

All notebooks must pass on a machine with GUI capabilities (DataSpell or Jupyter):

- [x] NB01 — Basic utilities
- [x] NB02 — Person/Actor models
- [x] NB03 — Credential manager
- [x] NB04 — Geographic data
- [x] NB05 — Choropleth generation
- [ ] NB06-NB13 — Remaining notebooks (expected to pass, no code changes needed)
- [ ] NB14 — GA4 Analytics Report (capstone, requires OAuth2 consent on first run)
- [ ] NB15-NB17 — Final notebooks

### Code Quality

- [ ] All 724 tests pass: `pytest tests/ -x -q`
- [ ] Version consistency: `python scripts/release_manager.py --check`
- [ ] Import verification: `python scripts/release_manager.py --verify`
- [ ] Flake8 clean: `flake8 siege_utilities --select=E9,F63,F7,F82`

### Branch Preparation

- [ ] All feature work merged to `develop` (or `dheerajchand/sketch/siege-utilities-restoration`)
- [ ] `CHANGELOG.md` finalized with release date
- [ ] Release branch created: `git checkout -b release/v2.0.0`

### Infrastructure

- [ ] Delete stale `v2.0.0` tag (see below)
- [ ] `PYPI_API_TOKEN` secret configured in GitHub repo settings
- [ ] TestPyPI dry-run succeeds

## Release Execution

### Step 1: Delete stale tag

```bash
git tag -d v2.0.0
git push origin :refs/tags/v2.0.0
```

### Step 2: Create release branch

```bash
git checkout develop
git pull origin develop
git checkout -b release/v2.0.0
```

### Step 3: Finalize changelog

Update the `[Unreleased]` header in `CHANGELOG.md`:

```markdown
## [2.0.0] - 2026-MM-DD
```

Commit the change:

```bash
git add CHANGELOG.md
git commit -m "chore: finalize changelog for v2.0.0"
```

### Step 4: Dry-run release

```bash
python scripts/release_manager.py --release \
    --bump-type major \
    --changelog \
    --dry-run
```

Verify all steps report success.

### Step 5: TestPyPI upload

```bash
python scripts/release_manager.py --release \
    --bump-type major \
    --changelog \
    --pypi \
    --repository testpypi \
    --skip-github
```

Verify the package appears on TestPyPI and installs correctly:

```bash
pip install --index-url https://test.pypi.org/simple/ siege-utilities==2.0.0
python -c "import siege_utilities; print(siege_utilities.__version__)"
```

### Step 6: Production release

```bash
python scripts/release_manager.py --release \
    --bump-type major \
    --changelog \
    --pypi
```

This will:
1. Bump version to 2.0.0
2. Build + validate
3. Upload to PyPI
4. Commit + tag `v2.0.0` + push
5. Create GitHub Release

### Step 7: Merge release branch

```bash
git checkout main
git merge release/v2.0.0
git push origin main

git checkout develop
git merge release/v2.0.0
git push origin develop

git branch -d release/v2.0.0
git push origin --delete release/v2.0.0
```

## Post-Release Verification

- [ ] `pip install siege-utilities==2.0.0` works from PyPI
- [ ] `python -c "import siege_utilities; print(siege_utilities.__version__)"` reports `2.0.0`
- [ ] GitHub Release page shows correct tag and notes
- [ ] CI `release` job ran successfully (triggered by the release event)
- [ ] `main` branch has the release commit and tag
- [ ] `develop` branch has the release merged back
- [ ] Update `docs/archive/SESSION_STATUS_2026.md` to reflect release completion
- [ ] Close Epic A #38 (merge restoration branch to main)

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Single `release_manager.py` script | Avoids confusion between two release tools; module-level functions match existing style |
| 4-file version scheme kept | Unusual but functional; changing it is a separate effort |
| No trusted publisher OIDC | Requires PyPI project setup; separate infrastructure ticket |
| `develop` branch as integration | Standard gitflow; prevents direct-to-main accidents |
| CHANGELOG.md over auto-generated notes | Human-curated notes are more useful for a data science library |
| Deprecation over deletion for `pypi_release.py` | Gives downstream callers migration time |

## Template for Future Releases

This document can serve as a template for future major releases. Copy it to `docs/RELEASE_PLAN_vN.md` and update the version-specific content.
