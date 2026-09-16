"""Canonical root-import contracts for distributed transform helpers."""

from siege_utilities.distributed import clean_and_reorder_bbox
from siege_utilities.distributed import pivot_summary_with_metrics


class Expr:
    def __init__(self, text):
        self.text = text

    def __getitem__(self, item):
        return Expr(f"{self.text}[{item}]")

    def cast(self, data_type):
        return Expr(f"cast({self.text} as {data_type})")

    def __repr__(self):
        return self.text


class ChainFrame:
    def __init__(self):
        self.with_columns = []

    def withColumn(self, name, expression):
        self.with_columns.append((name, repr(expression)))
        return self


class Row(dict):
    pass


class Grouped:
    def __init__(self, frame, group_cols):
        self.frame = frame
        self.group_cols = group_cols
        self.pivot_col = None

    def pivot(self, pivot_col):
        self.pivot_col = pivot_col
        return self

    def count(self):
        if self.pivot_col:
            return PivotFrame()
        return TotalFrame()


class PivotFrame:
    def join(self, total_df, on):
        assert isinstance(total_df, TotalFrame)
        assert on == ["region"]
        return AggregatedFrame()


class TotalFrame:
    def withColumnRenamed(self, old, new):
        assert (old, new) == ("count", "Total")
        return self


class AggregatedFrame:
    columns = ["region", "A", "B", "Total"]

    def collect(self):
        return [Row(region="North", A=2, B=None, Total=4)]


class PivotSourceFrame:
    def __init__(self):
        self.grouped_frames = []

    def groupBy(self, *group_cols):
        grouped = Grouped(self, group_cols)
        self.grouped_frames.append(grouped)
        return grouped


class CreatedFrame:
    def __init__(self):
        self.selected = None

    def select(self, *columns):
        self.selected = columns
        return self


class Spark:
    def __init__(self):
        self.created_rows = None
        self.created_frame = CreatedFrame()

    def createDataFrame(self, rows):
        self.created_rows = rows
        return self.created_frame


def test_clean_and_reorder_bbox_builds_expected_derived_columns(monkeypatch):
    from siege_utilities.distributed import spark_utils

    monkeypatch.setattr(
        spark_utils,
        "col",
        lambda name: Expr(name),
        raising=False,
    )
    monkeypatch.setattr(
        spark_utils,
        "translate",
        lambda expr, old, new: Expr(f"translate({expr},{old},{new})"),
        raising=False,
    )
    monkeypatch.setattr(
        spark_utils,
        "split",
        lambda expr, delimiter: Expr(f"split({expr},{delimiter})"),
        raising=False,
    )
    monkeypatch.setattr(
        spark_utils,
        "array",
        lambda *exprs: Expr("array(" + ",".join(map(repr, exprs)) + ")"),
        raising=False,
    )
    frame = ChainFrame()

    result = clean_and_reorder_bbox(frame, "bbox")

    assert result is frame
    assert frame.with_columns == [
        ("bbox_cleaned", "translate(bbox,[],)"),
        ("bbox_split", "split(bbox_cleaned,,)"),
        ("bbox_min_lat", "cast(bbox_split[0] as double)"),
        ("bbox_max_lat", "cast(bbox_split[1] as double)"),
        ("bbox_min_lon", "cast(bbox_split[2] as double)"),
        ("bbox_max_lon", "cast(bbox_split[3] as double)"),
        (
            "bbox_reordered",
            "array(bbox_min_lon,bbox_min_lat,bbox_max_lon,bbox_max_lat)",
        ),
    ]


def test_pivot_summary_with_metrics_builds_count_percent_total_rows():
    spark = Spark()
    source = PivotSourceFrame()

    result = pivot_summary_with_metrics(
        source,
        "region",
        "category",
        spark,
    )

    assert [grouped.group_cols for grouped in source.grouped_frames] == [
        ("region",),
        ("region",),
    ]
    assert source.grouped_frames[0].pivot_col == "category"
    assert source.grouped_frames[1].pivot_col is None
    assert result is spark.created_frame
    assert spark.created_rows == [
        {"Metric": "Count", "A": 2.0, "B": 0.0, "region": "North"},
        {"Metric": "Percentage (%)", "A": 50.0, "B": 0.0, "region": "North"},
        {"Metric": "Total", "A": 4.0, "B": 4.0, "region": "North"},
    ]
    assert spark.created_frame.selected == ("region", "Metric", "A", "B")
