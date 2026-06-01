Repository Hygiene
==================

This page summarizes repository hygiene expectations for contributors.

Policy goals
------------

- Keep commits reviewable and reproducible.
- Exclude local/temporary artifacts from version control.
- Preserve reviewer-visible notebook outputs.

Tracked vs ignored artifacts
----------------------------

Track:

- Source code and tests
- Documentation updates tied to behavior changes
- ``notebooks/output/`` artifacts used for review and verification

Ignore:

- Build/cache output
- IDE/editor local state
- Temporary/backup files
- Local secrets and machine-specific credentials

Special exception: notebooks output
-----------------------------------

``notebooks/output/`` is intentionally tracked so external contributors and reviewers can inspect generated notebook deliverables without re-running notebooks.

When notebook behavior changes, update both:

- the notebook source, and
- the corresponding artifacts in ``notebooks/output/``

Scripts policy
--------------

- Scripts in ``scripts/README.md`` marked as supported are expected to remain stable.
- One-off diagnostics should be labeled experimental and kept out of critical CI/release paths.
