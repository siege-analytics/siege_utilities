"""
External spatial data sources — one folder, one shape per provider.

This is the canonical home for every module that fetches spatial data
from an external source. Housed here under ELE-2438 (D3) as the first
step toward a unified provider interface.

Current providers:

- :mod:`boundary_providers` — CensusTIGER, GADM, RDH boundary retrieval
- :mod:`census_geocoder` — US Census geocoder (address → FIPS)
- :mod:`nces_download` — NCES school-district and locale boundaries
- :mod:`redistricting_data_hub` — RDH API client (precincts, plans, CVAP,
  PL 94-171, compactness metrics)

Not yet migrated (planned for the interface-unification follow-up epic):

- ``geo/spatial_data.py`` — ``CensusDataSource`` + ``GovernmentDataSource`` +
  ``OpenStreetMapDataSource``. File is 1,500+ lines mixing concerns; will be
  split as part of the provider-interface work.
- ``geo/census/`` subpackage — Census API client. Moves once the variable-registry
  split stabilizes.

The "structural moves only" scope of ELE-2438 does **not** unify these
providers behind a common ``fetch`` / ``accepts`` interface — that's a
separate, larger effort.
"""
