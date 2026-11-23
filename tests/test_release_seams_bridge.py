"""Fail-closed release acceptance bridge; no kernel replay or mocked SU answers."""
import pytest
from tests.test_notebooks import _release_acceptance_command, NOTEBOOKS_DIR


def declared():
    return {"SU_RELEASE_ACCEPTANCE_REPO":"declared-source", "SU_RELEASE_ACCEPTANCE_SHA":"declared-commit",
            "SU_RELEASE_ACCEPTANCE_WHEEL":"declared-wheel", "SU_RELEASE_ACCEPTANCE_RUNS":"retained-runs",
            "SU_RELEASE_ACCEPTANCE_LANE":"shapely-only"}


def test_missing_provenance_fails_not_skips():
    with pytest.raises(AssertionError,match="explicit provenance"):
        _release_acceptance_command(NOTEBOOKS_DIR/"acceptance/release_seams.ipynb",{})


def test_source_modes_are_mutually_exclusive():
    env={**declared(),"SU_RELEASE_ACCEPTANCE_SOURCE_PROVENANCE":"archive", "SU_RELEASE_ACCEPTANCE_COMPOSITION_PROVENANCE":"composition"}
    with pytest.raises(AssertionError,match="mutually exclusive"):
        _release_acceptance_command(NOTEBOOKS_DIR/"acceptance/release_seams.ipynb",env)


def test_component_diagnostic_requires_explicit_tree():
    env={**declared(),"SU_RELEASE_ACCEPTANCE_COMPOSITION_PROVENANCE":"composition"}
    with pytest.raises(AssertionError,match="content tree"):
        _release_acceptance_command(NOTEBOOKS_DIR/"acceptance/release_seams.ipynb",env)


@pytest.mark.parametrize("lane",["shapely-only","tobler"])
def test_both_lanes_have_real_runner_dispatch(lane):
    env={**declared(),"SU_RELEASE_ACCEPTANCE_LANE":lane}
    command=_release_acceptance_command(NOTEBOOKS_DIR/"acceptance/release_seams.ipynb",env)
    assert command[1]=="-I"
    assert command[command.index("--lane")+1]==lane
    assert command[command.index("--expected-sha")+1]=="declared-commit"
    assert command[-2:]==["--notebook",str(NOTEBOOKS_DIR/"acceptance/release_seams.ipynb")]


def test_unknown_lane_is_rejected():
    with pytest.raises(AssertionError):
        _release_acceptance_command(NOTEBOOKS_DIR/"acceptance/release_seams.ipynb",{**declared(),"SU_RELEASE_ACCEPTANCE_LANE":"silent-other-backend"})
