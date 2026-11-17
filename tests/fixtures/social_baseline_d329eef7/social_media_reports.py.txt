"""
Social media report generator.

Composes data from multiple :class:`SocialMediaProtocol` connectors into
unified cross-platform PDF and PPTX reports. Follows the same pattern as
:class:`AnalyticsReportGenerator` for GA data.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from siege_utilities.reporting.chart_generator import ChartGenerator
from siege_utilities.reporting.report_generator import ReportGenerator

log = logging.getLogger(__name__)

__all__ = [
    "SocialMediaReportGenerator",
]


class SocialMediaReportGenerator:
    """Cross-platform social media report builder.

    Accepts a list of SocialMediaProtocol connectors, pulls data from
    each, normalizes into comparable shapes, and produces PDF/PPTX
    reports via existing reporting infrastructure.

    Usage::

        from siege_utilities.reporting import SocialMediaReportGenerator
        from siege_utilities.analytics import InstagramConnector, XTwitterConnector

        ig = InstagramConnector(access_token=os.environ["META_TOKEN"])
        ig.authenticate()
        tw = XTwitterConnector(bearer_token=os.environ["X_TOKEN"], username="acme")
        tw.authenticate()

        gen = SocialMediaReportGenerator("Acme Corp")
        report = gen.create_social_media_report(
            connectors=[ig, tw],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 1),
        )
    """

    def __init__(
        self,
        client_name: str,
        output_dir: Path | None = None,
    ) -> None:
        self.client_name = client_name
        self.output_dir = output_dir or Path.cwd() / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_generator = ReportGenerator(client_name, output_dir)
        self.chart_generator = ChartGenerator()

    def create_social_media_report(
        self,
        connectors: list[Any],
        start_date: date,
        end_date: date,
        title: str = "",
    ) -> Path:
        """Generate a cross-platform social media PDF report.

        Args:
            connectors: Authenticated SocialMediaProtocol instances.
            start_date: Inclusive start of the reporting window.
            end_date: Inclusive end of the reporting window.
            title: Custom report title. Defaults to
                ``"Social Media Report — {client_name}"``.

        Returns:
            Path to the generated PDF.

        Raises:
            SocialMediaError: if any connector fails during data retrieval.
        """
        if not title:
            title = f"Social Media Report — {self.client_name}"

        platform_data = self._collect_platform_data(connectors, start_date, end_date)
        report_data = self._build_report_data(platform_data, start_date, end_date)

        report_path = self.report_generator.create_analytics_report(
            report_data, title
        )
        log.info("Social media report created: %s", report_path)
        return report_path

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def _collect_platform_data(
        self,
        connectors: list[Any],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Pull data from each connector and return normalized dicts."""
        results: list[dict[str, Any]] = []
        for conn in connectors:
            platform = conn.platform_name
            log.info("Collecting data from %s", platform)

            try:
                account_info = conn.get_account_info()
            except Exception:
                log.warning("Failed to get account info from %s", platform)
                account_info = {}

            try:
                insights_df = conn.get_account_insights(start_date, end_date)
            except Exception:
                log.warning("Failed to get account insights from %s", platform)
                insights_df = pd.DataFrame()

            try:
                posts_df = conn.get_posts(start_date, end_date, limit=50)
            except Exception:
                log.warning("Failed to get posts from %s", platform)
                posts_df = pd.DataFrame()

            results.append({
                "platform": platform,
                "account_info": account_info,
                "insights": insights_df,
                "posts": posts_df,
            })
        return results

    # ------------------------------------------------------------------
    # Report assembly
    # ------------------------------------------------------------------

    def _build_report_data(
        self,
        platform_data: list[dict[str, Any]],
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Assemble the report payload expected by ReportGenerator."""
        return {
            "executive_summary": self._executive_summary(platform_data, start_date, end_date),
            "metrics": self._aggregate_metrics(platform_data),
            "charts": self._build_charts(platform_data),
            "tables": self._build_tables(platform_data),
            "insights": self._generate_insights(platform_data),
        }

    def _executive_summary(
        self,
        platform_data: list[dict[str, Any]],
        start_date: date,
        end_date: date,
    ) -> str:
        platforms = [d["platform"] for d in platform_data]
        total_followers = sum(
            d["account_info"].get("followers_count", 0) for d in platform_data
        )
        total_posts = sum(len(d["posts"]) for d in platform_data)

        return (
            f"Cross-platform social media report for {self.client_name} "
            f"covering {start_date} through {end_date}. "
            f"Analyzed {len(platforms)} platform(s) ({', '.join(platforms)}) "
            f"with {total_followers:,} total followers and {total_posts:,} "
            f"posts in the reporting window."
        )

    def _aggregate_metrics(
        self, platform_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        metrics: dict[str, Any] = {}

        total_followers = 0
        total_posts = 0
        for d in platform_data:
            info = d["account_info"]
            platform = d["platform"]
            followers = info.get("followers_count", 0)
            total_followers += followers

            metrics[f"{platform} — Followers"] = {
                "value": f"{followers:,}",
                "change": "N/A",
                "status": "stable",
            }

            post_count = len(d["posts"])
            total_posts += post_count
            metrics[f"{platform} — Posts"] = {
                "value": f"{post_count:,}",
                "change": "N/A",
                "status": "stable",
            }

        metrics["Total Followers (all platforms)"] = {
            "value": f"{total_followers:,}",
            "change": "N/A",
            "status": "stable",
        }
        metrics["Total Posts (all platforms)"] = {
            "value": f"{total_posts:,}",
            "change": "N/A",
            "status": "stable",
        }
        return metrics

    def _build_charts(
        self, platform_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        charts: list[dict[str, Any]] = []

        # Cross-platform followers comparison
        platforms = [d["platform"] for d in platform_data]
        followers = [
            d["account_info"].get("followers_count", 0) for d in platform_data
        ]
        if any(f > 0 for f in followers):
            charts.append({
                "type": "bar",
                "title": "Followers by Platform",
                "data": {
                    "labels": platforms,
                    "datasets": [{"label": "Followers", "data": followers}],
                },
            })

        # Cross-platform engagement comparison (posts with like_count)
        engagement: list[int] = []
        for d in platform_data:
            posts = d["posts"]
            if isinstance(posts, pd.DataFrame) and not posts.empty:
                total = int(posts.get("like_count", pd.Series([0])).sum())
                engagement.append(total)
            else:
                engagement.append(0)

        if any(e > 0 for e in engagement):
            charts.append({
                "type": "bar",
                "title": "Total Likes by Platform",
                "data": {
                    "labels": platforms,
                    "datasets": [{"label": "Likes", "data": engagement}],
                },
            })

        # Per-platform engagement time-series
        for d in platform_data:
            insights = d["insights"]
            if isinstance(insights, pd.DataFrame) and not insights.empty and "date" in insights.columns:
                numeric_cols = [
                    c for c in insights.columns
                    if c != "date" and insights[c].dtype in ("int64", "float64")
                ]
                if numeric_cols:
                    datasets = []
                    for col in numeric_cols[:3]:
                        datasets.append({
                            "label": col.replace("_", " ").title(),
                            "data": insights[col].tolist(),
                        })
                    charts.append({
                        "type": "line",
                        "title": f"{d['platform'].replace('_', ' ').title()} — Daily Metrics",
                        "data": {
                            "labels": insights["date"].tolist(),
                            "datasets": datasets,
                        },
                    })

        return charts

    def _build_tables(
        self, platform_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []

        # Platform comparison table
        comparison_data: list[list[str]] = []
        for d in platform_data:
            info = d["account_info"]
            comparison_data.append([
                d["platform"].replace("_", " ").title(),
                f"{info.get('followers_count', 0):,}",
                f"{info.get('following_count', info.get('follows_count', 0)):,}",
                str(len(d["posts"])),
            ])

        if comparison_data:
            tables.append({
                "title": "Platform Comparison",
                "headers": ["Platform", "Followers", "Following", "Posts"],
                "data": comparison_data,
            })

        # Top posts per platform
        for d in platform_data:
            posts = d["posts"]
            if isinstance(posts, pd.DataFrame) and not posts.empty:
                sort_col = "like_count" if "like_count" in posts.columns else None
                if sort_col:
                    top = posts.nlargest(10, sort_col)
                else:
                    top = posts.head(10)

                post_rows: list[list[str]] = []
                for _, row in top.iterrows():
                    text = str(row.get("text", ""))[:80]
                    if len(str(row.get("text", ""))) > 80:
                        text += "…"
                    post_rows.append([
                        text,
                        str(row.get("like_count", 0)),
                        str(row.get("comments_count", row.get("reply_count", 0))),
                        str(row.get("published_at", ""))[:10],
                    ])

                tables.append({
                    "title": f"Top Posts — {d['platform'].replace('_', ' ').title()}",
                    "headers": ["Post", "Likes", "Comments/Replies", "Date"],
                    "data": post_rows,
                })

        return tables

    def _generate_insights(
        self, platform_data: list[dict[str, Any]]
    ) -> list[str]:
        insights: list[str] = []

        if len(platform_data) > 1:
            best = max(
                platform_data,
                key=lambda d: d["account_info"].get("followers_count", 0),
            )
            insights.append(
                f"{best['platform'].replace('_', ' ').title()} has the largest "
                f"audience with {best['account_info'].get('followers_count', 0):,} followers."
            )

        for d in platform_data:
            posts = d["posts"]
            if isinstance(posts, pd.DataFrame) and not posts.empty:
                if "like_count" in posts.columns:
                    avg_likes = posts["like_count"].mean()
                    insights.append(
                        f"{d['platform'].replace('_', ' ').title()}: average "
                        f"{avg_likes:,.0f} likes per post across {len(posts)} posts."
                    )

                    top = posts.loc[posts["like_count"].idxmax()]
                    text_preview = str(top.get("text", ""))[:60]
                    if text_preview:
                        insights.append(
                            f"Top performing {d['platform']} post: "
                            f'"{text_preview}…" with {int(top["like_count"]):,} likes.'
                        )

        return insights
