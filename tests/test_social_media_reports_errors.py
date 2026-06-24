"""Error-path coverage (SU-4b) for reporting.social_media_reports.

_collect_platform_data wraps each connector call in best-effort handlers; a
connector that raises on every call must degrade to empty data rather than
propagating, exercising all three except blocks.
"""
import datetime
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator


class _FailingConnector:
    platform_name = "fakebook"

    def get_account_info(self):
        raise RuntimeError("info failed")

    def get_account_insights(self, start, end):
        raise RuntimeError("insights failed")

    def get_posts(self, start, end, limit=50):
        raise RuntimeError("posts failed")


def test_collect_platform_data_degrades_on_connector_failures():
    gen = SocialMediaReportGenerator("client")
    out = gen._collect_platform_data(
        [_FailingConnector()], datetime.date(2024, 1, 1), datetime.date(2024, 1, 31)
    )
    assert isinstance(out, list) and len(out) == 1
