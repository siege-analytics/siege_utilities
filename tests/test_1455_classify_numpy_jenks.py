"""Numeric regression oracles for the numpy classification backend (#1455)."""

from itertools import combinations

import numpy as np
import pytest

from siege_utilities.geo import classification


def _sse(values):
    return float(np.sum((values - values.mean()) ** 2))


def _brute_force_sse(values, k):
    """Enumerate contiguous partitions without separating equal values."""
    ordered = np.sort(values)
    cuts = np.flatnonzero(np.diff(ordered)) + 1
    return min(
        sum(_sse(group) for group in np.split(ordered, split))
        for split in combinations(cuts, k - 1)
    )


def _assert_optimal(values, requested_k):
    values = np.asarray(values, dtype=float)
    expected_k = min(requested_k, len(np.unique(values)))
    result = classification.classify_series(values, "natural_breaks", requested_k)
    actual_sse = sum(_sse(values[result.bins == b]) for b in np.unique(result.bins))
    assert actual_sse == pytest.approx(_brute_force_sse(values, expected_k), abs=1e-9)
    assert result.backend == "numpy"
    assert result.k == expected_k
    np.testing.assert_array_equal(np.unique(result.bins), np.arange(expected_k))
    assert len(result.breaks) == expected_k + 1
    assert np.all(np.diff(result.breaks) > 0)
    np.testing.assert_array_equal(
        result.breaks[1:],
        [values[result.bins == b].max() for b in range(expected_k)],
    )
    return result


@pytest.mark.parametrize("n", range(6, 11))
@pytest.mark.parametrize("k", range(2, 5))
def test_numpy_jenks_matches_brute_force_random_samples(monkeypatch, n, k):
    monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", False)
    rng = np.random.default_rng(1455 + 10 * n + k)
    for sample in range(20):
        # Exercise both distinct observations and repeated values, unsorted.
        values = rng.normal(0, 10, n) if sample % 2 else rng.integers(-4, 5, n)
        _assert_optimal(values, k)


def test_numpy_jenks_keeps_singleton_top_class(monkeypatch):
    monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", False)
    values = [-6.85, -5.1, -4.36, -1.06, 0.58, 9.78, 13.57, 18.79]
    result = _assert_optimal(values, 4)
    np.testing.assert_array_equal(result.bins, [0, 0, 0, 1, 1, 2, 2, 3])
    np.testing.assert_array_equal(result.breaks, [-6.85, -4.36, 0.58, 13.57, 18.79])


@pytest.mark.parametrize("values", [[1, 2, 3], [3, 1, 2, 1, 3, 2]])
def test_numpy_jenks_caps_k_at_unique_count_without_empty_first_bin(monkeypatch, values):
    monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", False)
    result = _assert_optimal(values, 5)
    np.testing.assert_array_equal(result.bins, np.asarray(values) - 1)
    assert result.breaks[0] < result.breaks[1] == 1


@pytest.mark.parametrize(
    "scheme,values,k,expected_breaks,expected_bins",
    [
        ("quantiles", [1, 2, 3, 4, 5], 2, [1, 3, 5], [0, 0, 0, 1, 1]),
        (
            "quantiles", [0, 0, 0, 0, 1, 1, 1, 2, 2, 10], 4,
            [0, 1, 1.75, 10], [0, 0, 0, 0, 0, 0, 0, 2, 2, 2],
        ),
        (
            "natural_breaks", [1, 2, 3, 100, 101, 102], 2,
            [1, 3, 102], [0, 0, 0, 1, 1, 1],
        ),
        (
            "fisher_jenks", [1, 2, 3, 100, 101, 102], 2,
            [1, 3, 102], [0, 0, 0, 1, 1, 1],
        ),
        (
            "natural_breaks", [1, 2, 3], 5,
            [np.nextafter(1.0, -np.inf), 1, 2, 3], [0, 1, 2],
        ),
        (
            "natural_breaks", [1, 1, 2, 2, 3, 3], 5,
            [np.nextafter(1.0, -np.inf), 1, 2, 3], [0, 0, 1, 1, 2, 2],
        ),
        (
            "natural_breaks", [-6.85, -5.1, -4.36, -1.06, 0.58, 9.78, 13.57, 18.79], 4,
            [-6.85, -4.36, 0.58, 13.57, 18.79], [0, 0, 0, 1, 1, 2, 2, 3],
        ),
    ],
)
def test_on_break_assignments_and_edges_agree_across_backends(
    monkeypatch, scheme, values, k, expected_breaks, expected_bins,
):
    with monkeypatch.context() as numpy_backend:
        numpy_backend.setattr(classification, "_MAPCLASSIFY_AVAILABLE", False)
        result = classification.classify_series(values, scheme, k)
    np.testing.assert_array_equal(result.bins, expected_bins)
    np.testing.assert_array_equal(result.breaks, expected_breaks)

    # The numpy oracle still runs when the optional backend is absent.
    if classification._MAPCLASSIFY_AVAILABLE:
        other = classification.classify_series(values, scheme, k)
        assert other.backend == "mapclassify"
        assert other.k == result.k
        np.testing.assert_array_equal(other.bins, result.bins)
        np.testing.assert_array_equal(other.breaks, result.breaks)


@pytest.mark.parametrize("missing", [np.inf, -np.inf])
def test_numpy_equal_interval_treats_infinity_as_missing(monkeypatch, missing):
    monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", False)
    result = classification.classify_series([1, 2, missing], "equal_interval", k=2)
    assert np.all(np.isfinite(result.breaks))
    np.testing.assert_array_equal(result.breaks, [1, 1.5, 2])
    np.testing.assert_array_equal(result.bins, [0, 1, -1])


@pytest.mark.parametrize("backend", [False, True], ids=["numpy", "mapclassify"])
def test_nonfinite_mask_handles_constant_and_all_missing_inputs(monkeypatch, backend):
    if backend and not classification._MAPCLASSIFY_AVAILABLE:
        pytest.skip("mapclassify is not installed")
    monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", backend)
    result = classification.classify_series([np.inf, 2, np.nan, 2, -np.inf])
    assert result.k == 1
    np.testing.assert_array_equal(result.breaks, [2, 2])
    np.testing.assert_array_equal(result.bins, [-1, 0, -1, 0, -1])
    with pytest.raises(ValueError, match="empty"):
        classification.classify_series([np.nan, np.inf, -np.inf])
