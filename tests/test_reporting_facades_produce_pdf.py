"""Facade regressions: render real PDFs and read the collected data back."""

import json
from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("reportlab")
pd = pytest.importorskip("pandas")
PdfReader = pytest.importorskip("PyPDF2").PdfReader

from siege_utilities.reporting.analytics_reports import AnalyticsReportGenerator
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator


class _Connector:
    platform_name = "instagram"

    def get_account_info(self):
        return {"followers_count": 1234, "following_count": 432}

    def get_account_insights(self, start, end):
        return pd.DataFrame({"date": ["2026-01-01"], "reach": [57]})

    def get_posts(self, start, end, limit=50):
        return pd.DataFrame({"text": ["Launch <3 & community"], "like_count": [37]})


def _pdf_text(path, output_dir):
    assert isinstance(path, Path)
    assert path.parent == output_dir
    assert path.suffix == ".pdf"
    assert path.is_file()
    assert path.stat().st_size > 0
    assert path.read_bytes().startswith(b"%PDF-")
    return " ".join(" ".join(page.extract_text().split()) for page in PdfReader(path).pages)


def test_social_media_report_produces_pdf(tmp_path):
    gen = SocialMediaReportGenerator("Acme", output_dir=tmp_path)
    path = gen.create_social_media_report(
        [_Connector()], date(2026, 1, 1), date(2026, 1, 31), title="Social <3 & Acme"
    )
    text = _pdf_text(path, tmp_path)
    for expected in (
        "Social <3 & Acme", "1,234", "432", "Launch <3 & community",
        "average 37 likes per post", "Total Followers (all platforms)",
    ):
        assert expected in text


@pytest.mark.parametrize("report", ["google", "monthly", "quarterly", "campaign", "website"])
def test_analytics_facade_produces_pdf(report, tmp_path):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)
    if report == "google":
        path = gen.create_google_analytics_report({
            "total_users": 1234, "total_sessions": 2468,
            "top_pages": [{"page": "/launch", "views": 345, "unique_views": 234}],
            "traffic_sources": [{"source": "newsletter", "sessions": 88}],
        }, "January 2026", "Google <3 & Acme")
        expected = ["Google <3 & Acme", "Total Users", "1,234", "234", "newsletter",
                    "High engagement: 2.0 sessions per user on average"]
    elif report == "monthly":
        path = gen.create_monthly_analytics_report({
            "visits": 1234, "performance_score": 93, "summary": {"orders": 567},
            "daily_data": {"dates": ["2026-01-01"], "values": [42]},
        }, 2026, 1)
        expected = ["Monthly Analytics Report - 2026-01", "Visits", "1,234", "567",
                    "Excellent monthly performance score of 93/100"]
    elif report == "quarterly":
        path = gen.create_quarterly_analytics_report({
            "visits": 1234, "performance_score": 94, "summary": {"orders": 568},
            "monthly_data": {"months": ["January", "February"], "values": [42, 50]},
        }, 2026, 1)
        expected = ["Q1 2026 Analytics Report", "Visits", "1,234", "568",
                    "Strong quarterly performance score of 94/100"]
    elif report == "campaign":
        path = gen.create_campaign_performance_report({
            "impressions": 1234, "ctr": 3.75, "performance_summary": {"orders": 569},
            "daily_performance": {"dates": ["2026-01-01"], "impressions": [42], "clicks": [4]},
        }, "Launch", "January 2026")
        expected = ["Campaign Performance: Launch", "Impressions", "1,234", "569",
                    "Excellent click-through rate of 3.75%"]
    else:
        path = gen.create_website_performance_report({
            "load_time": 1.25, "unselected": "DO_NOT_INCLUDE",
            "tables": [{"title": "Pages", "headers": ["Page"], "data": [["/landing"]]}],
            "insights": ["Fast landing page"],
        }, ["load_time"], "Website <3 & Acme")
        expected = ["Website <3 & Acme", "load_time", "1.25", "/landing", "Fast landing page"]
    text = _pdf_text(path, tmp_path)
    for value in expected:
        assert value in text
    assert "DO_NOT_INCLUDE" not in text


@pytest.mark.parametrize("source", ["dict", "json", "dataframe", "csv"])
def test_custom_analytics_report_produces_pdf(source, tmp_path):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)
    if source in ("dict", "json"):
        data = {"visits": 1234, "pages": ["/landing"], "insight": "Steady audience growth"}
        if source == "json":
            data = json.dumps(data)
        expected = ["1,234", "/landing", "Steady audience growth"]
    else:
        data = pd.DataFrame({"page": ["/landing", "/home"], "visits": [1234, 2468]})
        if source == "csv":
            csv_path = tmp_path / "input.csv"
            data.to_csv(csv_path, index=False)
            data = str(csv_path)
        expected = ["/landing", "1234", "1851.00"]
    path = gen.create_custom_analytics_report(source, data, {"title": "Custom <3 & Acme"})
    text = _pdf_text(path, tmp_path)
    for value in ["Custom <3 & Acme", *expected]:
        assert value in text


@pytest.mark.parametrize("title", ["", "../../outside/report"])
def test_reports_with_the_same_title_remain_inside_output_dir(title, tmp_path):
    gen = AnalyticsReportGenerator("Acme", output_dir=tmp_path)
    first = gen.create_google_analytics_report({}, report_title=title)
    original = first.read_bytes()
    second = gen.create_google_analytics_report({}, report_title=title)
    expected_title = title or "Google Analytics Report - Acme"
    assert expected_title in _pdf_text(first, tmp_path)
    assert expected_title in _pdf_text(second, tmp_path)
    assert first != second
    assert first.read_bytes() == original
