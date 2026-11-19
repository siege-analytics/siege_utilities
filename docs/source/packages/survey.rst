Survey
======

Survey and polling analysis: crosstabs, weighting, significance testing, wave
management, rendering.

Weights and inference
---------------------

``View.base`` remains the displayed respondent base: the sum of weights
when weighted, otherwise the row count. ``View.effective_n`` is separate:
count tables use the number of valid responses or Kish's effective sample
size, ``sum(w)**2 / sum(w**2)``. Column proportion tests use this effective
sample size and exclude longitudinal delta columns. Multiplying every
weight by the same constant therefore does not change significance flags.
``top_n`` limits displayed categories; their shares retain the full-category
denominator, including categories omitted from the display.

``MEAN_SCALE`` uses the weighted mean and reliability-weight sample variance,
``sum(w * (x - mean)**2) / (sum(w) - sum(w**2) / sum(w))``. Its standard
error is ``sqrt(variance / effective_n)``. Missing metric values and zero
weights are excluded from this calculation. The display base stays unchanged.
When effective n is below 30, the 95% CI uses Student's t with effective n
minus one degrees of freedom and requires SciPy; otherwise it uses 1.96.
An effective sample of one has no estimable CI (``ci=None``). Weights must
be finite and nonnegative. These are weight-only approximations and do not
account for clustering or stratification.

``chi_square_flag`` uses ``View.respondent_count``, the unweighted frequency
for each category, and tests association in the unweighted sample. It rejects
metric-sum tables and manually aggregated tables without raw respondent
counts. A metric column containing only ones is treated as a respondent
indicator. For manual ``View`` construction, supply ``effective_n`` for
proportion tests and ``respondent_count`` for chi-square; neither value is
inferred from the weighted display base or count. Omit ``metric`` (and do not
include a default ``value`` column) to build a pure respondent-count table.

.. automodule:: siege_utilities.survey
   :members:
   :show-inheritance:

Submodules
----------

.. automodule:: siege_utilities.survey.crosstab
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.survey.models
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.survey.registry
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.survey.render
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.survey.significance
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.survey.waves
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.survey.weights
   :members:
   :show-inheritance:
