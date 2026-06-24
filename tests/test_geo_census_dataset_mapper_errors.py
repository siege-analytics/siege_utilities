"""Error-path coverage (SU-4b) for siege_utilities.geo.census_dataset_mapper.

Exercises the ``except ValueError`` guard in _score_dataset_for_use_case:
an unparseable time_period must be absorbed during scoring rather than
propagating out of get_best_dataset_for_use_case.
"""

from siege_utilities.config.census_registry import GeographyLevel
from siege_utilities.geo.census_dataset_mapper import CensusDatasetMapper


def test_get_best_dataset_handles_invalid_time_period_format():
    mapper = CensusDatasetMapper()
    # "not-a-date" makes strptime() raise ValueError inside scoring; the
    # except must swallow it so the call still returns ranked datasets.
    result = mapper.get_best_dataset_for_use_case(
        "poverty analysis", GeographyLevel.STATE, time_period="not-a-date"
    )
    assert isinstance(result, list)
