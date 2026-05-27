# Self-Review: SU#618 — NLRB Data Models

**Domain:** software engineering
**Geospatial cross-cut:** yes (FK to NLRBRegion spatial boundary)
**Trivial-against-state:** no — 4 new Django models + export module

## Assumptions

1. NLRB case models are non-spatial (no geometry) — they link to NLRBRegion via FK.
2. Dataclass equivalents already exist in nlrb_clients.py (NLRBCaseRecord, ElectionRecord, ULPRecord) from SU#617. Models provide to_record()/from_record() converters.
3. BargainingUnit stores soc_codes as JSONField (list of strings) since a unit can map to multiple SOC codes.
4. DataFrame export uses lazy pandas import — no hard dependency.

## Peer Review (Junior)

- NLRBCase model: 10 tests (import, fields, FK, str, from_record, to_record)
- ElectionResult model: 3 tests
- ULPCharge model: 3 tests
- BargainingUnit model: 3 tests
- DataFrame export: 6 tests (cases, elections, ULP, empty, fetch_result)
- 25 total tests (skip when Django/pandas unavailable, matching existing pattern)

## Lead Review (Adversarial)

- **Q: Why separate nlrb_cases.py from federal.py?** A: federal.py has spatial boundary models (TemporalBoundary subclasses). Case data is non-spatial — plain Django models. Different base class, different concerns.
- **Q: Why not store case_type as a Django choice field with CaseType enum?** A: NLRB introduces new case type codes occasionally. CharField is more flexible than constraining to a known set.
- **Q: Why dual region/region_number fields?** A: region_number is extracted from case number (always available). region FK links to the NLRBRegion spatial model (only populated when region boundaries exist in DB).

## Quantified Claims

- 25 new tests, all collected (skipped in non-Django env, matching existing pattern)
- 4 Django models: NLRBCase, ElectionResult, ULPCharge, BargainingUnit
- 1 export module with 4 functions
- ~250 lines of model code + ~75 lines of export code
