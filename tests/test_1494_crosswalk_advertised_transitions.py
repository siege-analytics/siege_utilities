"""Regression coverage for advertised crosswalks and direction handling (#1494)."""

from unittest.mock import patch

import pandas as pd
import pytest

from siege_utilities.geo.crosswalk import crosswalk_processor
from siege_utilities.geo.crosswalk.crosswalk_client import CrosswalkClient
from siege_utilities.geo.crosswalk.relationship_types import CROSSWALK_FILE_PATTERNS
from siege_utilities.geo.timeseries.longitudinal_data import LongitudinalAligner


@pytest.fixture
def source_data():
    return pd.DataFrame({"GEOID": ["06001000100"], "population": [100.0]})


def test_every_advertised_crosswalk_has_a_file_pattern(tmp_path):
    available = CrosswalkClient(cache_dir=tmp_path).list_available_crosswalks()
    advertised = {
        (entry["geography_level"], entry["source_year"], entry["target_year"])
        for entry in available
    }
    serveable = {
        (geography, source, target)
        for geography, patterns in CROSSWALK_FILE_PATTERNS.items()
        for (source, target), pattern in patterns.items()
        if pattern
    }
    assert advertised == serveable


@pytest.mark.parametrize("geography, source, target", [
    ("tract", 2000, 2010),
    ("block_group", 2000, 2010),
    ("block", 2000, 2010),
    ("county", 2000, 2010),
    ("block", 2010, 2020),
])
def test_unavailable_crosswalk_rejected_before_cache_or_download(
    tmp_path, geography, source, target,
):
    client = CrosswalkClient(cache_dir=tmp_path)
    with patch.object(client, "_is_cache_valid", wraps=client._is_cache_valid) as cached, patch.object(
        client, "_download_crosswalk", wraps=client._download_crosswalk,
    ) as download:
        with pytest.raises(ValueError, match="not supported"):
            client.get_crosswalk(source, target, geography)
    cached.assert_not_called()
    download.assert_not_called()


@pytest.mark.parametrize("source, target", [(2020, 2010), (2010, 2000), (2020, 2000)])
def test_backward_normalization_rejected_before_crosswalk_lookup(source_data, source, target):
    message = "Backward normalization is not supported"
    with patch.object(
        crosswalk_processor, "get_crosswalk", wraps=crosswalk_processor.get_crosswalk,
    ) as get_crosswalk:
        with pytest.raises(ValueError, match=f"{message}: {source}->{target}"):
            crosswalk_processor.normalize_to_year(source_data, source, target)
    get_crosswalk.assert_not_called()
    assert message in crosswalk_processor.normalize_to_year.__doc__


def test_same_year_normalization_returns_a_copy(source_data):
    with patch.object(crosswalk_processor, "get_crosswalk") as get_crosswalk:
        result = crosswalk_processor.normalize_to_year(source_data, 2000, 2000)
    pd.testing.assert_frame_equal(result, source_data)
    assert result is not source_data
    get_crosswalk.assert_not_called()


def test_forward_normalization_uses_source_area_weights(source_data):
    crosswalk = pd.DataFrame({
        "source_geoid": ["06001000100", "06001000100"],
        "target_geoid": ["06001000101", "06001000102"],
        "area_weight": [0.25, 0.75],
    })
    with patch.object(crosswalk_processor, "get_crosswalk", return_value=crosswalk):
        result = crosswalk_processor.normalize_to_year(
            source_data, 2010, 2020, value_columns=["population"],
        )
    assert result.set_index("GEOID")["population"].to_dict() == {
        "06001000101": 25.0, "06001000102": 75.0,
    }


@pytest.mark.parametrize("source, target, geography", [
    (2020, 2010, "tract"),
    (2010, 2000, "tract"),
    (2020, 2000, "tract"),
    (2020, 2010, "block"),
])
def test_aligner_rejects_backward_paths_before_attempting_alignment(
    source_data, source, target, geography,
):
    aligner = LongitudinalAligner(target_vintage=target, geography=geography)
    with patch.object(aligner, "_apply_crosswalk_step") as crosswalk, patch.object(
        aligner, "_apply_areal_interpolation",
    ) as areal:
        with pytest.raises(ValueError, match=f"No supported crosswalk path from {source} to {target}"):
            aligner.align(source_data, source)
    crosswalk.assert_not_called()
    areal.assert_not_called()


@pytest.fixture
def reviewer_tract_data():
    # Four 2000-vintage tracts, as in the review reproducer.
    return pd.DataFrame({
        "GEOID": ["06001000100", "06001000201", "06001000202", "06001000300"],
        "pop": [100.0, 120.0, 80.0, 700.0],
    })


@pytest.mark.parametrize("source, target, geography, areal_steps, crosswalk_steps", [
    (2000, 2010, "tract", [(2000, 2010)], []),
    (2000, 2020, "tract", [(2000, 2010)], [(2010, 2020)]),
    (2010, 2020, "block", [(2010, 2020)], []),
    (2010, 2020, "place", [(2010, 2020)], []),
])
def test_forward_path_without_crosswalk_falls_back_to_areal(
    reviewer_tract_data, caplog, source, target, geography, areal_steps, crosswalk_steps,
):
    # Forward transitions with no published crosswalk keep develop's areal
    # alignment, reported in method, warnings and a WARNING log (#1408 owns
    # whether this fallback stays).
    aligner = LongitudinalAligner(target_vintage=target, geography=geography)
    areal_result = reviewer_tract_data.assign(pop=[150.0, 150.0, 350.0, 350.0])
    with patch.object(
        aligner, "_apply_crosswalk_step", side_effect=lambda df, *a, **k: df.copy(),
    ) as crosswalk, patch.object(
        aligner, "_apply_areal_interpolation", return_value=areal_result,
    ) as areal, caplog.at_level("WARNING", logger="siege_utilities.geo.timeseries.longitudinal_data"):
        result = aligner.align(reviewer_tract_data, source, intensive_columns=[])

    assert [c.args[1:3] for c in areal.call_args_list] == areal_steps
    assert [c.args[1:3] for c in crosswalk.call_args_list] == crosswalk_steps
    assert result.method == "areal"
    assert result.data["pop"].tolist() == [150.0, 150.0, 350.0, 350.0]
    src, tgt = areal_steps[0]
    assert f"Used areal interpolation for {src}→{tgt} (crosswalk unavailable)" in result.warnings
    assert any(
        record.levelname == "WARNING" and f"no crosswalk is published for {src}->{tgt}" in record.getMessage()
        for record in caplog.records
    ), [record.getMessage() for record in caplog.records]


@pytest.mark.parametrize("geography", ["tract", "county", "block_group", "Block Group", "block-group", "blockgroup"])
def test_aligner_accepts_supported_geographies_and_aliases(source_data, geography):
    aligner = LongitudinalAligner(geography=geography)
    with patch.object(aligner, "_apply_crosswalk_step", return_value=source_data) as crosswalk:
        result = aligner.align(source_data, 2010)
    assert result.method == "crosswalk"
    assert crosswalk.call_args.args[1:3] == (2010, 2020)


def test_missing_file_download_guard_is_preserved(tmp_path):
    client = CrosswalkClient(cache_dir=tmp_path)
    with pytest.raises(ValueError, match="No crosswalk file available for tract 2000->2010"):
        client._download_crosswalk(2000, 2010, "tract")
