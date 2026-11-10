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

from siege_utilities.analytics._social_protocol import SocialMediaError
from siege_utilities.reporting.chart_generator import ChartGenerator
from siege_utilities.reporting.report_generator import ReportGenerator

log = logging.getLogger(__name__)

__all__ = [
    "SocialMediaReportGenerator",
]


def _known_sum(values) -> Any:
    """Sum available values, preserving unknown when none are available."""
    known = [value for value in values if pd.notna(value)]
    return sum(known) if known else None


def _format_metric(value: Any, spec: str = ",") -> str:
    return format(value, spec) if pd.notna(value) else "unavailable"


def _retrieval_error(operation: str, platform: str, exc: Exception) -> SocialMediaError:
    """Name the platform, operation and error type without the error's text.

    Connector errors can carry request URLs or headers with access tokens, so
    their text is never copied. Callers raise this ``from None`` so the original
    error is not chained into tracebacks either.
    """
    return SocialMediaError(
        f"Failed to get {operation} from {platform} ({type(exc).__name__})"
    )


def _numeric_likes(posts: pd.DataFrame) -> pd.Series:
    """Like counts as numbers; unparseable or missing counts become NaN."""
    return pd.to_numeric(posts.get("like_count", pd.Series(dtype=float)), errors="coerce")


def _numeric_count(value: Any) -> int | float | None:
    """An account count as a number; missing or unparseable counts become None.

    Connectors may return counts as text (``"1200"``), so every report section
    reads counts through this helper instead of the raw value.
    """
    number = pd.to_numeric(pd.Series([value], dtype=object), errors="coerce").iloc[0]
    if pd.isna(number):
        return None
    return int(number) if float(number).is_integer() else float(number)


def _followers(info: dict[str, Any]) -> int | float | None:
    return _numeric_count(info.get("followers_count"))


def _following(info: dict[str, Any]) -> int | float | None:
    return _numeric_count(info.get("following_count", info.get("follows_count")))


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
        *,
        posts_limit: int = 50,
    ) -> Path:
        """Generate a cross-platform social media PDF report.

        Args:
            connectors: Authenticated SocialMediaProtocol instances.
            start_date: Inclusive start of the reporting window.
            end_date: Inclusive end of the reporting window.
            title: Custom report title. Defaults to
                ``"Social Media Report — {client_name}"``.
            posts_limit: Positive maximum number of recent posts to retrieve
                per platform. Defaults to 50. Post counts, likes, rankings and
                averages describe this sample, not the full reporting window.

        Returns:
            Path to the generated PDF.

        Raises:
            SocialMediaError: if any connector fails during data retrieval.
            ValueError: if posts_limit is not a positive integer.
        """
        if isinstance(posts_limit, bool) or not isinstance(posts_limit, int) or posts_limit <= 0:
            raise ValueError("posts_limit must be a positive integer")
        if not title:
            title = f"Social Media Report — {self.client_name}"

        platform_data = self._collect_platform_data(connectors, start_date, end_date, posts_limit)
        report_data = self._build_report_data(platform_data, start_date, end_date, posts_limit)

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
        posts_limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Pull data from each connector and return normalized dicts."""
        results: list[dict[str, Any]] = []
        for conn in connectors:
            platform = conn.platform_name
            log.info("Collecting data from %s", platform)

            try:
                account_info = conn.get_account_info()
            except Exception as exc:
                raise _retrieval_error("account info", platform, exc) from None

            try:
                insights_df = conn.get_account_insights(start_date, end_date)
            except Exception as exc:
                raise _retrieval_error("account insights", platform, exc) from None

            try:
                posts_df = conn.get_posts(start_date, end_date, limit=posts_limit)
            except Exception as exc:
                raise _retrieval_error("posts", platform, exc) from None

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
        posts_limit: int = 50,
    ) -> dict[str, Any]:
        """Assemble the report payload expected by ReportGenerator."""
        return {
            "executive_summary": self._executive_summary(platform_data, start_date, end_date, posts_limit),
            "metrics": self._aggregate_metrics(platform_data, posts_limit),
            "charts": self._build_charts(platform_data),
            "tables": self._build_tables(platform_data, posts_limit),
            "insights": self._generate_insights(platform_data),
        }

    def _executive_summary(
        self,
        platform_data: list[dict[str, Any]],
        start_date: date,
        end_date: date,
        posts_limit: int = 50,
    ) -> str:
        platforms = [d["platform"] for d in platform_data]
        total_followers = _known_sum(_followers(d["account_info"]) for d in platform_data)
        total_posts = sum(len(d["posts"]) for d in platform_data)

        return (
            f"Cross-platform social media report for {self.client_name} "
            f"covering {start_date} through {end_date}. "
            f"Analyzed {len(platforms)} platform(s) ({', '.join(platforms)}) "
            f"with {_format_metric(total_followers)} total followers and {total_posts:,} "
            f"posts analyzed (most recent up to {posts_limit:,} per platform "
            f"within the reporting window). Post metrics describe this sample."
        )

    def _aggregate_metrics(
        self, platform_data: list[dict[str, Any]], posts_limit: int = 50,
    ) -> dict[str, Any]:
        metrics: dict[str, Any] = {}

        total_followers = _known_sum(_followers(d["account_info"]) for d in platform_data)
        total_posts = 0
        for d in platform_data:
            info = d["account_info"]
            platform = d["platform"]
            followers = _followers(info)

            metrics[f"{platform} — Followers"] = {
                "value": _format_metric(followers),
                "change": "N/A",
                "status": "stable",
            }

            post_count = len(d["posts"])
            total_posts += post_count
            metrics[f"{platform} — Posts analyzed (most recent up to {posts_limit:,})"] = {
                "value": f"{post_count:,}",
                "change": "N/A",
                "status": "stable",
            }

        metrics["Total Followers (all platforms)"] = {
            "value": _format_metric(total_followers),
            "change": "N/A",
            "status": "stable",
        }
        metrics[f"Posts analyzed (all platforms; most recent up to {posts_limit:,} each)"] = {
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
        followers = [_followers(d["account_info"]) for d in platform_data]
        if any(f is not None and f > 0 for f in followers):
            charts.append({
                "type": "bar",
                "title": "Followers by Platform",
                "data": {
                    "labels": platforms,
                    "datasets": [{"label": "Followers", "data": followers}],
                },
            })

        # Cross-platform engagement comparison (posts with like_count)
        engagement: list[int | None] = []
        for d in platform_data:
            posts = d["posts"]
            if isinstance(posts, pd.DataFrame) and not posts.empty:
                total = _known_sum(_numeric_likes(posts))
                engagement.append(int(total) if total is not None else None)
            else:
                engagement.append(0)

        if any(e is not None and e > 0 for e in engagement):
            charts.append({
                "type": "bar",
                "title": "Likes from analyzed posts by Platform",
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
                    c for c in insights.select_dtypes(include="number").columns
                    if c != "date"
                ]
                if numeric_cols:
                    datasets = []
                    for col in numeric_cols[:3]:
                        datasets.append({
                            "label": col.replace("_", " ").title(),
                            "data": [value if pd.notna(value) else None for value in insights[col]],
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
        self, platform_data: list[dict[str, Any]], posts_limit: int = 50,
    ) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []

        # Platform comparison table
        comparison_data: list[list[str]] = []
        for d in platform_data:
            info = d["account_info"]
            comparison_data.append([
                d["platform"].replace("_", " ").title(),
                _format_metric(_followers(info)),
                _format_metric(_following(info)),
                str(len(d["posts"])),
            ])

        if comparison_data:
            tables.append({
                "title": "Platform Comparison",
                "headers": [
                    "Platform", "Followers", "Following",
                    f"Posts analyzed (most recent up to {posts_limit:,})",
                ],
                "data": comparison_data,
            })

        # Top posts per platform
        for d in platform_data:
            posts = d["posts"]
            if isinstance(posts, pd.DataFrame) and not posts.empty:
                sort_col = "like_count" if "like_count" in posts.columns else None
                if sort_col:
                    # Rank by numeric likes; unknown likes sort last and are
                    # still listed as "unavailable".
                    top = posts.sort_values(
                        sort_col, ascending=False, kind="stable", na_position="last",
                        key=lambda s: pd.to_numeric(s, errors="coerce"),
                    ).head(10)
                else:
                    top = posts.head(10)

                post_rows: list[list[str]] = []
                for _, row in top.iterrows():
                    text = str(row.get("text", ""))[:80]
                    if len(str(row.get("text", ""))) > 80:
                        text += "…"
                    post_rows.append([
                        text,
                        _format_metric(row.get("like_count"), ""),
                        _format_metric(row.get("comments_count", row.get("reply_count")), ""),
                        str(row.get("published_at", ""))[:10],
                    ])

                tables.append({
                    "title": f"Top analyzed posts — {d['platform'].replace('_', ' ').title()}",
                    "headers": ["Post", "Likes", "Comments/Replies", "Date"],
                    "data": post_rows,
                })

        return tables

    def _generate_insights(
        self, platform_data: list[dict[str, Any]]
    ) -> list[str]:
        insights: list[str] = []

        known_audiences = [
            (d, followers) for d in platform_data
            if (followers := _followers(d["account_info"])) is not None
        ]
        if len(platform_data) > 1 and known_audiences:
            best, best_followers = max(known_audiences, key=lambda pair: pair[1])
            insights.append(
                f"{best['platform'].replace('_', ' ').title()} has the largest "
                f"audience with {_format_metric(best_followers)} followers."
            )

        for d in platform_data:
            posts = d["posts"]
            if isinstance(posts, pd.DataFrame) and not posts.empty:
                if "like_count" in posts.columns:
                    likes = _numeric_likes(posts)
                    known_likes = likes.dropna()
                    avg_likes = known_likes.mean() if not known_likes.empty else None
                    insights.append(
                        f"{d['platform'].replace('_', ' ').title()}: average "
                        f"{_format_metric(avg_likes, ',.0f')} likes per post among {len(posts)} analyzed posts "
                        "(excluding missing like counts)."
                    )

                    if known_likes.empty:
                        continue
                    # Select by position: connector frames may repeat index
                    # labels, and a label lookup would return several rows.
                    likes_by_position = likes.reset_index(drop=True)
                    top_position = likes_by_position.idxmax()
                    top = posts.iloc[top_position]
                    text_preview = str(top.get("text", ""))[:60]
                    if text_preview:
                        insights.append(
                            f"Top performing {d['platform']} post among analyzed posts: "
                            f'"{text_preview}…" with {int(likes_by_position.iloc[top_position]):,} likes.'
                        )

        return insights
