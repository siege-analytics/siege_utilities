# Self-review: report generator facades produce real PDFs (#1461, PR #1734)

Scope of this artifact: the PR as a whole at its code head 6cf13493, plus the process-only commit that syncs with develop and adds this file. The process commit changes `CHANGELOG.md` conflict handling and this document and no library code.

Review-Tier: A for the process commit (documentation only). The code commits under review were reviewed independently at an earlier head by the external reviewer.

## Assumptions

- Goal source: ticket #1461. The social-media and analytics report facades must write real PDFs through the existing renderer, return their `Path`, and keep their collected metrics, tables, insights and charts.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the earlier approval on the ticket.
- The code diff against `origin/develop` after the sync touches `siege_utilities/reporting/_facade_content.py`, `analytics_reports.py`, `social_media_reports.py`, `docs/source/packages/reporting.rst`, two test files and `CHANGELOG.md`. This commit adds no library code.
- The #1461 note already sits in `CHANGELOG.md` under `[4.1.0]` Fixed. The only conflict with develop was in that section; it was settled by keeping the #1461 entry and every develop entry, with no wording changed.
- Pre-author-inventory: NONE. Trivial-against-state: `git diff origin/develop -- CHANGELOG.md` shows only the #1461 entry as an addition after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_reporting_facade_content.py test_reporting_facades_produce_pdf.py` -> 14 passed in 34.78s. The facade tests use the real `ReportGenerator`.
- Hosted CI at the pushed head is recorded in the PR body once it finishes. The CI run cited in the earlier body belongs to an old head and is superseded.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1461 entry under `[4.1.0]` and none under `[Unreleased]`.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Review round after the develop sync (develop 71f02b0b)

Develop was merged additively; the only conflict was `CHANGELOG.md`, resolved by keeping the develop #1444 entry and the #1461 entry. No develop behavior disagrees with this PR. Two CodeRabbit threads were open and both were valid:

- 4309128042 (`_facade_content.py`): `_chart_images` returned `[]` for empty labels before it looked at the chart type, so `{"type": "doughnut", "data": {"labels": []}}` produced a PDF with no error. The type is now checked first against `_SUPPORTED_CHART_TYPES`; a supported type with no labels still draws nothing, and the final unreachable `raise` is gone. New tests: `test_unsupported_chart_type_raises_even_without_labels` (empty labels, and no `labels` key) and `test_supported_chart_type_without_labels_draws_nothing` for bar, line and pie.
- 4309128046 (`test_reporting_facades_produce_pdf.py`): the PDF tests read extracted text only, so a PDF with no rendered chart could pass. `_embedded_image_count` counts `/Image` XObjects, and `test_chart_bearing_facade_pdf_embeds_an_image_and_a_chartless_one_does_not` requires at least one for a monthly report that carries a chart and zero for a website report that carries none (a control, so the assertion cannot pass vacuously).

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_reporting_facade_content.py test_reporting_facades_produce_pdf.py -q` -> 20 passed in 31.82s (14 before, plus 6 new cases).

Red controls at this head: with `_facade_content.py` restored to the previous head (`git checkout HEAD -- siege_utilities/reporting/_facade_content.py` while the merge was in progress), `python -m pytest test_reporting_facade_content.py -q` gave 2 failed, 5 passed in 29.10s (the two empty-labels cases). With the fixed file and `labels = []` forced in `_chart_images`, so every chart is silently dropped, `python -m pytest test_reporting_facades_produce_pdf.py -q` gave 1 failed, 12 passed in 29.34s: only the new image test failed and every text-based test still passed, which is the gap the reviewer described. Both edits were reverted and the fixed file passed.

CHANGELOG classification: on v4.0.0 these facades called a `ReportGenerator` method with a different signature or methods that do not exist, wrote no PDF, and either raised or returned a content dictionary. Callers now get a real `Path`, so caller-visible behavior changed; the entry is under `### BREAKING` in `[4.1.0]` with a Migration line, and the Fixed entry remains. The PR body classification is updated to match.

## Notebook wording (review note on cf6ab305)

The reviewer noted that `notebooks/analytics/03_social_media_analytics.ipynb`, markdown cell 7 (`ed9cb89c`), still said `SocialMediaReportGenerator` "normally renders PDF/PPTX reports". The facade writes a PDF only (`siege_utilities/reporting/social_media_reports.py` documents PDF output and has no PPTX path), so the cell now says it "normally renders a PDF report". One line in one markdown cell changed; no code changed. Tests, run from the `tests` directory: `python -m pytest test_notebook_hygiene.py test_notebooks.py -q -p no:randomly` -> 265 passed, 1 skipped in 387.50s.

## Ticket-fitness exemption

Governing ticket: #1461 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1461 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (report facades returning dictionaries or calling nonexistent renderer methods instead of writing PDFs), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1461, and in the PR description, https://github.com/siege-analytics/siege_utilities/pull/1734. The reviewer verdicts are recorded on the ticket thread and the PR conversation.
- **Falsification:** revert the implementation (the facade changes in `siege_utilities/reporting/` of this PR); `tests/test_reporting_facades_produce_pdf.py::test_social_media_report_produces_pdf` goes red because the facade no longer returns a `Path` to a written, non-empty PDF. Observed revert run: with `siege_utilities/reporting/analytics_reports.py` and `social_media_reports.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/reporting/analytics_reports.py siege_utilities/reporting/social_media_reports.py`), `python -m pytest test_reporting_facades_produce_pdf.py::test_social_media_report_produces_pdf -q`, run from the tests directory, gave 1 failed in 28.73s (AssertionError: the facade does not return a `Path` to a written PDF). After `git checkout HEAD --` of the files the command gave 1 passed in 28.75s, `test_reporting_facade_content.py` with `test_reporting_facades_produce_pdf.py` gave 14 passed on the pushed head, and the worktree was clean. The latest commit of this PR moves the chart-type check ahead of the empty-labels shortcut, adds tests, and records the BREAKING classification described above.

## Lead review

The change reverts with one commit. The only code change in the latest commit makes an unsupported chart type with empty labels raise, as it already did with labels. No claim in this artifact exceeds what was observed.

## Develop integration round (develop d2c15b13, 2026-11-23)

**Scope and shape.** This round has one merge commit:
- parents `07a9f330` (the PR head) and `d2c15b13` (develop, which includes #1972, the 5.0.0 release, the relicensing and the 6.0.0 release preparation of #1979);
- it carries the conflict resolution and the follow-up changes listed below, reviewed as one exact tree.

The earlier sections of this file describe earlier rounds. Their references to a `[4.1.0]` CHANGELOG section are historical; the entry now sits under `[Unreleased]`.

**How the tree was built.**
1. A first integration tree, `4eb64af5`, merged develop `45ea8d15`. Its exact-tree review failed, and it was never committed.
2. Develop then moved to `d2c15b13`. The `45ea8d15..d2c15b13` range is the #1979 release preparation: 11 files, none under `siege_utilities/reporting/` and none of this PR's tests.
3. `git merge-tree --write-tree --merge-base 45ea8d15 d2c15b13 4eb64af5` replayed `4eb64af5` onto `d2c15b13` cleanly, giving `d3a0e2c6`.
4. A merge of `d2c15b13` into `07a9f330` was started with `--no-commit --no-ff`, and `d3a0e2c6` was loaded as its index.
5. The review findings below were then fixed in that tree.

### Merge
- **`CHANGELOG.md`.**
  - Develop's text is kept verbatim.
  - Both #1461 entries that the PR had placed in sections now released as 5.0.0 are removed: the `### Fixed` bullet and the BREAKING bullet.
  - ONE #1461 entry sits under the empty `## [Unreleased]`, above `## [6.0.0] - 2026-11-22`, under its own `### BREAKING` heading. It is worded "Through 6.0.0".
  - `git diff d2c15b13 -- CHANGELOG.md` is a pure 26-line insertion. A grep for `#1461` in `CHANGELOG.md` finds exactly one line, inside `[Unreleased]`, and none in `[6.0.0]` or earlier.
  - 6.0.0 was promoted to main without this change, so the entry stays under `[Unreleased]` and reads "Through 6.0.0".
- **Auto-merged files, read hunk by hunk.**
  - `analytics_reports.py`: the composed diff against develop is exactly this PR's facade calls, the website-performance metric selection, the DataFrame-processor column grouping and `str` values in dict data. #1972's `_page_views`, `_format_count` and the top-pages table, chart and insight code are unchanged from develop. `tests/test_1972_top_pages_tables.py` passes on the merged tree.
  - `social_media_reports.py`: the composed diff against develop is exactly the `_render_facade_report` call and the removal of the PPTX wording. Develop's #1469 behaviour is unchanged: fail-closed connector errors, `posts_limit`, numeric counts, `None` for unknown counts.
  - `notebooks/analytics/03_social_media_analytics.ipynb`: the one-cell "renders a PDF report" wording.

### Follow-up changes in the same tree
- **Chart gaps** (`_facade_content._chart_images`).
  - A `None` or NaN value is a gap: bar and pie charts omit it, a line chart keeps it as NaN (a break), and a chart with no known values is left out with a warning.
  - Before this change, develop's social payload, which carries `None` for an unknown count (for example followers `[None, 12]`), was drawn as a NaN bar labelled "nan". At the PR head, a pie with None failed with RuntimeError (caused by ValueError), as observed by the independent review.
- **Pie total.** A pie chart whose known values total zero raises `ValueError` naming the chart. Before this change the chart engine failed with `RuntimeError("Chart generation failed")`.
- **`tests/test_1469_social_media_report_totals.py`**, a develop test whose fixture moves. The social facade no longer calls `report_generator.create_analytics_report`, so the fixture now patches `social_media_reports._render_facade_report`. An adapter keeps the recorded call shape `(payload, title)`, so every payload assertion in the file is unchanged. The diff against develop:

```diff
@@ -11,6 +11,7 @@ import pandas as pd
 from siege_utilities.analytics._social_protocol import SocialMediaError
+from siege_utilities.reporting import social_media_reports
 from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator
@@ -54,7 +55,15 @@ class FakeConnector:
 def report(tmp_path, monkeypatch):
     generator = SocialMediaReportGenerator("client", output_dir=tmp_path)
     writer = Mock(return_value=tmp_path / "report.pdf")
-    monkeypatch.setattr(generator.report_generator, "create_analytics_report", writer)
+
+    # The report payload now reaches the PDF writer through
+    # _render_facade_report (#1461). The adapter keeps the recorded call shape
+    # (payload, title), so writer.call_args.args[0] is still the payload.
+    def render(report_generator, payload, title):
+        assert report_generator is generator.report_generator
+        return writer(payload, title)
+
+    monkeypatch.setattr(social_media_reports, "_render_facade_report", render)
     return generator, writer
```

- **New `tests/test_1461_facade_chart_gaps.py`.**
  - It covers: the zero-total pie; missing pie slices; missing bar values; line breaks; no-known-values for pie, bar and line; and a real social report with unknown counts that writes a PDF.
  - That last test spies on the real chart generator's `create_bar_chart` and asserts only known points are drawn: `[{"Label": ["known"], "Value": [12]}, {"Label": ["known"], "Value": [6]}]`.
  - The report generator is never mocked.
- **Kept as the PR had it** (maintainer decision): `create_website_performance_report` works. It selects the named metrics, and a missing name raises `KeyError`.

### Fixes after the first exact-tree review (`4eb64af5`)
- **Series length (S2-1).** `_known_points` paired labels and values with a plain `zip`, so a bar or pie series whose length differed from the labels was silently truncated. The PR head had raised in that case.
  - `_checked_series` now raises `ValueError` naming the chart (`Facade bar chart 'T - S' has 3 labels but 2 values`) for bar, line and pie, before anything is written. A bar chart with several datasets checks each dataset just before drawing it, so earlier datasets may already be drawn in memory when a later one fails, but no file results.
  - Tests: `test_series_length_mismatch_raises_naming_the_chart`, with 3 labels/2 values and 2 labels/3 values for each chart type (6 cases).
  - Public-entry test: `test_website_report_chart_length_mismatch_raises_and_writes_no_pdf`, which goes through `create_website_performance_report` with a `charts` payload and checks that no PDF is written.
- **Empty headings (S3-1).** A chart that draws nothing (no labels, no datasets, or no known values) is left out together with its section heading and caption, and a warning is logged in every case. This covers both the payload `charts` path and the custom-report `sections` path.
  - Tests: `test_chart_with_empty_labels_is_left_out_with_a_warning`, `test_charts_that_draw_nothing_leave_no_heading` (with a control chart that does render) and `test_custom_report_chart_section_that_draws_nothing_leaves_no_heading`.
  - The "no datasets" case is pinned by `test_chart_with_labels_and_no_datasets_is_left_out_with_a_warning` (bar and line, with `datasets` absent or empty) and `test_website_report_chart_with_no_datasets_leaves_no_heading`. These were added after the delta review of `1c4e0ea2` found that no test reached that branch (S3-5a).
- **Labels before series (S4-10).** Labels are checked first. A chart with no labels is left out with a warning even when it carries values (`test_chart_with_values_and_no_labels_is_left_out_with_a_warning`). A chart with labels and an empty series, or a series of the wrong length, raises. Through a public entry point, Google Analytics `daily_traffic` data with dates and no user counts raises and writes no PDF (`test_ga_daily_traffic_with_dates_and_no_users_raises_and_writes_no_pdf`). The CHANGELOG states this order.
- **File stem and table text (S3-2).**
  - `test_file_stem_is_cut_to_80_characters` uses a 200-character title.
  - `test_file_stem_falls_back_to_report` uses the title `!!!`.
  - `test_table_cells_are_printed_as_text_not_markup` puts `<b>bold</b> & co` in a table cell. Without escaping, ReportLab reads the cell as markup and prints `bold & co`.
- **Missing values (S4-1).** `_is_missing` uses `pandas.isna` for scalars, so NumPy NaN, `Decimal` NaN and `pandas.NA` are gaps as well as `None` and float NaN (`test_pie_omits_numpy_decimal_and_pandas_missing_values`). The scalar guard is pinned by `test_list_as_a_single_value_raises_the_named_non_numeric_error` (S3-5b). Without the guard, a list given as one value raises an unnamed "truth value of an array is ambiguous" `ValueError` instead of the named non-numeric one.
- **Non-numeric values (S4-2).** A known value that is not a number raises `ValueError` naming the chart, for bar, line and pie (`test_non_numeric_value_raises_naming_the_chart`). In `4eb64af5` the all-missing check called `math.isnan` on each line value, so reading the code shows that a string first value raised `TypeError`.
- **Bar titles (S4-7).** A bar dataset label with no chart title gives the title `Followers`, not ` - Followers` (`test_bar_title_is_the_dataset_label_when_the_chart_has_no_title`).
- **CHANGELOG (S4-5, S4-9, S4-10).**
  - The entry names every missing-value form, the 80-character cut with the `report` fallback, the new `ValueError` cases, the omitted headings and the order of the label and series checks.
  - It also says what each error names: the unsupported-type message names the type, the other messages name the chart, and for a line chart with several series they name the chart, not the series.
- **Not in this tree.** These findings are left for a follow-up issue:
  - facade tables do not repeat develop's header row across pages (S4-3);
  - the GA traffic-sources facade reads an absent count as 0, where other facades treat it as a gap (S4-4);
  - a GA traffic-source row whose count is `None` or text fails in develop's own formatting with an unnamed error, which predates this change;
  - a report made only of omitted charts is a title-only PDF, with the warnings as the only signal (S4-13);
  - value-type edges in caller-supplied chart configurations (S4-14).

## Test plan

Run from the worktree with Python 3.11, `-o addopts="" -p no:cacheprovider -p no:randomly`.

All results below are for the tree on develop `d2c15b13`, with the fixes applied. The broad run and M0 to M11 were made on `1c4e0ea2`. The last round changes only tests, the CHANGELOG and this document; its results are in the final bullet.

- **Facade, neighbour, release and changelog tests (on `1c4e0ea2`):** 1210 passed, 3 skipped. The skips are a python-pptx-missing-only test and two that need `weightipy`, which is not installed. The run covered:
  - `tests/test_1461_facade_chart_gaps.py` (then 26 cases, 33 together with `tests/test_reporting_facade_content.py`)
  - `tests/test_1469_social_media_report_totals.py`
  - `tests/test_1972_top_pages_tables.py`
  - `tests/test_reporting_facade_content.py` and `tests/test_reporting_facades_produce_pdf.py`
  - every other test under `tests/` that mentions `analytics_reports`, `social_media_reports`, `report_generator`, `_facade_content` or `chart_generator` (32 more files)
  - `tests/test_release_process.py`, which includes the release tests added for 6.0.0, and `tests/test_user_config_export_changelog.py`
- **Mutation checks.** Each edit was applied, run and reverted. Afterwards a grep for the mutation marker finds nothing, and `git diff` shows that `analytics_reports.py` and `social_media_reports.py` match the staged tree.
  - M0, develop's call shape (`create_analytics_report(report_data, title)`) in the GA and social facades: `tests/test_reporting_facades_produce_pdf.py -k "social or google or same_title"` gave 4 failed of 4, because the result is a `dict`, not a `Path`.
  - M1, the zero-total pie check removed: 1 failed (`test_pie_with_known_values_totalling_zero_raises`).
  - M2, the gap handling removed (`_is_missing` always false): 10 failed. That includes the end-to-end social test, which saw `[None, 12]` and `[None, 6]` passed to the chart generator, and both no-heading tests.
  - M3, the social follower gap dropped (`_followers` returns 0 for an unknown count): the re-pointed `test_1469` gave 21 failed, 26 passed. The moved fixture still catches a payload regression.
  - M4, the series length check removed (the equivalent of the plain `zip`): 7 failed. These are all six length cases and the website public-entry test. Bar and pie no longer raised (silent truncation), and line failed with the chart engine's `RuntimeError` instead of the named `ValueError`.
  - M5, both `if images:` guards replaced by `if True:`: 2 failed (`test_charts_that_draw_nothing_leave_no_heading` and `test_custom_report_chart_section_that_draws_nothing_leaves_no_heading`).
  - M6, `[:80]` changed to `[:81]`: 1 failed (`test_file_stem_is_cut_to_80_characters`).
  - M7, the `report` fallback changed to `untitled`: 1 failed (`test_file_stem_falls_back_to_report`).
  - M8, `_escape_paragraph` removed from table cells: 1 failed (`test_table_cells_are_printed_as_text_not_markup`). The PDF text was `bold & co`.
  - M9, `_is_missing` restored to its float-only form: 1 failed (`test_pie_omits_numpy_decimal_and_pandas_missing_values`, where `pandas.NA` was reported as non-numeric).
  - M10, the non-numeric check removed: 3 failed (`test_non_numeric_value_raises_naming_the_chart` for bar, line and pie).
  - M11, the earlier bar title expression: 1 failed (`test_bar_title_is_the_dataset_label_when_the_chart_has_no_title`, where the title was ` - Followers`).
- **Guards:** `check_exception_contracts` (208 flagged, 0 unlisted, 0 stale), `check_error_path_coverage` (401 modules, 0 fail), `check_atomic_writes`, `check_secure_writes`, `check_test_file_hygiene`, `check_no_stub_docstrings`, `check_unbounded_io siege_utilities`, `check_credential_urls`, `check_secret_literals`, `check_secret_repr`, `check_subprocess_safety`, `check_imports`, `check_notebook_inventory` and `check_notebook_capability_coverage` all pass.
  - `check_hollow_work` has 3 existing findings in files this PR does not touch.
- **Not run, or failing on develop as well:**
  - `check_broad_except`: 34 existing violations in files this PR does not touch, tracked as #1971.
  - `check_lazy_imports`: stops on unconfigured Django settings.
  - `check_lint_ratchet` phase 3: `flake8` is not installed locally, and the script compares committed SHAs. As a local substitute, `ruff check --select F,E9,E722,F601,F403,F405,F401,F841,F541` on the changed Python files passes. CI runs flake8.
  - The notebook execution tests were not run in this round. Notebook 03 stops at the report payload and does not call the PDF path.
- **Last round (tests, CHANGELOG and this document; `_facade_content.py` unchanged from `1c4e0ea2`).**
  - Results: `tests/test_1461_facade_chart_gaps.py`, `tests/test_1469_social_media_report_totals.py`, `tests/test_reporting_facade_content.py` and `tests/test_reporting_facades_produce_pdf.py` give 103 passed. That is 93 before, plus 10 new cases: 4 no-datasets cases, 1 website no-datasets case, 3 list-value cases, the GA `daily_traffic` case and the values-without-labels case.
  - Kill-proofs. Each was applied to the working file, run and restored; afterwards `git diff` shows `_facade_content.py` matching `1c4e0ea2` and a grep for the marker finds nothing.
    - K1: the "no datasets" warning removed. 5 failed, all the new no-datasets tests.
    - K2: the "no datasets" branch made to raise. 5 failed, the same tests.
    - K3: `pd.isna` applied without the scalar guard. 3 failed (`test_list_as_a_single_value_raises_the_named_non_numeric_error` for bar, line and pie).
    - K4: the length check removed. The GA `daily_traffic` test failed with the seven length tests.
    - K5: the "no labels" warning removed. 3 failed, including `test_chart_with_values_and_no_labels_is_left_out_with_a_warning`.

## Findings

| ID | Priority | Finding | Outcome |
|----|----------|---------|---------|
| R1 | P2 | Develop's social payloads carry `None` for unknown counts, and the facade drew them as NaN bars labelled "nan". At the PR head, a pie with None failed with RuntimeError (caused by ValueError), as observed by the independent review. | Gaps are omitted (bar, pie) or kept as NaN breaks (line); charts with no known values are left out with a warning. M2 shows the tests fail without it. |
| R2 | P2 | A pie chart whose values total zero failed inside the chart engine with an unspecific `RuntimeError`. | `ValueError` naming the chart; M1 shows the test fails without it. |
| R3 | P2 | After the merge, develop's `test_1469` fixture patched a method the social facade no longer calls. | The fixture patches `_render_facade_report` with a shape-preserving adapter; every payload assertion is unchanged; M3 shows it still catches a payload regression. |
| R4 | P3 | The PR's two #1461 CHANGELOG entries sat in sections now released as 5.0.0, and develop has since cut `[6.0.0]`. | One entry under the empty `[Unreleased]`, above `[6.0.0]`, with its own `### BREAKING` heading; the grep shows one occurrence. |
| R5 | P2 | Review S2-1: bar and pie silently truncated a series whose length differed from the labels. | `ValueError` naming the chart for bar, line and pie; M4 shows 7 tests fail without it. |
| R6 | P3 | Review S3-1: a chart that drew nothing left an empty heading, and empty labels were not logged. | The heading and caption are omitted and a warning is logged; M5 shows 2 tests fail without it. |
| R7 | P3 | Review S3-2: the 80-character stem cut and table-cell escaping had no tests. | Three tests; M6, M7 and M8 each make one fail. |
| R8 | P4 | Review S4-1, S4-2 and S4-7: NumPy, `Decimal` and pandas missing values, non-numeric values, and a leading separator in bar titles. | Fixed with tests; M9, M10 and M11 make them fail. |
| R9 | P3 | Delta review S3-5: the "no datasets" branch and the scalar guard in `_is_missing` were claimed as tested but no test reached them. | Tests added; K1, K2 and K3 make them fail. |
| R10 | P4 | Delta review S4-9 to S4-12: CHANGELOG precision on what each error names and on the order of the label and series checks; two statements in this document. | CHANGELOG and this document corrected; the order is pinned by two tests (K4, K5). S4-13 and S4-14 go to the follow-up issue. |
| R11 | P2 | Hosted CI at `ff743775` (matplotlib 3.11.2): a pie chart with `Decimal` values failed in matplotlib's `np.isfinite` check, so `test_pie_omits_numpy_decimal_and_pandas_missing_values` failed on every Python version. | Known values reach the chart engine as built-in numbers; reproduced red and then passing under the CI versions; KP1 and KP2 make the new tests fail. See the CI round below. |

## Independent review

The PR's earlier rounds were reviewed independently: the real-PDF end-to-end was confirmed at `cf6ab305`, and hosted CI passed at `07a9f330`. The first integration tree, `4eb64af5`, was reviewed exact-tree by an independent reviewer and failed, with one S2, four S3 and eight S4 findings. That review confirmed the #1972 composition in the PDF text, #1469's fail-closed behaviour and `None` gaps, the detection power of the re-pointed `test_1469` fixture, and the M0 to M3 results. The fixes above answer its findings, except S4-3 and S4-4, which go to a follow-up issue.

The fixed tree, `1c4e0ea2`, then passed an independent delta review with no S1 or S2 findings. That review reproduced all twelve mutations above and ran 44 more of its own, 41 of which were caught. The three it did not catch were the "no datasets" warning, the "no datasets" branch, and the scalar guard in `_is_missing` (S3-5). It also added six notes (S4-9 to S4-14). This tree closes S3-5 with tests, puts S4-9 and S4-10 into the CHANGELOG, and corrects S4-11 and S4-12 in this document. S4-13 and S4-14 go to the follow-up issue. A short delta review of this tree against `1c4e0ea2` comes before the commit. That review is linked from the merge commit's `Hostile-Review` trailer and from the PR.

## CI round on `ff743775` (matplotlib 3.11)

**Failure.**
- Hosted CI at `ff743775` failed one test on Python 3.11 to 3.14: `tests/test_1461_facade_chart_gaps.py::test_pie_omits_numpy_decimal_and_pandas_missing_values`.
- The chart engine raised `RuntimeError("Chart generation failed")` from matplotlib's pie: `np.isfinite` on `Decimal` values raises `TypeError: ufunc 'isfinite' not supported for the input types`.
- Locally the test passed, because the libraries differ:

| Package | CI | Local |
|---|---|---|
| matplotlib | 3.11.2 | 3.10.8 |
| numpy | 2.4.6 | 2.4.2 |
| reportlab | 5.1.0 | 4.4.10 |
| pillow | 13.0.0 | 12.1.1 |
| pandas | 2.3.3 | 2.3.3 |

**Reproduction.**
- A throwaway virtual environment held the CI versions; it was deleted afterwards.
- On `ff743775` it gives 1 failed and 102 passed over the four change test files. The failure is the same, with the same `np.isfinite` traceback.
- With the earlier behaviour (values passed through unchanged), bar and line charts drew `Decimal`, `numpy.int64` and `numpy.float32` values without error under these versions. The pie failed two ways: the `np.isfinite` error, and a `TypeError` from summing a `Decimal` with a NumPy float in the zero-total check.

**Fix (`_facade_content.py`).**
- `_checked_series` returns known values as built-in numbers through `_plain_number`: integral values (including `numpy.int64`) become `int`, so value labels keep printing `88` rather than `88.0`; other values (`Decimal`, `numpy.float32`) become `float`.
- This covers bar, line and pie. Missing values and the named `ValueError` messages are unchanged.
- A value that cannot be turned into a real number, such as a complex number, now raises the named non-numeric `ValueError`. Before, a complex value was passed to the chart engine.

**Tests.**
- `test_known_values_reach_the_chart_engine_as_builtin_numbers` (bar, line, pie): spies on the chart engine and asserts values `[2.5, 3, 1.5]` of types `[float, int, float]` for `Decimal`, `numpy.int64` and `numpy.float32` inputs. It does not depend on the matplotlib version.
- `test_decimal_and_numpy_values_render_through_the_real_chart_engine` (bar, line, pie): draws those values, with a gap, through the real chart engine.
- `test_complex_value_raises_the_named_non_numeric_error` (bar, line, pie).
- `test_pie_omits_numpy_decimal_and_pandas_missing_values` now also asserts that the surviving value is a `float`.

**Results.**
- Four change test files: 112 passed, both under the CI versions and locally.
- Broad reporting set (39 files): 1229 passed and 3 skipped under the CI versions. With `tests/guard/test_exception_contract_guard.py` added, 1312 passed and 3 skipped locally. No other difference from reportlab 5 or matplotlib 3.11 showed up.
- Kill-proofs. Each was applied to the working file, run and restored; afterwards a grep for the marker finds nothing.
  - KP1: `_plain_number` returns its input unchanged. Locally 8 failed: the three spy cases, the three complex cases, the pie render case and the existing `Decimal` pie test. Under the CI versions, the same 8 failed among the selected tests.
  - KP2: integral values are also turned into `float`. 3 failed (the spy cases).
- Guards with develop `c303621d`'s scripts:
  - `check_exception_contracts`: 212 flagged, 0 unlisted, 0 stale.
  - `check_broad_except`: 35 flagged, 0 unreviewed.
  - `check_error_path_coverage`: 401 modules, 0 failures.
  - `check_no_stub_docstrings` passes.
  - `ruff` with the F, E9 and lint-ratchet phase-3 rules passes on the changed files.
