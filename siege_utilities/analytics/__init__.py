"""
Analytics Module

This module provides analytics integration capabilities including:
- Google Analytics data retrieval and processing
- Client-associated analytics account management
- Data export to Pandas and Spark formats
"""

from .google_analytics import (
    GoogleAnalyticsConnector,
    create_ga_account_profile,
    save_ga_account_profile,
    load_ga_account_profile,
    list_ga_accounts_for_client,
    batch_retrieve_ga_data
)

from .facebook_business import (
    FacebookBusinessConnector,
    create_facebook_account_profile,
    save_facebook_account_profile,
    load_facebook_account_profile,
    list_facebook_accounts_for_client,
    batch_retrieve_facebook_data
)

__all__ = [
    'GoogleAnalyticsConnector',
    'create_ga_account_profile',
    'save_ga_account_profile',
    'load_ga_account_profile',
    'list_ga_accounts_for_client',
    'batch_retrieve_ga_data',
    'FacebookBusinessConnector',
    'create_facebook_account_profile',
    'save_facebook_account_profile',
    'load_facebook_account_profile',
    'list_facebook_accounts_for_client',
    'batch_retrieve_facebook_data'
]
