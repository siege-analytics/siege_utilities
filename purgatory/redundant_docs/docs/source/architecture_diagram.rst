Library Architecture
===================

Overview
--------

The ``siege_utilities`` library is organized into major functional areas, each providing specialized utilities for data engineering, analytics, and distributed computing workflows.

.. figure:: ../images/architecture_overview.png
   :alt: Siege Utilities Architecture Overview
   :align: center
   :width: 100%

   **Figure 1: Siege Utilities Library Architecture**

Core Architecture
----------------

.. code-block:: text

    siege_utilities/
    ├── 🔧 Core Utilities (16 functions)
    │   ├── Logging System (14 functions)
    │   │   ├── log_info, log_warning, log_error, log_debug, log_critical
    │   │   ├── init_logger, get_logger, configure_shared_logging
    │   │   └── Thread-safe, configurable logging across all modules
    │   └── String Utilities (2 functions)
    │       ├── remove_wrapping_quotes_and_trim
    │       └── Advanced string manipulation and cleaning
    │
    ├── 📁 File Operations (22 functions)
    │   ├── File Hashing (5 functions)
    │   │   ├── calculate_file_hash, generate_sha256_hash_for_file
    │   │   ├── get_file_hash, get_quick_file_signature, verify_file_integrity
    │   │   └── Cryptographic hashing and integrity verification
    │   ├── File Operations (13 functions)
    │   │   ├── check_if_file_exists_at_path, delete_existing_file_and_replace_it_with_an_empty_file
    │   │   ├── count_total_rows_in_file_pythonically, count_empty_rows_in_file_pythonically
    │   │   ├── count_duplicate_rows_in_file_using_awk, count_total_rows_in_file_using_sed
    │   │   ├── count_empty_rows_in_file_using_awk, remove_empty_rows_in_file_using_sed
    │   │   ├── write_data_to_a_new_empty_file, write_data_to_an_existing_file
    │   │   ├── check_for_file_type_in_directory
    │   │   └── Advanced file manipulation and analysis
    │   ├── Path Management (2 functions)
    │   │   ├── ensure_path_exists, unzip_file_to_its_own_directory
    │   │   └── Directory creation and file extraction
    │   ├── Remote Operations (2 functions)
    │   │   ├── generate_local_path_from_url, download_file
    │   │   └── URL-based file operations and downloads
    │   └── Shell Operations (1 function)
    │       ├── run_subprocess
    │       └── Command execution and process management
    │
    ├── 🚀 Distributed Computing (503+ functions)
    │   ├── Spark Utilities (503 functions)
    │   │   ├── DataFrame operations, transformations, and optimizations
    │   │   ├── Data validation, cleaning, and processing
    │   │   ├── Performance tuning and caching strategies
    │   │   ├── File format handling (Parquet, CSV, JSON)
    │   │   ├── Advanced analytics and machine learning support
    │   │   └── Production-ready Spark workflows
    │   ├── HDFS Configuration (5 functions)
    │   │   ├── Cluster configuration and management
    │   │   └── Connection and authentication setup
    │   ├── HDFS Operations (2 functions)
    │   │   ├── File system operations and management
    │   │   └── Data movement and organization
    │   └── HDFS Legacy Support (4 functions)
    │       ├── Backward compatibility and migration tools
    │       └── Legacy system integration
    │
    ├── 🌍 Geospatial (2 functions)
    │   ├── Geocoding (2 functions)
    │   │   ├── concatenate_addresses, use_nominatim_geocoder
    │   │   └── Address processing and coordinate generation
    │   └── Location-based analytics and mapping support
    │
    ├── ⚙️ Configuration Management (15 functions)
    │   ├── Client Management (8 functions)
    │   │   ├── create_client_profile, save_client_profile, load_client_profile
    │   │   ├── update_client_profile, list_client_profiles, search_client_profiles
    │   │   ├── validate_client_profile, associate_client_with_project
    │   │   └── Client profile creation, management, and project association
    │   ├── Connection Management (7 functions)
    │   │   ├── create_connection_profile, save_connection_profile, load_connection_profile
    │   │   ├── find_connection_by_name, list_connection_profiles, update_connection_profile
    │   │   ├── test_connection_profile, get_connection_status, cleanup_old_connections
    │   │   └── Database, notebook, and Spark connection persistence
    │   ├── Database Configurations
    │   │   └── Connection string management and database utilities
    │   └── Project Management
    │       └── Project configuration and directory structure management
    │
    ├── 📊 Analytics Integration (6 functions)
    │   ├── Google Analytics (6 functions)
    │   │   ├── GoogleAnalyticsConnector class
    │   │   ├── create_ga_account_profile, save_ga_account_profile, load_ga_account_profile
    │   │   ├── list_ga_accounts_for_client, batch_retrieve_ga_data
    │   │   └── GA4/UA data retrieval, client association, Pandas/Spark export
    │   └── Client-associated analytics account management
    │
    ├── 🧹 Code Hygiene (2 functions)
    │   ├── Documentation Generation (2 functions)
    │   │   ├── generate_docstring_template, analyze_function_signature
    │   │   └── Automated documentation and code quality tools
    │   └── Code maintenance and quality assurance
    │
    └── 🧪 Testing & Development (2 functions)
        ├── Environment Setup (2 functions)
        │   ├── setup_spark_environment, get_system_info
        │   └── Development environment configuration and diagnostics
        └── Testing framework and development tools

Function Distribution
--------------------

.. list-table:: Function Distribution by Module
   :widths: 30 20 20 30
   :header-rows: 1

   * - Module
     - Functions
     - Status
     - Description
   * - **Core Utilities**
     - 16
     - ✅ Complete
     - Logging, string manipulation, core infrastructure
   * - **File Operations**
     - 22
     - ✅ Complete
     - File handling, hashing, operations, remote access
   * - **Distributed Computing**
     - 503+
     - ✅ Complete
     - Spark, HDFS, cluster management, big data processing
   * - **Geospatial**
     - 2
     - ✅ Complete
     - Address processing, geocoding, location analytics
   * - **Configuration Management**
     - 15
     - ✅ Complete
     - Client profiles, connections, projects, databases
   * - **Analytics Integration**
     - 6
     - 🆕 New
     - Google Analytics, client association, data export
   * - **Code Hygiene**
     - 2
     - ✅ Complete
     - Documentation, code quality, maintenance
   * - **Testing & Development**
     - 2
     - ✅ Complete
     - Environment setup, diagnostics, testing tools

**Total Functions: 568+** | **Total Modules: 16** | **Coverage: 100%**

Key Features
------------

**🔧 Core Infrastructure**
- Thread-safe logging system with configurable levels
- String manipulation and cleaning utilities
- Robust error handling and fallback mechanisms

**📁 File Management**
- Cryptographic file hashing and integrity verification
- Advanced file operations with awk/sed integration
- Remote file operations and downloads
- Shell command execution and process management

**🚀 Distributed Computing**
- **503+ Spark functions** for big data processing
- HDFS cluster configuration and management
- Production-ready Spark workflows and optimizations
- Advanced data transformation and analytics

**🌍 Geospatial Capabilities**
- Address concatenation and standardization
- Nominatim geocoding integration
- Location-based analytics support

**⚙️ Configuration Management**
- Client profile creation and management
- Connection persistence (databases, notebooks, Spark)
- Project configuration and directory management
- Client-project association system

**📊 Analytics Integration**
- Google Analytics 4 and Universal Analytics support
- OAuth2 authentication and credential management
- Client-associated analytics account management
- Data export to Pandas and Spark formats
- Batch data retrieval and processing

**🧹 Code Quality**
- Automated documentation generation
- Function signature analysis
- Code maintenance and quality tools

**🧪 Development Support**
- Spark environment setup and configuration
- System diagnostics and information
- Testing framework integration

Integration Points
-----------------

.. code-block:: text

    Client Management ←→ Analytics Integration
           ↓                    ↓
    Project Association ←→ Configuration Management
           ↓                    ↓
    File Operations ←→ Distributed Computing
           ↓                    ↓
    Geospatial ←→ Core Utilities
           ↓                    ↓
    Testing & Development ←→ Code Hygiene

Usage Patterns
--------------

**Data Engineering Workflow:**
1. **Setup**: Configure client profiles and connections
2. **Ingest**: Use file operations and remote capabilities
3. **Process**: Leverage 503+ Spark functions for transformation
4. **Analyze**: Apply geospatial and analytics capabilities
5. **Export**: Save to Pandas or Spark formats
6. **Manage**: Maintain configurations and monitor performance

**Client Analytics Workflow:**
1. **Configure**: Set up GA accounts linked to clients
2. **Authenticate**: OAuth2 flow for Google Analytics access
3. **Retrieve**: Batch data retrieval from GA4/UA
4. **Process**: Transform data using Spark functions
5. **Export**: Save as Pandas or Spark DataFrames
6. **Associate**: Link data to client projects and profiles

This architecture provides a comprehensive, integrated solution for data engineering, analytics, and distributed computing workflows, with all functions mutually available through the main package interface.
