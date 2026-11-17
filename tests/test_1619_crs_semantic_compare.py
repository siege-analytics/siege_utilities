"""Spatial-join CRS metadata is compared semantically, not as raw values (#1619)."""

import logging
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from siege_utilities.engines.dataframe_engine import _validate_spatial_join_crs

ENGINE_LOGGER = "siege_utilities.engines.dataframe_engine"
REPO_ROOT = Path(__file__).resolve().parents[1]


class _Frame:
    """Frame stand-in whose ``crs`` is explicit metadata (a real attribute)."""

    def __init__(self, crs):
        self.crs = crs


class _ColumnResolvingFrame:
    """Mimics a Spark DataFrame: unknown attribute names resolve to columns."""

    def __getattr__(self, name):
        return f"<column {name}>"


def _mismatch_message(left, right):
    return (
        f"CRS mismatch in spatial_join: left has {left}, "
        f"right has {right}. Reproject one input to match the other."
    )


@pytest.fixture
def pyproj():
    return pytest.importorskip("pyproj")


@pytest.mark.parametrize("left, right", [
    ("EPSG:4326", "epsg:4326"),
    ("epsg:3857", "EPSG:3857"),
])
def test_case_variant_authority_codes_are_the_same_crs(pyproj, left, right):
    _validate_spatial_join_crs(_Frame(left), _Frame(right))


def test_crs_object_and_equivalent_string_are_the_same_crs(pyproj):
    # Guard, not a defect control: pyproj's CRS.__eq__ parses the other
    # operand, so raw comparison already accepted this pair.
    crs = pyproj.CRS.from_user_input("EPSG:4326")

    _validate_spatial_join_crs(_Frame(crs), _Frame("epsg:4326"))
    _validate_spatial_join_crs(_Frame("epsg:4326"), _Frame(crs))


@pytest.mark.parametrize("left, right", [
    ("EPSG:4326", "EPSG:3857"),
    ("epsg:4326", "EPSG:3857"),
])
def test_distinct_crs_strings_still_raise_before_the_join(pyproj, left, right):
    with pytest.raises(ValueError) as exc_info:
        _validate_spatial_join_crs(_Frame(left), _Frame(right))

    assert str(exc_info.value) == _mismatch_message(left, right)


def test_distinct_crs_object_and_string_still_raise(pyproj):
    left = pyproj.CRS.from_user_input("EPSG:4326")

    with pytest.raises(ValueError) as exc_info:
        _validate_spatial_join_crs(_Frame(left), _Frame("EPSG:3857"))

    assert str(exc_info.value) == _mismatch_message(left, "EPSG:3857")


def test_integer_code_and_authority_string_are_the_same_crs(pyproj):
    _validate_spatial_join_crs(_Frame(4326), _Frame("EPSG:4326"))


def test_axis_order_difference_still_raises(pyproj):
    # OGC:CRS84 is longitude-first, EPSG:4326 latitude-first; equality must
    # stay axis-order sensitive.
    with pytest.raises(ValueError) as exc_info:
        _validate_spatial_join_crs(_Frame("OGC:CRS84"), _Frame("EPSG:4326"))

    assert str(exc_info.value) == _mismatch_message("OGC:CRS84", "EPSG:4326")


def test_unparseable_metadata_is_never_treated_as_equal(pyproj):
    with pytest.raises(ValueError, match="CRS mismatch in spatial_join"):
        _validate_spatial_join_crs(_Frame("EPSG:4326"), _Frame("not a crs"))


def test_unparseable_non_string_metadata_is_never_treated_as_equal(pyproj):
    with pytest.raises(ValueError, match="CRS mismatch in spatial_join"):
        _validate_spatial_join_crs(_Frame(object()), _Frame("EPSG:4326"))


def test_proj_data_errors_propagate_instead_of_reporting_a_mismatch(pyproj, monkeypatch):
    from pyproj.exceptions import DataDirError

    def broken_from_user_input(value):
        raise DataDirError("PROJ data directory not found")

    monkeypatch.setattr(pyproj.CRS, "from_user_input", broken_from_user_input)

    with pytest.raises(DataDirError):
        _validate_spatial_join_crs(_Frame("EPSG:4326"), _Frame("epsg:4326"))


@pytest.mark.parametrize("left, right", [
    (None, "EPSG:3857"),
    ("EPSG:4326", None),
    (None, None),
])
def test_unknown_crs_is_allowed(left, right):
    _validate_spatial_join_crs(_Frame(left), _Frame(right))


def test_frame_without_crs_attribute_is_allowed():
    _validate_spatial_join_crs(object(), _Frame("EPSG:3857"))


def test_column_named_crs_is_not_metadata():
    _validate_spatial_join_crs(_ColumnResolvingFrame(), _Frame("EPSG:3857"))
    _validate_spatial_join_crs(_ColumnResolvingFrame(), _ColumnResolvingFrame())


def test_without_pyproj_values_are_compared_literally_and_logged(monkeypatch, caplog):
    # A None entry makes ``import pyproj`` raise ImportError.
    monkeypatch.setitem(sys.modules, "pyproj", None)
    caplog.set_level(logging.WARNING, logger=ENGINE_LOGGER)

    _validate_spatial_join_crs(_Frame("EPSG:4326"), _Frame("EPSG:4326"))
    with pytest.raises(ValueError, match="CRS mismatch in spatial_join"):
        _validate_spatial_join_crs(_Frame("EPSG:4326"), _Frame("epsg:4326"))

    warnings = [r for r in caplog.records if r.name == ENGINE_LOGGER]
    assert len(warnings) == 1
    assert "pyproj is not installed" in warnings[0].getMessage()


def _run_python(code):
    # Run from the repository root so the checkout, not an installed copy,
    # is imported.
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT, timeout=60,
    )


def test_tests_import_this_checkout():
    import siege_utilities.engines.dataframe_engine as engine_module

    assert Path(engine_module.__file__).resolve().is_relative_to(REPO_ROOT)


def test_engine_module_import_does_not_import_pyproj():
    result = _run_python("""
        import sys
        import siege_utilities.engines.dataframe_engine as engine_module
        print(engine_module.__file__)
        print("pyproj" in sys.modules)
    """)

    module_file, pyproj_loaded = result.stdout.splitlines()
    assert Path(module_file).resolve().is_relative_to(REPO_ROOT)
    assert pyproj_loaded == "False"


def test_engine_validates_crs_without_pyproj_installed():
    result = _run_python("""
        import sys
        sys.modules["pyproj"] = None
        from siege_utilities.engines.dataframe_engine import _validate_spatial_join_crs

        class Frame:
            def __init__(self, crs):
                self.crs = crs

        _validate_spatial_join_crs(Frame(None), Frame("EPSG:4326"))
        _validate_spatial_join_crs(Frame("EPSG:4326"), Frame("EPSG:4326"))
        try:
            _validate_spatial_join_crs(Frame("EPSG:4326"), Frame("EPSG:3857"))
        except ValueError as exc:
            print(exc)
    """)

    assert result.stdout.strip() == (
        "CRS mismatch in spatial_join: left has EPSG:4326, right has EPSG:3857. "
        "Reproject one input to match the other."
    )
