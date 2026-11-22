# Self-review: relicense to Apache-2.0 (#1967)

Review-Tier: C (license of the published package; packaging metadata and build requirement change).

## Assumptions
Goal source: #1967, relicense from `AGPL-3.0-only OR LicenseRef-Siege-Commercial` to `Apache-2.0`.
The copyright holders' consent is recorded on #1967 (issuecomment-7085998353).
Base: develop `819a82ea` (PR #1741). The two #1967 commits were replayed onto that live develop
tip after it advanced from `205ca932`; the new history preserves the #1741 changes. The replay
conflicted only in `CHANGELOG.md`. Resolution retains both the upstream #1579 BREAKING entry and
the #1967 License entry. The staged correction is limited to six documentation files; compared
with develop, the resulting PR changes only the #1967 files. No version bump, tag or release is
part of this change.

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
  `docs/source/license_model.rst` describe Apache-2.0.
  - Releases 1.0.0 through 3.8.1 were published under MIT, and releases 3.8.2 through 5.0.0
    under `AGPL-3.0-only OR LicenseRef-Siege-Commercial` (effective March 6, 2026).
  - Every published release keeps its terms.
  - Apache-2.0 applies to the repository from this change and to every release after 5.0.0.
  - Both "License history" sections include the MIT period.
- `docs/PARSONS_LICENSE_ANALYSIS.md`: a dated note at the top. Five links are now permalinks to
  the v5.0.0 commit `819d8188`: the three links to the removed AGPL and commercial texts, and the
  two links to the old `LICENSE`. The note says the files were removed, where the links point, and that the
  SPDX line it describes was in `LICENSE` up to 5.0.0. The analysis is otherwise unchanged.
- `docs/archive/design/survey-module-adr.md`: a dated note at the top. The text below it is
  unchanged.
- `CHANGELOG.md` `[Unreleased]`: the `### License` entry is retained alongside the upstream
  #1579 `### BREAKING` entry after the develop update.

## Test plan

Ran on the change, with results. The build, twine and artifact checks ran on tree `fcf187b2`.
The corrections after the independent review change only documentation, `README.md` among them
(the package long description). The release and changelog tests were re-run on the corrected tree,
and the final head is rebuilt and checked with twine after it is committed.

- `python -m build`, isolated, which installs `setuptools>=77.0.3`: built `siege_utilities-5.0.0.tar.gz` and
  `siege_utilities-5.0.0-py3-none-any.whl`.
- `twine check --strict` on both artifacts: PASSED.
- Wheel `METADATA` read with `unzip -p`: `Metadata-Version: 2.4`, `License-Expression: Apache-2.0`,
  and `License-File` entries for `LICENSE`, `NOTICE` and `LICENSES/wkls.md`. There is no
  `License ::` classifier and no legacy `License:` field.
- Wheel members: `dist-info/licenses/LICENSE`, `NOTICE` and `LICENSES/wkls.md`.
- sdist members: `LICENSE`, `NOTICE` and `LICENSES/wkls.md`.
- Negative: a `--no-isolation` build with the local setuptools 69.5.1 rejects
  `license = "Apache-2.0"` ("`project.license` must be valid exactly by one definition"). The
  `setuptools>=77.0.3` build requirement is therefore needed.
- Tests, 118 passed:
  - `tests/test_release_process.py`
  - `tests/test_user_config_export_changelog.py`
  - `tests/test_package_metadata_contract.py`
  - `tests/test_wheel_contents.py`
  - `tests/test_1895_soupsieve_marker.py`
  - `tests/test_architecture.py`
  - `tests/test_1852_multi_assign_crs_layers.py`
- `scripts/check_*` that pass:
  - `check_wheel_contents` (13 required data files)
  - `check_test_file_hygiene`
  - `check_exception_contracts` (208 flagged, 0 unlisted, 0 stale)
  - `check_atomic_writes`
  - `check_credential_urls`
  - `check_error_path_coverage`
  - `check_imports`
  - `check_no_stub_docstrings`
  - `check_notebook_capability_coverage`
  - `check_notebook_inventory`
  - `check_secret_literals`
  - `check_secret_repr`
  - `check_secure_writes`
  - `check_subprocess_safety`
  - `check_unbounded_io`
  - `check_symbol_test_coverage` (report only)
  - `check_hollow_work` (3 existing findings in files this change does not touch)
  - `check_lint_ratchet --phase all` phases 2 and 3 (no touched Python files)
- Grep for AGPL, Affero, `LicenseRef-Siege-Commercial` and `COMMERCIAL_LICENSE`: the remaining
  hits are history, listed under Evidence.

Not run, or failing on develop as well (this change has no Python source diff):

- `check_lint_ratchet` phase 4 and `check_lint_ratchet_phase1`: `flake8` is not installed in
  the local environment. CI runs flake8.
- `check_security`: `bandit` is not installed in the local environment. CI runs bandit.
- `check_lazy_imports`: stops at `siege_utilities.geo.django.services` because Django settings
  are not configured locally.
- `check_social_review_fidelity`: the local interpreter imported an installed copy of
  `siege_utilities` instead of the checkout.
- `check_broad_except`: 34 existing SU-1 violations, identical on develop `bc7e846a`, tracked as
  #1971.
- `check_test_litter`: a snapshot and compare wrapper around a pytest run, not a standalone check.

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
- `scripts/check_*`: results are listed in the Test plan above. This change has no Python source
  diff, so code guards report the same result as on develop.
- Grep for AGPL, Affero, `LicenseRef-Siege-Commercial` and `COMMERCIAL_LICENSE`: every
  remaining hit is history. That means released CHANGELOG sections, the "License history"
  sections, the README sentence about earlier releases, and the dated notes with the analysis
  and archived text they introduce.

## Pre-mortem
1. Tiger. Severity: P1. The built package declares the wrong license. Mitigation: wheel METADATA checked for `License-Expression: Apache-2.0` and the license files.
2. Tiger. Severity: P1. An old setuptools cannot build the project. Mitigation: build requirement raised to `setuptools>=77.0.3`; the isolated build installs it.
3. Tiger. Severity: P2. Published releases appear relicensed, or their terms are misstated. Mitigation: README, LICENSE_MODEL, license_model.rst and CHANGELOG state the MIT period (1.0.0 through 3.8.1) and the dual-license period (3.8.2 through 5.0.0). They also state that every published release keeps its terms.
4. Paper Tiger. Severity: P3. Links in historical text point to removed or replaced files. `docs/PARSONS_LICENSE_ANALYSIS.md` has three links to removed files (`LICENSES/AGPL-3.0.txt` once, `LICENSES/Siege-Commercial.txt` twice) and two links to the old `LICENSE`. Mitigation: all five are permalinks to the v5.0.0 commit, as the dated note explains.

## Findings

| ID | Priority | Finding | Outcome |
|----|----------|---------|---------|
| F1 | P1 | `license = "Apache-2.0"` needs setuptools 77 or later. Under the old `setuptools>=61.0` requirement, a non-isolated build with setuptools 69.5.1 fails ("`project.license` must be valid exactly by one definition"). Build requirement raised to `setuptools>=77.0.3`. The isolated build installs it and passes `twine check --strict`. | fixed |
| F2 | P2 | `NOTICE` needed a copyright year that the dual-license wording did not give. | `NOTICE` uses 2025-2026; 2025 is the year of the first commit on develop. It matches the MIT `LICENSE` of releases up to 3.8.1 ("Copyright (c) 2025 Siege Analytics"). |
| F3 | P2 | Current setuptools rejects a `License ::` classifier alongside a license expression. | The AGPL classifier is removed and no license classifier is added. The wheel METADATA has `License-Expression: Apache-2.0` and no `License ::` classifier. |
| F4 | P3 | Some `scripts/check_*` guards cannot run locally: flake8, bandit, Django settings, and an installed package that shadows the checkout. `check_broad_except` reports 34 existing violations. | Listed under the Test plan with reasons. This change has no Python source diff. `check_broad_except` is identical on develop and tracked as #1971. CI runs flake8 and bandit. |
| S2-1 | P2 | Independent review: the docs said every release up to 5.0.0 was dual-licensed. Releases 1.0.0 through 3.8.1 were MIT, and the "License history" sections omitted the MIT period. | CHANGELOG, README, `docs/LICENSE_MODEL.md` and `docs/source/license_model.rst` now state the MIT period and the dual-license period, and that every published release keeps its terms. Both history sections list the MIT period. Checked against `LICENSE` at v1.0.0 and v3.8.1 (MIT) and at v3.8.2 and v5.0.0 (dual). |
| S3-1 | P3 | Independent review: `docs/PARSONS_LICENSE_ANALYSIS.md` linked the removed AGPL and commercial texts (three links). It also described an SPDX line that `LICENSE` no longer has. | The three links, and the two links to the old `LICENSE`, are permalinks to the v5.0.0 commit `819d8188`. The dated note explains the removal and the SPDX line. |
| S3-2 | P3 | Independent review: the Sphinx `copyright` in `docs/source/conf.py` and `docs/source/conf_fast.py` (`2025-2026, Dheeraj Chand`) differs from the holder in `NOTICE`. | Pre-existing and out of scope; those files are unchanged. `NOTICE` names Siege Analytics, the holder named in the earlier license texts. The MIT `LICENSE` reads "Copyright (c) 2025 Siege Analytics". `LICENSES/Siege-Commercial.txt` reads "Copyright (c) Siege Analytics. All rights reserved.", and `COMMERCIAL_LICENSE.md` requires a "Copyright notice for Siege Analytics". |
| S3-3 | P3 | Independent review: the original self-review named `bc7e846a` as the base, and develop subsequently advanced. | Replayed the two #1967 commits onto the live develop tip `819a82ea` after #1741 landed. Resolved the `CHANGELOG.md` conflict by retaining both upstream #1579 and #1967 entries. The PR diff is scoped to #1967's files. |

## Independent review

An independent pre-push review of tree `fcf187b2` (commit `b6addaf8`) against develop
`bc7e846a` FAILED with one S2 and three S3 findings:
https://github.com/siege-analytics/siege_utilities/issues/1967#issuecomment-7086398153

It confirmed:
- the verbatim Apache-2.0 `LICENSE` and the `NOTICE`;
- the removed files and the unchanged `LICENSES/wkls.md`;
- the `pyproject.toml` license metadata;
- that no package, test, script, workflow or notebook file is touched.

The S2 was the misstated license history of earlier releases. The findings and their
resolutions are listed under Findings. The license-history corrections are independently re-reviewed on the refreshed tree after the
upstream develop update. That re-review is linked from this commit's `Hostile-Review` trailer and
from the pull request.
