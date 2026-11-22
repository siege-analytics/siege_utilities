# Self-review: relicense to Apache-2.0 (#1967)

Review-Tier: C (license of the published package; packaging metadata and build requirement change).

## Assumptions
Goal source: #1967, relicense from `AGPL-3.0-only OR LicenseRef-Siege-Commercial` to `Apache-2.0`.
The copyright holders' consent is recorded on #1967 (issuecomment-7085998353).
Base: develop `bc7e846a`. No version bump, tag or release is part of this change.

## Changes
- `LICENSE`: the canonical Apache License 2.0 text, downloaded from
  `https://www.apache.org/licenses/LICENSE-2.0.txt` and not retyped
  (sha256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`, 202 lines).
- `NOTICE` (new): "Siege Utilities", "Copyright 2025-2026 Siege Analytics", and a pointer to
  `LICENSES/wkls.md` for third-party attribution. 2025 is the year of the first commit on develop.
- Removed `COMMERCIAL_LICENSE.md`, `LICENSES/AGPL-3.0.txt` and `LICENSES/Siege-Commercial.txt`.
  `LICENSES/wkls.md` is kept unchanged.
- `pyproject.toml`:
  - `license = "Apache-2.0"` as an SPDX expression (PEP 639);
  - `license-files = ["LICENSE", "NOTICE", "LICENSES/*"]`;
  - build requirement raised to `setuptools>=77.0.3`, the first release that accepts a license expression;
  - AGPL classifier removed. No `License ::` classifier is added, because setuptools rejects one alongside a license expression.
- `README.md`, `CONTRIBUTING.md` (inbound = outbound), `docs/LICENSE_MODEL.md` and
  `docs/source/license_model.rst` describe Apache-2.0. They state that releases up to and
  including 5.0.0 keep their published terms.
- `docs/PARSONS_LICENSE_ANALYSIS.md` and `docs/archive/design/survey-module-adr.md`: a dated
  note at the top. The text below the note is unchanged.
- `CHANGELOG.md` `[Unreleased]`: a `### License` entry.

## Evidence
- `python -m build` (isolated, setuptools>=77.0.3) builds both artifacts, `siege_utilities-5.0.0.tar.gz` and `siege_utilities-5.0.0-py3-none-any.whl`.
  The log shows "adding license file" for `LICENSE`, `NOTICE` and `LICENSES/wkls.md`.
- `twine check --strict` passes on both artifacts.
- Wheel `METADATA`: `License-Expression: Apache-2.0`, plus `License-File: LICENSE`,
  `License-File: NOTICE` and `License-File: LICENSES/wkls.md`. There is no `License ::` classifier.
- The wheel contains `dist-info/licenses/LICENSE`, `NOTICE` and `LICENSES/wkls.md`.
  The sdist contains `LICENSE`, `NOTICE` and `LICENSES/wkls.md`.
- Negative check: a non-isolated build with the older local setuptools rejects
  `license = "Apache-2.0"` with "`project.license` must be valid exactly by one definition".
  The raised build requirement is therefore needed.
- Tests: `test_release_process`, `test_user_config_export_changelog`,
  `test_package_metadata_contract`, `test_wheel_contents`, `test_1895_soupsieve_marker`,
  `test_architecture` and `test_1852_multi_assign_crs_layers`: 118 passed.
- `scripts/check_*`: the results are in the PR description. This change has no Python source
  diff, so code guards report the same result as on develop.
- Grep for AGPL, Affero, `LicenseRef-Siege-Commercial` and `COMMERCIAL_LICENSE`: every
  remaining hit is history. That means released CHANGELOG sections, the "License history"
  sections, the README sentence about earlier releases, and the dated notes with the analysis
  and archived text they introduce.

## Pre-mortem
1. Tiger. Severity: P1. The built package declares the wrong license. Mitigation: wheel METADATA checked for `License-Expression: Apache-2.0` and the license files.
2. Tiger. Severity: P1. An old setuptools cannot build the project. Mitigation: build requirement raised to `setuptools>=77.0.3`; the isolated build installs it.
3. Paper Tiger. Severity: P2. Published releases appear relicensed. Mitigation: README, LICENSE_MODEL, license_model.rst and CHANGELOG state that releases up to and including 5.0.0 keep their terms.
4. Paper Tiger. Severity: P3. A link to a removed file remains in historical text: `docs/PARSONS_LICENSE_ANALYSIS.md` links `LICENSES/AGPL-3.0.txt`. It is kept as history under the dated note.
