# Issue 1592, round 4 verification

## Current develop refresh (2026-10-15)

Rebased on fully green develop `097839bd` (#1649); `0015_precinct_result_identity`
now depends on `0014_district_geoid_charclass`, giving `siege_geo` one
migration leaf. Removed the branch's duplicate generic Python-matrix PostGIS
service: the shared marker-based live job selects all new ORM and SQL cases,
while generic CI retains pure parser/state checks. A temporary isolated
PostgreSQL 17/PostGIS 3.6 instance applied migrations through 0015 in order;
`makemigrations siege_geo --check --dry-run` reported no changes. Fresh
detached-committed-tree verification: 155 selected live cases passed (70 from
this PR), with zero selected DB skips; the one `msal` skip is an unrelated
optional module-level collection skip, explicitly exempted by the live-lane
JUnit policy. Generic selection passed 32 pure loader/model cases, 70 live
cases deselected. These results do not replace full current-head CI and
independent review before merge.

The loader identity is (state_fips, election_year, election_type,
precinct_id, office, district, party_code, candidate_name, data_source).
The amended, unmerged 0015 migration mirrors the model fields and
constraint, remains non-atomic, builds the unique index concurrently,
and reverses the constraint and added columns. Column creation and
backfill can be retried after an index-build failure. Existing known
party display labels backfill to letters; unmapped legacy labels remain
verbatim because a former OTHER value cannot reveal its original letter.
Those labels are replaced by raw letters on a source reload.

Column position 1 supplies G/S/R/C/P, positions 2-3 the requested year,
positions 4-6 the office, position 7 the raw party letter, and positions
8-10 the candidate code. H followed by two digits, or HAL, maps to house;
the two digits or AL are stored in district. USH is removed. Display
labels remain DEM/REP/LIB/GRN/IND for known letters; other letters are
preserved verbatim. Totals group by election type, year, and office code,
so districts and different elections do not share denominators.

Before implementation, the 2020 documentation and all ten source field
sets were inspected. County-plus-PRECINCT resolves VA and PA. GEOID20 is
preferred where available; county-plus-VTDST20 resolves WY. GA needs
county-plus-CTYSOSID because PRECINCT_I has missing values. WI needs
county-plus-MCD_FIPS-plus-WARDID. MT's COUNTYFP10-plus-SOSPRECINC resolves
identified precincts but the full file includes unidentifiable rows.
The general resolver also accepts GEOID10/GEOID, VTDST10, PRECINCT_I,
PREC_ID, VTDST, precinct_id, VTD, and PCTNUM. It checks missing values,
uniqueness, and stored length on the whole file before replacing data.
Component separators are escaped. No index-derived IDs are used.

The source inventory also exposed VA PolygonZ boundaries with Z=0.
The loader now stores their 2D footprints in the existing 2D PostGIS
field. CRS behavior is unchanged: callers supply EPSG:4326.

The source documentation was downloaded directly from Harvard Dataverse:
[2016](https://dataverse.harvard.edu/api/access/datafile/14304779),
[2018](https://dataverse.harvard.edu/api/access/datafile/14304790), and
[2020](https://dataverse.harvard.edu/api/access/datafile/14304792).
All 79, 24, and 28 unique House column names found in those documents,
respectively, pass the new parser. The 2018 Minnesota governor regression
uses DWAL, RJOH, LWEL, CWRI, and OWRI. The documentation identifies C as
recount; the loader stores the raw C code. Unmapped offices and malformed
same-year G/S/R/C/P columns still produce warnings.

The real-file probe used actual downloaded shapefiles, transformed to
EPSG:4326 to satisfy the loader contract, and the real ORM on an isolated
PostGIS instance. Only the network fetch was substituted. Every accepted
source vote was summed independently and compared with the stored sum
after both initial load and reload; row counts were also checked.

| State | Dataverse file ID | Precincts | Loaded columns | Rows | Source = first load = reload votes | Warned columns |
|---|---:|---:|---:|---:|---:|---:|
| AZ | 4864722 | 1489 | 5 | 7445 | 6739422 | 0 |
| DE | 4773531 | 434 | 16 | 6944 | 1975850 | 4 |
| GA | 11070054 | 2682 | 29 | 77778 | 19862734 | 6 |
| NH | 11070060 | 321 | 11 | 3531 | 2393007 | 0 |
| PA | 14304796 | 9157 | 7 | 64099 | 13717149 | 8 |
| RI | 11070053 | 423 | 10 | 4230 | 1012019 | 0 |
| VA | 11070061 | 2477 | 7 | 17339 | 8866473 | 0 |
| WI | 14304795 | 7093 | 13 | 92209 | 3298041 | 0 |
| WY | 4789404 | 481 | 13 | 6253 | 819594 | 0 |

GA's R21USS columns were separately loaded for election_year=2021 from
the 2020 file: 10,728 rows with election_type=R and the source vote sum.

MT (file ID 4773527, 666 source rows) is explicitly rejected before any
write. Three zero-vote rows have null SOSPRECINC and NAME=NA; two share
COUNTYFP10=029, the third has COUNTYFP10=047. There is no source key to
distinguish the two Flathead rows. The error names COUNTYFP10/SOSPRECINC
and the missing-or-blank identifiers. No invented IDs, dropped rows, or
silent success are used. A successful full MT load could not be confirmed
without a corrected source identity. Authenticated RDH network fetching
was not exercised; this change leaves the provider unchanged.

Verification used Python 3.11.11 at the requested interpreter path with
SIEGE_TEST_DB_HOST=127.0.0.1 and SIEGE_TEST_DB_PORT=55492. Commands:

```sh
python -m pytest tests/test_rdh_precinct_loader.py tests/test_redistricting_models.py tests/test_geo_migration_graph.py --no-cov -q
python -m django makemigrations siege_geo --check --dry-run
```

Final restored output:

```text
103 passed in 5.22s
No changes detected in app 'siege_geo'
```

All modified Python files parse. The severe flake8 check and lint ratchet
phases 1-4 pass. Existing round-1/2/3 coverage remains; the invented USH
fixture and OTHER expectations were updated to the corrected VEST contract.

For red-on-revert, the three production files were stashed, leaving only
the updated tests against HEAD 657e60f35e692e0b328c329e18dc961a0ff92685.
Pytest selected every added test name with -k and --no-cov. Output:

```text
28 failed, 47 deselected in 4.54s
House: assert 6 == 14
MN governor: IntegrityError, (27, 2018, 001, governor, OTHER, WRI, rdh)
Special/general Senate: assert 8 == 12
GEOID20 and other real ID columns: Could not identify a precinct identifier column
Cross-county PRECINCT: Duplicate precinct identifiers in RDH results
VA zero-Z boundary: Geometry has Z dimension but column does not
```

The stash was restored before the final 103-test green run. Added test
names below account for 28 parameterized cases:

- `test_county_qualifies_cross_county_duplicate_precincts`
- `test_duplicate_within_county_raises`
- `test_geoid_preferred_over_county_local_precinct_and_vtd`
- `test_georgia_missing_precinct_code_uses_county_sos_id`
- `test_identifier_separator_does_not_merge_components`
- `test_migration_backfills_legacy_party_without_guessing_unknown_letters`
- `test_missing_county_identifier_raises_and_preserves_snapshot`
- `test_mn_2018_governor_party_collision_preserves_raw_letters`
- `test_other_election_types_load_and_warn_for_skipped_columns`
- `test_overlong_statewide_identifier_raises`
- `test_party_display_label_is_not_part_of_identity`
- `test_real_house_columns_retain_district_and_reload_idempotently`
- `test_real_precinct_id_columns_resolve_statewide`
- `test_special_and_general_senate_load_distinctly`
- `test_vest_zero_z_boundary_loads_into_2d_postgis`
- `test_wisconsin_wards_include_municipality`

Notebook-impact scan: no notebook calls load_precinct_results or imports
the touched loader/model modules. This is an existing documentation gap;
there are no affected notebook call sites to update.
