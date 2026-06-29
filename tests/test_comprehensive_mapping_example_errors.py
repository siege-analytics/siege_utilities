"""Error-path coverage (SU-4b) for reporting.examples.comprehensive_mapping_example.

create_comprehensive_powerpoint documents "raises on failure"; an invalid
(empty) maps_dict drives the failure through its except-and-re-raise handler.
"""
import pytest
from siege_utilities.reporting.examples.comprehensive_mapping_example import (
    create_comprehensive_powerpoint,
)


def test_create_comprehensive_powerpoint_raises_on_invalid_maps_dict():
    with pytest.raises(Exception):
        create_comprehensive_powerpoint({})
