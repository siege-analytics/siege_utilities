# Lint Ratchet Plan

Goal: move from best-effort linting to enforceable quality gates without blocking delivery.

## Current State

- CI blocks only on critical Flake8 runtime errors (`E9,F63,F7,F82`).
- Broader lint checks run in non-blocking mode.
- `ruff` currently reports a large backlog (hundreds of findings).

## Ratchet Strategy

### Phase 0 (Now): Baseline and Governance

- Keep existing blocking checks for runtime-safety errors.
- Publish coding style and PR rubric (done).
- Track lint debt categories and owners in issues.

### Phase 1: Block New Severe Violations

- Start failing CI on new instances of:
  - `E722` bare `except`
  - `F601` repeated dict keys
  - `F403/F405` import-star undefined names in touched modules
- Enforce on changed files first if full-repo enforcement is too disruptive.

### Phase 2: Core Hygiene Enforcement

- Add blocking rules for:
  - `F401` unused imports
  - `F841` unused variables
  - `F541` f-strings without placeholders
- Require touched-file clean lint for these rules.

### Phase 3: Full Module Ratchet

- Promote touched-file lint to full-module lint in high-change areas:
  - `siege_utilities/config`
  - `siege_utilities/geo`
  - `siege_utilities/files`
- Continue debt burndown in low-touch modules.

### Phase 4: Full-Repo Enforcement

- Make `ruff check siege_utilities tests` required in CI.
- Keep exception list minimal and temporary, with explicit issue links and sunset dates.

## Rollout Mechanics

- Use a parent issue to track phase completion and blockers.
- For each phase, create:
  - CI/workflow task
  - debt cleanup tasks
  - test updates where behavior changes
- Ratchet only forward; do not relax already-enforced rules.
- Keep required branch checks explicit and documented; include CodeRabbit status once installed.

## Definition of Done

- CI lint gate is required and stable.
- No bare except, no repeated dict keys, no import-star undefined names.
- Touched code paths are lint-clean and test-covered.
