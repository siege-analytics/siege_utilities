Getting Started
==============

Welcome to Siege Utilities! This comprehensive library provides **568+ functions** across **16 modules** for data engineering, analytics, and distributed computing workflows.

Quick Start
-----------

.. code-block:: python

    # Import the entire library - all functions are available!
    import siege_utilities as su
    
    # Check what's available
    print(f"Total functions: {len(su.get_available_functions())}")
    print(f"Package info: {su.get_package_info()}")

Core Capabilities
----------------

🔧 **Core Utilities (16 functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thread-safe logging system and string manipulation:

.. code-block:: python

    # Initialize logging
    su.init_logger(level='INFO')
    
    # Use logging functions anywhere
    su.log_info("Starting data processing")
    su.log_warning("Large dataset detected")
    su.log_error("Processing failed")
    
    # String utilities
    cleaned = su.remove_wrapping_quotes_and_trim('  "hello world"  ')
    print(cleaned)  # Output: hello world

📁 **File Operations (22 functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Advanced file handling, hashing, and operations:

.. code-block:: python

    # File hashing and integrity
    file_hash = su.calculate_file_hash('data.csv', algorithm='sha256')
    is_valid = su.verify_file_integrity('data.csv', expected_hash=file_hash)
    
    # File analysis
    total_rows = su.count_total_rows_in_file_pythonically('data.csv')
    empty_rows = su.count_empty_rows_in_file_pythonically('data.csv')
    
    # Path management
    su.ensure_path_exists('/path/to/new/directory')
    su.unzip_file_to_its_own_directory('archive.zip')
    
    # Remote operations
    local_path = su.generate_local_path_from_url('https://example.com/file.csv')
    su.download_file('https://example.com/file.csv', 'local_file.csv')

🚀 **Distributed Computing (503+ functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**This is where the power lies!** Full Spark ecosystem support:

.. code-block:: python

    # All 503+ Spark functions are available!
    from siege_utilities.distributed import spark_utils
    
    # DataFrame operations
    row_count = su.get_row_count(spark_df)
    su.repartition_and_cache(spark_df, num_partitions=10)
    
    # Data validation
    su.validate_geocode_data(spark_df)
    
    # File operations
    su.write_df_to_parquet(spark_df, 'output.parquet')
    new_df = su.read_parquet_to_df('input.parquet')
    
    # Advanced transformations
    flattened_df = su.flatten_json_column_and_join_back_to_df(
        spark_df, 'json_column'
    )
    
    # Performance optimization
    su.backup_full_dataframe(spark_df, 'backup.parquet')
    su.atomic_write_with_staging(spark_df, 'final_output.parquet')

🌍 **Geospatial (2 functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Address processing and geocoding:

.. code-block:: python

    # Address concatenation
    full_address = su.concatenate_addresses(
        street='123 Main St',
        city='New York',
        state='NY',
        zip_code='10001'
    )
    
    # Geocoding
    coordinates = su.use_nominatim_geocoder(full_address)
    print(f"Lat: {coordinates['lat']}, Lon: {coordinates['lon']}")

⚙️ **Configuration Management (15 functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Client profiles, connections, and project management:

.. code-block:: python

    # Client management
    client = su.create_client_profile(
        "Acme Corp", "ACME001",
        {"primary_contact": "John Doe", "email": "john@acme.com"}
    )
    su.save_client_profile(client)
    
    # Connection management
    connection = su.create_connection_profile(
        "Production DB", "database",
        {"connection_string": "postgresql://user:pass@localhost:5432/db"}
    )
    su.save_connection_profile(connection)
    
    # Project association
    su.associate_client_with_project("ACME001", "PROJ001")

📊 **Analytics Integration (6 functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Google Analytics integration with client association:

.. code-block:: python

    # Create GA account profile
    ga_profile = su.create_ga_account_profile(
        client_id="ACME001",
        ga_property_id="123456789",
        account_type="ga4"
    )
    su.save_ga_account_profile(ga_profile)
    
    # Batch data retrieval
    results = su.batch_retrieve_ga_data(
        client_id="ACME001",
        start_date="2024-01-01",
        end_date="2024-01-31",
        metrics=["sessions", "pageviews", "users"],
        dimensions=["date", "pagePath"],
        output_format="both"  # Both Pandas and Spark
    )
    
    print(f"Retrieved {results['total_rows']} rows from {results['accounts_processed']} accounts")

🧹 **Code Hygiene (2 functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Documentation and code quality tools:

.. code-block:: python

    # Generate docstring templates
    template = su.generate_docstring_template('my_function')
    
    # Analyze function signatures
    analysis = su.analyze_function_signature('my_function')

🧪 **Testing & Development (2 functions)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Environment setup and diagnostics:

.. code-block:: python

    # Setup Spark environment
    su.setup_spark_environment()
    
    # Get system information
    system_info = su.get_system_info()

Real-World Workflow Examples
---------------------------

**Data Engineering Pipeline:**

.. code-block:: python

    import siege_utilities as su
    
    # 1. Setup and logging
    su.init_logger(level='INFO')
    su.log_info("Starting data engineering pipeline")
    
    # 2. File operations
    su.ensure_path_exists('data/raw')
    su.ensure_path_exists('data/processed')
    
    # 3. Data ingestion
    su.download_file('https://api.example.com/data.csv', 'data/raw/input.csv')
    
    # 4. Data processing with Spark
    spark_df = su.read_parquet_to_df('data/raw/input.csv')
    su.validate_geocode_data(spark_df)
    
    # 5. Save processed data
    su.write_df_to_parquet(spark_df, 'data/processed/output.parquet')
    
    su.log_info("Pipeline completed successfully")

**Client Analytics Workflow:**

.. code-block:: python

    import siege_utilities as su
    
    # 1. Client setup
    client = su.create_client_profile(
        "Tech Startup", "TECH001",
        {"primary_contact": "Jane Smith", "email": "jane@techstartup.com"}
    )
    su.save_client_profile(client)
    
    # 2. GA account setup
    ga_profile = su.create_ga_account_profile(
        client_id="TECH001",
        ga_property_id="987654321",
        account_type="ga4"
    )
    su.save_ga_account_profile(ga_profile)
    
    # 3. Data retrieval
    results = su.batch_retrieve_ga_data(
        client_id="TECH001",
        start_date="2024-01-01",
        end_date="2024-01-31",
        metrics=["sessions", "pageviews"],
        dimensions=["date", "pagePath"],
        output_format="spark"
    )
    
    # 4. Process with Spark
    if results['success']:
        su.log_info(f"Retrieved {results['total_rows']} rows of analytics data")
        # Continue with Spark processing...

Installation and Dependencies
---------------------------

**Core Dependencies:**
- Python 3.8+
- pandas
- pathlib
- requests

**Optional Dependencies:**
- **PySpark**: For distributed computing (503+ functions)
- **Google Analytics**: For analytics integration
- **Geospatial**: For location-based analytics

**Installation:**

.. code-block:: bash

    # Basic installation
    pip install siege_utilities
    
    # With all dependencies
    pip install siege_utilities[full]
    
    # With specific components
    pip install siege_utilities[spark]      # PySpark support
    pip install siege_utilities[analytics]  # Google Analytics support

Performance and Scalability
--------------------------

- **Local Development**: All functions work locally for development and testing
- **Distributed Processing**: 503+ Spark functions for big data workflows
- **Memory Efficient**: Optimized for large datasets and production environments
- **Scalable**: From single-machine to cluster deployments

Next Steps
----------

1. **Explore Functions**: Use `su.get_available_functions()` to see all 568+ functions
2. **Check Package Info**: Use `su.get_package_info()` for detailed module information
3. **Run Tests**: Use the testing framework to verify functionality
4. **Build Workflows**: Combine functions to create your data engineering pipelines

The library is designed to be **mutually available** - every function can access every other function, creating a powerful and flexible development environment for data engineering and analytics workflows.
