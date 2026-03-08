# PR Review Rubric

Use this rubric for every pull request. If any required item is unchecked, the PR is not ready to merge.

## 1) API and Signatures (Required)

- [ ] Public functions and methods have complete type hints (inputs + return type).
- [ ] Signature changes are intentional and documented in PR notes.
- [ ] Optional behavior is keyword-based and explicit.
- [ ] Function names and arguments are domain-clear and unambiguous.

## 2) Design Quality (Required)

- [ ] Functional style used for stateless transformations where possible.
- [ ] Classes are used only for cohesive stateful/domain behavior.
- [ ] Iterative approach used unless recursion is naturally justified and bounded.
- [ ] No hidden side effects at import time.
- [ ] Convenience/broad imports are used only in API-boundary modules and remain explicit/tested/documented.

## 3) Error Handling (Required)

- [ ] No bare `except:` blocks.
- [ ] Exceptions are specific and include actionable context.
- [ ] No silent failure paths (`pass` without rationale, opaque `None` returns).
- [ ] Failure behavior is documented and tested.

## 4) Dependency and Environment Behavior (Required)

- [ ] Required dependencies are explicit.
- [ ] Optional dependency paths fail with actionable errors.
- [ ] Django + GDAL dependent behavior is covered by marked tests and setup docs.
- [ ] No secret material is logged or committed.

## 5) Tests and Validation (Required)

- [ ] Unit/integration tests added or updated for changed behavior.
- [ ] Regression tests added for bug fixes.
- [ ] Critical path tests pass.
- [ ] Lint passes for touched files/modules or debt is explicitly tracked.
- [ ] Required CI checks are green, including CodeRabbit review status.

## 6) Documentation (Required)

- [ ] Public API behavior changes are reflected in docs/examples.
- [ ] Config precedence/fallback/caching behavior is documented where relevant.
- [ ] Any migration/deprecation path is documented.
- [ ] Notebooks are updated for user-facing workflow/API changes.

## Severity Guidance for Reviewers

- Blocker: correctness bugs, data corruption risk, security/privacy risks, contract-breaking API changes without migration path.
- High: unreliable failure behavior, undocumented side effects, missing regression coverage for known bug class.
- Medium: maintainability issues that increase defect risk (naming, signature ambiguity, weak typing, poor boundaries).
- Low: style consistency, readability, and non-critical cleanup.
