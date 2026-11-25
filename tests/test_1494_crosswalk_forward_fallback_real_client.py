"""rv8 suggested drop-in test (#1829 at 3f40faf4): the forward fallback driven through the REAL crosswalk
client, not a stand-in. Only the areal step is stubbed (it needs boundary downloads).

Passes at head. Written so it can be pasted into tests/test_1494_crosswalk_advertised_transitions.py.
"""
import logging
from unittest.mock import patch

import pandas as pd
import pytest

from siege_utilities.geo.crosswalk import crosswalk_client
from siege_utilities.geo.timeseries.longitudinal_data import LongitudinalAligner


@pytest.mark.parametrize("source, target, geography, areal_steps", [
    (2000, 2010, "tract", [(2000, 2010)]),
    (2010, 2020, "block", [(2010, 2020)]),
    (2010, 2020, "place", [(2010, 2020)]),
])
def test_forward_unpublished_step_reaches_areal_through_the_real_client(
    tmp_path, monkeypatch, caplog, source, target, geography, areal_steps,
):
    downloads = []

    def no_download(*args, **kwargs):
        downloads.append(args)
        raise AssertionError("an unpublished step must not download")

    monkeypatch.setattr(crosswalk_client.requests, "get", no_download)
    monkeypatch.setattr(
        crosswalk_client, "_default_client", crosswalk_client.CrosswalkClient(cache_dir=tmp_path),
    )
    data = pd.DataFrame({
        "GEOID": ["06001000100", "06001000201", "06001000202", "06001000300"],
        "pop": [100.0, 120.0, 80.0, 700.0],
    })
    areal_result = data.assign(pop=[150.0, 150.0, 350.0, 350.0])
    aligner = LongitudinalAligner(target_vintage=target, geography=geography)
    with patch.object(
        aligner, "_apply_areal_interpolation", return_value=areal_result,
    ) as areal, caplog.at_level(logging.WARNING, logger="siege_utilities.geo.timeseries.longitudinal_data"):
        result = aligner.align(data, source, intensive_columns=[])

    assert downloads == []
    assert list(tmp_path.iterdir()) == []
    assert [c.args[1:3] for c in areal.call_args_list] == areal_steps
    assert result.method == "areal"
    assert result.data["pop"].tolist() == [150.0, 150.0, 350.0, 350.0]
    src, tgt = areal_steps[0]
    assert result.warnings == [f"Used areal interpolation for {src}→{tgt} (crosswalk unavailable)"]
    messages = [
        r.getMessage() for r in caplog.records
        if r.levelname == "WARNING" and f"Crosswalk {src}→{tgt} failed" in r.getMessage()
    ]
    assert len(messages) == 1 and "not supported" in messages[0], messages
