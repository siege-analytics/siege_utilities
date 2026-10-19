Analytics
=========

The analytics module provides utilities for working with various analytics platforms including
Facebook Business API, Google Analytics, and Google Workspace write APIs (Sheets, Docs, Slides).

For Google Workspace (Sheets, Docs, Slides, Drive), see :doc:`google_workspace`.

Statistical analytics behavior in 4.1.0
--------------------------------------

The following contracts change the behavior shipped in 4.0.0:

* Pipeline inputs describe current stages, without transition history. Read
  ``report.stage_ratios`` and each ``StageRatio.ratio`` instead of
  ``report.conversions`` and ``ConversionRate.rate``. The ratio is the next
  stage's count divided by this stage's independent count. It can exceed 1.0;
  an empty denominator gives ``None``. It does not measure cohort conversion.
* ``PipelineAnalyzer(aging_threshold=30)`` alerts when an item has spent more
  than 30 days in its stage. The threshold is now a positive, finite day limit,
  with 30 as the default, replacing the multiplier of the stage average. Choose
  a day limit when migrating callers that supplied the old multiplier.
* Forecast inputs containing ``None``, NaN, or infinity yield an
  ``Insufficient data`` grade, ``insufficient-data`` bias direction, and
  ``None`` MAPE and bias for the overall series and affected groups. Valid
  subsets are not used to grade an incomplete group. ``n_observations`` counts
  all pairs; ``n_excluded`` counts pairs with zero actuals or missing/non-finite
  values. An all-zero group with no missing values still raises ``ValueError``.
* Trend analysis sorts labels lexicographically; use chronologically sortable
  labels such as ``2026-Q1`` or ISO dates. OLS fits all valid period MAPEs with
  equally spaced periods. The fitted change over the whole span determines
  direction: below -1 percentage point is improving, above +1 is degrading,
  and the inclusive interval between them is stable. Periods with all-zero
  actuals or insufficient data are skipped; fewer than two valid periods gives
  ``None`` for direction.
* Health and risk tiers classify the reported two-decimal composite score.
  A raw score of 69.999 reported as 70.0 receives the tier for 70.0, including
  any corresponding risk intervention.
* Comparative weights must be finite, non-negative, cover the dimensions,
  and have a positive sum. They are normalized to sum to one, keeping weighted
  totals on the 1-5 scale regardless of the scale of the input weights.
* Price sensitivity inputs must align respondents across all four sequences.
  Every respondent must satisfy
  ``too_cheap <= cheap <= expensive <= too_expensive``; ties are allowed.
  Inconsistent ordering raises ``ValueError`` with the zero-based response
  index before curve computation. No responses are reordered or dropped.

Module Overview
--------------

.. automodule:: siege_utilities.analytics
   :members:
   :undoc-members:
   :show-inheritance:

Facebook Business Analytics
--------------------------

.. automodule:: siege_utilities.analytics.facebook_business
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.analytics.facebook_business.get_ad_accounts
   :noindex:

.. autofunction:: siege_utilities.analytics.facebook_business.get_campaigns
   :noindex:

.. autofunction:: siege_utilities.analytics.facebook_business.get_ad_sets
   :noindex:

.. autofunction:: siege_utilities.analytics.facebook_business.get_ads
   :noindex:

.. autofunction:: siege_utilities.analytics.facebook_business.get_insights
   :noindex:

Usage Examples
-------------

Facebook Business API setup:

.. code_block:: python

   import siege_utilities
   
   # Initialize Facebook Business API
   access_token = 'your_access_token'
   app_secret = 'your_app_secret'
   app_id = 'your_app_id'
   
   # Get ad accounts
   ad_accounts = siege_utilities.get_ad_accounts(access_token)
   print(f"Found {len(ad_accounts)} ad accounts")

Campaign data retrieval:

.. code_block:: python

   # Get campaigns for a specific ad account
   ad_account_id = 'act_123456789'
   campaigns = siege_utilities.get_campaigns(access_token, ad_account_id)
   
   for campaign in campaigns:
       print(f"Campaign: {campaign['name']}")
       print(f"Status: {campaign['status']}")
       print(f"Budget: {campaign['daily_budget']}")

Ad insights and performance:

.. code_block:: python

   # Get insights for ads
   ad_ids = ['123456789', '987654321']
   insights = siege_utilities.get_insights(
       access_token, 
       ad_ids, 
       fields=['impressions', 'clicks', 'spend', 'ctr']
   )
   
   for ad_insight in insights:
       print(f"Ad {ad_insight['ad_id']}:")
       print(f"  Impressions: {ad_insight['impressions']}")
       print(f"  Clicks: {ad_insight['clicks']}")
       print(f"  CTR: {ad_insight['ctr']}%")

Google Analytics
---------------

.. automodule:: siege_utilities.analytics.google_analytics
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.analytics.google_analytics.get_analytics_data
   :noindex:

.. autofunction:: siege_utilities.analytics.google_analytics.get_user_metrics
   :noindex:

.. autofunction:: siege_utilities.analytics.google_analytics.get_page_views
   :noindex:

Usage Examples
-------------

Google Analytics data retrieval:

.. code_block:: python

   # Get analytics data
   view_id = '123456789'
   start_date = '2024-01-01'
   end_date = '2024-01-31'
   
   analytics_data = siege_utilities.get_analytics_data(
       view_id, 
       start_date, 
       end_date,
       metrics=['sessions', 'users', 'pageviews']
   )
   
   print(f"Total sessions: {analytics_data['sessions']}")
   print(f"Total users: {analytics_data['users']}")

User behavior analysis:

.. code_block:: python

   # Get user metrics
   user_metrics = siege_utilities.get_user_metrics(
       view_id,
       start_date,
       end_date
   )
   
   print(f"New users: {user_metrics['new_users']}")
   print(f"Returning users: {user_metrics['returning_users']}")
   print(f"Average session duration: {user_metrics['avg_session_duration']}")

Page performance analysis:

.. code_block:: python

   # Get page view data
   page_views = siege_utilities.get_page_views(
       view_id,
       start_date,
       end_date,
       max_results=10
   )
   
   print("Top pages by views:")
   for page in page_views:
       print(f"  {page['page_path']}: {page['pageviews']} views")

Unit Tests
----------

The analytics modules have comprehensive test coverage:

.. code_block:: text

   ✅ Analytics modules are thoroughly tested
   
   Test Coverage:
   - Facebook Business API authentication
   - Ad account, campaign, and ad retrieval
   - Insights data processing
   - Google Analytics data retrieval
   - User metrics calculation
   - Page view analysis
   - Error handling for API failures
   - Rate limiting and pagination

Test Results: All analytics tests pass successfully with comprehensive coverage.
