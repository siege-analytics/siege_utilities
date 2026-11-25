"""Regression tests for #2041 (seaborn coupling) and #2042 (profile-less factory).

#2041: the chart engines imported matplotlib and seaborn under one guard, so a
missing seaborn disabled matplotlib too and every chart silently came back as
a placeholder (a blank 1x1 PNG when matplotlib itself was absent).

#2042: ``create_report_generator()`` raised FileNotFoundError when no user
profile existed, even though ``ReportGenerator`` has its own default output
directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("reportlab")
pytest.importorskip("PIL")

REPO_ROOT = Path(__file__).resolve().parents[1]

ENGINE_MODULES = [
    "siege_utilities.reporting.engines.base_engine",
    "siege_utilities.reporting.engines.bar_engine",
    "siege_utilities.reporting.engines.stats_engine",
    "siege_utilities.reporting.engines.map_engine",
    "siege_utilities.reporting.engines.composite_engine",
    "siege_utilities.reporting.chart_generator",
]

# Runs in a fresh interpreter with seaborn made unimportable before any
# siege_utilities module loads, so the module-level import guards see the
# missing package exactly as they would in a seaborn-free install.
_NO_SEABORN_PRELUDE = textwrap.dedent(
    """
    import sys
    sys.modules["seaborn"] = None  # any `import seaborn` now raises ImportError
    import base64, io, json, warnings
    import matplotlib
    matplotlib.use("Agg")
    from PIL import Image as PILImage

    def png_size(rl_image):
        data_uri = rl_image.filename
        raw = base64.b64decode(data_uri.split(",", 1)[1])
        return list(PILImage.open(io.BytesIO(raw)).size)
    """
)


def _run_without_seaborn(body: str) -> dict:
    """Run ``body`` with seaborn blocked; it must print one JSON object last."""
    script = _NO_SEABORN_PRELUDE + textwrap.dedent(body)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT)] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    env["MPLBACKEND"] = "Agg"
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (
        f"subprocess failed (rc={proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# #2041 -- seaborn missing, matplotlib present
# ---------------------------------------------------------------------------


def test_engine_guards_keep_matplotlib_when_seaborn_is_missing():
    result = _run_without_seaborn(
        f"""
        import importlib
        out = {{}}
        for name in {ENGINE_MODULES!r}:
            mod = importlib.import_module(name)
            out[name] = [
                getattr(mod, "MATPLOTLIB_AVAILABLE", None),
                getattr(mod, "SEABORN_AVAILABLE", None),
            ]
        print(json.dumps(out))
        """
    )
    for name in ENGINE_MODULES:
        assert result[name] == [True, False], (
            f"{name}: expected MATPLOTLIB_AVAILABLE=True and "
            f"SEABORN_AVAILABLE=False with seaborn missing, got {result[name]}"
        )


def test_charts_render_real_images_without_seaborn():
    result = _run_without_seaborn(
        """
        import pandas as pd
        from siege_utilities.reporting.chart_generator import ChartGenerator

        placeholder_calls = []
        original = ChartGenerator._create_placeholder_chart

        def spy(self, *args, **kwargs):
            placeholder_calls.append([repr(a) for a in args] + [repr(kwargs)])
            return original(self, *args, **kwargs)

        ChartGenerator._create_placeholder_chart = spy
        gen = ChartGenerator()

        sizes = {}
        sizes["bar"] = png_size(gen.create_bar_chart(
            {"category": ["a", "b", "c"], "value": [3, 1, 2]},
            x_column="category", y_column="value", title="bar"))
        sizes["heatmap"] = png_size(gen.create_heatmap(
            pd.DataFrame({"x": ["a", "a", "b", "b"], "y": ["p", "q", "p", "q"],
                          "v": [1.0, 2.0, 3.0, 4.0]}),
            x_column="x", y_column="y", value_column="v", title="heat"))
        sizes["correlation_heatmap"] = png_size(gen.create_heatmap(
            pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 5, 9], "c": [9, 3, 2, 1]}),
            title="corr"))
        print(json.dumps({"sizes": sizes, "placeholder_calls": placeholder_calls}))
        """
    )
    assert result["placeholder_calls"] == [], (
        "charts fell back to a placeholder with matplotlib present: "
        f"{result['placeholder_calls']}"
    )
    for kind, (w, h) in result["sizes"].items():
        assert w > 1 and h > 1, f"{kind} chart is a {w}x{h} image"


def test_root_chart_facade_does_not_require_seaborn():
    result = _run_without_seaborn(
        """
        import pandas as pd
        import siege_utilities as su

        fn = su.create_heatmap
        wrapped = bool(getattr(fn, "__siege_optional_dependency_wrapper__", False))
        size = None
        if not wrapped:
            size = png_size(fn(
                pd.DataFrame({"a": [1, 2, 3], "b": [3, 1, 2]}), title="root"))
        print(json.dumps({"wrapped": wrapped, "size": size}))
        """
    )
    assert result["wrapped"] is False, (
        "siege_utilities.create_heatmap was replaced by a missing-dependency "
        "wrapper although only seaborn (optional) is missing"
    )
    w, h = result["size"]
    assert w > 1 and h > 1


def test_polling_heatmap_renders_without_seaborn():
    result = _run_without_seaborn(
        """
        import pandas as pd
        from siege_utilities.reporting.analytics.polling_analyzer import PollingAnalyzer

        crosstab = pd.DataFrame(
            {"Yes": [30, 12], "No": [5, 20]}, index=["North", "South"])
        fig = PollingAnalyzer().create_heatmap_visualization(
            crosstab, title="poll", metric="count")
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        texts = sorted(t.get_text() for t in fig.axes[0].texts)
        print(json.dumps({"size": list(PILImage.open(buf).size), "texts": texts}))
        """
    )
    w, h = result["size"]
    assert w > 1 and h > 1
    assert result["texts"] == ["12", "20", "30", "5"]


def test_matplotlib_heatmap_fallback_matches_seaborn_layout():
    """Without seaborn, cells, labels and annotations follow seaborn's layout."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    from siege_utilities.reporting._heatmap import matplotlib_heatmap

    data = pd.DataFrame(
        [[1.0, float("nan")], [3.0, 4.25]],
        index=pd.Index(["r1", "r2"], name="rows"),
        columns=pd.Index(["c1", "c2"], name="cols"),
    )
    fig, ax = plt.subplots()
    try:
        matplotlib_heatmap(ax, data, cmap="YlOrRd", fmt=".2g")
        assert [t.get_text() for t in ax.get_xticklabels()] == ["c1", "c2"]
        assert [t.get_text() for t in ax.get_yticklabels()] == ["r1", "r2"]
        assert ax.get_xlabel() == "cols"
        assert ax.get_ylabel() == "rows"
        # First row is drawn at the top, as seaborn does.
        assert ax.get_ylim() == (2.0, 0.0)
        annotations = {(t.get_position(), t.get_text()) for t in ax.texts}
        assert annotations == {
            ((0.5, 0.5), "1"),
            ((0.5, 1.5), "3"),
            ((1.5, 1.5), "4.2"),
        }
        assert len(fig.axes) == 2, "expected a colorbar axis"
    finally:
        plt.close(fig)


# ---------------------------------------------------------------------------
# #2041 -- placeholders are never silent
# ---------------------------------------------------------------------------


@pytest.fixture
def no_matplotlib(monkeypatch):
    """Simulate a matplotlib-free install for the engine modules."""
    from siege_utilities.reporting.engines import (
        bar_engine,
        base_engine,
        composite_engine,
        map_engine,
        stats_engine,
    )

    for mod in (base_engine, bar_engine, stats_engine, map_engine, composite_engine):
        monkeypatch.setattr(mod, "MATPLOTLIB_AVAILABLE", False)


def _placeholder_warnings(record):
    return [str(w.message) for w in record if "placeholder" in str(w.message)]


@pytest.mark.parametrize(
    "call",
    [
        lambda gen: gen.create_bar_chart(
            {"k": ["a", "b"], "v": [1, 2]}, x_column="k", y_column="v"),
        lambda gen: gen.create_heatmap({"a": [1, 2, 3], "b": [3, 1, 2]}),
        lambda gen: gen.create_scatter_plot(
            {"x": [1, 2], "y": [2, 1]}, x_column="x", y_column="y"),
    ],
    ids=["bar", "heatmap", "scatter"],
)
def test_blank_placeholder_warns_naming_matplotlib(no_matplotlib, call):
    from siege_utilities.reporting.chart_generator import ChartGenerator

    gen = ChartGenerator()
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        image = call(gen)

    assert image is not None
    messages = _placeholder_warnings(record)
    assert messages, "a blank placeholder chart was returned without a warning"
    assert any("matplotlib" in m for m in messages), messages


def test_placeholder_warning_names_the_module_actually_missing(monkeypatch):
    """With matplotlib present, the warning names geopandas, not matplotlib."""
    from siege_utilities.reporting.chart_generator import ChartGenerator
    from siege_utilities.reporting.engines import map_engine

    monkeypatch.setattr(map_engine, "GEOPANDAS_AVAILABLE", False)
    gen = ChartGenerator()
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        gen.create_bivariate_choropleth_matplotlib(
            {"loc": ["a"], "v1": [1], "v2": [2]}, geodata=None,
            location_column="loc", value_column1="v1", value_column2="v2")

    messages = _placeholder_warnings(record)
    assert messages, "placeholder returned without a warning"
    assert all("geopandas" in m for m in messages), messages
    assert not any("matplotlib" in m for m in messages), messages


def test_failed_placeholder_rendering_warns_and_returns_blank_image(monkeypatch):
    """The placeholder's own failure path is not silent either (SU-4b)."""
    import base64
    import io

    from PIL import Image as PILImage

    from siege_utilities.reporting.chart_generator import ChartGenerator
    from siege_utilities.reporting.engines import base_engine

    def failing_subplots(*args, **kwargs):
        raise ValueError("simulated figure failure")

    gen = ChartGenerator()
    monkeypatch.setattr(base_engine.plt, "subplots", failing_subplots)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        image = gen._create_placeholder_chart(4, 3, "Map saved to example.html")

    messages = [str(w.message) for w in record]
    assert any(
        "placeholder chart rendering failed" in m and "simulated figure failure" in m
        for m in messages
    ), messages
    raw = base64.b64decode(image.filename.split(",", 1)[1])
    assert PILImage.open(io.BytesIO(raw)).size == (1, 1)


def test_informational_placeholder_does_not_warn_when_matplotlib_present():
    """The saved-map notice is a placeholder by design, not a failure."""
    from siege_utilities.reporting.chart_generator import ChartGenerator

    gen = ChartGenerator()
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        gen._create_placeholder_chart(4, 3, "Map saved to example.html")
    assert _placeholder_warnings(record) == []


# ---------------------------------------------------------------------------
# #2042 -- create_report_generator with no user profile
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SIEGE_USERNAME", raising=False)
    monkeypatch.setenv("USER", "no-profile-user")
    monkeypatch.chdir(work)
    return home, work


@pytest.mark.parametrize("client_code", [None, "acme"])
def test_create_report_generator_without_profile_uses_constructor_default(
    clean_home, client_code
):
    from siege_utilities.reporting import create_report_generator
    from siege_utilities.reporting.report_generator import ReportGenerator

    home, work = clean_home
    assert not (home / ".siege_utilities" / "profiles").exists()

    generator = create_report_generator("Acme", client_code)

    assert isinstance(generator, ReportGenerator)
    # ReportGenerator's own default (``output_dir or Path.cwd() / "reports"``).
    assert generator.output_dir == work / "reports"
    assert generator.output_dir.is_dir()
    assert not (home / "Downloads").exists()


def test_create_report_generator_without_profile_logs_the_fallback(
    clean_home, caplog
):
    from siege_utilities.reporting import create_report_generator

    _, work = clean_home
    with caplog.at_level("WARNING", logger="siege_utilities.reporting"):
        create_report_generator("Acme")
    assert any(
        "no-profile-user" in r.getMessage() and str(work / "reports") in r.getMessage()
        for r in caplog.records
    ), [r.getMessage() for r in caplog.records]


@pytest.mark.parametrize("client_code", [None, "acme"])
def test_create_powerpoint_generator_without_profile_uses_constructor_default(
    clean_home, client_code
):
    pytest.importorskip("pptx")
    from siege_utilities.reporting import create_powerpoint_generator
    from siege_utilities.reporting.powerpoint_generator import PowerPointGenerator

    home, work = clean_home
    assert not (home / ".siege_utilities" / "profiles").exists()

    generator = create_powerpoint_generator("Acme", client_code)

    assert isinstance(generator, PowerPointGenerator)
    # PowerPointGenerator's own default (``output_dir or Path.cwd() / "presentations"``).
    assert generator.output_dir == work / "presentations"
    assert generator.output_dir.is_dir()
    assert not (home / "Downloads").exists()


def test_create_powerpoint_generator_without_profile_logs_the_fallback(
    clean_home, caplog
):
    pytest.importorskip("pptx")
    from siege_utilities.reporting import create_powerpoint_generator

    _, work = clean_home
    with caplog.at_level("WARNING", logger="siege_utilities.reporting"):
        create_powerpoint_generator("Acme")
    assert any(
        "no-profile-user" in r.getMessage()
        and str(work / "presentations") in r.getMessage()
        for r in caplog.records
    ), [r.getMessage() for r in caplog.records]
