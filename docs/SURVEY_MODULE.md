# Survey Module — Design Reference

`siege_utilities.survey` is a professional survey/crosstab report engine for Python 3.12+.
It produces polished tables, charts, and geographic representations from respondent-level
DataFrames, and assembles them into structured report arguments that can be rendered to
PDF, PowerPoint, or Google Slides.

---

## Contents

- [Why a survey module in siege_utilities?](#why)
- [Architecture: Stack → Cluster → Chain → View](#architecture)
- [The Argument pattern](#argument-pattern)
- [Table type taxonomy](#table-types)
- [RIM weighting: the weightipy decision](#weightipy)
- [Geography-first design](#geography)
- [Significance testing](#significance)
- [Integration with existing SU primitives](#integration)
- [Installation](#installation)
- [Quick start](#quick-start)
- [API reference summary](#api)

---

## Why a survey module in siege_utilities? {#why}

Electoral and public-opinion data arrives as survey microdata: one row per respondent,
columns for demographics and question responses. The canonical workflow is:

1. Weight respondents to known population targets (RIM/raking)
2. Cross-tabulate question responses against demographic breaks
3. Test for statistical significance
4. Render tables + charts + geographic maps
5. Assemble into a slide deck or PDF

No maintained Python library covered this workflow end-to-end as of early 2026
(see [ADR: why not Quantipy3](archive/design/survey-module-adr.md)), so we built
the module fresh inside siege_utilities, reusing existing SU primitives wherever
possible.

---

## Architecture: Stack → Cluster → Chain → View {#architecture}

The hierarchy mirrors the one Quantipy3 adopted from UNICOM Intelligence's OSCAR platform,
which has been the industry standard for commercial survey reporting for 20+ years.
We adopted the naming and the conceptual layers but wrote every line from scratch.

```text
Stack
└── Cluster  (one report section / deck section)
    └── Chain  (one cross-tabulation slide: question × breaks)
        └── View  (one cell: count, pct, sig flag)
```

### Stack

The complete report. Holds all `Cluster` objects and a shared `WeightScheme`.

```python
from siege_utilities.survey.models import Stack, Cluster, WeightScheme

stack = Stack(
    name="TX Senate Donor Analysis 2026",
    weight_scheme=WeightScheme(targets={
        "geography": {"Travis": 0.28, "Harris": 0.32, "Bexar": 0.15, "other": 0.25},
    }),
)
```

### Cluster

A named group of Chains. Maps to one section of the final report.

```python
donor_profile = Cluster(name="Donor Profile")
stack.add_cluster(donor_profile)
```

### Chain

One cross-tabulation: a single question (`row_var`) broken by one or more demographic
columns (`break_vars`). Carries the `TableType`, `base_note`, and optional `geo_column`
that triggers map generation.

```python
from siege_utilities.survey.crosstab import build_chain
from siege_utilities.reporting.pages.page_models import TableType

chain = build_chain(
    df,
    row_var="party_id",
    break_vars=["county", "cycle"],
    table_type=TableType.CROSS_TAB,
    geo_column="county",
)
```

`Chain.to_dataframe()` renders the cross-tab as a display-ready wide `DataFrame`.
`Chain.to_argument(headline, narrative)` converts it directly to an `Argument`.

### View

The atomic unit: one statistic in one cell.

```python
from siege_utilities.survey.models import View

v = View(metric="Democrat", base=342, count=205.0, pct=0.60)
# v.sig_flag = "B"  # set by column_proportion_test if significantly different from column B
```

---

## The Argument pattern {#argument-pattern}

Every deliverable unit in a report is an `Argument`:
**headline → narrative → table → chart + optional map.**

```text
headline    "Party ID by County — Travis + Harris"
narrative   "Democrats hold a 20-point advantage in Travis County but trail
             in Harris County when donors with multiple cycles are excluded."
table       Chain.to_dataframe()          ← the numbers
chart       matplotlib Figure             ← visual summary
map_figure  ChoroplethFigure or None      ← geographic context
```

The `layout` field auto-resolves:
- `map_figure` present → `"full_width"` (stacked: title / table / figure)
- `map_figure` absent  → `"side_by_side"` (title top, table left, figure right)

```python
from siege_utilities.survey.render import chain_to_argument

arg = chain_to_argument(
    chain,
    headline="Party ID by County",
    narrative="Democrats lead Travis by 20 points.",
)
# arg.layout == "full_width"  because chain.geo_column was set
```

`base_note` and `source_note` attach directly to the Argument and appear as footnotes
below the table in all renderers.

---

## Table type taxonomy {#table-types}

`TableType` is the single most load-bearing design decision in the module.
It drives chart selection, base calculation, significance testing strategy, and
map aggregation. Using the wrong type for a data shape silently produces incorrect
percentages and misleading charts.

| TableType | Percents sum to | Base | Default chart | Map? |
|---|---|---|---|---|
| `SINGLE_RESPONSE` | 100% | Column respondents | Horizontal bar | Yes |
| `MULTIPLE_RESPONSE` | >100% | Respondents (not responses) | **Grouped bar** | Yes |
| `CROSS_TAB` | 100% per column | Column respondents | Grouped bar or heatmap | Yes |
| `LONGITUDINAL` | — | Per-period respondents | Line chart | Yes |
| `RANKING` | — | Total | Sorted horizontal bar | Yes |
| `MEAN_SCALE` | — | Per-cell respondents | Bar with error bars | Sometimes |
| `BANNER` | 100% per column | Column respondents | Small-multiple bars | Yes |

### Multiple response tables — the most commonly mis-styled type

A multiple-response question (e.g. "Select all issues that matter to you") allows
respondents to pick more than one option. **Column percentages will and should exceed
100%.** Three things must be correct:

1. **Base = respondents, not responses.** Dividing by total responses produces
   mathematically meaningless percentages.
2. **Chart = grouped bar, not stacked bar.** A stacked bar implies mutual exclusivity —
   the segments "add up to something." For multiple response data they don't.
3. **Base note is mandatory.** Readers unfamiliar with the question type will assume
   100% sums. The note makes the interpretation explicit.

`build_chain` handles all three automatically for `TableType.MULTIPLE_RESPONSE`:

```python
chain = build_chain(df, "issues", ["geography"],
                    table_type=TableType.MULTIPLE_RESPONSE)
# chain.base_note == "n=1,247 respondents; multiple responses permitted;
#                     percentages sum to more than 100%"
```

### Longitudinal tables — delta column

`build_chain` for `LONGITUDINAL` pivots the time variable to columns and computes
a delta column (last period − first period). The delta key is stored on `chain.delta_column`
so renderers can style it differently (e.g. color by sign).

---

## RIM weighting: the weightipy decision {#weightipy}

### What is RIM weighting?

Raking / Iterative Proportional Fitting (RIM) adjusts respondent weights so the
weighted sample matches known population marginals on multiple variables simultaneously.
It is the standard method for correcting demographic skew in survey data.

Example: a sample of 500 donors over-represents Travis County (40%) relative to the
actual population (28%). RIM weighting adjusts individual weights so that the weighted
total matches the 28% target without destroying the relationship between variables.

### Why weightipy is a real dependency, not just inspiration

We evaluated two approaches:

**Option A — Inspiration only.** Borrow the algorithm, reimplement from scratch.

**Option B — Real dependency.** Take `weightipy` as `pip install siege-utilities[survey]`.

We chose **Option B** for these reasons:

| Factor | Assessment |
|---|---|
| Maintenance status | [weightipy 0.4.2](https://pypi.org/project/weightipy/) released February 2026; Python 3.12 explicit; pandas 3.0 compatible |
| Scope match | weightipy does exactly one thing — raking — and does it correctly |
| Implementation risk | IPF convergence edge cases (non-integer weights, impossible targets, sparse cells) are non-trivial; weightipy has been tested against them |
| Wheel size | weightipy is a pure-Python package with no binary dependencies |
| License | MIT |

Reimplementing a correct, converging IPF from scratch would have added 300–400 lines
of numerical code that we'd own forever. Taking a maintained, tested, MIT-licensed
package as an optional extra costs nothing.

### Keeping it optional

The `[survey]` extra keeps `weightipy` out of the core install:

```toml
[project.optional-dependencies]
survey = ["weightipy>=0.4.0"]
```

```bash
pip install siege-utilities          # no weightipy
pip install siege-utilities[survey]  # includes weightipy
```

`apply_rim_weights()` raises a clear `ImportError` with installation instructions
if called without weightipy installed.

### Usage

```python
from siege_utilities.survey.weights import apply_rim_weights

df = apply_rim_weights(
    df,
    targets={
        "age_group": {"18-34": 0.25, "35-54": 0.40, "55+": 0.35},
        "gender":    {"M": 0.48, "F": 0.52},
        "county":    {"Travis": 0.28, "Harris": 0.32, "Bexar": 0.15, "other": 0.25},
    },
    weight_col="weight",
)
```

Targets per variable must sum to 1.0. `WeightScheme.validate()` raises `ValueError`
immediately if they don't — fail-fast before the iteration starts.

---

## Geography-first design {#geography}

The guiding principle: **every argument should have a map unless it's structurally
impossible to have one.**

Maps are not decorative. In electoral and donor analysis, geography often contains
the key finding — a statewide average conceals a Travis/Harris split that changes
the strategic recommendation. The table and chart show the numbers; the map shows
where the story is happening.

Every `Chain` has a `geo_column` field. When set:
- `chain_to_argument()` calls the choropleth builder and attaches `map_figure`
- `Argument.__post_init__` auto-sets `layout = "full_width"`
- Google Slides renderer uses the stacked layout (more vertical space for the map)

**Exceptions** — types where a map is structurally problematic:
- Flow analysis (inter-committee transfer networks) — relationship between nodes, not geography of nodes
- Pure ratios or derived metrics with no geographic granularity in the source data

For all other types, `geo_column` should be set.

---

## Significance testing {#significance}

Two methods are provided, for different purposes:

### Column proportion test (`column_proportion_test`)

Tests each pair of columns using a two-proportion z-test. When column j's proportion
for a row category is significantly higher than column i's (at `alpha`), column i's
letter label is appended to column j's `sig_flag`.

This is the SPSS/Dimensions-style ABC annotation used in commercial survey tables.

```python
from siege_utilities.survey.significance import column_proportion_test

chain = column_proportion_test(chain, alpha=0.05)
# chain.views["county=Travis"][0].sig_flag == "B"
# means Travis is significantly higher than Harris on this metric
```

Requires `scipy` (in the `[analytics]` extra). Falls back to `z_crit = 1.96` if scipy
is absent, which is equivalent to `alpha=0.05` for large samples.

### Chi-square flag (`chi_square_flag`)

Tests the entire cross-tabulation table for any statistically significant association
using chi-square. Sets `chain.chi_square_significant` and `chain.chi_square_p`.

Delegates to `siege_utilities.data.cross_tabulation.chi_square_test` — the existing
SU implementation — rather than reimplementing it.

```python
from siege_utilities.survey.significance import chi_square_flag

chain = chi_square_flag(chain, alpha=0.05)
if chain.chi_square_significant:
    print(f"Significant association (p={chain.chi_square_p:.4f})")
```

---

## Integration with existing SU primitives {#integration}

The survey module delegates to existing SU infrastructure; it does not duplicate it.

| Need | Provided by | Survey module action |
|---|---|---|
| Chi-square test | `data.cross_tabulation.chi_square_test` | Calls directly |
| Choropleth map | `reporting.chart_generator.ChartGenerator` | Calls `create_choropleth_map` |
| Google Slides output | `analytics.google_slides` | `create_argument_slide`, `create_report_from_arguments` |
| Report page models | `reporting.pages.page_models` | Imports `Argument`, `TableType` |

---

## Installation {#installation}

```bash
# Core only (TableType, Argument, Chain, build_chain — no weighting)
pip install siege-utilities

# With RIM weighting support
pip install siege-utilities[survey]

# With full reporting stack (charts, maps, Slides)
pip install siege-utilities[survey,reporting,analytics]
```

---

## Quick start {#quick-start}

```python
import pandas as pd
from siege_utilities.survey.crosstab import build_chain
from siege_utilities.survey.render import chain_to_argument, stack_to_arguments
from siege_utilities.survey.weights import apply_rim_weights
from siege_utilities.survey.models import Stack, Cluster, WeightScheme
from siege_utilities.reporting.pages.page_models import TableType

# 1. Load respondent-level data
df = pd.read_csv("donors_2024.csv")

# 2. Apply RIM weights (optional)
df = apply_rim_weights(df, targets={
    "county": {"Travis": 0.28, "Harris": 0.32, "Bexar": 0.15, "other": 0.25},
})

# 3. Build chains
party_chain = build_chain(
    df, row_var="party_id", break_vars=["county"],
    table_type=TableType.CROSS_TAB,
    weight_var="weight",
    geo_column="county",
)

issues_chain = build_chain(
    df, row_var="top_issue", break_vars=["county"],
    table_type=TableType.MULTIPLE_RESPONSE,
    weight_var="weight",
    geo_column="county",
)

# 4. Assemble into a Stack
stack = Stack(name="TX Donor Profile 2024")
cluster = Cluster(name="Demographics")
cluster.add_chain(party_chain).add_chain(issues_chain)
stack.add_cluster(cluster)

# 5. Convert to Arguments for rendering
party_arg = party_chain.to_argument(
    headline="Party ID by County",
    narrative="Democrats hold a 20-point advantage in Travis County.",
)
# party_arg.layout == "full_width"  (geo_column set → map generated → full_width)
# party_arg.chart  ← grouped bar chart
# party_arg.map_figure ← choropleth

# 6. Render to Google Slides
from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
from siege_utilities.analytics.google_slides import create_report_from_arguments

client = GoogleWorkspaceClient.from_service_account()
pres_id = create_report_from_arguments(
    client,
    title="TX Senate Donor Intelligence — 2024 Cycle",
    arguments=[party_arg, issues_chain.to_argument("Top Issues", "...")],
    theme_presentation_id="YOUR_TEMPLATE_PRES_ID",
)
```

---

## API reference summary {#api}

| Symbol | Module | Description |
|---|---|---|
| `Stack` | `survey.models` | Complete report container |
| `Cluster` | `survey.models` | Named section of a report |
| `Chain` | `survey.models` | One cross-tabulation |
| `View` | `survey.models` | One cell statistic |
| `WeightScheme` | `survey.models` | RIM target marginals |
| `TableType` | `reporting.pages.page_models` | 7-variant table type enum |
| `Argument` | `reporting.pages.page_models` | Atomic report unit (headline+table+chart+map) |
| `build_chain` | `survey.crosstab` | Build a Chain from a DataFrame |
| `apply_rim_weights` | `survey.weights` | RIM/raking weights via weightipy |
| `column_proportion_test` | `survey.significance` | ABC sig markers (z-test) |
| `chi_square_flag` | `survey.significance` | Chi-square association flag |
| `chain_to_argument` | `survey.render` | Chain → Argument (chart + map) |
| `stack_to_arguments` | `survey.render` | Walk full Stack → Arguments |
| `create_argument_slide` | `analytics.google_slides` | Add one Argument slide to Slides |
| `create_report_from_arguments` | `analytics.google_slides` | Full presentation from Arguments |

---

## See also

- [Architecture Decision Record — Survey Module](archive/design/survey-module-adr.md)
- [Multi-Source Tabulation Guide](MULTI_SOURCE_TABULATION_GUIDE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [weightipy on PyPI](https://pypi.org/project/weightipy/)
- [Quantipy3 (archived reference)](https://github.com/Quantipy/quantipy3) — the open-source OSCAR-inspired library we studied; abandoned as of 2023
