# Lint Policy

This document explains why CI lint checks fail, what commands to run locally before
pushing, and how to keep the phase4 baseline from drifting.

See [LINT_RATCHET_PLAN.md](LINT_RATCHET_PLAN.md) for the phased rollout strategy.

---

## Why CI Lint Keeps Failing When Local Checks Pass

Five root causes account for nearly every "passed locally, failed in CI" lint or release incident:

### 1. The CONTRIBUTING.md pre-PR checklist was incomplete

The checklist showed only the phase-1 `flake8 --select=E9,F63,F7,F82` command.
CI runs phases 2–4 via `scripts/check_lint_ratchet.py`, which enforces
`F401` (unused imports), `F841` (unused variables), and `F541` (f-strings without
placeholders) on every file touched by the PR. Those rules were invisible to developers
following the documented checklist.

**Fix:** run the full ratchet script locally (see commands below).

### 2. No pre-commit hook enforces lint before commit

There is no `.pre-commit-config.yaml` in the repo. Nothing stops a commit that
introduces new F401/F841 violations. The first time a developer sees the failure is
when CI runs on their push.

**Fix:** install the pre-commit hook shown below.

### 3. Phase-4 baseline can drift from the codebase

`lint_baselines/phase4_flake8_fingerprints.txt` is hand-maintained. If a PR is merged
that cleans up violations without regenerating the baseline, subsequent PRs fail phase 4
because the baseline references fingerprints that no longer exist.

**Fix:** regenerate the baseline in a dedicated debt-cleanup PR using
`python scripts/check_lint_ratchet.py --phase phase4 --update-baseline`.

### 4. Version bump omitted from the release PR (release-mechanics gap)

CI's "Verify release tag matches package version" step runs only on the `release` event —
it never fires on a normal PR push. This means a PR that forgets to bump
`pyproject.toml` passes all pre-merge checks, the tag gets created, and only then does
the release job fail before PyPI upload.

**Fix:** the version bump (`pyproject.toml` + any `__version__` literals) belongs in the
**same PR** as the code being released, committed before the GitHub Release is created.
Checklist addition for release PRs:

```bash
# Confirm version in pyproject.toml matches the intended tag before merging
grep '^version' pyproject.toml
```

### 5. Bypassing the canonical release script

`scripts/release_manager.py` atomically updates all six version-bearing files
(`pyproject.toml`, `setup.py`, `siege_utilities/__init__.py`, `docs/conf.py`,
`docs/source/conf.py`, `docs/source/conf_fast.py`) in a single `--set-version` or
`--bump` call. When version bumps are done file-by-file across multiple PRs instead,
at least one file is always missed. CI's "Verify version consistency" step then fails
every release attempt until all six are aligned.

**Fix:** always use the release script for version management:

```bash
# Check current consistency
python scripts/release_manager.py --check

# Bump (updates all 6 files at once)
python scripts/release_manager.py --bump patch

# Or set an explicit version
python scripts/release_manager.py --set-version 3.13.2
```

The `--release` workflow does the full 12-step dance (version bump → tests → build →
merge develop → tag → PyPI → GitHub Release). Use `--dry-run` to preview.

---

## Commands to Run Before Every Push

Run these in order. Stop and fix before continuing if any step fails.

```bash
# Phase 1 — runtime-safety errors on changed files (matches CI lint-ratchet-phase1)
flake8 siege_utilities --count --select=E9,F63,F7,F82 --show-source --statistics

# Phases 2-4 — hygiene + module ratchet + full-repo fingerprint
# (local aggregate; CI runs each phase separately with explicit --base-sha/--head-sha)
python scripts/check_lint_ratchet.py --phase phase2
python scripts/check_lint_ratchet.py --phase phase3
python scripts/check_lint_ratchet.py --phase phase4
```

Or run all phases in one call:

```bash
python scripts/check_lint_ratchet.py --phase all
```

---

## Optional: Pre-commit Hook

Installing pre-commit runs the phase-1 check automatically on every `git commit`,
so violations are caught at the source before they reach CI.

```bash
pip install pre-commit
# From repo root:
pre-commit install
```

If the repo gains a `.pre-commit-config.yaml`, the full ratchet can be wired in there.
Until then, the manual commands above are the authoritative gate.

---

## Updating the Phase-4 Baseline

The baseline (`lint_baselines/phase4_flake8_fingerprints.txt`) must only be updated in
a dedicated lint-debt cleanup PR — **never** as a side effect of a feature PR.

```bash
python scripts/check_lint_ratchet.py --phase phase4 --update-baseline
git add lint_baselines/phase4_flake8_fingerprints.txt
git commit -m "chore(lint): regenerate phase4 baseline after debt cleanup"
```

Include the PR title `chore(lint): phase4 baseline refresh — <brief reason>` so it is
easy to identify in git history.

---

## Rule Reference

| Phase | Rules enforced | Scope |
|-------|---------------|-------|
| 1 | `E9, F63, F7, F82` | Full package (`flake8 siege_utilities --select=E9,F63,F7,F82`) |
| 2 | `F401, F841, F541` | Files touched by the PR |
| 3 | `E722, F601, F403, F405` + phase 2 | Entire domain (`siege_utilities/geo/`, `config/`, `files/`) if any file in domain is touched |
| 4 | `E722, F601, F403, F405` + phase 2 | Full repo, fingerprint-matched against baseline |
