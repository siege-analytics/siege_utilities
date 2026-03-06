# Repository Hygiene Policy

This policy defines what should and should not be committed to `siege_utilities`.

## Goals

- Keep the repository reviewable and reproducible.
- Prevent one-off local artifacts from polluting history.
- Preserve generated notebook outputs needed for reviewer visibility.

## Tracked Artifacts

Commit:
- Source code and tests.
- Documentation updates that match behavior changes.
- Notebook outputs in `notebooks/output/` when they are part of reviewed deliverables.

Do not commit:
- Local IDE/editor state.
- Cache/build outputs.
- Temporary backup files.
- Personal environment files and local secrets.

## Explicit Exception: `notebooks/output/`

`notebooks/output/` remains tracked by policy so reviewers can inspect rendered notebook artifacts without re-running notebooks.

If notebook logic changes, update both:
- the notebook itself, and
- the expected output artifacts in `notebooks/output/`.

## Scripts and One-off Analysis

- Stable scripts used by contributors/CI should be documented in `scripts/README.md` under supported workflows.
- One-off analysis scripts must be clearly labeled as experimental and should not become implicit dependencies for CI or release automation.

## Contribution Checklist

Before opening a PR:
- Verify no local cruft files are staged.
- Confirm docs and notebook outputs are updated for user-facing/API changes.
- Confirm references in docs point to files that actually exist in the repository.
