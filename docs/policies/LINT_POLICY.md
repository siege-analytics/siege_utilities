# Lint Policy

This document explains why CI lint checks fail, what commands to run locally before
pushing, and how to keep the phase4 baseline from drifting.

See [LINT_RATCHET_PLAN.md](LINT_RATCHET_PLAN.md) for the phased rollout strategy.

---

## Why CI Lint Keeps Failing When Local Checks Pass

Three root causes account for nearly every "passed locally, failed in CI" lint incident:

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

---

## Commands to Run Before Every Push

Run these in order. Stop and fix before continuing if any step fails.

```bash
# Phase 1 — runtime-safety errors on changed files (matches CI lint-ratchet-phase1)
flake8 siege_utilities --count --select=E9,F63,F7,F82 --show-source --statistics

# Phases 2-4 — hygiene + module ratchet + full-repo fingerprint (matches CI lint-ratchet-phases2-4)
python scripts/check_lint_ratchet.py --phase phase2
python scripts/check_lint_ratchet.py --phase phase3
python scripts/check_lint_ratchet.py --phase phase4
```

Or run all phases in one call (the script accepts `all`):

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
| 1 | `E722, F601, F403, F405` | Files touched by the PR |
| 2 | `F401, F841, F541` | Files touched by the PR |
| 3 | All of phase 1 + 2 | Entire domain (`siege_utilities/geo/`, `config/`, `files/`) if any file in domain is touched |
| 4 | All of phase 1 + 2 | Full repo, fingerprint-matched against baseline |
