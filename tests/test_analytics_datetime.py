"""Regression tests for analytics dates and timezones (#1444)."""

import time
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from siege_utilities.analytics import pipeline
from siege_utilities.analytics.instagram import InstagramConnector
from siege_utilities.analytics.pipeline import PipelineAnalyzer, PipelineItem


@pytest.fixture
def instagram(monkeypatch):
    """Exercise the connector with all HTTP requests intercepted."""
    response = Mock(status_code=200)
    response.json.return_value = {"data": []}
    request = Mock(return_value=response)
    with InstagramConnector("test-token", ig_user_id="123") as connector:
        monkeypatch.setattr(connector._session, "request", request)
        connector.authenticate()
        request.reset_mock()
        yield connector, request, response


@pytest.fixture(params=["America/Chicago", "Pacific/Auckland"])
def host_timezone(request, monkeypatch):
    """Restore the process timezone even after an assertion fails."""
    if not hasattr(time, "tzset"):
        pytest.skip("Changing the host timezone requires time.tzset")
    try:
        with monkeypatch.context() as context:
            context.setenv("TZ", request.param)
            time.tzset()
            yield
    finally:
        time.tzset()


@pytest.mark.parametrize("month", [1, 7])
def test_instagram_insight_window_is_utc(instagram, host_timezone, month):
    connector, request, _ = instagram
    connector.get_account_insights(date(2026, month, 1), date(2026, month, 2))

    request.assert_called_once()
    params = request.call_args.kwargs["params"]
    assert params["period"] == "day"
    assert params["since"] == int(
        datetime(2026, month, 1, tzinfo=timezone.utc).timestamp()
    )
    assert params["until"] == int(
        datetime(2026, month, 3, tzinfo=timezone.utc).timestamp()
    ) - 1


@pytest.mark.parametrize(
    "end_time, covered_day",
    [
        ("2026-01-02T00:00:00+0000", "2026-01-01"),
        ("2026-01-02T08:00:00+0000", "2026-01-01"),
        ("2026-01-02T00:00:00+05:30", "2026-01-01"),
        ("2026-01-01T00:00:00-08:00", "2025-12-31"),
        ("2024-03-01T00:00:00Z", "2024-02-29"),
        ("2026-03-01T00:00:00Z", "2026-02-28"),
    ],
)
def test_instagram_insights_use_covered_day(instagram, end_time, covered_day):
    connector, _, response = instagram
    response.json.return_value = {
        "data": [
            {
                "name": "reach",
                "period": "day",
                "values": [{"end_time": end_time, "value": 7}],
            },
            {
                "name": "profile_views",
                "period": "day",
                "values": [{"end_time": end_time, "value": 3}],
            },
        ],
    }
    day = date.fromisoformat(covered_day)
    frame = connector.get_account_insights(
        day, day, ["reach", "profile_views"],
    )

    assert list(frame.columns) == ["date", "reach", "profile_views"]
    assert frame.to_dict("records") == [
        {"date": covered_day, "reach": 7, "profile_views": 3},
    ]


@pytest.fixture
def utc_now(monkeypatch):
    """Freeze now while preserving datetime.now's naive/aware semantics."""
    reference = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
    clock = Mock(wraps=datetime)
    clock.now.side_effect = lambda tz=None: (
        reference.astimezone(tz) if tz is not None
        else reference.replace(tzinfo=None)
    )
    monkeypatch.setattr(pipeline, "datetime", clock)
    return reference, clock.now


def test_pipeline_default_as_of_accepts_aware_timestamps(utc_now):
    reference, now = utc_now
    entered = (reference - timedelta(days=5)).astimezone(
        timezone(timedelta(hours=-8))
    )
    item = PipelineItem("aware", "lead", 100, entered)

    report = PipelineAnalyzer(["lead"]).analyze([item])

    now.assert_called_once_with(timezone.utc)
    assert report.velocity[0].avg_days == 5.0
    assert report.velocity[0].max_days == 5.0
    assert item.entered_stage is entered


@pytest.mark.parametrize("as_of_kind", ["default", "naive", "utc", "offset"])
def test_pipeline_mixed_timestamps_are_normalized_to_utc(utc_now, as_of_kind):
    reference, _ = utc_now
    offset = timezone(timedelta(hours=5, minutes=30))
    as_of = {
        "default": None,
        "naive": reference.replace(tzinfo=None),
        "utc": reference,
        "offset": reference.astimezone(offset),
    }[as_of_kind]
    items = [
        PipelineItem("naive", "lead", 100,
                     (reference - timedelta(days=3)).replace(tzinfo=None)),
        PipelineItem("offset", "lead", 100,
                     (reference - timedelta(days=5)).astimezone(offset)),
        PipelineItem("aging", "lead", 100, reference - timedelta(days=20)),
        PipelineItem("future", "lead", 100, reference + timedelta(days=2)),
        PipelineItem("missing", "lead", 100),
    ]

    report = PipelineAnalyzer(["lead"]).analyze(items, as_of=as_of)

    assert len(report.velocity) == 1
    velocity = report.velocity[0]
    assert velocity.stage == "lead"
    assert velocity.avg_days == 7.0
    assert velocity.max_days == 20.0
    assert velocity.aging_items == ["aging"]
    assert items[0].entered_stage.tzinfo is None


def test_pipeline_default_as_of_is_utc_for_naive_only_input(utc_now):
    reference, now = utc_now
    item = PipelineItem(
        "naive", "lead", 100,
        (reference - timedelta(days=2)).replace(tzinfo=None),
    )

    report = PipelineAnalyzer(["lead"]).analyze([item])

    now.assert_called_once_with(timezone.utc)
    assert report.velocity[0].avg_days == 2.0
    assert report.velocity[0].max_days == 2.0


def test_pipeline_velocity_measures_elapsed_time_across_dst():
    chicago = ZoneInfo("America/Chicago")
    # The spring-forward interval is 27 elapsed hours, not 28 wall-clock hours.
    entered = datetime(2026, 3, 7, 12, tzinfo=chicago)
    as_of = datetime(2026, 3, 8, 16, tzinfo=chicago)
    item = PipelineItem("dst", "lead", 100, entered)

    report = PipelineAnalyzer(["lead"]).analyze([item], as_of=as_of)

    assert report.velocity[0].avg_days == 1.1
    assert report.velocity[0].max_days == 1.1
