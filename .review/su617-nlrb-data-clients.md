# Self-Review: SU#617 — NLRB Data Source Clients

**Domain:** software engineering
**Geospatial cross-cut:** yes (NLRB region extraction from case numbers)
**Trivial-against-state:** no — new provider module with 3 clients + facade

## Assumptions

1. data.gov XML schema uses camelCase or snake_case field names — parser handles both.
2. labordata GitHub repo CSV files are at `/data/{cases,elections,charges}.csv` under main branch.
3. NxGen HTML scraping is best-effort; marked fragile. Uses stdlib HTMLParser to avoid BeautifulSoup dependency.
4. `requests` is lazy-imported — clients accept an injected `session` parameter for testability without requests installed.
5. Source priority for deduplication: labordata > data.gov > NxGen (labordata has cleanest data).

## Peer Review (Junior)

- NLRBCaseRecord: 3 tests (minimal, full, to_dict)
- ElectionRecord: 1 test
- ULPRecord: 1 test
- NLRBFetchResult: 3 tests (empty, errors, total_records)
- CaseType enum: 2 tests
- Helpers: 8 date parsing, 6 safe_int, 5 region extraction
- NLRBDatagovClient: 7 tests (single case, empty, HTTP error, malformed XML, missing number, alternate fields, multiple)
- NLRBLabordataClient: 6 tests (cases, elections, ULP charges, failure, empty number, alternate fields)
- NLRBNxGenClient: 3 tests (HTTP error, empty HTML, table parsing)
- NLRBDataClient facade: 7 tests (dedup, priority, elections, errors, nxgen toggle, priority order)
- 52 total tests passing

## Lead Review (Adversarial)

- **Q: Why catch `Exception` instead of `requests.RequestException`?** A: Because `requests` is lazy-imported and may not be available. The `session` parameter allows mock injection in tests. In production with requests installed, the broad catch still works correctly.
- **Q: NxGen HTML parser assumes specific CSS classes — what if they change?** A: That's exactly why the client is marked fragile. The parser returns an empty list on failure with a warning log. No exception propagation.
- **Q: Why not use pandas for CSV parsing?** A: stdlib csv.DictReader has zero dependencies. The records are parsed into dataclasses, not DataFrames. DataFrame export is WS4-T2's concern.

## Quantified Claims

- 52 new tests, all passing
- ~350 lines of implementation (records, helpers, 3 clients, facade)
- Zero new dependencies (requests is lazy, HTML parsing uses stdlib)
