# Summary

Describe what changed and why.

## Change Classification

- [ ] Bug fix (restores intended behavior, no scope expansion)
- [ ] Feature (new capability or materially expanded behavior)
- [ ] Breaking change (consumer updates required)

If breaking, include migration notes:

## Release Impact

- [ ] Patch
- [ ] Minor
- [ ] Major

Reason for selected release impact:

API contract note:
- [ ] If public API symbols were added intentionally, `scripts/contracts/contract_allowlist.json` is updated in this PR.

## Verification

- [ ] Tests added/updated for changed behavior
- [ ] Regression test added for bug fix (if applicable)
- [ ] Critical path tests run (`tests/test_smoke.py`, `tests/test_runtime_guard.py`, `tests/test_sql_safety.py`)
- [ ] Lint run for touched files/modules
- [ ] Documentation updated in this PR
- [ ] Notebooks updated in this PR (if user-facing workflow/API changed)

Commands run:

## Required Review Checklist

- [ ] Complies with `CODING_STYLE.md`
- [ ] Meets `PR_REVIEW_RUBRIC.md` requirements
- [ ] Classification/release impact aligns with `CHANGE_CLASSIFICATION_AND_RELEASE_POLICY.md`
- [ ] Docs/notebooks/changelog updated for user-visible behavior

## Risks and Rollback

- Risk summary:
- Rollback plan:
