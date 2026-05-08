# WKLS (Well Known Locations) — license attribution

`siege_utilities` integrates the [wkls](https://github.com/wherobots/wkls)
Python package as the default global gazetteer backend (`[wkls]` extra).

## Code license

WKLS is released under the **Apache License 2.0**. See the upstream
repository for the canonical text.

## Data license — Overture Maps Divisions

WKLS reads administrative-boundary geometry from the **Overture Maps
Foundation's Divisions theme**, hosted on AWS Open Data Registry. The
Divisions dataset is built from multiple upstream sources, each of
which carries its own attribution / share-alike requirements:

| Source | License | Obligation |
|---|---|---|
| OpenStreetMap contributors | **ODbL 1.0** | Attribution + **share-alike** on derivative datasets |
| geoBoundaries | CC BY 4.0 | Attribution |
| Esri Community Maps | CC BY 4.0 | Attribution |
| Land Information New Zealand (LINZ) | CC BY 4.0 | Attribution |

**What this means for siege_utilities consumers**:

1. **Attribution**: any work that ships geometry derived from WKLS
   queries should attribute Overture Maps Foundation and the upstream
   source(s) involved. The upstream `wkls` package preserves source
   attribution on each row — see the `source` column in result
   metadata.

2. **ODbL share-alike (OSM-derived rows)**: if your work creates a
   *derivative database* (a published dataset that includes
   OSM-derived geometries) you must license that derivative database
   under ODbL 1.0. *Producing reports / analyses that use the
   geometries internally is not creating a derivative database* — that
   distinction matters and is the part that bites people.

3. **No warranty**: as with any open-data source, geometries are
   community-curated and may contain errors. siege_utilities does not
   add a warranty layer; consumers verify against ground truth where
   it matters.

## See also

- Overture Maps license terms: <https://docs.overturemaps.org/attribution/>
- ODbL 1.0 full text: <https://opendatacommons.org/licenses/odbl/1-0/>
- WKLS GitHub: <https://github.com/wherobots/wkls>
