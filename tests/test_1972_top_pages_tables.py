"""Top-pages consumers read the page rows the GA producers emit (#1972)."""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator
from siege_utilities.reporting.examples.google_analytics_report_example import (
    generate_sample_ga_data,
)
from siege_utilities.reporting.idml_export import export_report_idml


def _ga4_page(path: str, pageviews: int, **extra: Any) -> dict[str, Any]:
    """A top-pages row with the keys fetch_real_ga4_data emits."""
    return {'page': path, 'pageviews': pageviews, 'avg_time': 120.0,
            'bounce_rate': 45.0, **extra}


@pytest.fixture
def generator(tmp_path: Path) -> AnalyticsReportGenerator:
    return AnalyticsReportGenerator(client_name='test', output_dir=tmp_path)


def _top_pages_table(generator: AnalyticsReportGenerator,
                     pages: list[dict[str, Any]]) -> list[list[str]]:
    tables = generator._create_ga_tables({'top_pages': pages})
    return next(t for t in tables if t['title'] == 'Top Pages by Page Views')['data']


def _top_pages_charts(generator: AnalyticsReportGenerator,
                      pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    charts = generator._create_ga_charts({'top_pages': pages})
    return [c for c in charts if c['title'] == 'Top Performing Pages']


def test_table_shows_pageviews_and_marks_a_missing_unique_view_count(generator):
    rows = _top_pages_table(generator, [
        _ga4_page('/', 1234),
        _ga4_page('/about', 80, unique_views=1000),
    ])
    assert rows[0] == ['/', '1,234', 'N/A', '120.0s', '45.0%']
    assert rows[1] == ['/about', '80', '1,000', '120.0s', '45.0%']


def test_table_prefers_pageviews_and_accepts_caller_rows_keyed_views(generator):
    rows = _top_pages_table(generator, [
        {'page': '/both', 'pageviews': 70, 'views': 5},
        {'page': '/legacy', 'views': 50},
    ])
    assert [row[1] for row in rows] == ['70', '50']


def test_table_shows_na_for_a_page_without_any_view_count(generator):
    rows = _top_pages_table(generator, [{'page': '/none', 'avg_time': 1.0, 'bounce_rate': 2.0}])
    assert rows[0][:3] == ['/none', 'N/A', 'N/A']


def test_table_reads_the_sample_generator_page_views(generator):
    data = generate_sample_ga_data(datetime(2026, 1, 1), datetime(2026, 1, 31))
    rows = _top_pages_table(generator, data['top_pages'])
    expected = [[f"{page['pageviews']:,}", f"{page['unique_views']:,}"]
                for page in data['top_pages']]
    assert [row[1:3] for row in rows] == expected
    assert all(page['pageviews'] > 0 for page in data['top_pages'])


def test_chart_plots_pageviews_and_leaves_out_pages_without_a_count(generator):
    charts = _top_pages_charts(generator, [
        _ga4_page('/', 200),
        {'page': '/uncounted', 'avg_time': 1.0, 'bounce_rate': 2.0},
        _ga4_page('/c', 80),
    ])
    assert len(charts) == 1
    data = charts[0]['data']
    assert data['labels'] == ['/', '/c']
    assert data['datasets'][0]['data'] == [200, 80]


def test_chart_is_skipped_when_no_page_has_a_count(generator):
    pages = [{'page': '/a', 'avg_time': 1.0, 'bounce_rate': 2.0},
             {'page': '/b', 'avg_time': 1.0, 'bounce_rate': 2.0}]
    assert _top_pages_charts(generator, pages) == []


def test_insight_names_the_top_page_with_its_pageviews(generator):
    insights = generator._generate_ga_insights({'top_pages': [_ga4_page('/', 1234)]})
    assert "'/' is the top performing page with 1,234 views" in insights


def test_insight_omits_the_count_for_a_top_page_without_one(generator):
    insights = generator._generate_ga_insights(
        {'top_pages': [{'page': '/', 'avg_time': 1.0, 'bounce_rate': 2.0}]})
    assert "'/' is the top performing page" in insights
    assert not any('views' in insight for insight in insights)


def test_idml_top_pages_marks_a_missing_unique_view_count(tmp_path):
    ga_data = {'top_pages': [_ga4_page('/', 200), _ga4_page('/about', 80, unique_views=60)]}
    output = export_report_idml(ga_data, str(tmp_path / 'report.idml'))
    with zipfile.ZipFile(output) as archive:
        stories = '\n'.join(archive.read(name).decode() for name in archive.namelist()
                            if name.startswith('Stories/'))
    assert '/\t200\tN/A\t120.0s\t45.0%' in stories
    assert '/about\t80\t60\t120.0s\t45.0%' in stories


# A count of 0 is a real value: fetch_real_ga4_data coerces an unavailable
# screenPageViews to 0. It must render as 0, never as missing.

def test_table_shows_a_zero_count_as_zero(generator):
    rows = _top_pages_table(generator, [
        _ga4_page('/zero', 0, unique_views=0),
        {'page': '/zero-pageviews', 'pageviews': 0, 'views': 5},
    ])
    assert rows[0][:3] == ['/zero', '0', '0']
    assert rows[1][1] == '0'


def test_chart_keeps_a_page_with_zero_pageviews(generator):
    charts = _top_pages_charts(generator, [_ga4_page('/', 200), _ga4_page('/zero', 0)])
    data = charts[0]['data']
    assert data['labels'] == ['/', '/zero']
    assert data['datasets'][0]['data'] == [200, 0]


def test_insight_keeps_a_zero_count(generator):
    insights = generator._generate_ga_insights({'top_pages': [_ga4_page('/', 0)]})
    assert "'/' is the top performing page with 0 views" in insights


def test_idml_shows_a_zero_unique_view_count(tmp_path):
    ga_data = {'top_pages': [_ga4_page('/', 0, unique_views=0)]}
    output = export_report_idml(ga_data, str(tmp_path / 'report.idml'))
    with zipfile.ZipFile(output) as archive:
        stories = '\n'.join(archive.read(name).decode() for name in archive.namelist()
                            if name.startswith('Stories/'))
    assert '/\t0\t0\t120.0s\t45.0%' in stories


def test_chart_plots_only_counted_pages_within_the_first_ten_rows(generator):
    pages = [_ga4_page(f'/p{i}', 1000 - i) for i in range(1, 13)]
    pages[2] = {'page': '/p3', 'avg_time': 1.0, 'bounce_rate': 2.0}  # uncounted, inside the first ten
    labels = _top_pages_charts(generator, pages)[0]['data']['labels']
    assert labels == ['/p1', '/p2', '/p4', '/p5', '/p6', '/p7', '/p8', '/p9', '/p10']
    assert '/p11' not in labels and '/p12' not in labels
