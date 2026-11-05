# Self-review -- pin duckdb below 2.0 (#1861)

Clean-history re-cut of #1863 (force-pushed once) as an ordinary reviewed
successor from develop. DuckDB 2.0 adaptation is tracked separately (#1862).

## Assumptions

Domain(s): software engineering / packaging (a dependency version bound; no library code changes).
Goal source: #1861 and the merge-actor preflight (both outside this diff); change content taken from #1863 via `gh pr diff 1863`.
Base: a fresh branch from live `develop` (dc7d3f76), verified before branching.
Working as: software engineer (Junior) and tech lead (Lead); both reviews are below.

## Peer review

- Change: in `pyproject.toml`, the `performance` and `all` extras move from
  `duckdb>=0.7.0` to `duckdb>=0.7.0,<2.0`, each with a two-line rationale
  comment. Both dependency declarations are bounded; no other file in the code
  diff. CHANGELOG.md gains a `[4.1.0]` Fixed entry, and this artifact is
  committed in-repo (the Self-Review-Source trailer points here, not outside
  the repo).
- Diff fidelity: the pyproject hunks match #1863 (index `d5e48f45..63148033`).
- Packaging truth: the lower bound is unchanged; the upper bound is added in
  both extras; the extras groups do not overlap for duckdb.
- Verification: the DuckDB-sensitive class-hardening and engine suite runs 190
  passing under the installed duckdb 1.4.4 (inside the new bound). The bound
  specifier admits 0.7.0 / 1.4.4 / 1.9.9 and excludes 0.6.9 / 2.0.0 / 2.1.0.
  The DuckDB 2.0 red vs 1.5.x green matrix is established by #1863's CI run
  41002770455 (baseline evidence only; not re-run here).
- Exact-head CI (run 41974132207, head 52c72bb6) installed duckdb 1.5.6 and
  showed no class-hardening failure, but 3.13 and 3.14 each failed the three
  CA/HI/OR cases of
  `test_population_service_resilience.py::test_command_skips_unpublished_vtd_without_error`:
  Django's `gis.W001` system check (hosted GDAL 3.8.4, below 3.9) writes into
  the command stderr the test asserts is empty. The test file is the same on
  develop. Fix (test-only): the test passes `--skip-checks`, so its strict
  `stderr == ""` assertion covers only command-owned output, and a fixture
  registers a stand-in system-check warning so the case is deterministic on any
  GDAL. `gis.W001` is not silenced in settings, and the workflow is unchanged.

## Lead review

In packaging: the bound closes the risk that a DuckDB 2.0 install silently
destabilizes the class-hardening suite (DuckDB 2.0 changes tokenizer byte
offsets and prepared-statement result metadata). Approach fit: an additive
upper bound is the lowest-blast-radius fix and touches no runtime code path.
Blast radius: the two extras only. Sequencing: lands on develop via ordinary
review, superseding the force-pushed #1863, which is left open for the merge
owner to close. No findings.

On the system-check test fix: skipping checks in one command test narrows what
that assertion observes. It does not hide a security warning from users, and
the remaining command tests still run system checks. Scope stays test-only.

## Test plan

- DuckDB-sensitive class-hardening and engine suite under duckdb 1.4.4 (within
  the new bound): 190 passed (test_round5..9_class_hardening,
  test_final_hardening_consensus, test_dataframe_engine,
  test_duckdb_read_spatial_1380, test_boundary_engine).
- Bound specifier check: `>=0.7.0,<2.0` admits 0.7.0 / 1.4.4 / 1.9.9 and
  excludes 0.6.9 / 2.0.0 / 2.1.0.
- DuckDB 2.0 red vs 1.5.x green: established by #1863 CI run 41002770455
  (baseline evidence; not re-run here).
- No library code changed and no new `.py`, so syntax and import gates are N/A
  beyond the runs above.
- `tests/test_population_service_resilience.py` with Homebrew GDAL, Django 5.2.14 and
  the CI Django settings: with the stand-in warning fixture and without
  `--skip-checks`, the three CA/HI/OR cases fail (3 failed, 7 passed, the CI
  shape); with `--skip-checks`, 10 passed.
