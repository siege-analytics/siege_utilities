# Self-review: PR #1806 Snowflake auto-create dtype mapping (#1484)

## Assumptions

Working as: software engineer (Junior) and tech lead (Lead).
Goal source: ticket #1484 item 1, within the scope set by the maintainer decision recorded at https://github.com/siege-analytics/siege_utilities/pull/1806#issuecomment-6258234574 (dtype mapping only; context restoration rides with #1421).
Domain(s): data engineering (pandas dtypes, Snowflake DDL).
Base: develop `2deb6a1f`, merged additively for an actual CHANGELOG conflict.

## Scope correction (this round)

Commit `9bfbb6e9` went beyond that decision. It added per-call session-context snapshot and restore, including new quoted `USE` statements in the restore path and a `_quote_reported_name` helper, plus `write_pandas(use_logical_type=True)` with an old-SDK refusal for datetime frames. The owner's current-head note at https://github.com/siege-analytics/siege_utilities/issues/1484#issuecomment-6649267710 had asked for both items to be stated as deferred.

This round returns the PR to its decided scope, additively, with no history rewrite:
- `siege_utilities/analytics/snowflake_connector.py` is restored to develop's version, and then only `_map_pandas_to_snowflake_type` is rewritten.
- `git diff develop -- siege_utilities/analytics/snowflake_connector.py` shows hunks only inside that function. Every `USE DATABASE`/`USE SCHEMA`/`DROP`/`DESCRIBE` line is byte-identical to develop.
- The context and logical-type tests are removed, together with that code. The test file is renamed to `tests/test_1484_snowflake_dtype_mapping.py`.

Net diff against develop: the mapping function, its test file, the CHANGELOG entry, and this record.

## Develop merge

The only conflict was in CHANGELOG `[4.1.0]` Fixed, where the #1484 entry and develop's #1475, #1661, #1439 and #1871 entries sat at the same position. Every develop line was kept, and no line was removed against either parent. No develop behaviour disagrees with this PR.

## Item 1: the mapping

The new mapping uses `pandas.api.types` predicates instead of name matching:
- categoricals map to the type of their categories;
- `is_bool_dtype` gives `BOOLEAN`;
- `is_integer_dtype` gives `NUMBER(38,0)`;
- `is_float_dtype` gives `FLOAT`;
- `DatetimeTZDtype` gives `TIMESTAMP_TZ`;
- `is_datetime64_dtype` gives `TIMESTAMP_NTZ`;
- `is_timedelta64_dtype` gives `VARCHAR`;
- everything else gives `VARCHAR`.

Timedelta stays `VARCHAR`, as in v4.0.0, because Snowflake has no `INTERVAL` column type. There is no claim of a native interval type or of a proven duration round-trip. The mapper only chooses the column type; it does not serialize values. Callers who need durations in a usable form serialize them before upload (for example `.dt.total_seconds()`) or pre-create the table and pass `auto_create_table=False`. How `write_pandas` loads durations is part of the deferred logical-type work (#1884).

Datetime scope (claim qualification after review). The tested datetime families are pandas `DatetimeTZDtype`, which maps to `TIMESTAMP_TZ`, and naive NumPy `datetime64`, which maps to `TIMESTAMP_NTZ`. Arrow-backed timestamp dtypes are not recognised by either the v4.0.0 mapper or this one: `Series.convert_dtypes(dtype_backend="pyarrow")` gives `timestamp[<unit>, tz=UTC][pyarrow]` or `timestamp[<unit>][pyarrow]`, with the unit following the source column (`us` under pandas 3.0.5), and both fall back to `VARCHAR(16777216)`, checked at this head. This is an unchanged, unsupported shape, not a new regression. No native Arrow loading or round-trip is claimed. The mapper's code is unchanged by this qualification: only the docstring changed, and a hash of the function's AST without its docstring is identical before and after.

| Dtype | v4.0.0 | Now | Test |
|---|---|---|---|
| `Int64`, `UInt8` (nullable) | `VARCHAR` | `NUMBER(38,0)` | `test_mapping_corrects_v400_misclassified_dtypes` |
| `Float64` (nullable) | `VARCHAR` | `FLOAT` | same |
| `datetime64[ns, UTC]`, `datetime64[ns, America/Chicago]` | `TIMESTAMP_NTZ` | `TIMESTAMP_TZ` | same |
| `category` of int / float / tz datetime | `VARCHAR` | `NUMBER(38,0)` / `FLOAT` / `TIMESTAMP_TZ` | same |
| `interval[int64]` (pandas `IntervalDtype`, not a duration) | `NUMBER(38,0)`: the name `interval[int64, right]` contains "int" | `VARCHAR` | same |
| `timedelta64[ns]` (an actual duration) | `VARCHAR` | `VARCHAR` (unchanged) | `test_mapping_keeps_v400_types_that_were_already_right` |
| `int64`, `uint8`, `float64`, `bool`, `boolean`, `datetime64[ns]`, `timedelta64[ns]`, `object`, `string`, string categories, `period[M]` | unchanged | unchanged | `test_mapping_keeps_v400_types_that_were_already_right` |
| CREATE TABLE built from an `Int64` and a tz-aware column | `VARCHAR`, `TIMESTAMP_NTZ` | `NUMBER(38,0)`, `TIMESTAMP_TZ` | `test_auto_create_uses_the_mapped_types` |

Red at v4.0.0: v4.0.0's exact `_map_pandas_to_snowflake_type` source was extracted from the tag and run in place of the new method, in memory. The 9 corrected cases and the auto-create test fail (10); the 11 unchanged cases pass. At the tip, all 21 pass.

## #1484 acceptance items

| Item | Status |
|---|---|
| 1. Mapping uses `pd.api.types` predicates; tz-aware maps to `TIMESTAMP_TZ` | DONE, as above |
| 2. `write_pandas` with `use_logical_type=True` where supported | DEFERRED: outside this PR's decided scope; a follow-up issue is proposed (Related: #1484, #1421) |
| 3. Scoped `USE` statements | DEFERRED to #1421 / draft #1821, per the maintainer decision |

The PR body therefore says `Refs #1484`, not `Fixes`.

## CHANGELOG

The entry moves to `[4.1.0]` `### BREAKING`. A v4.0.0 caller that auto-creates a table from the same frame gets different column types (`VARCHAR` becomes numeric, `TIMESTAMP_NTZ` becomes `TIMESTAMP_TZ`, `NUMBER` becomes `VARCHAR` for intervals). The Migration line says how to keep the old types.

## Lead review

In data engineering, the change is confined to one pure function that feeds `CREATE TABLE`. No I/O, quoting or session state changes. Existing tables are not altered.

## Test plan

Python 3.11.11:
- `tests/test_1484_snowflake_dtype_mapping.py`: 21 passed.
- With the Snowflake connector, consensus, SQL-safety, final-hardening, lazy-introspection, backward-compatibility, changelog and release-process suites: 332 passed, 1 skipped.

No live Snowflake account was used.

## Ticket-fitness exemption

writing-rules:4 exemption for each governing ticket. The #1398 epic is context only.

### #1484
- **Reason:** #1484 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the problem, the probe output and the done-when criteria are in the #1484 body. The owner's criteria are at issuecomment-6649267710, and the maintainer scope decision at PR comment 6258234574. Investigation, pre-mortem and Junior/Senior records are on the ticket at issuecomment-6651144188 and issuecomment-6651207952.
- **Falsification:** restore develop's `_map_pandas_to_snowflake_type` and 10 tests in `tests/test_1484_snowflake_dtype_mapping.py` go red. For example, `test_mapping_corrects_v400_misclassified_dtypes[Int64-NUMBER(38,0)]` fails because a nullable `Int64` column maps to `VARCHAR(16777216)`.

### #1421
- **Reason:** #1421 predates the canonical template.
- **Evidence:** this PR does not implement #1421. Per the maintainer decision, it keeps the existing quoting and leaves the choice to #1421. Its tie to #1421 is that it must not change the quoted `USE`/`DROP`/`DESCRIBE` lines.
- **Falsification:** if this PR altered the #1421 quoting convention, `tests/test_final_hardening_consensus.py::test_snowflake_get_table_info_quotes_identifier` would go red. It passes, and `git diff develop` shows no change outside the mapping function.
