## Assumptions
Domain(s): geo, boundary providers
Geospatial cross-cut: yes
Goal source: ticket #1044
Goal source verification: Codex hostile review session 260619-apt-sequoia, findings S2-1/2/3
Plan reference: design note on #1044
Pre-author-inventory: siege_utilities/geo/providers/boundary_providers.py (existing file)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Three findings in the ticket, but two are already handled:
- `get_geographic_boundaries()` — already deprecated with DeprecationWarning, replacement exists (fetch_geographic_boundaries)
- `get_census_boundaries()` — already deprecated since v3.16.0

The only actionable finding is RDHProvider.get_boundary() returning None when no datasets found, while CensusTIGERProvider raises BoundaryFetchError. The ABC contract says GeoDataFrame return, not Optional[GeoDataFrame].

## Trivial-pre-mortem declaration
Single line change in RDHProvider.get_boundary(). No external callers check for None from this provider — grep confirms all references are re-exports or the definition itself.

## Peer review

### Syntax check
Python: `ast.parse()` passes.

### Build validation
No build changes.

## Lead review

### Phase A: Structural coherence
Changed `return None` to `raise BoundaryFetchError(...)` at boundary_providers.py:454-459. Now consistent with CensusTIGERProvider (line 132) and the ABC contract.

### Phase B: Did this close the gap?
- [x] RDH raises BoundaryFetchError on no datasets (was: return None)
- [x] Error message includes level, state, year, format for diagnostics
- [x] Consistent with CensusTIGERProvider behavior
- [x] No external callers checked for None from this path
- [x] AST parse clean

## Findings
No findings.

## Evidence-predates-work
Artifact: plans/self-review-1044.md
