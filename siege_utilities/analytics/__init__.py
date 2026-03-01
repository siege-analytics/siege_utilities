"""
Analytics Module — lazy-loaded.

Provides analytics integration: Google Analytics, Facebook Business,
Snowflake, and Data.world connectors.
"""

import importlib
import sys

_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


_register([
    'GoogleAnalyticsConnector', 'create_ga_account_profile', 'save_ga_account_profile',
    'load_ga_account_profile', 'list_ga_accounts_for_client', 'batch_retrieve_ga_data',
], '.google_analytics')

_register([
    'FacebookBusinessConnector', 'create_facebook_account_profile',
    'save_facebook_account_profile', 'load_facebook_account_profile',
    'list_facebook_accounts_for_client', 'batch_retrieve_facebook_data',
], '.facebook_business')

_register([
    'SnowflakeConnector', 'get_snowflake_connector', 'upload_to_snowflake',
    'download_from_snowflake', 'execute_snowflake_query', 'SNOWFLAKE_AVAILABLE',
], '.snowflake_connector')

_register([
    'DataDotWorldConnector', 'get_datadotworld_connector', 'search_datasets',
    'list_datasets', 'search_datadotworld_datasets', 'load_datadotworld_dataset',
    'query_datadotworld_dataset', 'DATADOTWORLD_AVAILABLE',
], '.datadotworld_connector')

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))
