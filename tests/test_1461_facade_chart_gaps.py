"""Facade chart gaps, chart validation, file names and table text (#1461).

Develop's social-media payloads carry ``None`` for an unknown count (for
example followers ``[None, 12]``). A missing value is a gap, never a zero:
bar and pie charts omit it, a line chart leaves a break, and a chart with no
labels or no known values is left out, heading included, with a warning. A
pie chart whose known values total zero, a series whose length differs from
the labels, and a non-numeric value raise ``ValueError`` naming the chart.
The spies wrap the chart generator's real methods and the report generator is
never mocked.
"""

import logging
import math
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip("reportlab")
pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")
PdfReader = pytest.importorskip("PyPDF2").PdfReader

from siege_utilities.reporting._facade_content import _chart_images
from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator
from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator

LOGGER = "siege_utilities.reporting._facade_content"


@pytest.fixture
def generator(tmp_path):
    return ReportGenerator("Acme", output_dir=tmp_path)


def _spy(generator, method):
    real = getattr(generator.chart_generator, method)
    spy = Mock(wraps=real)
    setattr(generator.chart_generator, method, spy)
    return spy


def test_pie_with_known_values_totalling_zero_raises(generator):
    config = {"type": "pie", "title": "Sources", "data": {"labels": ["a", "b"], "data": [0, 0]}}
    with pytest.raises(ValueError, match="'Sources' has values that total zero"):
        _chart_images(config, generator)


def test_pie_omits_missing_slices(generator):
    spy = _spy(generator, "create_pie_chart")
    config = {"type": "pie", "title": "Sources",
              "data": {"labels": ["a", "b", "c"], "data": [None, 3, float("nan")]}}

    images = _chart_images(config, generator)

    assert len(images) == 1
    assert spy.call_args.args[0] == {"Label": ["b"], "Value": [3]}


def test_bar_omits_missing_values(generator):
    spy = _spy(generator, "create_bar_chart")
    config = {"type": "bar", "title": "Followers",
              "data": {"labels": ["fakebook", "known"],
                       "datasets": [{"label": "Followers", "data": [None, 12]}]}}

    images = _chart_images(config, generator)

    assert len(images) == 1
    assert spy.call_args.args[0] == {"Label": ["known"], "Value": [12]}


def test_line_keeps_missing_values_as_breaks(generator):
    spy = _spy(generator, "create_line_chart")
    config = {"type": "line", "title": "Daily",
              "data": {"labels": ["d1", "d2", "d3"],
                       "datasets": [{"label": "Reach", "data": [3, None, 5]}]}}

    images = _chart_images(config, generator)

    assert len(images) == 1
    series = spy.call_args.args[0]["1. Reach"]
    assert series[0] == 3 and series[2] == 5
    assert math.isnan(series[1])


@pytest.mark.parametrize("config", [
    {"type": "pie", "title": "All unknown", "data": {"labels": ["a", "b"], "data": [None, None]}},
    {"type": "bar", "title": "All unknown",
     "data": {"labels": ["a", "b"], "datasets": [{"data": [None, float("nan")]}]}},
    {"type": "line", "title": "All unknown",
     "data": {"labels": ["a", "b"], "datasets": [{"label": "x", "data": [None, None]}]}},
], ids=["pie", "bar", "line"])
def test_chart_with_no_known_values_is_left_out_with_a_warning(generator, caplog, config):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert _chart_images(config, generator) == []
    assert any(
        record.name == LOGGER and "has no known values" in record.getMessage()
        for record in caplog.records
    )


class _Connector:
    def __init__(self, platform_name, followers, likes):
        self.platform_name = platform_name
        self.followers = followers
        self.likes = likes

    def get_account_info(self):
        return {"followers_count": self.followers, "following_count": 5}

    def get_account_insights(self, start_date, end_date):
        return pd.DataFrame({"date": ["2026-01-01", "2026-01-02"], "reach": [3, None]})

    def get_posts(self, start_date, end_date, *, limit):
        return pd.DataFrame({"text": ["first post"], "like_count": [self.likes]})


def test_social_report_with_unknown_counts_writes_a_pdf_without_drawing_them(tmp_path):
    # The followers chart is [None, 12] and the likes chart [None, 6]: the
    # None-gap shape develop's social payload produces for unknown counts.
    # Chart labels are drawn inside images, which PDF text extraction cannot
    # read, so the spy records what the real chart generator was asked to draw.
    gen = SocialMediaReportGenerator("Acme", output_dir=tmp_path)
    bar_spy = _spy(gen.report_generator, "create_bar_chart")

    path = gen.create_social_media_report(
        [_Connector("fakebook", None, None), _Connector("known", 12, 6)],
        date(2026, 1, 1), date(2026, 1, 31),
    )

    assert isinstance(path, Path) and path.is_file()
    assert path.read_bytes().startswith(b"%PDF-")
    text = " ".join(" ".join(page.extract_text().split()) for page in PdfReader(path).pages)
    assert "Followers by Platform" in text
    assert "unavailable" in text
    drawn = [call.args[0] for call in bar_spy.call_args_list]
    assert drawn == [
        {"Label": ["known"], "Value": [12]},
        {"Label": ["known"], "Value": [6]},
    ]


def _chart_config(kind, labels, values, title="Mismatch"):
    if kind == "pie":
        return {"type": kind, "title": title, "data": {"labels": labels, "data": values}}
    return {"type": kind, "title": title,
            "data": {"labels": labels, "datasets": [{"label": "Series", "data": values}]}}


@pytest.mark.parametrize("kind", ["bar", "line", "pie"])
@pytest.mark.parametrize("labels, values", [
    (["a", "b", "c"], [1, 2]),
    (["a", "b"], [1, 2, 3]),
], ids=["3-labels-2-values", "2-labels-3-values"])
def test_series_length_mismatch_raises_naming_the_chart(generator, kind, labels, values):
    with pytest.raises(ValueError, match=rf"Facade {kind} chart 'Mismatch.*' has "
                                         rf"{len(labels)} labels but {len(values)} values"):
        _chart_images(_chart_config(kind, labels, values), generator)


def test_website_report_chart_length_mismatch_raises_and_writes_no_pdf(tmp_path):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)
    payload = {"load_time": 1.25, "charts": [_chart_config("bar", ["a", "b", "c"], [1, 2])]}

    with pytest.raises(ValueError, match="'Mismatch - Series' has 3 labels but 2 values"):
        gen.create_website_performance_report(payload, ["load_time"])

    assert list(tmp_path.glob("*.pdf")) == []


def test_ga_daily_traffic_with_dates_and_no_users_raises_and_writes_no_pdf(tmp_path):
    # Labels are checked before the series: dates with no user counts is an
    # empty series of the wrong length, which raises rather than being left out.
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)

    with pytest.raises(ValueError, match="'Daily Website Traffic' has 2 labels but 0 values"):
        gen.create_google_analytics_report({"daily_traffic": {"dates": ["2026-01-01", "2026-01-02"]}})

    assert list(tmp_path.glob("*.pdf")) == []


def test_chart_with_values_and_no_labels_is_left_out_with_a_warning(generator, caplog):
    config = {"type": "bar", "title": "Unlabelled",
              "data": {"labels": [], "datasets": [{"data": [1, 2]}]}}
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert _chart_images(config, generator) == []
    assert any(
        record.name == LOGGER and "'Unlabelled' has no labels" in record.getMessage()
        for record in caplog.records
    )


@pytest.mark.parametrize("kind", ["bar", "line", "pie"])
def test_non_numeric_value_raises_naming_the_chart(generator, kind):
    config = _chart_config(kind, ["a", "b"], ["many", 2], title="Words")
    with pytest.raises(ValueError, match=rf"Facade {kind} chart 'Words.*' has a non-numeric value: 'many'"):
        _chart_images(config, generator)


@pytest.mark.parametrize("kind", ["bar", "line", "pie"])
def test_list_as_a_single_value_raises_the_named_non_numeric_error(generator, kind):
    config = _chart_config(kind, ["a", "b"], [[1, 2], 3], title="Nested")
    with pytest.raises(ValueError, match=rf"Facade {kind} chart 'Nested.*' has a non-numeric value: \[1, 2\]"):
        _chart_images(config, generator)


def test_pie_omits_numpy_decimal_and_pandas_missing_values(generator):
    spy = _spy(generator, "create_pie_chart")
    config = {"type": "pie", "title": "Sources",
              "data": {"labels": ["a", "b", "c", "d"],
                       "data": [np.nan, Decimal("NaN"), pd.NA, Decimal("3")]}}

    _chart_images(config, generator)

    assert spy.call_args.args[0] == {"Label": ["d"], "Value": [Decimal("3")]}


def test_bar_title_is_the_dataset_label_when_the_chart_has_no_title(generator):
    spy = _spy(generator, "create_bar_chart")
    config = {"type": "bar", "data": {"labels": ["a"],
                                      "datasets": [{"label": "Followers", "data": [1]}]}}

    _chart_images(config, generator)

    assert spy.call_args.kwargs["title"] == "Followers"


def test_chart_with_empty_labels_is_left_out_with_a_warning(generator, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert _chart_images({"type": "bar", "title": "Empty", "data": {"labels": []}}, generator) == []
    assert any(
        record.name == LOGGER and "'Empty' has no labels" in record.getMessage()
        for record in caplog.records
    )


@pytest.mark.parametrize("data", [
    {"labels": ["a", "b"]},
    {"labels": ["a", "b"], "datasets": []},
], ids=["datasets-absent", "datasets-empty"])
@pytest.mark.parametrize("kind", ["bar", "line"])
def test_chart_with_labels_and_no_datasets_is_left_out_with_a_warning(generator, caplog, kind, data):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert _chart_images({"type": kind, "title": "No Series", "data": data}, generator) == []
    assert any(
        record.name == LOGGER and f"Facade {kind} chart 'No Series' has no datasets" in record.getMessage()
        for record in caplog.records
    )


def test_website_report_chart_with_no_datasets_leaves_no_heading(tmp_path, caplog):
    payload = {"charts": [
        {"type": "line", "title": "No Series Chart", "data": {"labels": ["d1", "d2"], "datasets": []}},
    ]}

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        path, text = _website_pdf_text(tmp_path, payload)

    assert path.is_file()
    assert "load_time" in text
    assert "No Series Chart" not in text
    assert any(
        record.name == LOGGER and "'No Series Chart' has no datasets" in record.getMessage()
        for record in caplog.records
    )


def _website_pdf_text(tmp_path, payload, title="Website"):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)
    path = gen.create_website_performance_report({"load_time": 1.25, **payload}, ["load_time"], title)
    return path, " ".join(" ".join(page.extract_text().split()) for page in PdfReader(path).pages)


def test_charts_that_draw_nothing_leave_no_heading(tmp_path, caplog):
    payload = {"charts": [
        {"type": "bar", "title": "Ghost Chart",
         "data": {"labels": ["a"], "datasets": [{"data": [None]}]}},
        {"type": "pie", "title": "Empty Chart", "data": {"labels": [], "data": []}},
        {"type": "bar", "title": "Real Chart",
         "data": {"labels": ["a"], "datasets": [{"data": [4]}]}},
    ]}

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _, text = _website_pdf_text(tmp_path, payload)

    assert "Real Chart" in text
    assert "Ghost Chart" not in text
    assert "Empty Chart" not in text
    messages = [record.getMessage() for record in caplog.records if record.name == LOGGER]
    assert any("'Ghost Chart' has no known values" in message for message in messages)
    assert any("'Empty Chart' has no labels" in message for message in messages)


def test_custom_report_chart_section_that_draws_nothing_leaves_no_heading(tmp_path):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)
    data = {"ghost_values": [math.nan, math.nan], "real_values": [1, 2]}
    path = gen.create_custom_analytics_report("dict", data, {"title": "Custom"})
    text = " ".join(" ".join(page.extract_text().split()) for page in PdfReader(path).pages)
    assert "Real Values Chart" in text
    assert "Chart showing real_values values" in text
    assert "Ghost Values Chart" not in text
    assert "Chart showing ghost_values values" not in text


def test_file_stem_is_cut_to_80_characters(tmp_path):
    path, _ = _website_pdf_text(tmp_path, {}, title="A" * 200)
    assert re.fullmatch(r"A{80}_[0-9a-f]{32}", path.stem)


def test_file_stem_falls_back_to_report(tmp_path):
    path, _ = _website_pdf_text(tmp_path, {}, title="!!!")
    assert re.fullmatch(r"report_[0-9a-f]{32}", path.stem)


def test_table_cells_are_printed_as_text_not_markup(tmp_path):
    payload = {"tables": [{"title": "Pages", "headers": ["Page"],
                           "data": [["<b>bold</b> & co"]]}]}
    _, text = _website_pdf_text(tmp_path, payload)
    assert "<b>bold</b> & co" in text
