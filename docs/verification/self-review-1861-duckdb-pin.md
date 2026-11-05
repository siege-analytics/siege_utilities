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

## Lead review

In packaging: the bound closes the risk that a DuckDB 2.0 install silently
destabilizes the class-hardening suite (DuckDB 2.0 changes tokenizer byte
offsets and prepared-statement result metadata). Approach fit: an additive
upper bound is the lowest-blast-radius fix and touches no runtime code path.
Blast radius: the two extras only. Sequencing: lands on develop via ordinary
review, superseding the force-pushed #1863, which is left open for the merge
owner to close. No findings.

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
