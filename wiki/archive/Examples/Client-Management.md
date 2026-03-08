# 👥 Client Management - Profile Creation and Management

<div align="center">

![Client Management](https://img.shields.io/badge/Client_Management-Profiles_%26_Branding-blue)
![Configuration](https://img.shields.io/badge/Configuration-Profiles_%26_Connections-green)
![Branding](https://img.shields.io/badge/Branding-Custom_Styling-orange)

**Create and manage client profiles with professional branding** 🎨

</div>

---

## 🎯 **What You'll Learn**

This example demonstrates how to:
- ✅ Create comprehensive client profiles with contact information
- ✅ Set up professional branding with logos and colors
- ✅ Manage connection profiles for different services
- ✅ Save, load, and validate client configurations
- ✅ Integrate client branding into reports and presentations

## 🚀 **Quick Start**

```python
import siege_utilities

# Create a client profile
client = siege_utilities.create_client_profile(
    "Acme Corporation",
    "ACME001",
    {"primary_contact": "John Smith", "email": "john@acme.com"}
)

# Save and use the profile
siege_utilities.save_client_profile(client, "config")
print(f"✅ Created client: {client['client_name']}")
```

## 📋 **Complete Implementation**

### **1. Client Profile Management**

```python
import siege_utilities
import pathlib
from datetime import datetime

def demo_client_management():
    """Demonstrate client profile management."""
    print("=" * 60)
    print("CLIENT PROFILE MANAGEMENT DEMO")
    print("=" * 60)
    
    # Create a client profile with comprehensive information
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
```

### **2. Connection Profile Management**

```python
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
        auto_connect=False,
        spark_version="3.2.0",
        executor_memory="4g",
        driver_memory="2g"
    )
    
    print(f"✅ Created Spark connection: {spark_conn['name']}")
    print(f"   Connection ID: {spark_conn['connection_id']}")
    print(f"   Master URL: {spark_conn['connection_params']['master_url']}")
    print(f"   Spark Version: {spark_conn['metadata']['spark_version']}")
    
    # Save connection profiles
    siege_utilities.save_connection_profile(notebook_conn, "demo_config")
    siege_utilities.save_connection_profile(spark_conn, "demo_config")
    
    return notebook_conn, spark_conn
```

### **3. Client Branding Integration**

```python
def demo_client_branding():
    """Demonstrate client branding integration."""
    print("\n" + "=" * 60)
    print("CLIENT BRANDING INTEGRATION DEMO")
    print("=" * 60)
    
    # Load client profile
    client_profile = siege_utilities.load_client_profile("ACME001", "demo_config")
    
    # Extract branding information
    brand_colors = client_profile['design_artifacts']['brand_colors']
    logo_path = client_profile['design_artifacts']['logo_path']
    company_name = client_profile['client_name']
    
    print(f"🎨 Branding Information:")
    print(f"   Company: {company_name}")
    print(f"   Primary Color: {brand_colors[0]}")
    print(f"   Secondary Color: {brand_colors[1]}")
    print(f"   Logo: {logo_path}")
    
    # Create branded report template
    report_template = {
        'title': f"{company_name} Analytics Report",
        'primary_color': brand_colors[0],
        'secondary_color': brand_colors[1],
        'logo_path': logo_path,
        'company_name': company_name,
        'generated_date': datetime.now().strftime('%Y-%m-%d')
    }
    
    print(f"📊 Report Template Created:")
    print(f"   Title: {report_template['title']}")
    print(f"   Primary Color: {report_template['primary_color']}")
    print(f"   Generated: {report_template['generated_date']}")
    
    return report_template
```

### **4. Complete Demo Pipeline**

```python
def run_complete_demo():
    """Run the complete client management demonstration."""
    
    print("🚀 SIEGE UTILITIES CLIENT MANAGEMENT DEMONSTRATION")
    print("=" * 80)
    
    try:
        # Step 1: Client Profile Management
        client_profile = demo_client_management()
        
        # Step 2: Connection Profile Management
        notebook_conn, spark_conn = demo_connection_management()
        
        # Step 3: Client Branding Integration
        report_template = demo_client_branding()
        
        # Step 4: Summary
        print("\n" + "=" * 80)
        print("DEMONSTRATION SUMMARY")
        print("=" * 80)
        
        print(f"✅ Client Profile: {client_profile['client_name']} ({client_profile['client_id']})")
        print(f"✅ Notebook Connection: {notebook_conn['name']}")
        print(f"✅ Spark Connection: {spark_conn['name']}")
        print(f"✅ Report Template: {report_template['title']}")
        
        print(f"\n📁 Configuration saved to: demo_config/")
        print(f"🎨 Branding colors: {client_profile['design_artifacts']['brand_colors']}")
        print(f"🔗 Connections ready for use")
        
        return {
            'client_profile': client_profile,
            'notebook_connection': notebook_conn,
            'spark_connection': spark_conn,
            'report_template': report_template
        }
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        return None

# Run the complete demonstration
if __name__ == "__main__":
    results = run_complete_demo()
```

## 📊 **Expected Output**

```
🚀 SIEGE UTILITIES CLIENT MANAGEMENT DEMONSTRATION
================================================================================

============================================================
CLIENT PROFILE MANAGEMENT DEMO
============================================================
✅ Created client profile: Acme Corporation
   Client ID: ACME001
   Industry: Technology
   Brand Colors: ['#0066CC', '#FF6600']
✅ Saved client profile to: demo_config/client_profiles/ACME001.json
✅ Profile validation: PASS

============================================================
CONNECTION PROFILE MANAGEMENT DEMO
============================================================
✅ Created notebook connection: Acme Jupyter Lab
   Connection ID: notebook_acme_jupyter_lab_001
   URL: http://localhost:8888
   Auto-connect: True
✅ Created Spark connection: Acme Spark Cluster
   Connection ID: spark_acme_spark_cluster_001
   Master URL: spark://spark-master:7077
   Spark Version: 3.2.0

============================================================
CLIENT BRANDING INTEGRATION DEMO
============================================================
🎨 Branding Information:
   Company: Acme Corporation
   Primary Color: #0066CC
   Secondary Color: #FF6600
   Logo: /assets/logos/acme_logo.png
📊 Report Template Created:
   Title: Acme Corporation Analytics Report
   Primary Color: #0066CC
   Generated: 2024-01-15

================================================================================
DEMONSTRATION SUMMARY
================================================================================
✅ Client Profile: Acme Corporation (ACME001)
✅ Notebook Connection: Acme Jupyter Lab
✅ Spark Connection: Acme Spark Cluster
✅ Report Template: Acme Corporation Analytics Report

📁 Configuration saved to: demo_config/
🎨 Branding colors: ['#0066CC', '#FF6600']
🔗 Connections ready for use
```

## 🔧 **Configuration Files Created**

### **Client Profile Structure**
```json
{
  "client_id": "ACME001",
  "client_name": "Acme Corporation",
  "contact_info": {
    "primary_contact": "John Smith",
    "email": "john.smith@acmecorp.com",
    "phone": "+1-555-0123",
    "address": "123 Business Ave, Tech City, TC 12345"
  },
  "metadata": {
    "industry": "Technology",
    "project_count": 0,
    "created_date": "2024-01-15T10:30:00",
    "last_updated": "2024-01-15T10:30:00"
  },
  "design_artifacts": {
    "logo_path": "/assets/logos/acme_logo.png",
    "brand_colors": ["#0066CC", "#FF6600"],
    "font_family": "Arial",
    "notes": "Premium technology client with focus on data analytics"
  }
}
```

### **Connection Profile Structure**
```json
{
  "connection_id": "notebook_acme_jupyter_lab_001",
  "name": "Acme Jupyter Lab",
  "connection_type": "notebook",
  "connection_params": {
    "url": "http://localhost:8888",
    "token": "abc123def456",
    "workspace": "/home/user/notebooks/acme_project"
  },
  "metadata": {
    "auto_connect": true,
    "kernel_type": "python3",
    "workspace_path": "/home/user/notebooks/acme_project",
    "preferred_browser": "chrome",
    "created_date": "2024-01-15T10:30:00"
  }
}
```

## 🎨 **Branding Integration Examples**

### **1. Report Generation with Client Branding**

```python
def create_branded_report(client_id, data, report_type="analytics"):
    """Create a report using client branding."""
    
    # Load client profile
    client_profile = siege_utilities.load_client_profile(client_id, "config")
    
    # Extract branding
    brand_colors = client_profile['design_artifacts']['brand_colors']
    company_name = client_profile['client_name']
    
    # Create report with branding
    if report_type == "analytics":
        report = siege_utilities.create_analytics_report(
            title=f"{company_name} Analytics Report",
            charts=data['charts'],
            data_summary=data['summary'],
            insights=data['insights'],
            recommendations=data['recommendations'],
            branding={
                'primary_color': brand_colors[0],
                'secondary_color': brand_colors[1],
                'company_name': company_name
            }
        )
    
    return report
```

### **2. Presentation with Client Branding**

```python
def create_branded_presentation(client_id, slides_data):
    """Create a presentation using client branding."""
    
    # Load client profile
    client_profile = siege_utilities.load_client_profile(client_id, "config")
    
    # Create presentation with branding
    presentation = siege_utilities.create_presentation(
        title=f"{client_profile['client_name']} Presentation",
        slides=slides_data,
        branding=client_profile['design_artifacts']
    )
    
    return presentation
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **🔐 Profile Not Found**: Ensure client ID exists and path is correct
2. **🎨 Branding Not Applied**: Check that design artifacts are properly set
3. **💾 Save Failures**: Verify directory permissions and disk space
4. **🔗 Connection Errors**: Validate connection parameters and network access

### **Best Practices**

- **🔐 Security**: Store sensitive information (tokens, passwords) securely
- **🎨 Consistency**: Use consistent branding across all client materials
- **📁 Organization**: Organize profiles by client ID for easy retrieval
- **🔄 Updates**: Regularly update client information and branding
- **📊 Validation**: Always validate profiles after creation or modification

## 🚀 **Next Steps**

After mastering client management:

- **[Report Generation](Report-Generation.md)** - Create branded reports and presentations
- **[Analytics Integration](Analytics-Integration.md)** - Connect client data to analytics
- **[Automation](Automation-Guide.md)** - Automate client reporting workflows
- **[Multi-Client Management](Multi-Client-Management.md)** - Manage multiple clients efficiently

## 🔗 **Related Examples**

- **[Getting Started](Getting-Started.md)** - First steps with Siege Utilities
- **[File Operations](File-Operations.md)** - Manage configuration files
- **[Testing Guide](Testing-Guide.md)** - Test your client configurations
- **[Performance Optimization](Performance-Optimization.md)** - Optimize client workflows

---

<div align="center">

**Ready to manage your clients professionally?** 👥

**[Next: Report Generation](Report-Generation.md)** → **[Analytics Integration](Analytics-Integration.md)**

</div>
