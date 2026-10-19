"""Connector retrieval failures must stop social report collection (#1469)."""
import datetime

import pytest

from siege_utilities.analytics._social_protocol import SocialMediaError
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator


class _FailingConnector:
    platform_name = "fakebook"

    def get_account_info(self):
        raise RuntimeError("info failed")

    def get_account_insights(self, start, end):
        raise RuntimeError("insights failed")

    def get_posts(self, start, end, limit=50):
        raise RuntimeError("posts failed")


def test_collect_platform_data_raises_on_connector_failures(tmp_path):
    gen = SocialMediaReportGenerator("client", output_dir=tmp_path)
    with pytest.raises(SocialMediaError, match="fakebook.*info failed") as exc:
        gen._collect_platform_data(
            [_FailingConnector()], datetime.date(2024, 1, 1), datetime.date(2024, 1, 31)
        )
    assert isinstance(exc.value.__cause__, RuntimeError)
