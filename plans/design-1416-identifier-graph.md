---
ticket_refs:
  - siege-analytics/siege_utilities#1416: design note for gaps A and B (operator ruling 2026-11-05, do not ship debt)
---

# Design: one corroborating key suffices (B) and normalized phone/address keys (A)

Ticket: #1416 done-when, "A merge requires at least one corroborating key (email, phone or normalized address), or it is emitted as a candidate pair for review with a confidence below 1.0."

## Current behavior at `f71e3cd9`

- A record's identifier seed is `json([normalized_name, {column: value, ...}])` over every available identifier column. Records merge only when the name and the entire available identifier set agree.
- Gap B: `A{email=x, phone=p}` and `B{email=x}` share a corroborating email but do not merge.
- Gap A: identifier values are only stripped and lowercased, so `(512) 555-0100` and `512-555-0100` differ, and there is no address key at all.

## A: normalized keys

No phone or address text normalizer exists in `siege_utilities`. `geo/providers/batch_geocoder.normalize_addresses` only reshapes geocoder input into `AddressInput`; it does not canonicalize text. So two frozen, versioned normalizers are added beside `normalize_name_v1` in `siege_utilities/identifiers/normalize.py`, following that module's pinning rule:

- `normalize_phone_v1(value)`: digits only. A leading US country code `1` is dropped when the result has 11 digits. Results with fewer than 7 digits return `""`, so a fragment such as an extension number is never treated as identity evidence.
- `normalize_phone_v1(value)` also drops a trailing extension (`x12`, `ext. 12`) before taking digits.
- `normalize_address_v1(street, city, state, postal_code)` normalizes each component separately: NFKD with combining marks removed, casefold, punctuation to spaces, whitespace collapsed. The street gets USPS street-suffix and directional abbreviations, and all unit designators (`#`, `apt`, `suite`, `unit`, ...) become `unit`. Only the state field maps state names to postal codes, so "West Virginia Ave" stays a street. Only the postal field is reduced to five digits, zero-padded, so a house number is never read as a ZIP and a numeric ZIP keeps its leading zero. Components are joined with `" | "`. An empty street returns `""`.

  (Revised after hostile review. An earlier draft took a one-line string and applied state and ZIP rules anywhere in it.)

In `crm_dedup_pipeline`:

- `identifier_columns` defaults to `["email", "phone"]`.
- A new `identifier_normalizers` mapping defaults to `{"phone": normalize_phone_v1}`. Any other column keeps the existing strip-and-casefold.
- A new `address_columns` parameter defaults to `["address_street", "address_city", "address_state", "address_postal_code"]`, matching `CRMContact.to_dataframe`. Its parts are joined and normalized into one `address` identifier. That identifier exists only when the street part is present, because city, state or ZIP alone is shared by far too many people to be identity evidence.
- Missing columns are ignored, as before. Passing `[]` for both disables identifier merging.

## B: transitive grouping with guards

Records that have at least one identifier become nodes. An edge joins two records when they share:

1. the same normalized name (exact equality, the name guard), and
2. at least one identifier column with an equal normalized value.

Union-find merges along edges. Determinism:

- Edges are processed in sorted key order `(normalized_name, column, value)`.
- Members within a key are sorted by `(record_seed, source_system, source_id)`.
- Each member is tried against every earlier member of the key. Trying only the first member let one conflicting record keep two compatible ones apart; the hostile review found this.
- Each component's `canonical_id` is `uuid5(namespace, min(member record seeds))`. That ID can change when a later run adds a member with a smaller seed, so persisted merge tables should be regenerated rather than appended to.

Row order does not change the result, and a singleton or a fully agreeing group keeps the ID it had before this change.

### False-merge risk and the guards

The risk the operator named is a shared household email, or a reused phone, chaining distinct people.

1. **Name guard (per edge).** Records only connect when their normalized names are equal, so `Maria Garcia` and `Jose Garcia` sharing a household email never connect, directly or through a chain. `normalize_name_v1` keeps generational suffixes (`john smith jr` ≠ `john smith`), so a father and son are kept apart when the suffix is present.
2. **Conflict guard: email only (operator ruling 2026-11-05, final).** Each component keeps at most one normalized email. A union is refused only when both components hold an email and the emails differ. Two same-name people with different emails who share a household phone therefore stay apart, and A–B–C chains whose ends hold different emails are cut. Phone and address link but never block, because one person often has several. The draft guard covered every column; the hostile review showed it split real equal-email matches (a different phone, a partial address, a numeric ZIP, `#2` vs `Apt 2`), so the operator chose email-only.
3. **Address key requires a street.** City, state or ZIP alone never links records.

Refused unions are counted and logged as a warning. The records keep separate `canonical_id` values and still share `name_candidate_id`, so they surface for human review.

### Review candidates and confidence (operator ruling 2026-11-05)

- An identifier-backed record gets `match_confidence` 1.0 when it has no unresolved namesake.
- It gets 0.75 when a same-name record sits in another group *without* an email conflict. It could be the same person, so the pair is a review candidate; an example is Grace Hopper with only an email and Grace Hopper with only an address.
- Groups kept apart *by* an email conflict are probably different people, so they keep 1.0. They still share `name_candidate_id` so a reviewer can see them.
- Name-only rows keep 0.5 or 0.25.

### Residual risk (stated, not hidden)

- Same-name people with no email (or the same email) who share a phone or address merge. An example is a father and son both recorded as `John Smith` with no suffix at one household. `CRMContact` has no suffix field.
- One person recorded with two different emails is split. That is the safe direction, and the records surface through `name_candidate_id`.
- The name guard keeps people with different names apart even through chains.
- No component-size cap is added, because any threshold would be arbitrary.
- Callers who want the previous email-only corroboration pass `identifier_columns=["email"], address_columns=[]`, which is tested.

## Tests

The red-first set fails at `f71e3cd9`. Controls such as row-order stability, distinct addresses, street-less addresses and namesakes sharing nothing also pass at `f71e3cd9`; they guard against regressions and are labeled as controls in the self-review.

- A–B by email plus B–C by phone (same name) gives one `canonical_id`.
- `A{email, phone}` with `B{email}` merges.
- Same-name people sharing nothing stay split. Different-name people sharing an email stay split. Same-name people with conflicting emails who share a phone stay split, the refusal is logged, and both keep 1.0. An A–B–C chain whose ends hold different emails is cut.
- An equal email still merges with a different phone, a partial address, a text vs numeric ZIP, or `#2` vs `Apt 2` (all merged at `f71e3cd9`).
- Unmerged namesakes without an email conflict are both 0.75.
- IDs are identical across a shuffled row order.
- Phone: `(512) 555-0100` == `512-555-0100` == `+1 512 555 0100`; short fragments are ignored.
- Address variants match (`100 Congress Avenue, Austin, Texas 78701-1234` vs `100 congress ave austin tx 78701`). Distinct addresses do not (`101 ...`, `N` vs `S Main St`). City/state/ZIP without a street is not an identifier.
