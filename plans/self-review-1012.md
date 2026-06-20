---
ticket: "#1012"
scope: "connectors/_models.py, connectors/__init__.py"
---

# Self-Review — #1012 Shared CRM Data Models

## Junior Assessment

Added 5 Pydantic v2 models to `connectors/_models.py`:
- `CRMAddress` — shared nested address type
- `CRMContact` — person record with address flattening
- `CRMAccount` — company record with Decimal revenue
- `CRMOpportunity` — deal record with Decimal amount, date fields
- `CRMActivity` — activity/task/event record

Updated `connectors/__init__.py` with PEP 562 lazy loading for the 5 models.

Verified: imports work, `to_dataframe()` flattens correctly, Decimal→float
conversion in DataFrame output, lazy import from package init resolves correctly.

## Lead Assessment

**SU-1 compliance:** Models use `extra="forbid"` — unknown fields raise, no
silent swallowing. `to_dataframe()` returns meaningful DataFrames, never
empty on valid input. Empty list input returns an empty DataFrame with correct
columns — this is correct behavior (empty input, empty output), not an SU-1
violation.

**Decimal handling:** `revenue` and `amount` are `Decimal` in the model but
converted to `float` in `to_dataframe()` output. This is intentional — pandas
doesn't natively support Decimal columns, and downstream numeric operations
(groupby-sum, choropleth binning) expect float. The Decimal→float conversion
happens at the DataFrame boundary, not in the model itself.

**Lazy loading:** Follows the established PEP 562 pattern from CLAUDE.md.
`__getattr__` raises `AttributeError` for unknown names — no silent stubs.
First access imports and caches via `globals().update()`.

**No notebook impact:** No existing notebooks reference `connectors/`.

## Trivial-investigation declaration

Pure data models with no side effects, no I/O, no external dependencies
beyond pydantic and pandas (both already in core deps). The models define
shapes — they don't connect to anything. The only verification needed was
that `ConnectorProtocol` exists (verified against origin/develop) and that
the Pydantic pattern matches `config/models/` conventions (verified by
reading `person.py`).

## Trivial pre-mortem declaration

Risk profile is minimal: new file, no changes to existing contracts, no
behavioral changes to existing code. The `__init__.py` change adds names
to `__all__` and a `__getattr__` — existing imports are unaffected because
the protocol types are still eagerly imported at the top.
