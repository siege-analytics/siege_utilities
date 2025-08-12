#!/usr/bin/env python3
"""
Demonstration script for client and connection configuration functionality.
Shows how to create, manage, and use client profiles and connection profiles.
"""

import sys
import pathlib
from datetime import datetime

# Add the parent directory to the path so we can import siege_utilities
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import siege_utilities


def demo_client_management():
    """Demonstrate client profile management."""
    print("=" * 60)
    print("CLIENT PROFILE MANAGEMENT DEMO")
    print("=" * 60)
    
    # Create a client profile
    contact_info = {
        "primary_contact": "John Smith",
        "email": "john.smith@acmecorp.com",
        "phone": "+1-555-0123",
        "address": "123 Business Ave, Tech City, TC 12345"
    }
    
    client_profile = siege_utilities.create_client_profile(
        "Acme Corporation",
        "ACME001",
        contact_info,
        industry="Technology",
        project_count=0,
        logo_path="/assets/logos/acme_logo.png",
        brand_colors=["#0066CC", "#FF6600"],
        notes="Premium technology client with focus on data analytics"
    )
    
    print(f"✅ Created client profile: {client_profile['client_name']}")
    print(f"   Client ID: {client_profile['client_id']}")
    print(f"   Industry: {client_profile['metadata']['industry']}")
    print(f"   Brand Colors: {client_profile['design_artifacts']['brand_colors']}")
    
    # Save the client profile
    config_dir = "demo_config"
    saved_path = siege_utilities.save_client_profile(client_profile, config_dir)
    print(f"✅ Saved client profile to: {saved_path}")
    
    # Load and validate the profile
    loaded_profile = siege_utilities.load_client_profile("ACME001", config_dir)
    validation = siege_utilities.validate_client_profile(loaded_profile)
    
    print(f"✅ Profile validation: {'PASS' if validation['is_valid'] else 'FAIL'}")
    if validation['warnings']:
        print(f"   Warnings: {', '.join(validation['warnings'])}")
    
    return client_profile


def demo_connection_management():
    """Demonstrate connection profile management."""
    print("\n" + "=" * 60)
    print("CONNECTION PROFILE MANAGEMENT DEMO")
    print("=" * 60)
    
    # Create a notebook connection profile
    notebook_params = {
        "url": "http://localhost:8888",
        "token": "abc123def456",
        "workspace": "/home/user/notebooks/acme_project"
    }
    
    notebook_conn = siege_utilities.create_connection_profile(
        "Acme Jupyter Lab",
        "notebook",
        notebook_params,
        auto_connect=True,
        kernel_type="python3",
        workspace_path="/home/user/notebooks/acme_project",
        preferred_browser="chrome"
    )
    
    print(f"✅ Created notebook connection: {notebook_conn['name']}")
    print(f"   Connection ID: {notebook_conn['connection_id']}")
    print(f"   URL: {notebook_conn['connection_params']['url']}")
    print(f"   Auto-connect: {notebook_conn['metadata']['auto_connect']}")
    
    # Create a Spark connection profile
    spark_params = {
        "master_url": "spark://spark-master:7077",
        "app_name": "AcmeAnalytics"
    }
    
    spark_conn = siege_utilities.create_connection_profile(
        "Acme Spark Cluster",
        "spark",
        spark_params,
        driver_memory="4g",
        executor_memory="2g",
        spark_home="/opt/spark",
        hadoop_conf_dir="/opt/hadoop/etc/hadoop"
    )
    
    print(f"✅ Created Spark connection: {spark_conn['name']}")
    print(f"   Master URL: {spark_conn['connection_params']['master_url']}")
    print(f"   Driver Memory: {spark_conn['spark_specific']['driver_memory']}")
    
    # Save both connections
    config_dir = "demo_config"
    notebook_path = siege_utilities.save_connection_profile(notebook_conn, config_dir)
    spark_path = siege_utilities.save_connection_profile(spark_conn, config_dir)
    
    print(f"✅ Saved connections to: {config_dir}/connections/")
    
    # List all connections
    all_connections = siege_utilities.list_connection_profiles(config_directory=config_dir)
    print(f"✅ Total connections: {len(all_connections)}")
    
    for conn in all_connections:
        print(f"   - {conn['name']} ({conn['type']}): {conn['status']}")
    
    return notebook_conn, spark_conn


def demo_project_association():
    """Demonstrate associating clients with projects."""
    print("\n" + "=" * 60)
    print("PROJECT ASSOCIATION DEMO")
    print("=" * 60)
    
    config_dir = "demo_config"
    
    # Create a project configuration
    project_config = siege_utilities.create_project_config(
        "Acme Data Analytics Platform",
        "ACME001",
        description="Comprehensive data analytics platform for Acme Corporation",
        data_format="parquet",
        log_level="INFO"
    )
    
    # Save project config
    project_path = siege_utilities.save_project_config(project_config, config_dir)
    print(f"✅ Created project: {project_config['project_name']}")
    
    # Setup project directories
    success = siege_utilities.setup_project_directories(project_config)
    if success:
        print("✅ Project directories created")
    
    # Associate client with project
    success = siege_utilities.associate_client_with_project("ACME001", "ACME001", config_dir)
    if success:
        print("✅ Associated client ACME001 with project ACME001")
    
    # Get client-project associations
    associations = siege_utilities.get_client_project_associations("ACME001", config_dir)
    print(f"✅ Client ACME001 has {len(associations)} project(s): {associations}")
    
    return project_config


def demo_search_and_filtering():
    """Demonstrate search and filtering capabilities."""
    print("\n" + "=" * 60)
    print("SEARCH AND FILTERING DEMO")
    print("=" * 60)
    
    config_dir = "demo_config"
    
    # Search for clients by industry
    tech_clients = siege_utilities.search_client_profiles(
        "Technology", 
        ["metadata.industry"], 
        config_dir
    )
    print(f"✅ Found {len(tech_clients)} technology clients")
    
    # List notebook connections only
    notebook_connections = siege_utilities.list_connection_profiles("notebook", config_dir)
    print(f"✅ Found {len(notebook_connections)} notebook connections")
    
    # Get connection status
    if notebook_connections:
        first_conn = notebook_connections[0]
        status = siege_utilities.get_connection_status(first_conn['connection_id'], config_dir)
        print(f"✅ Connection status for {status['name']}:")
        print(f"   Health: {status['health']}")
        print(f"   Last connected: {status['last_connected'] or 'Never'}")
        print(f"   Connection count: {status['connection_count']}")


def demo_package_info():
    """Demonstrate package information and discovery."""
    print("\n" + "=" * 60)
    print("PACKAGE INFORMATION DEMO")
    print("=" * 60)
    
    # Get comprehensive package info
    package_info = siege_utilities.get_package_info()
    print(f"✅ Package: {package_info['package_name']} v{package_info['version']}")
    print(f"   Total functions: {package_info['total_functions']}")
    print(f"   Total modules: {package_info['total_modules']}")
    
    # Show available function categories
    print("\n📋 Available function categories:")
    for category, functions in package_info['categories'].items():
        if functions:
            print(f"   {category.capitalize()}: {len(functions)} functions")
    
    # Check dependencies
    dependencies = siege_utilities.check_dependencies()
    print(f"\n🔧 Dependency status:")
    available_deps = [dep for dep, available in dependencies.items() if available]
    print(f"   Available: {', '.join(available_deps)}")
    
    missing_deps = [dep for dep, available in dependencies.items() if not available]
    if missing_deps:
        print(f"   Missing: {', '.join(missing_deps)}")


def cleanup_demo():
    """Clean up demo files."""
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)
    
    import shutil
    
    # Remove demo config directory
    if pathlib.Path("demo_config").exists():
        shutil.rmtree("demo_config")
        print("✅ Removed demo configuration directory")
    
    # Remove any created project directories
    if pathlib.Path("projects/ACME001").exists():
        shutil.rmtree("projects/ACME001")
        print("✅ Removed demo project directory")


def main():
    """Run the complete demonstration."""
    print("🚀 Siege Utilities - Client & Connection Configuration Demo")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run all demos
        client_profile = demo_client_management()
        notebook_conn, spark_conn = demo_connection_management()
        project_config = demo_project_association()
        demo_search_and_filtering()
        demo_package_info()
        
        print("\n" + "=" * 60)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ Client profile management working")
        print("✅ Connection profile management working")
        print("✅ Project association working")
        print("✅ Search and filtering working")
        print("✅ Package discovery working")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always cleanup
        cleanup_demo()
    
    print(f"\nDemo completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
