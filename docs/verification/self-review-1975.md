# Self-review: license wording corrections (#1975)

Review-Tier: C (wording in the package long description and the relicensing record).

## Assumptions
Goal source: #1975, two wording notes from the independent review of the relicensing change (#1967).
Base: develop `a41896f1`, which contains the relicensing change. No version bump, tag or release
is part of this change, and the `setuptools>=77.0.3` floor in `pyproject.toml` is unchanged.

## Changes
- `README.md` license section: "Apache-2.0 applies to the repository from this change" now reads
  "Apache-2.0 applies to the current development revision and to every release after 5.0.0."
  It was the only "this change" wording in `README.md`. `README.md` is the package long
  description, so the change is visible to users of the package metadata.
- Class sweep of the same imprecise wording, aligned to "the current development revision and
  every release after 5.0.0":
  - `CHANGELOG.md` `[Unreleased]` `### License`: the unreleased relicensing entry, corrected in
    place, with a reference to #1975.
  - `docs/LICENSE_MODEL.md` and `docs/source/license_model.rst`: the Apache-2.0 item of the
    "License history" list.
  - `docs/PARSONS_LICENSE_ANALYSIS.md`: the dated note at the top.
  - `docs/verification/self-review-1967.md`: the line in its Changes list that restates the
    README wording.
- `docs/verification/self-review-1967.md`: the build-requirement line no longer calls setuptools
  77.0.3 "the first release that accepts a license expression". License-expression support began
  in setuptools 77.0.0; 77.0.3 is the chosen supported minimum.

## Class sweep
Files checked for "this change", "from this change", "relicensing change" and "first release
that accepts":
- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `NOTICE`
- `docs/LICENSE_MODEL.md`
- `docs/source/license_model.rst`
- `docs/PARSONS_LICENSE_ANALYSIS.md`
- `docs/archive/design/survey-module-adr.md`
- `docs/verification/self-review-1967.md`

Files changed:
- `README.md`
- `CHANGELOG.md`
- `docs/LICENSE_MODEL.md`
- `docs/source/license_model.rst`
- `docs/PARSONS_LICENSE_ANALYSIS.md`
- `docs/verification/self-review-1967.md`

After the change, a tracked-tree grep for "from this change", "relicensing change" and "first
release that accepts" has one hit: `plans/801-self-review.md:116`. It is unrelated; the sentence
says a deselected test failure was not a regression "from this change" in an earlier PR.
`CHANGELOG.md` lines 1228 and 2204 use "this change" in entries for earlier versions, also
unrelated. This self-review quotes the old wording only to describe the change.

## Test plan
- `tests/test_release_process.py` and `tests/test_user_config_export_changelog.py` on this tree.
- `scripts/check_test_file_hygiene.py` on this tree.
- `git diff --cached --check` on the staged change.
- The tracked-tree grep recorded under Class sweep.

## Findings

| ID | Priority | Finding | Outcome |
|----|----------|---------|---------|
| F1 | P3 | "Applies to the repository from this change" (and "from the relicensing change") does not say which revisions are covered once the change is merged. | `README.md`, the unreleased CHANGELOG entry, both license-model pages, the Parsons note and the relicensing self-review now say "the current development revision and every release after 5.0.0". |
| F2 | P3 | The relicensing self-review called setuptools 77.0.3 the first release that accepts a license expression; support began in 77.0.0. | The line now names 77.0.0 as the first supporting release and 77.0.3 as the chosen minimum. The `pyproject.toml` floor is unchanged. |

## Independent review
An independent exact-tree review of this staged change is linked from the commit's
`Hostile-Review` trailer and from the pull request.
