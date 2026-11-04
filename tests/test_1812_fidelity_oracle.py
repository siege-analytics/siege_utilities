"""R-1812-3 oracle for the social fidelity audit comparator (#1812).

The audit in scripts/check_social_review_fidelity.py must authorize a
baseline-zero -> current-null only at the explicit omitted-post cells and
compare everything else strictly (type, timezone, index name). These checks
encode the reviewer's adversarial seeds (review-1812-154e2f0e.md): the prior
comparator false-greened the timezone relabel, the 0 -> False change, the
index-name change, a non-count zero -> null, and the counterbalanced swap.

The script is loaded by path (it is not an importable package module); the
real `audit()` runs the baseline-vs-current comparison offline via git show.
"""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_social_review_fidelity.py"
_spec = importlib.util.spec_from_file_location("check_social_review_fidelity", _SCRIPT)
fidelity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fidelity)

IG_OMITTED = "instagram._posts_to_dataframe.omitted"
IG_POPULATED = "instagram._posts_to_dataframe.populated"


def _frame(col, value):
    return pd.DataFrame({col: [value]})


def test_unmutated_audit_is_green():
    # The real baseline-vs-current audit still passes: exactly the eight
    # authorized omitted-post nulls, nothing else. This is the green-at-head
    # control; it fails if the explicit locations or counts are wrong.
    fidelity.audit()


def test_authorized_set_has_eight_locations():
    assert len(fidelity._AUTHORIZED) == 8


def test_authorized_zero_to_null_is_counted_and_recorded():
    hits = set()
    n = fidelity.compare(_frame("like_count", 0), _frame("like_count", None), IG_OMITTED, hits)
    assert n == 1
    assert hits == {f"{IG_OMITTED}[0,'like_count']"}


def test_zero_to_null_outside_authorized_fixture_is_rejected():
    # The populated-measured-0-nulled half of the counterbalanced swap.
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", 0), _frame("like_count", None), IG_POPULATED, set())


def test_null_to_zero_is_rejected_even_at_authorized_location():
    # The omitted-null-fabricated-to-0 half: authorized cells permit zero->null,
    # never null->zero, so the swap cannot net to the expected total.
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", None), _frame("like_count", 0), IG_OMITTED, set())


def test_non_count_zero_to_null_is_rejected():
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("engagement_rate", 0.0), _frame("engagement_rate", None), IG_OMITTED, set())


def test_same_instant_timezone_relabel_is_rejected():
    utc = pd.Timestamp("2026-01-02T00:00:00Z")
    with pytest.raises(AssertionError):
        fidelity.compare(
            _frame("published_at", utc),
            _frame("published_at", utc.tz_convert("America/Chicago")),
            IG_POPULATED, set(),
        )


def test_zero_to_false_type_change_is_rejected():
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", 0), _frame("like_count", False), IG_POPULATED, set())


def test_index_name_change_is_rejected():
    old = _frame("like_count", 1)
    new = _frame("like_count", 1)
    new.index.name = "relabelled"
    with pytest.raises(AssertionError):
        fidelity.compare(old, new, IG_POPULATED, set())


def test_lost_authorized_null_is_not_recorded():
    # If the omitted fix is lost (cell stays 0), the location is never hit, so
    # audit()'s `hits == _AUTHORIZED` assertion fails -- a compensating change
    # cannot mask the lost null.
    hits = set()
    fidelity.compare(_frame("like_count", 0), _frame("like_count", 0), IG_OMITTED, hits)
    assert hits == set()
    assert fidelity._AUTHORIZED - hits


def test_changed_known_count_is_rejected():
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", 4), _frame("like_count", 5), IG_POPULATED, set())


def test_removed_row_is_rejected():
    old = pd.DataFrame({"like_count": [1, 2]})
    new = pd.DataFrame({"like_count": [1]})
    with pytest.raises(AssertionError):
        fidelity.compare(old, new, IG_POPULATED, set())
