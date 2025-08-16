"""
Analytics Module

This module provides analytics integration capabilities including:
- Google Analytics data retrieval and processing
- Facebook Business API integration
- Snowflake data warehouse connectivity
- Data.world data discovery and access
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

from .snowflake_connector import (
    SnowflakeConnector,
    get_snowflake_connector,
    upload_to_snowflake,
    download_from_snowflake,
    execute_snowflake_query,
    SNOWFLAKE_AVAILABLE
)

from .datadotworld_connector import (
    DataDotWorldConnector,
    get_datadotworld_connector,
    search_datadotworld_datasets,
    load_datadotworld_dataset,
    query_datadotworld_dataset,
    DATADOTWORLD_AVAILABLE
)

__all__ = [
    # Google Analytics
    'GoogleAnalyticsConnector',
    'create_ga_account_profile',
    'save_ga_account_profile',
    'load_ga_account_profile',
    'list_ga_accounts_for_client',
    'batch_retrieve_ga_data',
    
    # Facebook Business
    'FacebookBusinessConnector',
    'create_facebook_account_profile',
    'save_facebook_account_profile',
    'load_facebook_account_profile',
    'list_facebook_accounts_for_client',
    'batch_retrieve_facebook_data',
    
    # Snowflake
    'SnowflakeConnector',
    'get_snowflake_connector',
    'upload_to_snowflake',
    'download_from_snowflake',
    'execute_snowflake_query',
    'SNOWFLAKE_AVAILABLE',
    
    # Data.world
    'DataDotWorldConnector',
    'get_datadotworld_connector',
    'search_datadotworld_datasets',
    'load_datadotworld_dataset',
    'query_datadotworld_dataset',
    'DATADOTWORLD_AVAILABLE'
]
