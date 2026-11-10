# Self-review: renumber the pending release to 5.0.0 (#1885)

Numbering only. No tag, release, upload or publication; 5.0.0 is not
published. The base is develop `2deb6a1f`.

## Decision

Maintainer decision 2026-11-10, recorded on #1818 review thread 4312759586
(reply 4522200436) and in #1885. The pending release contains intentional
breaking changes under `### BREAKING`, and the release policy
(`docs/policies/CHANGE_CLASSIFICATION_AND_RELEASE_POLICY.md`) requires a MAJOR
release for them. The release is therefore 5.0.0, a normal MAJOR, with no 4.1.0
policy waiver. Only `v4.0.0` is tagged and no 4.1.0 GitHub release or upload
exists, so no published artifact changes.

## Changes (6 lines, 6 files)

- `pyproject.toml:13`: `version = "5.0.0"`.
- `siege_utilities/__init__.py:33`: fallback `__version__ = "5.0.0"`.
- `docs/source/conf.py:9` and `docs/source/conf_fast.py:9`:
  `release = '5.0.0'`. Both are version files in
  `scripts/release_manager.py` `VERSION_FILES`, so they track the pending
  version.
- `CHANGELOG.md:34`: `## [4.1.0] - 2026-10-18` becomes `## [5.0.0]`. The date
  is dropped rather than carried over or invented: 2026-10-18 belonged to the
  held 4.1.0 candidate, and `RELEASING.md` dates the section when the release
  is cut. Develop's tests do not require a dated heading for this section
  (`tests/test_release_process.py` checks dates only for the 3.18-3.23
  headings). `release_manager.py`'s section parser (`^## \[X.Y.Z\].*$`)
  accepts the undated heading. Every entry and every BREAKING and Migration
  line is byte-identical: the CHANGELOG diff against develop is this single
  heading line.
- `RELEASING.md:92`: "4.1.0 is the first release through this workflow"
  becomes 5.0.0.

## `4.1.0` references kept on purpose

- `CHANGELOG.md:763`, inside an existing entry: "For the planned 4.1.0
  release, SSL failures now raise...". Entries stay byte-identical in this
  change. If that wording should follow the renumber, it needs a separate
  entry edit.
- Historical records (`docs/verification/self-review-1780.md`, `-1794`,
  `-1809`, `-1861-duckdb-pin.md`, `plans/self-review-1444-metadata.md`) describe
  past work filed under `[4.1.0]` at the time.
- `docs/archive/SESSION_STATUS_2026.md:883` refers to PySpark 4.1.0, which is
  unrelated.

## CHANGELOG entry for the rename

None. The section heading is the record of the version number. No develop
test or convention asks for an entry about renumbering, and Keep a Changelog
records changes to the software, not to its version label.

## Release-policy tests

None relaxed. Develop has no test tying BREAKING entries to a MAJOR bump.
`tests/test_package_metadata_contract.py::test_fallback_version_matches_pyproject`
is the version-coupled test:

- with only `pyproject.toml` renumbered (fallback left at 4.1.0), it fails:
  `assert '4.1.0' == '5.0.0'`;
- with both renumbered, it passes.

## Verification (local Python 3.11.11)

- `tests/test_release_process.py`, `test_package_metadata_contract.py`,
  `test_user_config_export_changelog.py`, `test_smoke.py`,
  `test_backward_compat.py`, `test_runtime_module.py`,
  `test_public_api_surface.py`: 542 passed.
- `python scripts/release_manager.py --check` (read-only): consistent,
  canonical 5.0.0. `docs/conf.py` is reported FILE MISSING, as it already is
  on develop.

## Other in-flight PRs

None are edited. Their entries under `## [4.1.0]` are interim cohort labels
for the pending 5.0.0. A PR that merges after this one resolves its CHANGELOG
conflict by keeping its entry under `## [5.0.0]`.
