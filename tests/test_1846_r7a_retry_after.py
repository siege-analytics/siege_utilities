"""R-1846-7a keep/drop matrix for `_validated_retry_after` (#1846).

Hub amendment R-1846-7a to F2(a): the sanitizer's retry-after validator must
accept an exact ``int``/``float`` while applying finiteness asymmetrically --
a non-finite value (``inf``/``nan``) passes through to preserve the B1 over-cap
"do not sleep" sentinel (test_connector_over_cap_raises_without_sleep), but a
negative *finite* value is dropped. Exact-type-only (the pre-amendment shape)
would have kept ``-1``/``-0.5``; this test goes red against that revert.
"""
import math

import pytest

from siege_utilities.connectors._protocol import _SecretRedactionMixin


class _IntSub(int):
    pass


class _FloatSub(float):
    pass


def _exc_with(retry_after):
    exc = ValueError("ordinary")
    exc.retry_after = retry_after
    return exc


KEPT = [0, 7, 7.5, float("inf"), float("-inf"), float("nan")]
DROPPED = [-1, -0.5, True, False, _IntSub(7), _FloatSub(7.0), "7", None, object()]


@pytest.mark.parametrize("value", KEPT)
def test_validated_retry_after_keeps(value):
    result = _SecretRedactionMixin._validated_retry_after(_exc_with(value))
    # Identity, so a kept ``nan`` (``nan != nan``) still asserts cleanly.
    assert result is value


@pytest.mark.parametrize("value", DROPPED)
def test_validated_retry_after_drops(value):
    assert _SecretRedactionMixin._validated_retry_after(_exc_with(value)) is None


def test_non_finite_carveout_precedes_non_negative_check():
    # nan >= 0 is False; the non-finite branch must be evaluated first or the
    # sentinel would be stripped.
    nan = float("nan")
    assert math.isnan(_SecretRedactionMixin._validated_retry_after(_exc_with(nan)))
