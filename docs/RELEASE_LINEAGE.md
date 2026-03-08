# Release Lineage Reconstruction

Date: March 8, 2026

## Goal

Reconstruct missing historical release boundaries so the repository has a coherent semantic-version lineage from `v1.x` onward.

## Findings

`pyproject.toml` version transitions show the missing 1.x boundaries:

- `c69fa4b` -> `1.0.0`
- `44b0f26` -> `1.0.1`
- `8f02651` -> `1.1.0`
- `60b0d00` -> `2.0.0` (already tagged/released)

## Actions Completed

Retroactive git tags were created and pushed:

- `v1.0.0` -> `c69fa4b`
- `v1.0.1` -> `44b0f26`
- `v1.1.0` -> `8f02651`

## Remaining Step

Create GitHub release objects for these tags.

Current CLI token in this environment can list releases and merge PRs, but release creation returned scope/404 errors. When authenticated with sufficient scope, run:

```bash
gh release create v1.0.0 --repo siege-analytics/siege_utilities \
  --title "v1.0.0 (retroactive)" \
  --target c69fa4b \
  --notes "Retroactive release created from historical 1.0.0 version commit."

gh release create v1.0.1 --repo siege-analytics/siege_utilities \
  --title "v1.0.1 (retroactive)" \
  --target 44b0f26 \
  --notes "Retroactive release created from historical 1.0.1 version commit."

gh release create v1.1.0 --repo siege-analytics/siege_utilities \
  --title "v1.1.0 (retroactive)" \
  --target 8f02651 \
  --notes "Retroactive release created from historical 1.1.0 version commit."
```

If `gh release create` reports missing scope, refresh auth:

```bash
gh auth refresh -h github.com -s workflow
```

## Notes

- This approach does not rewrite history.
- Tags are immutable release anchors; GitHub release objects are metadata on top.
- Existing `v2+` tags and releases remain unchanged.
