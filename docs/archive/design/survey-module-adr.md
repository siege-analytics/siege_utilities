# ADR: Survey Module Architecture Decisions

**Date:** 2026-04-22  
**Status:** Accepted  
**Authors:** Dheeraj Chand, Steve Blackmon  
**Linear:** SAL-67 (survey module epic)

---

## Context

Electoral and public-opinion data arrives as survey microdata: one row per respondent, columns for demographics and question responses. The canonical workflow is weight → cross-tabulate → test → render → assemble. No maintained Python library covered this workflow end-to-end as of early 2026, so the module was built fresh inside `siege_utilities`.

This ADR captures the four major architectural decisions made during design.

---

## Decision 1 — Why not Quantipy3?

### Options evaluated

| Option | Description |
|---|---|
| **Quantipy3** | Open-source Python port of UNICOM Intelligence's OSCAR platform |
| **Build from scratch** | New module inside `siege_utilities`, inspired by OSCAR hierarchy |

### Assessment of Quantipy3

Quantipy3 ([github.com/Quantipy/quantipy3](https://github.com/Quantipy/quantipy3)) is the canonical open-source Python survey reporting library. We studied it extensively.

| Factor | Status |
|---|---|
| Python version support | Python 3.7 maximum. Incompatible with Python 3.12+. |
| Last meaningful commit | 2021 (minor fixes through mid-2023, then silent). |
| Maintenance | Effectively abandoned. No active maintainer. |
| pandas compatibility | Requires pandas 1.x. Incompatible with pandas 2.0+. |
| Dependency footprint | Heavy non-optional binary dependencies (quantipy's own stack). |
| OSCAR architecture | Sound conceptual model; naming conventions worth preserving. |

Quantipy3's architecture (Stack → DataSet → Chain → View) is sound and battle-tested across 20+ years of commercial survey reporting. We adopted the naming and the layered concept but wrote every line of implementation from scratch to get Python 3.12 / pandas 3.0 compatibility and a clean, minimal dependency surface.

### Decision

**Do not use Quantipy3.** Build fresh, preserving the Stack/Cluster/Chain/View naming and layered concept.

---

## Decision 2 — weightipy: real dependency vs. reimplement

### What RIM weighting is

Raking / Iterative Proportional Fitting (RIM) adjusts respondent weights so the weighted sample matches known population marginals on multiple variables simultaneously. It is the standard method for correcting demographic skew in survey data and a non-negotiable step in the electoral/donor analysis workflow.

### Options evaluated

| Option | Description |
|---|---|
| **Option A — inspiration only** | Study weightipy algorithm, reimplement IPF from scratch inside `siege_utilities` |
| **Option B — real dependency** | Take `weightipy` as `pip install siege-utilities[survey]` |

### Assessment

| Factor | Assessment |
|---|---|
| **Maintenance status** | [weightipy 0.4.2](https://pypi.org/project/weightipy/) released February 2026; Python 3.12 explicit in classifiers; pandas 3.0 compatible |
| **Scope match** | weightipy does exactly one thing — raking — and does it correctly |
| **Implementation risk** | IPF convergence edge cases (non-integer weights, impossible targets, sparse cells) are non-trivial. weightipy has been tested against them |
| **Wheel size** | Pure-Python package. No binary dependencies. Installs everywhere |
| **License** | MIT — permissive, compatible with AGPL-3.0 dual-license model |
| **Maintenance burden** | Owning a correct, converging IPF implementation would add 300–400 lines of numerical code we maintain forever |

### Decision

**Option B — real dependency.** Take weightipy as `pip install siege-utilities[survey]`.

Reimplementing a correct, converging IPF from scratch would add 300–400 lines of numerical code that we'd own forever. Taking a maintained, tested, MIT-licensed package as an optional extra costs nothing.

### Implementation detail

The `[survey]` extra keeps `weightipy` out of the core install:

```toml
[project.optional-dependencies]
survey = ["weightipy>=0.4.0"]
```

`apply_rim_weights()` raises a clear `ImportError` with installation instructions if called without weightipy installed.

---

## Decision 3 — TableType taxonomy

### Problem

Chart selection, base calculation, significance testing strategy, and map aggregation all depend on the *type* of question being cross-tabulated. Using the wrong type for a data shape silently produces incorrect percentages and misleading charts. This needed an explicit, enforced taxonomy.

### Decision

Seven `TableType` variants, implemented as a Python `Enum`:

| TableType | Percents sum to | Base | Default chart |
|---|---|---|---|
| `SINGLE_RESPONSE` | 100% | Column respondents | Horizontal bar |
| `MULTIPLE_RESPONSE` | >100% | Respondents (not responses) | Grouped bar |
| `CROSS_TAB` | 100% per column | Column respondents | Grouped bar or heatmap |
| `LONGITUDINAL` | — | Per-period respondents | Line chart |
| `RANKING` | — | Total | Sorted horizontal bar |
| `MEAN_SCALE` | — | Per-cell respondents | Bar with error bars |
| `BANNER` | 100% per column | Column respondents | Small-multiple bars |

### Critical consequence: MULTIPLE_RESPONSE base calculation

A multiple-response question allows respondents to pick more than one option. **Column percentages will and should exceed 100%.** Three things must be correct:

1. **Base = respondents, not responses.** Dividing by total responses produces mathematically meaningless percentages.
2. **Chart = grouped bar, not stacked bar.** A stacked bar implies mutual exclusivity. For multiple response data the segments do not "add up to something."
3. **Base note is mandatory.** Readers unfamiliar with the question type will assume 100% sums.

`build_chain` enforces all three automatically for `TableType.MULTIPLE_RESPONSE`.

---

## Decision 4 — Argument as the atomic report unit

### Problem

The existing SU reporting pipeline assembled PDFs and slide decks by threading individual charts, tables, and text blocks through low-level layout functions. This made it impossible to swap renderers (PDF → Slides → PowerPoint) without rewriting the assembly logic.

### Decision

Introduce `Argument` as a renderer-agnostic atomic unit:

```
headline    string
narrative   string
table       DataFrame
chart       matplotlib Figure (or None)
map_figure  ChoroplethFigure (or None)
layout      "full_width" | "side_by_side"  (auto-resolved from map presence)
base_note   string (or None)
source_note string (or None)
```

The `layout` field auto-resolves in `__post_init__`:
- `map_figure` present → `"full_width"` (stacked: title / table / figure)
- `map_figure` absent  → `"side_by_side"` (title top, table left, figure right)

Every renderer (PDF, Slides, PowerPoint) accepts a `List[Argument]` and handles layout internally. This means `chain_to_argument()` is renderer-agnostic; the survey module does not need to know which output format will be used.

---

## Decision 5 — Geography-first design

### Principle

**Every argument should have a map unless it is structurally impossible to have one.**

Maps are not decorative. In electoral and donor analysis, geography often contains the key finding — a statewide average conceals a Travis/Harris split that changes the strategic recommendation. The table and chart show the numbers; the map shows where the story is happening.

### Implementation

Every `Chain` has a `geo_column` field. When set, `chain_to_argument()` calls the choropleth builder and attaches `map_figure`, which triggers the `full_width` layout.

**Structural exceptions** where a map is not appropriate:
- Flow analysis (inter-committee transfer networks) — the finding is about relationships between nodes, not the geography of nodes
- Pure ratios or derived metrics with no geographic granularity in the source data

---

## Consequences

- `weightipy` must be listed as an optional dependency and kept current
- `TableType` is the single most load-bearing design decision; wrong type → wrong numbers
- `Argument` is the boundary contract between the survey module and all renderers — its fields must remain stable or be versioned explicitly
- All new question types must be added to `TableType` before being used in `build_chain`

---

## References

- [weightipy on PyPI](https://pypi.org/project/weightipy/)
- [Quantipy3 on GitHub](https://github.com/Quantipy/quantipy3) — archived reference, studied and rejected
- [Survey Module Reference](../SURVEY_MODULE.md)
- [Multi-Source Tabulation Guide](../MULTI_SOURCE_TABULATION_GUIDE.md)
