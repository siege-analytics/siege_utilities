"""
Analytics Module — lazy-loaded.

Provides analytics integration: Google Analytics, Facebook Business,
Snowflake, Data.world connectors, and Google Workspace write APIs
(Sheets, Docs, Slides).
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

# Google Workspace write APIs (Docs, Sheets, Slides)
_register([
    'GoogleWorkspaceClient', 'WORKSPACE_SCOPES',
], '.google_workspace')

# Google Sheets (no name collisions — exported directly)
_register([
    'create_spreadsheet', 'write_values', 'append_rows', 'read_values',
    'write_dataframe', 'read_dataframe', 'add_sheet',
    'get_spreadsheet_metadata', 'copy_spreadsheet',
], '.google_sheets')

# Google Slides and Docs have overlapping function names (insert_text, etc.)
# Import them via their modules: analytics.google_slides.insert_text
# Only export non-colliding top-level convenience functions here.
_register([
    'create_presentation', 'get_presentation', 'copy_presentation',
    'add_blank_slide', 'create_textbox',
], '.google_slides')

_register([
    'create_document', 'get_document', 'copy_document', 'read_document_text',
    'insert_paragraph', 'insert_table', 'replace_text',
], '.google_docs')

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
