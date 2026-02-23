# Release Management

## Versioning Policy

siege_utilities follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **Major** (X.0.0) — breaking API changes
- **Minor** (0.X.0) — new features, backward-compatible
- **Patch** (0.0.X) — bug fixes only

Pre-release versions use the format `X.Y.Z-rc.N` (e.g., `2.0.0-rc.1`).

Version is tracked in **four** files, all kept in sync by `scripts/release_manager.py`:

| File | Location |
|------|----------|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `setup.py` | `version="X.Y.Z"` |
| `siege_utilities/__init__.py` | `__version__ = "X.Y.Z"` |
| `siege_utilities/__init__.py` | `'version': 'X.Y.Z'` in `get_package_info()` |

## Branch Naming Convention

| Pattern | Purpose | Base | Merges to |
|---------|---------|------|-----------|
| `main` | Stable releases only | — | — |
| `develop` | Integration branch | — | `main` (via release branch) |
| `dheerajchand/<name>` | Feature development (author-prefixed) | `develop` | `develop` |
| `feature/<name>` | Feature development (type-prefixed) | `develop` | `develop` |
| `release/vX.Y.Z` | Release stabilization | `develop` | `main` AND `develop` |
| `hotfix/vX.Y.Z` | Urgent production fixes | `main` | `main` AND `develop` |

**Rules:**
- All feature work branches from and merges back to `develop`
- Only release and hotfix branches touch `main`
- Branch names use lowercase, hyphens, no spaces
- The `dheerajchand/sketch/*` pattern is legacy; new branches use `dheerajchand/<name>`

## Release Workflow

### 1. Feature Development

```
develop ──── dheerajchand/my-feature ──── PR ──── develop
```

Features are developed on author-prefixed branches, tested via CI, and merged to `develop` via PR.

### 2. Release Stabilization

When `develop` is ready for release:

```bash
# Create release branch
git checkout develop
git pull origin develop
git checkout -b release/v2.0.0

# Stabilize: fix last-minute bugs, update CHANGELOG.md
# No new features — only fixes and documentation
```

### 3. Execute Release

```bash
# Full release with PyPI upload
python scripts/release_manager.py --release \
    --bump-type major \
    --changelog \
    --pypi \
    --repository pypi

# Or dry-run first
python scripts/release_manager.py --release \
    --bump-type major \
    --changelog \
    --dry-run
```

The release manager executes a 10-step workflow:

1. Check version consistency across all 4 files
2. Run test suite (unless `--skip-tests`)
3. Bump version
4. Verify package imports correctly
5. Clean build artifacts
6. Build package (`python -m build`)
7. Validate package (`twine check dist/*`)
8. Upload to PyPI (if `--pypi`)
9. Git commit + annotated tag + push
10. Create GitHub release (unless `--skip-github`)

### 4. Merge Release Branch

After the release succeeds:

```bash
# Merge to main
git checkout main
git merge release/v2.0.0
git push origin main

# Merge back to develop
git checkout develop
git merge release/v2.0.0
git push origin develop

# Clean up
git branch -d release/v2.0.0
git push origin --delete release/v2.0.0
```

## Hotfix Workflow

For urgent fixes to a released version:

```bash
# Branch from main
git checkout main
git checkout -b hotfix/v2.0.1

# Fix the issue, then release
python scripts/release_manager.py --release \
    --bump-type patch \
    --release-notes "Fix critical bug in X" \
    --pypi

# Merge to main AND develop
git checkout main
git merge hotfix/v2.0.1
git push origin main

git checkout develop
git merge hotfix/v2.0.1
git push origin develop

# Clean up
git branch -d hotfix/v2.0.1
git push origin --delete hotfix/v2.0.1
```

## Tool Reference

### `scripts/release_manager.py`

The single CLI tool for all release operations.

#### Commands

```bash
# Check version consistency
python scripts/release_manager.py --check

# Bump version
python scripts/release_manager.py --bump [major|minor|patch]

# Set explicit version
python scripts/release_manager.py --set-version 2.0.0

# Build package (clean + build + validate)
python scripts/release_manager.py --build --clean

# Build and upload to PyPI
python scripts/release_manager.py --build --clean --pypi --token $PYPI_API_TOKEN

# Run tests
python scripts/release_manager.py --test

# Verify import
python scripts/release_manager.py --verify

# Full release
python scripts/release_manager.py --release \
    --bump-type minor \
    --release-notes "New features" \
    --pypi

# Full release using CHANGELOG.md for notes
python scripts/release_manager.py --release \
    --bump-type major \
    --changelog \
    --pypi

# Dry-run release (no side effects)
python scripts/release_manager.py --release \
    --bump-type patch \
    --changelog \
    --dry-run
```

#### Flags

| Flag | Description |
|------|-------------|
| `--check` | Check version consistency across all files |
| `--bump TYPE` | Bump version (major, minor, patch) |
| `--set-version VER` | Set explicit version string |
| `--build` | Build sdist + wheel, validate with twine |
| `--test` | Run pytest suite |
| `--verify` | Verify package import + version |
| `--release` | Full 10-step release workflow |
| `--bump-type TYPE` | Bump type for `--release` |
| `--release-notes TEXT` | Release notes text |
| `--changelog` | Use CHANGELOG.md for release notes |
| `--skip-tests` | Skip test suite during release |
| `--skip-github` | Skip GitHub release creation |
| `--pypi` | Upload to PyPI after build |
| `--repository REPO` | `pypi` (default) or `testpypi` |
| `--token TOKEN` | PyPI API token (or `PYPI_API_TOKEN` env var) |
| `--dry-run` | Show actions without executing |
| `--clean` | Clean build artifacts before building |

### Deprecated: `siege_utilities.hygiene.pypi_release`

This module is deprecated as of v2.0.0. All public functions emit `DeprecationWarning` and will be removed in v3.0.0. Use `scripts/release_manager.py` instead.

## CI/CD Integration

### How It Works

The CI pipeline in `.github/workflows/ci.yml` has four build stages:

1. **test** — runs on every push to `main`, `develop`, `dheerajchand/**`, `release/**`, `hotfix/**`
2. **battle-test** — comprehensive stress testing (after test passes)
3. **build** — builds package, validates with twine (after test + battle-test)
4. **release** — publishes to PyPI (only on GitHub Release events)

### PyPI Publishing

The `release` job fires when a GitHub Release is published. It downloads the build artifact and uploads to PyPI using the `PYPI_API_TOKEN` secret.

To trigger a release:
1. Run `scripts/release_manager.py --release` locally (creates the tag + GitHub Release)
2. CI detects the `release: published` event
3. CI publishes to PyPI automatically

Or use `--pypi` flag to upload directly from local machine.

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `PYPI_API_TOKEN` | PyPI upload token (API token, not password) |
| `GITHUB_TOKEN` | Automatic — provided by GitHub Actions |

## Stale Tag Cleanup

A premature `v2.0.0` tag exists pointing to old code on `main` (before the restoration). Before the real 2.0.0 release, delete it:

```bash
# Delete local tag
git tag -d v2.0.0

# Delete remote tag
git push origin :refs/tags/v2.0.0
```

This must happen before running `release_manager.py` for the 2.0.0 release, otherwise git will refuse to create the tag.

## Changelog

Release notes are maintained in `CHANGELOG.md` at the repo root, following the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. The `--changelog` flag reads from this file automatically.

Update `CHANGELOG.md` as part of the release branch stabilization, before running the release manager.
