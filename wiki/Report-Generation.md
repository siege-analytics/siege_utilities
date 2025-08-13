# 📄 Report Generation

<div align="center">

**Professional Document Creation with PDF and PowerPoint Integration**

![Report System](https://img.shields.io/badge/Report%20System-PDF%20%2B%20PowerPoint-blue?style=for-the-badge&logo=file-pdf)

</div>

---

## 🎯 **Overview**

The Siege Utilities reporting system transforms your geographic analysis and data insights into **publication-quality professional documents**. With support for comprehensive PDF reports and PowerPoint presentations, you can create enterprise-grade deliverables that impress clients and stakeholders.

---

## 🚀 **Quick Start**

### **Basic PDF Report**
```python
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

# Add map section
report_content = report_gen.add_map_section(
    report_content,
    "Regional Analysis",
    [bivariate_map],
    map_type="bivariate_choropleth"
)

# Generate PDF
report_gen.generate_pdf_report(report_content, "report.pdf")
```

### **Basic PowerPoint Presentation**
```python
from siege_utilities.reporting.powerpoint_generator import PowerPointGenerator

# Initialize PowerPoint generator
ppt_gen = PowerPointGenerator()

# Create presentation
presentation = ppt_gen.create_comprehensive_presentation(
    title="Geographic Analysis",
    include_toc=True,
    include_agenda=True
)

# Add map slide
presentation = ppt_gen.add_map_slide(
    presentation,
    "Regional Overview",
    [bivariate_map]
)

# Generate PowerPoint
ppt_gen.generate_powerpoint_presentation(presentation, "presentation.pptx")
```

---

## 📄 **PDF Report System**

### **Document Structure**

**Professional Organization**:
1. **Title Page**: Cover with metadata and branding
2. **Table of Contents**: Automated with page numbers
3. **Executive Summary**: High-level overview
4. **Methodology**: Technical approach
5. **Content Sections**: Maps, charts, tables, text
6. **Appendices**: Supporting materials
7. **Professional Features**: Page numbering, headers, footers

### **Creating Comprehensive Reports**

```python
# Create comprehensive report structure
report_content = report_gen.create_comprehensive_report(
    title="Market Performance Analysis",
    author="Siege Analytics Team",
    client="Global Retail Corp",
    report_type="market_analysis",
    sections=[],
    appendices=[],
    table_of_contents=True,
    page_numbers=True,
    header_footer=True
)
```

### **Adding Content Sections**

**Text Sections**:
```python
report_content = report_gen.add_text_section(
    report_content,
    "Executive Summary",
    """This comprehensive analysis examines market performance across geographic regions, 
    revealing significant opportunities for expansion and optimization. Key findings include 
    strong correlation between population density and market penetration, with notable 
    variations in customer satisfaction metrics.""",
    level=1,
    page_break_after=True
)
```

**Map Sections**:
```python
report_content = report_gen.add_map_section(
    report_content,
    "Regional Market Performance",
    [bivariate_map, marker_map],
    map_type="mixed",
    description="Comprehensive geographic analysis showing market penetration and customer satisfaction across regions.",
    level=1,
    page_break_after=True
)
```

**Chart Sections**:
```python
report_content = report_gen.add_chart_section(
    report_content,
    "Performance Metrics",
    [bar_chart, line_chart, scatter_plot],
    description="Key performance indicators and trend analysis across different metrics.",
    level=1,
    layout="grid"
)
```

**Table Sections**:
```python
report_content = report_gen.add_table_section(
    report_content,
    "Regional Performance Summary",
    performance_data,
    headers=["Region", "Market Penetration", "Customer Satisfaction", "Revenue Growth"],
    level=1
)
```

**Appendices**:
```python
report_content = report_gen.add_appendix(
    report_content,
    "Raw Data Tables",
    raw_data_df,
    appendix_type="data"
)
```

---

## 📊 **PowerPoint Presentation System**

### **Slide Types**

**Professional Structure**:
- **Title Slides**: Presentation headers with branding
- **Table of Contents**: Navigation and structure overview
- **Agenda Slides**: Meeting and presentation planning
- **Content Slides**: Various types and layouts
- **Summary Slides**: Key points and next steps

### **Creating Comprehensive Presentations**

```python
# Create presentation structure
presentation = ppt_gen.create_comprehensive_presentation(
    title="Market Performance Analysis",
    author="Siege Analytics Team",
    client="Global Retail Corp",
    presentation_type="market_analysis",
    sections=[],
    include_toc=True,
    include_agenda=True
)
```

### **Adding Slide Content**

**Text Slides**:
```python
presentation = ppt_gen.add_text_slide(
    presentation,
    "Analysis Overview",
    """• Comprehensive market performance analysis
    • Geographic visualization and insights
    • Strategic recommendations and next steps
    • Data-driven decision support""",
    level=1,
    bullet_points=True
)
```

**Map Slides**:
```python
presentation = ppt_gen.add_map_slide(
    presentation,
    "Regional Market Overview",
    [bivariate_map],
    map_type="bivariate_choropleth",
    description="Bivariate analysis showing market penetration and customer satisfaction",
    level=1
)
```

**Chart Slides**:
```python
presentation = ppt_gen.add_chart_slide(
    presentation,
    "Performance Trends",
    [trend_chart, comparison_chart],
    description="Key performance trends and comparative analysis",
    level=1,
    layout="two_charts"
)
```

**Table Slides**:
```python
presentation = ppt_gen.add_table_slide(
    presentation,
    "Regional Performance Summary",
    performance_data,
    headers=["Region", "Market Penetration", "Customer Satisfaction"],
    level=1
)
```

**Comparison Slides**:
```python
presentation = ppt_gen.add_comparison_slide(
    presentation,
    "Before vs After Analysis",
    {
        'left_title': 'Before Implementation',
        'left_content': ['Low market penetration', 'Customer dissatisfaction', 'Limited growth'],
        'right_title': 'After Implementation',
        'right_content': ['Improved penetration', 'Higher satisfaction', 'Strong growth']
    },
    level=1
)
```

**Summary Slides**:
```python
presentation = ppt_gen.add_summary_slide(
    presentation,
    "Key Findings & Next Steps",
    [
        "Strong regional performance variations identified",
        "Market penetration correlates with customer satisfaction",
        "Strategic expansion opportunities in underperforming regions",
        "Implementation timeline: Q1-Q2 2024"
    ],
    level=1
)
```

---

## 🎨 **Professional Features**

### **Document Organization**

**Section Levels**:
- **Level 0**: Main sections (title page, TOC, appendices)
- **Level 1**: Primary content sections
- **Level 2**: Subsections and detailed content

**Page Management**:
```python
# Add page breaks for better organization
report_content = report_gen.add_text_section(
    report_content,
    "Executive Summary",
    summary_text,
    level=1,
    page_break_before=True,  # Start on new page
    page_break_after=True     # End with page break
)
```

### **Client Branding**

**Custom Styling**:
```python
from siege_utilities.reporting.client_branding import ClientBrandingManager

# Initialize branding manager
branding_manager = ClientBrandingManager()

# Get client branding
branding_config = branding_manager.get_client_branding('client_name')

# Apply to report generator
report_gen = ReportGenerator(branding_config=branding_config)
```

**Branding Elements**:
- **Colors**: Primary and secondary brand colors
- **Fonts**: Brand-appropriate typography
- **Logos**: Company and client logos
- **Layout**: Consistent visual hierarchy

---

## 🔧 **Advanced Features**

### **Automated Report Generation**

**Batch Processing**:
```python
import schedule
import time

def generate_daily_report():
    """Generate daily performance report."""
    # Collect data from multiple sources
    data_sources = collect_data_from_apis()
    
    # Create report
    report_content = create_report_content(data_sources)
    
    # Generate and save
    report_gen.generate_pdf_report(report_content, f"daily_report_{time.strftime('%Y%m%d')}.pdf")

# Schedule daily generation
schedule.every().day.at("09:00").do(generate_daily_report)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

**Template System**:
```python
# Use custom templates
report_content = report_gen.create_comprehensive_report(
    title="Custom Report",
    template_config='path/to/custom_template.yaml'
)
```

### **Multi-Format Output**

**Simultaneous Generation**:
```python
# Generate both PDF and PowerPoint
pdf_success = report_gen.generate_pdf_report(report_content, "report.pdf")
ppt_success = ppt_gen.generate_powerpoint_presentation(presentation, "presentation.pptx")

print(f"PDF: {'✅' if pdf_success else '❌'}")
print(f"PowerPoint: {'✅' if ppt_success else '❌'}")
```

**Custom Formats**:
```python
# Export to different formats
report_gen.export_to_format(report_content, "report.html", format="html")
report_gen.export_to_format(report_content, "report.docx", format="word")
```

---

## 📊 **Integration Examples**

### **With Mapping System**

```python
# Create maps first
chart_gen = ChartGenerator()
bivariate_map = chart_gen.create_bivariate_choropleth_matplotlib(
    data=regional_data,
    location_column='region',
    value_column1='market_penetration',
    value_column2='customer_satisfaction'
)

# Then create report with maps
report_content = report_gen.create_comprehensive_report(
    title="Geographic Market Analysis"
)

report_content = report_gen.add_map_section(
    report_content,
    "Market Performance by Region",
    [bivariate_map],
    map_type="bivariate_choropleth"
)
```

### **With External Data Sources**

```python
# Collect data from multiple sources
ga_data = collect_google_analytics_data()
fb_data = collect_facebook_data()
db_data = collect_database_data()

# Create unified dataset
combined_data = combine_data_sources([ga_data, fb_data, db_data])

# Generate visualizations
charts = create_charts_from_data(combined_data)

# Create comprehensive report
report_content = report_gen.create_comprehensive_report(
    title="Multi-Source Analysis Report"
)

for chart in charts:
    report_content = report_gen.add_chart_section(
        report_content,
        chart['title'],
        [chart['visualization']]
    )
```

---

## 🎯 **Best Practices**

### **Report Organization**

1. **Logical Flow**: Organize content in logical sequence
2. **Consistent Formatting**: Maintain professional appearance
3. **Clear Sections**: Well-defined section boundaries
4. **Appropriate Detail**: Match detail level to audience

### **Content Quality**

1. **Executive Summary**: High-level insights and recommendations
2. **Methodology**: Clear technical approach
3. **Visual Elements**: Professional charts and maps
4. **Actionable Insights**: Clear next steps and recommendations

### **Professional Presentation**

1. **Branding Consistency**: Apply client branding throughout
2. **Page Layout**: Professional spacing and organization
3. **Typography**: Readable and appropriate fonts
4. **Visual Hierarchy**: Clear information structure

---

## 🚨 **Troubleshooting**

### **Common Issues**

**PDF Generation Errors**:
```python
# Check template configuration
template_path = report_content.get('template_config')
if template_path and not Path(template_path).exists():
    print(f"Template not found: {template_path}")

# Verify content structure
if 'sections' not in report_content:
    print("Report content missing sections")
```

**PowerPoint Generation Issues**:
```python
# Check slide content
for section in presentation.get('sections', []):
    if not section.get('content'):
        print(f"Section '{section.get('title')}' has no content")

# Verify file paths
output_dir = Path(output_path).parent
if not output_dir.exists():
    output_dir.mkdir(parents=True)
```

### **Performance Optimization**

**Large Reports**:
```python
# Process sections in chunks
section_chunks = [sections[i:i+10] for i in range(0, len(sections), 10)]

for chunk in section_chunks:
    # Process chunk
    process_section_chunk(chunk)
    
    # Clear memory
    gc.collect()
```

**Memory Management**:
```python
# Clear large objects after use
del large_dataframe
gc.collect()

# Use efficient data types
df = df.astype({'large_column': 'category'})
```

---

## 📚 **Additional Resources**

- **[Mapping & Visualization](Mapping-and-Visualization)**: Create the maps for your reports
- **[Integration & APIs](Integration-and-APIs)**: Connect with external data sources
- **[Recipes & Examples](Recipes-and-Examples)**: Step-by-step implementation guides
- **[API Reference](https://siege-analytics.github.io/siege_utilities/)**: Complete method documentation

---

<div align="center">

**Ready to create professional reports and presentations?**

[🗺️ Create Maps](Mapping-and-Visualization) • [🔌 Integrate APIs](Integration-and-APIs) • [📖 View Examples](Recipes-and-Examples)

---

*Transform your insights into professional deliverables with Siege Utilities* 📄✨

</div>
