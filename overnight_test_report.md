# Overnight Testing Report - 2025-09-11 02:01:29

## Summary

- **Total Functions**: 749
- **Tested Functions**: 650
- **Successful Tests**: 96
- **Failed Tests**: 508
- **Skipped Tests**: 46

## Module Summary

### siege_utilities.analytics
- Importable: True
- Functions: 18
- Classes: 4

### siege_utilities.config
- Importable: True
- Functions: 42
- Classes: 3

### siege_utilities.core
- Importable: True
- Functions: 17
- Classes: 0

### siege_utilities.data
- Importable: True
- Functions: 10
- Classes: 0

### siege_utilities.distributed
- Importable: True
- Functions: 490
- Classes: 0

### siege_utilities.files
- Importable: True
- Functions: 14
- Classes: 3

### siege_utilities.geo
- Importable: True
- Functions: 10
- Classes: 14

### siege_utilities.git
- Importable: True
- Functions: 29
- Classes: 0

### siege_utilities.reporting
- Importable: True
- Functions: 4
- Classes: 9

### siege_utilities.testing
- Importable: True
- Functions: 16
- Classes: 0

## Recommendations

### Fix 508 broken functions (Priority: high)
- **Category**: broken_functions
- **Description**: Functions that failed testing: siege_utilities.config.classify_urbanicity, siege_utilities.config.create_database_config, siege_utilities.config.ensure_directory_exists, siege_utilities.config.get_nces_download_url, siege_utilities.config.get_relative_to_home, siege_utilities.config.get_tiger_url, siege_utilities.config.setup_standard_directories, siege_utilities.core.dataclass, siege_utilities.core.field, siege_utilities.data.generate_synthetic_businesses
- **Action**: Review and fix import/execution issues

### Add type hints to 42 functions (Priority: medium)
- **Category**: type_hints
- **Description**: Functions missing type hints: siege_utilities.config.initialize_siege_directories, siege_utilities.core.contextmanager, siege_utilities.core.dataclass, siege_utilities.core.field, siege_utilities.distributed.backup_full_dataframe, siege_utilities.distributed.check_hdfs_status, siege_utilities.distributed.clean_and_reorder_bbox, siege_utilities.distributed.compute_walkability, siege_utilities.distributed.create_hdfs_operations, siege_utilities.distributed.create_unique_staging_directory
- **Action**: Add comprehensive type annotations

## Detailed Function Results

### siege_utilities.analytics.batch_retrieve_facebook_data
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 6
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.batch_retrieve_ga_data
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.create_facebook_account_profile
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.create_ga_account_profile
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.download_from_snowflake
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.execute_snowflake_query
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.get_datadotworld_connector
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.get_snowflake_connector
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.list_facebook_accounts_for_client
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.list_ga_accounts_for_client
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.load_datadotworld_dataset
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.load_facebook_account_profile
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.load_ga_account_profile
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.query_datadotworld_dataset
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.save_facebook_account_profile
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.save_ga_account_profile
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.search_datadotworld_datasets
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.analytics.upload_to_snowflake
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.classify_urbanicity
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: '>=' not supported between instances of 'NoneType' and 'int'

### siege_utilities.config.cleanup_old_connections
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.create_database_config
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 8
- **Execution Error**: Failed with None values: create_database_config() takes 7 positional arguments but 8 were given

### siege_utilities.config.create_temporary_service_account_file
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.credential_status
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Skipped - might prompt for user input

### siege_utilities.config.ensure_directory_exists
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_cache_path
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_chart_dimensions
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_connection_status
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.get_credential
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - might prompt for user input

### siege_utilities.config.get_data_path
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_download_directory
- **Status**: working (updated for profile system)
- **Importable**: True
- **Profile Integration**: ✅ Uses hierarchical resolution with user/client profiles
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_file_path
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_file_type
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.get_fips_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_ga_credentials
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Skipped - might prompt for user input

### siege_utilities.config.get_ga_service_account_credentials
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Skipped - might prompt for user input

### siege_utilities.config.get_google_service_account_from_1password
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1
- **Execution Error**: Skipped - might prompt for user input

### siege_utilities.config.get_locale_category
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_locale_subcategory
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_nces_download_url
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: Unsupported NCES data type: None

### siege_utilities.config.get_output_path
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_project_path
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_relative_to_home
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_service_row_limit
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_service_timeout
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_tiger_url
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: Unsupported geographic level: None

### siege_utilities.config.get_timeout
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_urbanicity_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.get_user_config
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.config.initialize_siege_directories
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 0

### siege_utilities.config.list_database_configs
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.load_database_config
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.normalize_state_identifier
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.save_database_config
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.setup_standard_directories
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.store_credential
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Skipped - might prompt for user input

### siege_utilities.config.store_ga_credentials_from_file
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.store_ga_service_account_from_file
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.test_database_connection
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.config.validate_geographic_level
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.config.validate_locale_code
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.core.cleanup_all_loggers
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.core.cleanup_logger
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.core.configure_shared_logging
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.core.contextmanager
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.core.dataclass
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 11
- **Execution Error**: Failed with None values: dataclass() takes from 0 to 1 positional arguments but 11 were given

### siege_utilities.core.field
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 8
- **Execution Error**: Failed with None values: field() takes 0 positional arguments but 8 were given

### siege_utilities.core.get_logger
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.core.import_module_with_fallbacks
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.core.init_logger
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7

### siege_utilities.core.log_critical
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.core.log_debug
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.core.log_error
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.core.log_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.core.log_warning
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.core.remove_wrapping_quotes_and_trim
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.core.set_default_logger_name
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.core.temporary_logging_config
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.data.create_sample_dataset
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5

### siege_utilities.data.generate_synthetic_businesses
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: unsupported operand type(s) for *: 'NoneType' and 'float'

### siege_utilities.data.generate_synthetic_housing
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: unsupported operand type(s) for *: 'NoneType' and 'float'

### siege_utilities.data.generate_synthetic_population
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 8
- **Execution Error**: Failed with None values: unsupported operand type(s) for *: 'NoneType' and 'float'

### siege_utilities.data.get_census_boundaries
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4

### siege_utilities.data.get_census_data
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5

### siege_utilities.data.get_dataset_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.data.join_boundaries_and_data
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4

### siege_utilities.data.list_available_datasets
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.data.load_sample_data
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: load_sample_data() takes 1 positional argument but 2 were given

### siege_utilities.distributed.abs
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.acos
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.acosh
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.add_months
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.aes_decrypt
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.aes_encrypt
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 6
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.aggregate
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.any_value
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.approx_count_distinct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.approx_percentile
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.array
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.array_agg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.array_append
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.array_compact
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.array_contains
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.array_distinct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.array_except
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.array_insert
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.array_intersect
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.array_join
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.array_max
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.array_min
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.array_position
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.array_prepend
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.array_remove
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.array_repeat
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.array_size
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.array_sort
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.array_union
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.arrays_overlap
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.arrays_zip
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.asc
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.asc_nulls_first
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.asc_nulls_last
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.ascii
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.asin
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.asinh
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.assert_true
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.atan
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.atan2
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.atanh
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.atomic_write_with_staging
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7

### siege_utilities.distributed.avg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.backup_full_dataframe
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2
- **Execution Error**: Failed with None values: name 'DEBUG_SUBDIRECTORY' is not defined

### siege_utilities.distributed.base64
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bin
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bit_and
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bit_count
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bit_get
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.bit_length
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bit_or
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bit_xor
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bitmap_bit_position
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bitmap_bucket_number
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bitmap_construct_agg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bitmap_count
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bitmap_or_agg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bitwise_not
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bool_and
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bool_or
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.broadcast
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.bround
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.btrim
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.bucket
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_INT] Argument `numBuckets` should be a Column or int, got NoneType.

### siege_utilities.distributed.call_function
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.call_udf
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.cardinality
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.cbrt
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.ceil
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.ceiling
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.char
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.char_length
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.character_length
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.check_hdfs_status
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 0

### siege_utilities.distributed.clean_and_reorder_bbox
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'withColumn'

### siege_utilities.distributed.coalesce
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.col
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.collate
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.collation
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.collect_list
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.collect_set
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.column
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.compute_walkability
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.distributed.concat
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.concat_ws
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.contains
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.conv
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.convert_timezone
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.corr
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.cos
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.cosh
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.cot
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.count
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.count_distinct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.count_if
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.count_min_sketch
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.covar_pop
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.covar_samp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.crc32
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.create_cluster_config
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: create_cluster_config() takes 1 positional argument but 2 were given

### siege_utilities.distributed.create_geocoding_config
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: create_geocoding_config() takes 1 positional argument but 2 were given

### siege_utilities.distributed.create_hdfs_config
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.create_hdfs_operations
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.create_local_config
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: create_local_config() takes 1 positional argument but 2 were given

### siege_utilities.distributed.create_map
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.create_unique_staging_directory
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2
- **Execution Error**: Failed with None values: name 'Path' is not defined

### siege_utilities.distributed.csc
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.cume_dist
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.curdate
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.current_catalog
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.current_database
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.current_date
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.current_schema
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.current_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.current_timezone
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.current_user
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.dataclass
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 11
- **Execution Error**: Failed with None values: dataclass() takes from 0 to 1 positional arguments but 11 were given

### siege_utilities.distributed.date_add
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.date_diff
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.date_format
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.date_from_unix_date
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.date_part
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.date_sub
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.date_trunc
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.dateadd
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.datediff
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.datepart
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.day
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.dayname
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.dayofmonth
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.dayofweek
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.dayofyear
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.days
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.decode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.degrees
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.dense_rank
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.desc
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.desc_nulls_first
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.desc_nulls_last
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.e
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.element_at
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.elt
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.encode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.endswith
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.ensure_literal
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.distributed.equal_null
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.every
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.exists
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.exp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.explode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.explode_outer
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.expm1
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.export_prepared_df_as_csv_to_path_using_delimiter
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'stem'

### siege_utilities.distributed.export_pyspark_df_to_excel
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 3

### siege_utilities.distributed.expr
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.extract
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.factorial
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.filter
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.find_in_set
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.first
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.first_value
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.flatten
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.flatten_json_column_and_join_back_to_df
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 10
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'filter'

### siege_utilities.distributed.floor
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.forall
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.format_number
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.format_string
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.from_csv
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `schema` should be a Column or str, got NoneType.

### siege_utilities.distributed.from_json
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.from_unixtime
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.from_utc_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.from_xml
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR_OR_STRUCT] Argument `schema` should be a StructType, Column or str, got NoneType.

### siege_utilities.distributed.get
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.get_json_object
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.get_quick_file_signature
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.get_row_count
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.getbit
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.greatest
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.grouping
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.grouping_id
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.hash
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.hex
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.histogram_numeric
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.hll_sketch_agg
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.hll_sketch_estimate
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.hll_union
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.hll_union_agg
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.hour
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.hours
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.hypot
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.ifnull
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.ilike
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.import_module_with_fallbacks
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.distributed.initcap
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.inline
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.inline_outer
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.input_file_block_length
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.input_file_block_start
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.input_file_name
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.instr
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.is_valid_utf8
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.is_variant_null
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.isnan
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.isnotnull
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.isnull
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.java_method
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.json_array_length
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.json_object_keys
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.json_tuple
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.kurtosis
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.lag
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.last
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.last_day
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.last_value
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.lcase
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.lead
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.least
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.left
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.length
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.levenshtein
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.like
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.listagg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.listagg_distinct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.lit
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.ln
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.localtimestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.locate
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.log
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.log10
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.log1p
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.log2
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.log_error
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.distributed.log_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.distributed.lower
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.lpad
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.ltrim
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.make_date
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.make_dt_interval
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.make_interval
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.make_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.make_timestamp_ltz
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.make_timestamp_ntz
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 6
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.make_valid_utf8
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.make_ym_interval
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.map_concat
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.map_contains_key
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.map_entries
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.map_filter
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.map_from_arrays
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.map_from_entries
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.map_keys
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.map_values
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.map_zip_with
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.mark_valid_geocode_data
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'columns'

### siege_utilities.distributed.mask
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.max
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.max_by
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.md5
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.mean
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.median
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.min
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.min_by
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.minute
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.mode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.monotonically_increasing_id
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.month
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.monthname
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.months
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.months_between
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.move_column_to_front_of_dataframe
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.distributed.named_struct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.nanvl
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.negate
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.negative
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.next_day
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.now
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.nth_value
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.ntile
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.nullif
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.nullifzero
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.nvl
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.nvl2
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.octet_length
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.overlay
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_INT_OR_STR] Argument `pos` should be a Column, int or str, got NoneType.

### siege_utilities.distributed.pandas_udf
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 3
- **Execution Error**: Failed with None values: [PACKAGE_NOT_INSTALLED] PyArrow >= 11.0.0 must be installed; however, it was not found.

### siege_utilities.distributed.parse_json
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.parse_url
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.percent_rank
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.percentile
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.percentile_approx
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.pi
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.pivot_summary_table_for_bools
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 3
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'count'

### siege_utilities.distributed.pivot_summary_with_metrics
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 4
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'groupBy'

### siege_utilities.distributed.pmod
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.posexplode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.posexplode_outer
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.position
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.positive
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.pow
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.power
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.prepare_dataframe_for_export
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'columns'

### siege_utilities.distributed.prepare_summary_dataframe
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 3
- **Execution Error**: Failed with None values: 'NoneType' object is not iterable

### siege_utilities.distributed.print_debug_table
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'toPandas'

### siege_utilities.distributed.printf
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.product
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.quarter
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.radians
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.raise_error
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.rand
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.randn
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.randstr
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.rank
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.read_parquet_to_df
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.distributed.reduce
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.reflect
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.regexp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regexp_count
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regexp_extract
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regexp_extract_all
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regexp_instr
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regexp_like
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regexp_replace
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.regexp_substr
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.register_temp_table
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.distributed.regr_avgx
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_avgy
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_count
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_intercept
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_r2
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_slope
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_sxx
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_sxy
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.regr_syy
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.repartition_and_cache
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.distributed.repeat
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.replace
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.reproject_geom_columns
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 4
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'split'

### siege_utilities.distributed.reverse
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.right
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.rint
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.rlike
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.round
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.row_number
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.rpad
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.rtrim
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.sanitise_dataframe_column_names
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.schema_of_csv
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `csv` should be a Column or str, got NoneType.

### siege_utilities.distributed.schema_of_json
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `json` should be a Column or str, got NoneType.

### siege_utilities.distributed.schema_of_variant
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.schema_of_variant_agg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.schema_of_xml
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `xml` should be a Column or str, got NoneType.

### siege_utilities.distributed.sec
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.second
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.sentences
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.sequence
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.session_user
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.session_window
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.setup_distributed_environment
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.sha
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.sha1
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.sha2
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [VALUE_NOT_ALLOWED] Value for `numBits` has to be amongst the following values: [0, 224, 256, 384, 512].

### siege_utilities.distributed.shiftleft
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.shiftright
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.shiftrightunsigned
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.shuffle
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.sign
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.signum
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.sin
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.sinh
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.size
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.skewness
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.slice
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.some
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.sort_array
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.soundex
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.spark_partition_id
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.split
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.split_part
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.sqrt
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.stack
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.startswith
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.std
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.stddev
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.stddev_pop
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.stddev_samp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.str_to_map
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.string_agg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.string_agg_distinct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.struct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.substr
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.substring
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.substring_index
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.sum
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.sum_distinct
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.tabulate_null_vs_not_null
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.distributed.tan
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.tanh
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.timestamp_add
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.timestamp_diff
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.timestamp_micros
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.timestamp_millis
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.timestamp_seconds
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.to_binary
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_char
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_csv
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_date
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_json
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_number
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_timestamp_ltz
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_timestamp_ntz
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_unix_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_utc_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.to_varchar
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.to_variant_object
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.to_xml
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.transform
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.transform_keys
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.transform_values
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.distributed.translate
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.trim
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.trunc
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_add
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_aes_decrypt
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.try_avg
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.try_divide
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_element_at
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_make_interval
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.try_make_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_make_timestamp_ltz
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 7
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_make_timestamp_ntz
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 6
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_mod
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_multiply
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_parse_json
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.try_parse_url
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.distributed.try_reflect
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.try_subtract
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_sum
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.try_to_binary
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_to_number
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_to_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.try_url_decode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.try_validate_utf8
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.try_variant_get
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.typeof
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.ucase
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.udf
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: udf() takes from 0 to 2 positional arguments but 3 were given

### siege_utilities.distributed.udtf
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: udtf() takes from 0 to 1 positional arguments but 3 were given

### siege_utilities.distributed.unbase64
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.unhex
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.uniform
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.unix_date
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.unix_micros
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.unix_millis
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.unix_seconds
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.unix_timestamp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.unwrap_udt
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.upper
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.url_decode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.url_encode
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.user
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.validate_geocode_data
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'columns'

### siege_utilities.distributed.validate_geometry
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 3
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'select'

### siege_utilities.distributed.validate_utf8
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.var_pop
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.var_samp
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.variance
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.variant_get
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 

### siege_utilities.distributed.version
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0
- **Execution Error**: Execution failed: 

### siege_utilities.distributed.weekday
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.weekofyear
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.when
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN] Argument `condition` should be a Column, got NoneType.

### siege_utilities.distributed.width_bucket
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.window
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.window_time
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.write_df_to_parquet
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3

### siege_utilities.distributed.xpath
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_boolean
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_double
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_float
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_int
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_long
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_number
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_short
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xpath_string
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: [NOT_COLUMN_OR_STR] Argument `col` should be a Column or str, got NoneType.

### siege_utilities.distributed.xxhash64
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.year
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.years
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.zeroifnull
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.distributed.zip_with
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: [SESSION_OR_CONTEXT_NOT_EXISTS] SparkContext or SparkSession should be created first.

### siege_utilities.files.cleanup_all_loggers
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 0

### siege_utilities.files.cleanup_logger
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.files.configure_shared_logging
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 4
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.files.disable_shared_logging
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 0

### siege_utilities.files.get_all_loggers
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 0

### siege_utilities.files.get_logger
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.files.init_logger
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 7

### siege_utilities.files.log_critical
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2

### siege_utilities.files.log_debug
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2

### siege_utilities.files.log_error
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2

### siege_utilities.files.log_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.files.log_warning
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 2

### siege_utilities.files.parse_log_level
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.files.set_default_logger_name
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.geo.compare_census_datasets
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.geo.concatenate_addresses
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 5

### siege_utilities.geo.get_analysis_approach
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'lower'

### siege_utilities.geo.get_best_dataset_for_analysis
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: None is not a valid GeographyLevel

### siege_utilities.geo.get_census_data_selector
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.geo.get_census_dataset_mapper
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.geo.get_census_intelligence
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 0

### siege_utilities.geo.quick_census_selection
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'lower'

### siege_utilities.geo.select_census_datasets
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'lower'

### siege_utilities.geo.use_nominatim_geocoder
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 4
- **Execution Error**: Failed with None values: name 'log_warning' is not defined

### siege_utilities.git.analyze_branch_status
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.apply_stash
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.categorize_commits
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.cherry_pick_commit
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.clean_working_directory
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3

### siege_utilities.git.complete_feature_workflow
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5

### siege_utilities.git.create_feature_branch
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: expected string or bytes-like object, got 'NoneType'

### siege_utilities.git.create_tag
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.enforce_commit_conventions
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.generate_branch_report
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.get_branch_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.get_commit_history
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.git.get_file_changes
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.get_log_summary
- **Status**: skipped
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Skipped - requires external dependencies

### siege_utilities.git.get_remote_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.get_repository_status
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.get_stash_list
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.get_tag_list
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.git.hotfix_workflow
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: Invalid hotfix name: ["Branch name doesn't follow any standard pattern", 'Branch name contains uppercase letters (use lowercase)', 'Branch name contains invalid characters']

### siege_utilities.git.merge_branch
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.pull_branch
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.push_branch
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.rebase_branch
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: expected str, bytes or os.PathLike object, not NoneType

### siege_utilities.git.release_workflow
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: expected string or bytes-like object, got 'NoneType'

### siege_utilities.git.reset_to_commit
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: Invalid reset type. Must be one of: ['soft', 'mixed', 'hard']

### siege_utilities.git.start_feature_workflow
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4
- **Execution Error**: Failed with None values: Invalid feature name: ["Branch name doesn't follow any standard pattern", 'Branch name contains uppercase letters (use lowercase)', 'Branch name contains invalid characters']

### siege_utilities.git.stash_changes
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3

### siege_utilities.git.switch_branch
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 'in <string>' requires string as left operand, not NoneType

### siege_utilities.git.validate_branch_naming
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.reporting.create_content_page
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 6
- **Execution Error**: Failed with None values: cannot unpack non-iterable NoneType object

### siege_utilities.reporting.create_table_of_contents
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 5
- **Execution Error**: Failed with None values: cannot unpack non-iterable NoneType object

### siege_utilities.reporting.create_title_page
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 8
- **Execution Error**: Failed with None values: cannot unpack non-iterable NoneType object

### siege_utilities.reporting.generate_sections_from_report_structure
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.testing.build_pytest_command
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 4

### siege_utilities.testing.check_java_version
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.testing.diagnose_environment
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.testing.ensure_env_vars
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 1

### siege_utilities.testing.get_system_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.testing.get_test_report
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.testing.import_module_with_fallbacks
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'startswith'

### siege_utilities.testing.log_error
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.testing.log_info
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: False
- **Parameters**: 1

### siege_utilities.testing.log_warning
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 2

### siege_utilities.testing.quick_environment_setup
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.testing.quick_smoke_test
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.testing.run_command
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 3
- **Execution Error**: Failed with None values: can only join an iterable

### siege_utilities.testing.run_comprehensive_test
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

### siege_utilities.testing.run_test_suite
- **Status**: failed
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 6
- **Execution Error**: Failed with None values: 'NoneType' object has no attribute 'upper'

### siege_utilities.testing.setup_spark_environment
- **Status**: working
- **Importable**: True
- **Callable**: True
- **Has Docstring**: True
- **Has Type Hints**: True
- **Parameters**: 0

