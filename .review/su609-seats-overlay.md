# Self-Review: SU#609 — Seats Overlay

**Domain:** software engineering
**Geospatial cross-cut:** yes (political geography, redistricting plans, seat containment)
**Trivial-against-state:** no — new overlay bridging redistricting models to place history

## Assumptions

1. SeatsOverlay implements PlaceHistoryOverlay and returns SeatAssignment timeline.
2. "Seat is identity, not geography" — returns Seat + Plan, not CD geometry.
3. Provider pattern (SeatsDataProvider ABC) decouples from Django for testability.
4. DictSeatsProvider enables full testing with time range and state_fips filtering.
5. Partial containment supported (containment_pct for geographies split across districts).
6. Multiple offices (US_HOUSE, STATE_UPPER, STATE_LOWER) coexist in results.

## Peer Review (Junior)

- SeatAssignment: 2 tests (defaults, fields)
- SeatsOverlayResult: 4 tests (empty, current districts, offices, for_office)
- DictSeatsProvider: 6 tests (empty, add/get, time range, state_fips, sorted, reverse range)
- SeatsOverlay: 9 tests (is_overlay, fetch, empty, no provider, multiple offices, state_fips, multi-plan, registry, partial containment)
- 21 total tests passing

## Lead Review (Adversarial)

- **Q: Why not query BoundaryIntersection directly?** A: BoundaryIntersection provides spatial overlap; PlanDistrictAssignment provides the Seat→Boundary mapping with plan context. The Django provider will join both. The overlay abstraction lets us test the timeline logic without either.
- **Q: How does this handle a GEOID that spans two districts?** A: Multiple SeatAssignments with containment_pct < 1.0. The test verifies partial containment sums to 1.0.

## Quantified Claims

- 21 new tests, all passing
- ~190 lines of implementation (result types + provider + overlay)
- ~190 lines of tests
