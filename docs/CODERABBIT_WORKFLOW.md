# CodeRabbit Workflow

This repository uses CodeRabbit for automated PR review.

## Required Status

- `CodeRabbit` is a required status check on protected branches (`develop` and `main`).
- PRs cannot be merged until the check is successful.
- Standard contributor PR target is `develop`.

## Scope and Policy

CodeRabbit behavior is configured in `.coderabbit.yaml`.

Review focus for this repository:
- correctness and regression risk
- API contract stability
- test coverage for bug fixes
- docs/notebook updates for user-facing changes

## Merge Readiness Rules

Before merge:
- Resolve or explicitly justify all high-signal CodeRabbit findings.
- Add regression tests for bug fixes and API behavior changes.
- Update docs and notebooks when behavior/API changed.
- Confirm `CodeRabbit` and required CI checks are green.

## Handling False Positives

If a finding is not valid:
- respond in-thread with a technical rationale,
- link to tests or docs that demonstrate expected behavior,
- avoid dismissing without explanation.

## Maintainer Checklist

- Keep `.coderabbit.yaml` aligned with current contribution policy.
- Treat repeated findings as policy/tooling gaps and codify fixes in CI/lint/docs.
