#!/usr/bin/env python3
"""
Census Data Intelligence System - Streamlit Demo
Interactive web application showcasing all Census Data Intelligence capabilities
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from siege_utilities.geo import (
        CensusDirectoryDiscovery, CensusDataSource,
        select_census_datasets, get_analysis_approach,
        get_census_dataset_mapper, get_census_data_selector
    )
    CENSUS_AVAILABLE = True
except ImportError as e:
    st.error(f"Failed to import Census utilities: {e}")
    CENSUS_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Census Data Intelligence System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #1f77b4;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""
    
    # Header
    st.markdown('<h1 class="main-header">🧠 Census Data Intelligence System</h1>', unsafe_allow_html=True)
    st.markdown("### Making complex Census data human-comprehensible!")
    
    if not CENSUS_AVAILABLE:
        st.error("""
        **Census utilities not available!** 
        
        Please install the required dependencies:
        ```bash
        pip install siege-utilities[geo]
        ```
        """)
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a section:",
        [
            "🏠 Home & Overview",
            "🔍 Data Discovery",
            "🧠 Intelligent Selection",
            "📊 Analysis Examples",
            "🏗️ System Architecture",
            "⚙️ Configuration & Setup"
        ]
    )
    
    # Page routing
    if page == "🏠 Home & Overview":
        show_home_page()
    elif page == "🔍 Data Discovery":
        show_data_discovery_page()
    elif page == "🧠 Intelligent Selection":
        show_intelligent_selection_page()
    elif page == "📊 Analysis Examples":
        show_analysis_examples_page()
    elif page == "🏗️ System Architecture":
        show_architecture_page()
    elif page == "⚙️ Configuration & Setup":
        show_configuration_page()

def show_home_page():
    """Display the home page with overview and key features"""
    
    st.header("🏠 Welcome to Census Data Intelligence")
    
    # Key features overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🧠 Intelligent Selection</h3>
            <p>AI-powered recommendations for the best Census datasets</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>🔗 Relationship Mapping</h3>
            <p>Understand how Census datasets relate to each other</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>✅ Quality Assurance</h3>
            <p>Built-in guidance for methodology and best practices</p>
        </div>
        """, unsafe_allow_html=True)
    
    # System status
    st.subheader("📊 System Status")
    
    try:
        # Check Census utilities availability
        discovery = CensusDirectoryDiscovery()
        source = CensusDataSource()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Census Discovery", "✅ Available")
        
        with col2:
            st.metric("State Information", "✅ Available")
        
        with col3:
            st.metric("Dataset Mapper", "✅ Available")
        
        with col4:
            st.metric("Data Selector", "✅ Available")
        
        st.success("🎉 All Census Data Intelligence components are available and ready!")
        
    except Exception as e:
        st.error(f"❌ System check failed: {e}")
    
    # Quick start guide
    st.subheader("🚀 Quick Start Guide")
    
    st.markdown("""
    ### 1. **Data Discovery**
    Navigate to the **Data Discovery** section to explore available Census years and boundary types.
    
    ### 2. **Intelligent Selection**
    Use the **Intelligent Selection** section to get AI-powered recommendations for your analysis.
    
    ### 3. **Analysis Examples**
    Check out the **Analysis Examples** section for real-world use cases and workflows.
    
    ### 4. **System Architecture**
    Learn about the system design in the **System Architecture** section.
    """)
    
    # Recent updates
    st.subheader("📝 Recent Updates")
    
    st.markdown("""
    - **Enhanced Census Utilities**: Dynamic discovery and intelligent data access
    - **Advanced Census Workflows**: End-to-end Census data analysis pipelines
    - **Census Data Intelligence Guide**: Complete guide to Census data selection
    - **Real Estate Market Intelligence**: Market analysis and investment insights
    - **Business Intelligence Site Selection**: Location optimization for businesses
    """)

def show_data_discovery_page():
    """Display the data discovery page"""
    
    st.header("🔍 Census Data Discovery")
    st.markdown("Explore available Census data and discover what's available for your analysis.")
    
    try:
        # Initialize discovery system
        discovery = CensusDirectoryDiscovery()
        source = CensusDataSource()
        
        # Available years
        st.subheader("📅 Available Census Years")
        
        with st.spinner("Discovering available years..."):
            years = discovery.get_available_years()
        
        if years:
            # Create a nice visualization of available years
            years_df = pd.DataFrame({'Year': years})
            years_df = years_df.sort_values('Year', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(
                    years_df, 
                    x='Year', 
                    y=[1] * len(years_df),
                    title="Available Census Years",
                    labels={'y': 'Available'},
                    color='Year',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.write("**Available Years:**")
                for year in years[:10]:  # Show first 10
                    st.write(f"• {year}")
                if len(years) > 10:
                    st.write(f"... and {len(years) - 10} more")
        
        # Available boundary types
        st.subheader("🗺️ Available Boundary Types")
        
        with st.spinner("Discovering available boundary types..."):
            boundaries = discovery.get_available_boundary_types()
        
        if boundaries:
            boundary_df = pd.DataFrame([
                {'Boundary Type': k, 'Available': 'Yes'} 
                for k in boundaries.keys()
            ])
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(
                    boundary_df,
                    x='Boundary Type',
                    y=[1] * len(boundary_df),
                    title="Available Boundary Types",
                    labels={'y': 'Available'},
                    color='Boundary Type'
                )
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.write("**Boundary Types:**")
                for boundary in boundaries.keys():
                    st.write(f"• {boundary}")
        
        # State information system
        st.subheader("🏛️ State Information System")
        
        # State lookup interface
        col1, col2 = st.columns(2)
        
        with col1:
            state_input = st.selectbox(
                "Select a state:",
                ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
            )
        
        with col2:
            lookup_type = st.selectbox(
                "Lookup by:",
                ["Abbreviation", "Name", "FIPS Code"]
            )
        
        if st.button("Get State Information"):
            try:
                if lookup_type == "Abbreviation":
                    info = source.get_comprehensive_state_info(state_input)
                elif lookup_type == "Name":
                    info = source.get_state_by_name(state_input)
                else:  # FIPS
                    info = source.get_state_by_fips(state_input)
                
                if info:
                    st.success(f"**State Information for {info.get('name', state_input)}**")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Name", info.get('name', 'N/A'))
                    with col2:
                        st.metric("FIPS Code", info.get('fips', 'N/A'))
                    with col3:
                        st.metric("Abbreviation", info.get('abbreviation', 'N/A'))
                else:
                    st.error("State not found")
                    
            except Exception as e:
                st.error(f"Error looking up state: {e}")
        
        # Data availability checker
        st.subheader("🔍 Check Data Availability")
        
        col1, col2 = st.columns(2)
        
        with col1:
            check_year = st.selectbox("Select year:", years[:10] if years else [])
        
        with col2:
            check_boundary = st.selectbox("Select boundary type:", list(boundaries.keys()) if boundaries else [])
        
        if st.button("Check Availability"):
            try:
                available = discovery.check_data_availability(check_year, check_boundary)
                if available:
                    st.success(f"✅ Data available for {check_boundary} boundaries in {check_year}")
                else:
                    st.warning(f"⚠️ Data not available for {check_boundary} boundaries in {check_year}")
            except Exception as e:
                st.error(f"Error checking availability: {e}")
    
    except Exception as e:
        st.error(f"Data discovery failed: {e}")

def show_intelligent_selection_page():
    """Display the intelligent selection page"""
    
    st.header("🧠 Intelligent Dataset Selection")
    st.markdown("Get AI-powered recommendations for the best Census datasets based on your analysis needs.")
    
    try:
        # Analysis type selection
        st.subheader("🎯 Analysis Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            analysis_type = st.selectbox(
                "Analysis Type:",
                [
                    "demographics", "housing", "business", "transportation",
                    "education", "health", "poverty", "employment",
                    "income", "migration", "veterans", "disability"
                ]
            )
        
        with col2:
            geography_level = st.selectbox(
                "Geography Level:",
                [
                    "nation", "state", "county", "tract", "block group",
                    "block", "cd", "zcta", "place", "cbsa"
                ]
            )
        
        # Additional parameters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            time_period = st.selectbox(
                "Time Period:",
                ["2020", "2019", "2018", "2017", "2016", "2015", "2010", "2000"]
            )
        
        with col2:
            variables = st.multiselect(
                "Variables of Interest:",
                [
                    "population", "income", "education", "housing", "employment",
                    "poverty", "age", "race", "ethnicity", "language",
                    "commute", "health_insurance", "veteran_status"
                ]
            )
        
        with col3:
            reliability_requirement = st.selectbox(
                "Reliability Requirement:",
                ["High", "Medium", "Low", "Any"]
            )
        
        # Get recommendations
        if st.button("🚀 Get Dataset Recommendations"):
            with st.spinner("Analyzing your requirements and finding the best datasets..."):
                try:
                    recommendations = select_census_datasets(
                        analysis_type=analysis_type,
                        geography_level=geography_level,
                        time_period=time_period,
                        variables=variables,
                        reliability_requirement=reliability_requirement
                    )
                    
                    if recommendations and 'recommendations' in recommendations:
                        st.success("✅ Dataset recommendations generated successfully!")
                        
                        # Display primary recommendation
                        primary = recommendations.get('primary_recommendation')
                        if primary:
                            st.subheader("🥇 Primary Recommendation")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Dataset", primary.get('dataset', 'N/A'))
                            with col2:
                                st.metric("Reliability", primary.get('reliability', 'N/A'))
                            with col3:
                                st.metric("Coverage", primary.get('coverage', 'N/A'))
                            
                            st.markdown(f"**Rationale:** {primary.get('rationale', 'N/A')}")
                        
                        # Display all recommendations
                        st.subheader("📋 All Recommendations")
                        
                        recs_df = pd.DataFrame(recommendations['recommendations'])
                        if not recs_df.empty:
                            st.dataframe(recs_df, use_container_width=True)
                        
                        # Display analysis approach
                        if 'analysis_approach' in recommendations:
                            st.subheader("📊 Recommended Analysis Approach")
                            st.info(recommendations['analysis_approach'])
                        
                        # Display methodology notes
                        if 'methodology_notes' in recommendations:
                            st.subheader("📚 Methodology Notes")
                            for note in recommendations['methodology_notes']:
                                st.write(f"• {note}")
                        
                        # Display quality checks
                        if 'quality_checks' in recommendations:
                            st.subheader("✅ Quality Checks")
                            for check in recommendations['quality_checks']:
                                st.write(f"• {check}")
                        
                        # Display reporting considerations
                        if 'reporting_considerations' in recommendations:
                            st.subheader("📝 Reporting Considerations")
                            for consideration in recommendations['reporting_considerations']:
                                st.write(f"• {consideration}")
                        
                        # Export recommendations
                        if st.button("📥 Export Recommendations"):
                            recommendations_json = json.dumps(recommendations, indent=2)
                            st.download_button(
                                label="Download JSON",
                                data=recommendations_json,
                                file_name=f"census_recommendations_{analysis_type}_{geography_level}.json",
                                mime="application/json"
                            )
                    
                    else:
                        st.warning("No recommendations found for the specified parameters.")
                        
                except Exception as e:
                    st.error(f"Failed to get recommendations: {e}")
        
        # Dataset comparison
        st.subheader("🔍 Dataset Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            dataset1 = st.text_input("First dataset name:")
        
        with col2:
            dataset2 = st.text_input("Second dataset name:")
        
        if st.button("Compare Datasets"):
            if dataset1 and dataset2:
                try:
                    from siege_utilities.geo import compare_census_datasets
                    comparison = compare_census_datasets(dataset1, dataset2)
                    
                    if comparison:
                        st.success("Dataset comparison completed!")
                        
                        # Display comparison results
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**{dataset1}**")
                            st.write(f"Survey Type: {comparison.get('survey_type_1', 'N/A')}")
                            st.write(f"Geography: {comparison.get('geography_levels_1', 'N/A')}")
                            st.write(f"Reliability: {comparison.get('reliability_1', 'N/A')}")
                        
                        with col2:
                            st.write(f"**{dataset2}**")
                            st.write(f"Survey Type: {comparison.get('survey_type_2', 'N/A')}")
                            st.write(f"Geography: {comparison.get('geography_levels_2', 'N/A')}")
                            st.write(f"Reliability: {comparison.get('reliability_2', 'N/A')}")
                        
                        # Display overlap analysis
                        if 'variable_overlap' in comparison:
                            st.write(f"**Variable Overlap:** {len(comparison['variable_overlap'])} variables")
                        
                        if 'geography_overlap' in comparison:
                            st.write(f"**Geography Overlap:** {len(comparison['geography_overlap'])} levels")
                        
                        # Display recommendations
                        if 'recommendations' in comparison:
                            st.subheader("💡 Recommendations")
                            for rec in comparison['recommendations']:
                                st.write(f"• {rec}")
                    else:
                        st.warning("Could not compare the specified datasets.")
                        
                except Exception as e:
                    st.error(f"Dataset comparison failed: {e}")
            else:
                st.warning("Please enter both dataset names.")
    
    except Exception as e:
        st.error(f"Intelligent selection failed: {e}")

def show_analysis_examples_page():
    """Display analysis examples and use cases"""
    
    st.header("📊 Analysis Examples & Use Cases")
    st.markdown("Real-world examples demonstrating how to use the Census Data Intelligence System.")
    
    # Example 1: Demographic Analysis
    st.subheader("👥 Example 1: Demographic Analysis Pipeline")
    
    with st.expander("Click to see the complete demographic analysis workflow"):
        st.markdown("""
        ### Complete Demographic Analysis Pipeline
        
        This example shows how to perform a comprehensive demographic analysis:
        
        ```python
        from siege_utilities.geo import select_census_datasets, get_analysis_approach
        
        # 1. Get dataset recommendations
        recommendations = select_census_datasets(
            analysis_type="demographics",
            geography_level="tract",
            variables=["population", "income", "education", "age", "race"]
        )
        
        # 2. Get analysis approach
        approach = get_analysis_approach(
            analysis_type="demographics",
            geography_level="tract",
            time_constraints="medium"
        )
        
        # 3. Follow the recommended approach
        print(f"Primary dataset: {recommendations['primary_recommendation']['dataset']}")
        print(f"Analysis approach: {approach['approach']}")
        ```
        
        **Key Benefits:**
        - Automatic dataset selection
        - Methodology guidance
        - Quality assurance checks
        - Reporting considerations
        """)
    
    # Example 2: Real Estate Market Intelligence
    st.subheader("🏠 Example 2: Real Estate Market Intelligence")
    
    with st.expander("Click to see the real estate market analysis workflow"):
        st.markdown("""
        ### Real Estate Market Intelligence System
        
        This example demonstrates market analysis and investment insights:
        
        ```python
        from siege_utilities.geo import select_census_datasets
        
        # Get datasets for real estate analysis
        recommendations = select_census_datasets(
            analysis_type="housing",
            geography_level="tract",
            variables=["housing_units", "median_value", "rent", "occupancy"]
        )
        
        # Combine with demographic data
        demo_recommendations = select_census_datasets(
            analysis_type="demographics",
            geography_level="tract",
            variables=["income", "education", "age"]
        )
        
        # Analyze market potential
        print("Market Analysis Datasets:")
        print(f"Housing: {recommendations['primary_recommendation']['dataset']}")
        print(f"Demographics: {demo_recommendations['primary_recommendation']['dataset']}")
        ```
        
        **Use Cases:**
        - Investment opportunity identification
        - Market saturation analysis
        - Demographic fit assessment
        - Property value forecasting
        """)
    
    # Example 3: Business Site Selection
    st.subheader("🏢 Example 3: Business Site Selection")
    
    with st.expander("Click to see the business site selection workflow"):
        st.markdown("""
        ### Business Intelligence Site Selection
        
        This example shows location optimization for businesses:
        
        ```python
        from siege_utilities.geo import select_census_datasets, get_analysis_approach
        
        # Get datasets for business analysis
        recommendations = select_census_datasets(
            analysis_type="business",
            geography_level="tract",
            variables=["employment", "businesses", "income", "education"]
        )
        
        # Get analysis approach
        approach = get_analysis_approach(
            analysis_type="business",
            geography_level="tract"
        )
        
        # Site selection criteria
        print("Site Selection Analysis:")
        print(f"Primary dataset: {recommendations['primary_recommendation']['dataset']}")
        print(f"Approach: {approach['approach']}")
        ```
        
        **Applications:**
        - Retail location optimization
        - Service area analysis
        - Competitive landscape assessment
        - Market penetration strategy
        """)
    
    # Interactive example builder
    st.subheader("🔧 Build Your Own Example")
    
    col1, col2 = st.columns(2)
    
    with col1:
        example_type = st.selectbox(
            "Example Type:",
            ["Custom Analysis", "Dataset Comparison", "Workflow Builder"]
        )
    
    with col2:
        if example_type == "Custom Analysis":
            st.write("Configure your analysis parameters")
        elif example_type == "Dataset Comparison":
            st.write("Compare two datasets")
        else:
            st.write("Build a custom workflow")
    
    if st.button("🚀 Generate Example"):
        st.info("Example generation feature coming soon! This will allow you to build custom analysis workflows.")

def show_architecture_page():
    """Display system architecture information"""
    
    st.header("🏗️ System Architecture")
    st.markdown("Learn about the design decisions and system architecture of the Census Data Intelligence System.")
    
    # Architecture overview
    st.subheader("🏛️ High-Level Architecture")
    
    st.markdown("""
    The Census Data Intelligence System follows a **hybrid OOP/Functional design** that combines:
    
    - **Object-Oriented Programming** for complex state management
    - **Functional Programming** for stateless utilities
    - **Enum-based Type System** for categorical data
    - **Dataclass-based Data Structures** for structured information
    """)
    
    # Component diagram
    st.subheader("🔧 System Components")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Core Components:**
        
        - **CensusDirectoryDiscovery**: Dynamic data discovery
        - **CensusDataSource**: Data access and state information
        - **CensusDatasetMapper**: Dataset relationship mapping
        - **CensusDataSelector**: Intelligent dataset selection
        
        **Supporting Systems:**
        
        - **State Information System**: FIPS codes and lookups
        - **URL Construction**: Dynamic Census URL building
        - **Caching System**: Performance optimization
        - **Error Handling**: Graceful degradation
        """)
    
    with col2:
        st.markdown("""
        **Design Patterns:**
        
        - **Factory Pattern**: Dataset creation and management
        - **Strategy Pattern**: Analysis approach selection
        - **Template Method**: Workflow definition
        - **Observer Pattern**: Change notification
        
        **Data Structures:**
        
        - **Enums**: SurveyType, GeographyLevel, DataReliability
        - **Dataclasses**: CensusDataset, DatasetRelationship
        - **Dictionaries**: Configuration and mapping data
        - **Lists**: Collections and recommendations
        """)
    
    # Data flow
    st.subheader("📊 Data Flow")
    
    st.markdown("""
    **1. Discovery Phase:**
    - Parse Census TIGER/Line directory structure
    - Identify available years and boundary types
    - Cache discovery results for performance
    
    **2. Selection Phase:**
    - Analyze user requirements and constraints
    - Score datasets based on suitability
    - Generate recommendations with rationale
    
    **3. Analysis Phase:**
    - Provide methodology guidance
    - Suggest quality checks
    - Recommend reporting approaches
    
    **4. Integration Phase:**
    - Connect with external data sources
    - Support multiple output formats
    - Enable workflow automation
    """)
    
    # Performance characteristics
    st.subheader("⚡ Performance Characteristics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Optimization Features:**
        
        - **Lazy Loading**: Load data only when needed
        - **Intelligent Caching**: Minimize network requests
        - **Batch Operations**: Process multiple items efficiently
        - **Parallel Processing**: Concurrent data operations
        """)
    
    with col2:
        st.markdown("""
        **Scalability Features:**
        
        - **Modular Design**: Easy to extend and modify
        - **Plugin Architecture**: Support for custom data sources
        - **API Integration**: RESTful interfaces for external systems
        - **Distributed Support**: Work with Spark and distributed computing
        """)
    
    # Future directions
    st.subheader("🚀 Future Architecture Directions")
    
    st.markdown("""
    **Planned Enhancements:**
    
    - **Machine Learning Integration**: AI-powered dataset recommendations
    - **Microservices Architecture**: Scalable service deployment
    - **Real-time Processing**: Streaming data analysis capabilities
    - **Cloud Native**: Kubernetes and container orchestration
    
    **Integration Opportunities:**
    
    - **Data Science Platforms**: Jupyter, Databricks, Snowflake
    - **Business Intelligence**: Tableau, Power BI, Looker
    - **Geographic Systems**: ArcGIS, QGIS, Mapbox
    - **Enterprise Systems**: SAP, Salesforce, Microsoft Dynamics
    """)

def show_configuration_page():
    """Display configuration and setup information"""
    
    st.header("⚙️ Configuration & Setup")
    st.markdown("Configure and customize the Census Data Intelligence System for your needs.")
    
    # Installation guide
    st.subheader("📦 Installation Guide")
    
    st.markdown("""
    ### Basic Installation
    
    ```bash
    # Install with geographic dependencies
    pip install siege-utilities[geo]
    
    # Or install all dependencies
    pip install siege-utilities[all]
    ```
    
    ### Development Installation
    
    ```bash
    # Clone the repository
    git clone https://github.com/siege-analytics/siege_utilities.git
    cd siege_utilities
    
    # Install in development mode
    pip install -e .
    ```
    """)
    
    # Configuration options
    st.subheader("🔧 Configuration Options")
    
    # Wiki sync configuration
    st.markdown("**Wiki Synchronization Configuration:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sync_interval = st.slider("Sync Interval (hours)", 1, 168, 24)
        auto_commit = st.checkbox("Auto-commit changes", value=True)
        auto_push = st.checkbox("Auto-push to remote", value=False)
    
    with col2:
        backup_enabled = st.checkbox("Enable backups", value=True)
        excluded_files = st.multiselect(
            "Excluded files:",
            [".git", ".gitignore", "*.tmp", "*.log"],
            default=[".git", ".gitignore", "*.tmp"]
        )
    
    if st.button("💾 Save Wiki Sync Configuration"):
        config = {
            "sync_interval_hours": sync_interval,
            "auto_commit": auto_commit,
            "auto_push": auto_push,
            "backup_enabled": backup_enabled,
            "excluded_files": excluded_files
        }
        
        # Save configuration
        with open("wiki_sync_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        st.success("Configuration saved successfully!")
    
    # Release management configuration
    st.subheader("🚀 Release Management Configuration")
    
    st.markdown("""
    **Environment Variables:**
    
    ```bash
    # GitHub API token for creating releases
    export GITHUB_TOKEN="ghp_your_token_here"
    
    # PyPI API token for uploading packages
    export PYPI_TOKEN="pypi_your_token_here"
    ```
    
    **Release Commands:**
    
    ```bash
    # Check version consistency
    ./scripts/release.sh check
    
    # Bump version
    ./scripts/release.sh bump minor
    
    # Full release
    ./scripts/release.sh release minor "New features added"
    ```
    """)
    
    # System diagnostics
    st.subheader("🔍 System Diagnostics")
    
    if st.button("🔍 Run System Diagnostics"):
        try:
            # Check system components
            st.info("Running system diagnostics...")
            
            # Check Census utilities
            try:
                from siege_utilities.geo import CensusDirectoryDiscovery
                st.success("✅ Census utilities available")
            except ImportError as e:
                st.error(f"❌ Census utilities not available: {e}")
            
            # Check required packages
            required_packages = [
                "pandas", "numpy", "plotly", "streamlit",
                "requests", "beautifulsoup4", "geopandas"
            ]
            
            for package in required_packages:
                try:
                    __import__(package)
                    st.success(f"✅ {package} available")
                except ImportError:
                    st.warning(f"⚠️ {package} not available")
            
            # Check configuration files
            config_files = [
                "wiki_sync_config.json",
                "wiki_sync_log.json"
            ]
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    st.success(f"✅ {config_file} exists")
                else:
                    st.info(f"ℹ️ {config_file} not found (will be created)")
            
            st.success("🎉 System diagnostics completed!")
            
        except Exception as e:
            st.error(f"System diagnostics failed: {e}")
    
    # Troubleshooting
    st.subheader("🛠️ Troubleshooting")
    
    with st.expander("Common Issues and Solutions"):
        st.markdown("""
        **Issue: Census utilities not available**
        - Solution: Install with `pip install siege-utilities[geo]`
        
        **Issue: Network errors during discovery**
        - Solution: Check internet connection and firewall settings
        
        **Issue: SSL certificate errors**
        - Solution: The system automatically retries with SSL verification disabled
        
        **Issue: Import errors**
        - Solution: Check Python path and virtual environment setup
        
        **Issue: Configuration not saving**
        - Solution: Check file permissions and disk space
        """)
    
    # Support and resources
    st.subheader("📚 Support & Resources")
    
    st.markdown("""
    **Documentation:**
    - [GitHub Wiki](https://github.com/siege-analytics/siege_utilities/wiki)
    - [Sphinx Documentation](docs/)
    - [Release Management Guide](docs/RELEASE_MANAGEMENT.md)
    
    **Examples:**
    - [Census Intelligence Demo](examples/census_intelligence_demo.py)
    - [Enhanced Features Demo](examples/enhanced_features_demo.py)
    
    **Support:**
    - [GitHub Issues](https://github.com/siege-analytics/siege_utilities/issues)
    - [Wiki Documentation](https://github.com/siege-analytics/siege_utilities/wiki)
    """)

if __name__ == "__main__":
    main()
