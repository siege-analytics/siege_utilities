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
    with pytest.raises(SocialMediaError, match=r"account info from fakebook \(RuntimeError\)") as exc:
        gen._collect_platform_data(
            [_FailingConnector()], datetime.date(2024, 1, 1), datetime.date(2024, 1, 31)
        )
    # The connector's text and the chained cause are withheld: they can carry
    # credentials (see test_1469_social_media_report_totals secret controls).
    assert "info failed" not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__suppress_context__ is True
    assert exc.value.__context__ is None
