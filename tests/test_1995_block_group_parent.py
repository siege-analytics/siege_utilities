"""A block GEOID's block group is its first 12 digits (refs #1995)."""

import pytest

from siege_utilities.geo import geoid_utils as gu

BLOCK = gu.construct_geoid(geography="block", state="01", county="003",
                           tract="010800", block_group="1", block="1011")


def test_block_geoid_fixture_is_the_issue_example():
    assert BLOCK == "010030108001011"


def test_block_group_is_the_parent_of_a_block():
    assert gu.extract_parent_geoid(BLOCK, "block", "block_group") == "010030108001"


def test_block_group_is_the_first_digit_of_the_block_number():
    # Block 2034 has distinct digits, so only its first digit (2) gives 060371011002.
    assert gu.extract_parent_geoid("060371011002034", "block", "block_group") == "060371011002"


def test_other_block_parents_are_unchanged():
    assert gu.extract_parent_geoid(BLOCK, "block", "tract") == "01003010800"
    assert gu.extract_parent_geoid(BLOCK, "block", "county") == "01003"
    assert gu.extract_parent_geoid(BLOCK, "block", "state") == "01"


@pytest.mark.parametrize("geoid, child", [
    ("01003010800", "tract"),
    ("010030108001", "block_group"),
])
def test_block_group_parent_of_a_non_block_raises(geoid, child):
    with pytest.raises(ValueError, match="block_group"):
        gu.extract_parent_geoid(geoid, child, "block_group")
