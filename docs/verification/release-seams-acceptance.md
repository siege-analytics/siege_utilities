# Release seam acceptance notebook

`notebooks/acceptance/release_seams.ipynb` composes actual public APIs over invented EPSG:6933 rectangles and Census-format CSV. It does not certify live providers, credentials, production data, six real maps, PDFs or a release.

## Required independent lanes

Run the same source-clean notebook in two own isolated environments: (1) Shapely/NumPy only, WITHOUT Tobler, DuckDB or mapclassify; (2) Tobler with mapclassify. Install an actual wheel built from the declared source, not an editable checkout. No xfail, skipped code cells, adaptive classification answers, or mocked SU functions. External dependency transport, the dependency output-writer failure, and test-owned provider subclasses are explicitly identified in the notebook. `allocate_total=True` is a documented cross-backend limitation, not an equivalence assertion.

## Standalone runner

Use that environment's Python:

```sh
python -I scripts/run_release_seams.py --repo "$SU_RELEASE_ACCEPTANCE_REPO" --expected-sha "$SU_RELEASE_ACCEPTANCE_SHA" --wheel "$SU_RELEASE_ACCEPTANCE_WHEEL" --notebook notebooks/acceptance/release_seams.ipynb --runs "$SU_RELEASE_ACCEPTANCE_RUNS" --lane "$SU_RELEASE_ACCEPTANCE_LANE"
```

For a verified own API archive add `--source-provenance receipt.json`. A clean Git integrated-candidate checkout OR a verified API archive of a REAL MERGED integrated candidate satisfying every receipt predicate below is eligible runtime input; passing existing required CI remains required. For a mechanical component diagnostic instead add `--composition-provenance composition-provenance.json --expected-composition-tree CONTENT_TREE`; `--expected-sha` is then the actual baseline commit and candidate SHA is null. Composition/null-SHA/base-only archive runs remain diagnostics, not candidate/CI/release acceptance.

## Pytest/CI bridge

Set the five `SU_RELEASE_ACCEPTANCE_*` variables used above. In EACH required environment run:

```sh
python -I -m pytest -o addopts='' -m integration tests/test_notebooks.py::test_release_acceptance_notebook
```

For a verified API archive additionally set `SU_RELEASE_ACCEPTANCE_SOURCE_PROVENANCE`; only the real merged integrated-candidate archive defined below is eligible for candidate acceptance. For component diagnostics set the pair `SU_RELEASE_ACCEPTANCE_COMPOSITION_PROVENANCE` / `SU_RELEASE_ACCEPTANCE_COMPOSITION_TREE`. Missing provenance fails; it never skips. The integration selector separates this installed-wheel release lane from the normal unit matrix; it is not evidence of success when unselected. Actual execution in both lanes is required for release acceptance, either manually through the supported standalone runner/bridge or through normal CI. Durable CI automation is an optional normal-owner follow-up, not a new source-publication or protection-change prerequisite. Existing required CI and genuine source-publication/review predicates remain unchanged; this patch changes no workflows or protections.

## Same-candidate acceptance execution; optional durable CI

Acceptance requires actual execution in BOTH isolated lanes against the same real integrated candidate, with retained evidence. A supported manual runner/bridge execution or normal CI execution can satisfy this requirement; collection, registration, a workflow definition or an unselected CI group cannot. Existing required CI must also pass. A newly created two-lane workflow, new required status checks and protection changes are NOT universal prerequisites for feature-source publication.

The acceptance operator must:

1. Use the real integrated candidate commit, retain its exact SHA/tree and build a wheel from that source. Input may be a clean Git checkout, or an unaltered API archive of a REAL MERGED integrated commit under the strict archive predicates below. Do not install an old whole PR head, overlay components, an editable checkout or an unrelated published version.
2. Create two independent environments; install the wheel plus Python >=3.11, pandas<3, NumPy, SciPy, GeoPandas, Shapely>=2, pyproj, pyarrow, censusgeocode, matplotlib, pytest, nbclient, nbformat and ipykernel. The `shapely-only` environment must lack Tobler, DuckDB and mapclassify. The `tobler` environment must include Tobler and mapclassify.
3. Set `SU_RELEASE_ACCEPTANCE_REPO` to the clean candidate checkout or qualified unaltered merged-candidate API extraction, `SU_RELEASE_ACCEPTANCE_SHA` to its actual commit, `SU_RELEASE_ACCEPTANCE_WHEEL` to the exact built wheel, `SU_RELEASE_ACCEPTANCE_RUNS` to a retained per-lane artifact directory and `SU_RELEASE_ACCEPTANCE_LANE` to the exact lane. For clean Git input leave archive/composition variables unset. For qualified merged-candidate archive input set only `SU_RELEASE_ACCEPTANCE_SOURCE_PROVENANCE` to its retained verified receipt, never composition overrides.
4. In EACH environment run the explicit pytest command above or the equivalent supported standalone runner. Existing CI's `-k pure -m 'not integration'` does not select this group. Both invocations must actually execute all22 code cells in order and exit0; collection or exclusion does not count.
5. Retain the entire per-lane run directory on success AND failure: manifest/verdict, executed notebook, dependencies, stdout/stderr/kernel startup logs and real output files with hashes. Retain candidate/build/wheel identities too. Upload these artifacts when using CI. Keep existing required CI; any later durable automation follows normal workflow ownership/review without an admin bypass or synthetic success.

Exact-candidate BOTH-lane execution and existing required CI remain unearned until their actual receipts exist. Optional durable CI implementation is a follow-up, not a substitute for execution or an additional universal publication veto.

### Strict merged-candidate API-archive runtime input

Retain actual GitHub API acquisition, merge/integration, commit-SHA and commit-tree receipts for a REAL MERGED integrated candidate containing the intended library repairs and this notebook delivery. Recompute the entire extracted source tree and require exact equality with that API commit tree; no overlays or source edits are permitted. Record the actual input kind as API archive, never as a clean Git checkout. Build the wheel from that exact source and retain every wheel/source/installed file-set and byte comparison. BOTH isolated lanes must use the SAME actual candidate SHA, tree and wheel bytes, execute all22 cells in order with exit0, and retain complete per-lane manifests and artifacts. Actual existing required CI and normal PR/release/tag/publisher gates remain unchanged.

This is runtime-input policy only, not approval to use an archive as canonical fingerprint/v2/Git evidence, repair a refused bootstrap, retry another rejected unit or bypass ordinary provider/Task admission. Base-only archives, component/null-SHA compositions and the historical own404/critic887/test-only56a5 diagnostics are not relabeled. Acquisition must be normally admitted; stop any specific refusal.

## Evidence and interpretation

Retain every executed notebook, per-cell failures/counts, manifest, complete dependency versions, import origin, runner and wheel hashes, installed/source/wheel member comparisons, stdout/stderr/startup logs and output hashes. The final notebook cell means only "reached end". Any failed, empty, unexecuted or out-of-order cell fails the runner, even if later cells pass. Keep executed output outside committed notebooks.

Current issue #1422 supplies the mathematical correctness criteria. Strict >30-day default aging and the inclusive ±1pp OLS band are #1826 design pins, not assertions that #1422 chose those thresholds. #1824, #1826 and #1801 components are separate source identities until actual integration. A passing local composition never turns a failing baseline green retroactively.

## Governance

```sh
python scripts/check_notebook_inventory.py --check --require-all-live-governed
python scripts/check_notebook_capability_coverage.py --check
python -I -m pytest -o addopts='' tests/test_notebook_hygiene.py tests/test_release_seams_source.py tests/test_release_seams_bridge.py
```

The source is registered in `RE_WRITTEN`, the explicit `release_acceptance` execution group, and the geo/data/analytics capability inventory. Existing groups and assertions are unchanged. No library-core file is part of this delivery patch.
