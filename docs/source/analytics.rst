Analytics
=========

The analytics module provides utilities for working with various analytics platforms including Facebook Business API and Google Analytics.

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
