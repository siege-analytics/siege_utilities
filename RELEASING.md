# Releasing siege-utilities

There is one way to put a release on PyPI: push a `v*` tag and let
[`.github/workflows/publish-tag.yml`](.github/workflows/publish-tag.yml)
publish it (#1419).

## Rules

- **Manual uploads to PyPI are prohibited.** That covers `twine upload`,
  `uv publish`, `python -m build && twine upload` from a laptop, and any token
  in a local environment. `scripts/release_manager.py` refuses
  `--repository pypi`; `--build --pypi` uploads to TestPyPI only.
- A release tag is `v` + the `version` in `pyproject.toml`, exactly, and it
  points at a commit that is already on `main`.
- Never move, re-point or delete a pushed release tag, and never rewrite
  `main`. PyPI filenames are immutable: a version that has been uploaded,
  or deleted, cannot be uploaded again. Fix forward with a new version.
- The version bump happens on `develop` at release-candidate time, not in the
  release step.

## What the workflow does

`publish-tag.yml` runs on a `v*` tag push. Each job needs the one before it,
so nothing is uploaded unless all of them succeed:

1. **verify-tag**: the ref is a `v*` tag, the tag equals
   `v<pyproject version>`, `release_manager.py --check` finds the version
   strings consistent, and the tagged commit is an ancestor of `origin/main`.
2. **ci**: the whole of `ci.yml`, called as a reusable workflow on the tagged
   commit. Every blocking job must pass, including `test` (3.11-3.13),
   `test-postgis` and `build`.
3. **build**: sdist and wheel from the tag, `twine check`, and
   `scripts/check_wheel_contents.py`. The wheel root must be exactly
   `siege_utilities`, every data file the code loads must be present, and no
   member name may contain whitespace (#1420).
4. **publish**: `pypa/gh-action-pypi-publish` from the `pypi` GitHub
   environment, authenticated with the `PYPI_API_TOKEN` repository secret.
   This is the only place that secret is used. When a PyPI trusted publisher
   is configured (below), the token is dropped and the action also uploads
   PEP 740 attestations.

A GitHub release no longer triggers CI or an upload. Create it after the
publish job succeeds, with notes from `CHANGELOG.md`.

## Cutting a release

1. On `develop`: the version is already bumped (RC), `CHANGELOG.md` has a
   dated section for it, and CI is green.
2. Reconcile `develop` and `main` and merge `develop` into `main` through a
   pull request. This is an ops step at release time.
3. Tag the merge commit on `main` and push **only that tag**:

   ```bash
   git fetch origin main
   git tag -a vX.Y.Z -m "vX.Y.Z" origin/main
   git push origin refs/tags/vX.Y.Z
   ```

   (`git push --tags` pushes every local tag and can start a publish run for
   each of them.)
4. Watch it: `gh run list --workflow publish-tag.yml -R siege-analytics/siege_utilities`.
   If a job fails for a transient reason, re-run the failed jobs. If it fails
   for a real reason, fix it on `develop` and release a new version. Do not
   re-point the tag.
5. Check the PyPI files match the tag (and, once trusted publishing is on,
   show provenance), then create the GitHub release from the tag.

## One-time setup (repository admins)

Already in place: the `PYPI_API_TOKEN` repository secret, which earlier
releases used. The `pypi` environment is created on the first run if it does
not exist; restrict its deployments to tags matching `v*`.

Optional upgrade to trusted publishing with attestations:

1. PyPI project `siege-utilities` → Publishing → add a GitHub trusted
   publisher: owner `siege-analytics`, repository `siege_utilities`, workflow
   `publish-tag.yml`, environment `pypi`.
2. Delete the `password:` line from the publish step in `publish-tag.yml`.
3. After one release has published that way, delete the `PYPI_API_TOKEN`
   secret and revoke the token on PyPI.

## Historical tags (documentation only)

These dispositions record what exists. No tag is moved, re-created or deleted
and no history is rewritten.

| Tag | Points at | On `main` | GitHub release | PyPI | Disposition |
|---|---|---|---|---|---|
| `v3.19.0` | `75c8125f` | No | Yes | 3.19.0, uploaded 2026-06-20 | Keep as is. `75c8125f` ("fix version to 3.19.0 for tag backfill", 2026-06-19) changes only version strings in 5 files, on top of `13a2653f`, which is on `main` (2026-05-28). The 3.19.0 code is `main`@`13a2653f`. |
| `v3.21.0` | `7764b35d` | Yes | No | Never uploaded | Keep as is. 3.21.0 was not published to PyPI and will not be; a wheel exists only on Nexus (#1419, #1401). Its changes reached PyPI in 3.22.0. |
| `v4.0.0` | `9c3463b1` | Yes | Yes | 4.0.0, uploaded 2026-10-11 by hand, before CI, without attestations | Keep as is (the file cannot be replaced). The wheel matches the tag but also ships a top-level `spikes` package and lacks the SQL/YAML data files (#1420). 4.1.0 is the first release through this workflow. |

3.24.0 was never tagged and never uploaded to PyPI; a 3.24.0 wheel exists on
Nexus (#1401). Nexus publishing is tracked in #1401, not here.

See also [docs/RELEASE_LINEAGE.md](docs/RELEASE_LINEAGE.md) for the 1.x
retroactive tags.
