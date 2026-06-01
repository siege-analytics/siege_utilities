CodeRabbit Workflow
===================

This project uses CodeRabbit as an automated PR reviewer.

Required status
---------------

- ``CodeRabbit`` is required for merge on ``main``.

Review focus
------------

Configured in ``.coderabbit.yaml``:

- correctness and regression risk
- API compatibility and contract stability
- test coverage for bug fixes
- documentation and notebook alignment with behavior changes

Merge readiness
---------------

Before merge:

- resolve or justify high-signal findings
- add/update regression tests for behavior changes
- update docs/notebooks for user-facing changes
- ensure CodeRabbit and required CI checks are green
