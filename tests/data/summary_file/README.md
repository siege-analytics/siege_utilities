# ACS table-based Summary File slices

Headers and selected complete rows inspected from Census on 2026-10-11:

- https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/1YRData/acsdt1y2022-b01003.dat
- https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/1YRData/acsdt1y2022-b19013.dat

The web reader exposed the raw text (its cache reported five days old).
Shell download was unavailable because DNS was blocked. These fixtures copy
the observed header and rows verbatim, retaining source order. They contain
nation, Alabama, California, Baldwin County, Alameda County, Los Angeles
County and San Diego County, plus geographic components that must be excluded.

Confirmed headers:

```text
GEO_ID|B01003_E001|B01003_M001
GEO_ID|B19013_E001|B19013_M001
```

The seven-character whole-geography prefixes are `0400000` for states and
`0500000` for counties. `04000A0US06` is a component of California and must not
be included when requesting the state total. B01003's national row is
`0100000US|333287562|-555555555`; its MOE sentinel must become NaN.

Tests serve these bytes through a mocked HTTP boundary. Synthetic rows used
for tract/block-group/place and other sentinel edge cases are marked in the
test code, and are not represented here as Census observations. No geography
lookup is downloaded by the tests. `NAME` enrichment is deferred; the bulk
result retains an object column of missing names.
