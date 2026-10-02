"""Root-import contracts for the sample-data registry constants.

SAMPLE_DATASETS, CENSUS_SAMPLES and SYNTHETIC_SAMPLES are canonical
(root-registered) public symbols the per-symbol coverage scanner (epic #1199)
reported as direct_coverage=False. Pin the public registry contract and the
self-consistency between the three through the root ``siege_utilities``
namespace.
"""

from siege_utilities import SAMPLE_DATASETS
from siege_utilities import CENSUS_SAMPLES
from siege_utilities import SYNTHETIC_SAMPLES


def test_census_and_synthetic_membership_is_exact():
    assert CENSUS_SAMPLES == [
        "census_tract_sample",
        "census_county_sample",
        "metropolitan_sample",
    ]
    assert SYNTHETIC_SAMPLES == [
        "synthetic_population",
        "synthetic_businesses",
        "synthetic_housing",
    ]
    # Canonical ordering is stable: the primary sample of each partition is
    # listed first.
    assert CENSUS_SAMPLES.index("census_tract_sample") == 0
    assert SYNTHETIC_SAMPLES.index("synthetic_population") == 0


def test_sample_datasets_catalog_matches_partitions():
    assert isinstance(SAMPLE_DATASETS, dict)
    # The catalog keyset is exactly the census + synthetic partitions.
    assert set(SAMPLE_DATASETS) == set(CENSUS_SAMPLES) | set(SYNTHETIC_SAMPLES)
    # census and synthetic are disjoint partitions of the catalog.
    assert not (set(CENSUS_SAMPLES) & set(SYNTHETIC_SAMPLES))


def test_every_catalog_entry_has_a_description():
    for name, meta in SAMPLE_DATASETS.items():
        assert isinstance(meta, dict), name
        assert meta.get("description"), name
