# Change Classification and Release Policy

This policy defines what is a bug, what is a feature, and when releases should happen.

## 1) Change Classification

### Bug Fix

A change is a bug fix when it restores intended behavior without expanding scope.

Typical bug-fix signals:

- Previously working behavior regressed.
- Implementation does not match documented behavior or public contract.
- Input validation, error handling, or data mapping is incorrect.
- Performance or resource behavior is clearly defective (timeouts, leaks, runaway retries).
- Security/privacy behavior violates policy or expected safeguards.

### Feature

A change is a feature when it introduces new capability or materially expands behavior.

Typical feature signals:

- New public API, command, module, service, or output format.
- New supported workflow, integration, or dependency path.
- Existing API gains new behavior that users can opt into.
- New domain model/entity is added.

### Breaking Change

A change is breaking when existing consumers must modify usage to upgrade safely.

Breaking-change signals:

- Public function/class signature changes incompatibly.
- Return schema/type changes incompatibly.
- Config keys, defaults, or precedence behavior changes incompatibly.
- Required dependency/runtime changes.
- Behavior relied on by callers is removed or renamed.

## 2) PR Requirements by Change Type

### Bug Fix PR

- Must include a regression test proving failure before fix and success after.
- Must describe root cause and affected scope.
- Must mention user-visible impact (if any).
- Must include documentation updates.
- Must include notebook updates when the fix affects user-facing workflows.

### Feature PR

- Must include tests for happy path and failure paths.
- Must include docs updates for usage and constraints.
- Must include migration/compatibility notes if touching existing APIs.
- Must include notebook updates showing the new capability in practice.

### Breaking Change PR

- Must be explicitly labeled as breaking.
- Must include migration guidance.
- Must update changelog and release notes with before/after examples.
- Must update notebooks that demonstrate affected workflows.

## 3) Release Triggers and Cadence

Use semantic versioning:

- MAJOR: breaking changes.
- MINOR: backward-compatible features.
- PATCH: backward-compatible bug fixes and docs-only critical clarifications.

Recommended release triggers:

- PATCH release:
  - Any production-impacting bug fix.
  - Security fix.
  - Critical correctness fix.
- MINOR release:
  - One or more meaningful features ready for adoption.
  - Backward-compatible API expansions.
- MAJOR release:
  - Any intentional breaking API/config/runtime change.

Cadence guideline:

- Patch: as needed (can be same day for severe issues).
- Minor: batch periodically (for example biweekly/monthly depending on throughput).
- Major: only when migration plan and adoption communication are ready.

## 4) Release Readiness Gate

A release is ready only when:

- Tests pass in required environments (including Django + GDAL stack for full suite).
- Lint gates for enforced phases pass.
- Required PR/CI checks are green (including CodeRabbit once enabled).
- Changelog entries are complete and accurate.
- Open blockers are resolved or explicitly deferred with risk acceptance.
- Backward compatibility impact is documented.
- Documentation and notebook updates for included changes are complete.

## 5) Backport Policy

- Patch branches may accept:
  - Critical bug fixes
  - Security fixes
  - Low-risk docs clarifications
- Patch branches must not accept:
  - New features
  - Refactors without direct bug/security value
  - Breaking changes
