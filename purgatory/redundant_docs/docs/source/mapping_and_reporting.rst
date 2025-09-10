Mapping and Reporting System
============================

Overview
--------

The siege_utilities mapping and reporting system provides enterprise-grade capabilities for geographic data visualization and professional document generation. This system goes far beyond basic mapping to offer multiple visualization types, sophisticated document structures, and professional output formats.

Key Features
-----------

- **7+ Map Types**: Choropleth, marker, 3D, heatmap, cluster, and flow maps
- **Professional Reports**: PDF generation with TOC, sections, and appendices
- **PowerPoint Integration**: Automated presentation creation with various slide types
- **Client Branding**: Custom styling and professional appearance
- **Multiple Data Sources**: Integration with external APIs and databases

Installation
-----------

Install the required dependencies:

.. code-block:: bash

    pip install -r siege_utilities/reporting/requirements_bivariate_choropleth.txt

Required packages include:
- geopandas
- shapely
- folium
- matplotlib
- seaborn
- pandas
- numpy
- scipy

Quick Start
-----------

Basic Bivariate Choropleth Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.reporting.chart_generator import ChartGenerator
    import pandas as pd

    # Initialize chart generator
    chart_gen = ChartGenerator()

    # Sample data
    data = {
        'state': ['California', 'Texas', 'New York', 'Florida'],
        'population': [39512223, 28995881, 19453561, 21477737],
        'income': [75235, 64034, 72741, 59227]
    }
    df = pd.DataFrame(data)

    # Create bivariate choropleth
    chart = chart_gen.create_bivariate_choropleth_matplotlib(
        data=df,
        location_column='state',
        value_column1='population',
        value_column2='income',
        title="Population vs Income by State"
    )

Marker Map with Geographic Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Create marker map
    marker_map = chart_gen.create_marker_map(
        data=cities_df,
        latitude_column='latitude',
        longitude_column='longitude',
        value_column='population',
        label_column='city',
        title="US Cities Population Map"
    )

3D Elevation Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Create 3D elevation map
    elevation_map = chart_gen.create_3d_map(
        data=cities_df,
        latitude_column='latitude',
        longitude_column='longitude',
        elevation_column='elevation',
        title="City Elevation 3D Visualization"
    )

Comprehensive Report Generation
------------------------------

Creating Professional PDF Reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.reporting.report_generator import ReportGenerator

    # Initialize report generator
    report_gen = ReportGenerator()

    # Create comprehensive report
    report_content = report_gen.create_comprehensive_report(
        title="Geographic Analysis Report",
        author="Analytics Team",
        client="Research Institute",
        table_of_contents=True,
        page_numbers=True
    )

    # Add sections
    report_content = report_gen.add_map_section(
        report_content,
        "Regional Analysis",
        [bivariate_map],
        map_type="bivariate_choropleth"
    )

    # Generate PDF
    report_gen.generate_pdf_report(report_content, "report.pdf")

PowerPoint Presentation Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.reporting.powerpoint_generator import PowerPointGenerator

    # Initialize PowerPoint generator
    ppt_gen = PowerPointGenerator()

    # Create presentation
    presentation = ppt_gen.create_comprehensive_presentation(
        title="Geographic Analysis",
        include_toc=True,
        include_agenda=True
    )

    # Add slides
    presentation = ppt_gen.add_map_slide(
        presentation,
        "Regional Overview",
        [bivariate_map]
    )

    # Generate PowerPoint
    ppt_gen.generate_powerpoint_presentation(presentation, "presentation.pptx")

Map Types Reference
------------------

Bivariate Choropleth Maps
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    chart_gen.create_bivariate_choropleth_matplotlib(
        data=dataframe,
        geodata=geodataframe,
        location_column='region',
        value_column1='metric1',
        value_column2='metric2',
        title="Bivariate Analysis",
        width=12.0,
        height=10.0,
        color_scheme='custom'
    )

**Parameters:**
- ``data``: DataFrame with location and value data
- ``geodata``: GeoDataFrame or path to geographic file
- ``location_column``: Column name for geographic locations
- ``value_column1``: First variable for analysis
- ``value_column2``: Second variable for analysis
- ``title``: Map title
- ``width/height``: Dimensions in inches
- ``color_scheme``: Color palette selection

Marker Maps
~~~~~~~~~~~

.. code-block:: python

    chart_gen.create_marker_map(
        data=dataframe,
        latitude_column='lat',
        longitude_column='lon',
        value_column='population',
        label_column='city',
        title="Location Map",
        map_style='open-street-map',
        zoom_level=10
    )

**Parameters:**
- ``latitude_column``: Column containing latitude values
- ``longitude_column``: Column containing longitude values
- ``value_column``: Column for marker size encoding
- ``label_column``: Column for popup labels
- ``map_style``: Map tile style selection
- ``zoom_level``: Initial zoom level

3D Maps
~~~~~~~~

.. code-block:: python

    chart_gen.create_3d_map(
        data=dataframe,
        latitude_column='lat',
        longitude_column='lon',
        elevation_column='elevation',
        title="3D Visualization",
        view_angle=45,
        elevation_scale=1.0
    )

**Parameters:**
- ``elevation_column``: Column containing elevation/height data
- ``view_angle``: 3D viewing angle in degrees
- ``elevation_scale``: Scale factor for elevation values

Heatmap Maps
~~~~~~~~~~~~

.. code-block:: python

    chart_gen.create_heatmap_map(
        data=dataframe,
        latitude_column='lat',
        longitude_column='lon',
        value_column='intensity',
        title="Density Heatmap",
        grid_size=50,
        blur_radius=0.5
    )

**Parameters:**
- ``grid_size``: Number of grid cells for heatmap
- ``blur_radius``: Blur radius for smoothing

Cluster Maps
~~~~~~~~~~~~

.. code-block:: python

    chart_gen.create_cluster_map(
        data=dataframe,
        latitude_column='lat',
        longitude_column='lon',
        cluster_column='region',
        label_column='city',
        title="Clustered Locations",
        max_cluster_radius=80
    )

**Parameters:**
- ``cluster_column``: Column for clustering values
- ``max_cluster_radius``: Maximum radius for clustering

Flow Maps
~~~~~~~~~

.. code-block:: python

    chart_gen.create_flow_map(
        data=dataframe,
        origin_lat_column='origin_lat',
        origin_lon_column='origin_lon',
        dest_lat_column='dest_lat',
        dest_lon_column='dest_lon',
        flow_value_column='volume',
        title="Flow Patterns"
    )

**Parameters:**
- ``origin_lat_column``: Origin latitude column
- ``origin_lon_column``: Origin longitude column
- ``dest_lat_column``: Destination latitude column
- ``dest_lon_column``: Destination longitude column
- ``flow_value_column``: Flow intensity values

Advanced Choropleth Maps
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    chart_gen.create_advanced_choropleth(
        data=dataframe,
        geodata=geodataframe,
        location_column='region',
        value_column='metric',
        title="Advanced Analysis",
        classification='natural_breaks',
        bins=5,
        color_scheme='YlOrRd'
    )

**Classification Methods:**
- ``quantiles``: Equal number of observations per bin
- ``equal_interval``: Equal width bins
- ``natural_breaks``: Natural grouping of data

Report Structure
----------------

PDF Report Components
~~~~~~~~~~~~~~~~~~~~

1. **Title Page**: Cover with metadata and branding
2. **Table of Contents**: Automated with page numbers
3. **Executive Summary**: High-level overview
4. **Methodology**: Technical approach
5. **Content Sections**: Maps, charts, tables, text
6. **Appendices**: Supporting materials
7. **Professional Features**: Page numbering, headers, footers

PowerPoint Structure
~~~~~~~~~~~~~~~~~~~

1. **Title Slide**: Presentation header
2. **Table of Contents**: Navigation overview
3. **Agenda**: Meeting structure
4. **Content Slides**: Various types and layouts
5. **Summary**: Key points and next steps

Section Types
~~~~~~~~~~~~

- **Text Sections**: Rich text with formatting
- **Chart Sections**: Multiple chart layouts
- **Map Sections**: Geographic visualizations
- **Table Sections**: Data tables with styling
- **Appendix Sections**: Supporting materials

Integration Examples
-------------------

Google Analytics Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.analytics.google_analytics import GoogleAnalyticsConnector

    # Initialize connector
    ga_connector = GoogleAnalyticsConnector(
        credentials_path='credentials.json',
        property_id='your_property_id'
    )

    # Retrieve geographic data
    ga_data = ga_connector.batch_retrieve_ga_data(
        metrics=['sessions', 'bounce_rate'],
        dimensions=['country', 'region'],
        date_range=['2023-01-01', '2023-12-31']
    )

    # Create geographic visualization
    chart = chart_gen.create_bivariate_choropleth_matplotlib(
        data=ga_data,
        location_column='region',
        value_column1='sessions',
        value_column2='bounce_rate'
    )

Database Integration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.config.databases import DatabaseConnector

    # Initialize database connector
    db_connector = DatabaseConnector(
        connection_string='postgresql://user:password@localhost/dbname'
    )

    # Query customer data
    customer_data = db_connector.execute_query("""
        SELECT state, COUNT(*) as customers, AVG(revenue) as avg_revenue
        FROM customers GROUP BY state
    """)

    # Create customer analysis map
    chart = chart_gen.create_bivariate_choropleth_matplotlib(
        data=customer_data,
        location_column='state',
        value_column1='customers',
        value_column2='avg_revenue'
    )

Custom API Integration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import requests

    def fetch_api_data(endpoint, api_key):
        response = requests.get(endpoint, headers={'Authorization': f'Bearer {api_key}'})
        return response.json()

    # Fetch custom data
    custom_data = fetch_api_data(
        'https://api.example.com/geographic-metrics',
        'your_api_key'
    )

    # Process and visualize
    df = pd.DataFrame(custom_data)
    chart = chart_gen.create_marker_map(
        data=df,
        latitude_column='lat',
        longitude_column='lon',
        value_column='metric'
    )

Best Practices
--------------

Data Preparation
~~~~~~~~~~~~~~~

1. **Clean Data**: Remove duplicates and handle missing values
2. **Coordinate Systems**: Ensure consistent geographic projections
3. **Data Types**: Use appropriate numeric and string types
4. **Validation**: Verify geographic identifier matches

Map Design
~~~~~~~~~~

1. **Color Schemes**: Choose appropriate palettes for data characteristics
2. **Legend Design**: Clear and informative legends
3. **Title and Labels**: Descriptive and concise
4. **Scale and Projection**: Appropriate for geographic scope

Report Organization
~~~~~~~~~~~~~~~~~~

1. **Logical Flow**: Organize content in logical sequence
2. **Consistent Formatting**: Maintain professional appearance
3. **Clear Sections**: Well-defined section boundaries
4. **Appropriate Detail**: Match detail level to audience

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~

1. **Data Sampling**: Use sampling for large datasets
2. **Caching**: Cache frequently used geographic data
3. **Parallel Processing**: Use multi-core processing when available
4. **Memory Management**: Optimize data structures

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~

1. **"GeoPandas not available"**: Install required dependencies
2. **"Location column not found"**: Check column names in data
3. **"No numeric data found"**: Ensure value columns contain numbers
4. **Memory issues**: Use data sampling or optimization

Performance Issues
~~~~~~~~~~~~~~~~~

1. **Large Datasets**: Implement data aggregation
2. **Complex Geometries**: Simplify geographic boundaries
3. **Multiple Maps**: Use batch processing
4. **Rendering Quality**: Adjust DPI and figure sizes

Error Handling
~~~~~~~~~~~~~

1. **API Failures**: Implement retry logic
2. **Data Mismatches**: Validate geographic identifiers
3. **File Errors**: Check file paths and permissions
4. **Memory Errors**: Monitor resource usage

Examples and Recipes
--------------------

For comprehensive examples, see:
- `comprehensive_mapping_example.py` - Full demonstration
- `bivariate_choropleth_example.py` - Basic choropleth usage
- Recipe guides in `docs/recipes/reporting/`

Additional Resources
-------------------

- **API Reference**: Complete method documentation
- **Recipe Guides**: Step-by-step implementation
- **Best Practices**: Professional usage recommendations
- **Troubleshooting**: Common issues and solutions
- **Community Support**: GitHub issues and discussions

The mapping and reporting system provides enterprise-grade capabilities for geographic data visualization and professional document generation, making it easy to create publication-quality outputs for business intelligence and client reporting needs.
