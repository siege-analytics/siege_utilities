#!/usr/bin/env python3
import json

# Create the notebook structure
notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Bivariate Choropleth Test\n",
                "\n",
                "This notebook will create a bivariate choropleth map step by step."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Cell 1: Setup and Import\n",
                "import siege_utilities\n",
                "print(\"🚀 STEP 1: SETUP AND IMPORTS\")\n",
                "print(\"=\" * 50)\n",
                "print(f\"✅ Siege Utilities version: {siege_utilities.__version__}\")\n",
                "print(f\"📦 Total functions available: {len(dir(siege_utilities))}\")\n",
                "\n",
                "# Show what functions we actually have\n",
                "key_functions = {\n",
                "    \"Sample Data\": \"get_census_tract_sample\",\n",
                "    \"Chart Generator\": \"ChartGenerator\",\n",
                "    \"Census Samples\": \"CENSUS_SAMPLES\",\n",
                "    \"Sample Datasets\": \"SAMPLE_DATASETS\"\n",
                "}\n",
                "\n",
                "for name, func in key_functions.items():\n",
                "    available = hasattr(siege_utilities, func)\n",
                "    status = \"✅ AVAILABLE\" if available else \"❌ MISSING\"\n",
                "    print(f\"{name:20} {status}\")\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Cell 2: Create the Bivariate Choropleth - This will show the actual map!\n",
                "print(\"🎨 STEP 2: CREATING THE BIVARIATE CHOROPLETH MAP\")\n",
                "print(\"=\" * 50)\n",
                "\n",
                "try:\n",
                "    # Get the ChartGenerator\n",
                "    print(\"🔧 Getting ChartGenerator...\")\n",
                "    chart_gen = siege_utilities.ChartGenerator()\n",
                "    print(f\"✅ ChartGenerator created: {type(chart_gen)}\")\n",
                "    \n",
                "    # Create sample data for visualization\n",
                "    print(\"\\n🔧 Creating sample data for visualization...\")\n",
                "    import pandas as pd\n",
                "    \n",
                "    # Create sample tract data\n",
                "    sample_data = pd.DataFrame({\n",
                "        \"tract_fips\": [\"06001000100\", \"06001000200\", \"06001000300\", \"06001000400\", \"06001000500\"],\n",
                "        \"income_category\": [\"Low\", \"Medium\", \"High\", \"Low\", \"Medium\"],\n",
                "        \"education_category\": [\"High School or Less\", \"Some College\", \"Bachelor's or Higher\", \"Some College\", \"High School or Less\"],\n",
                "        \"population\": [1500, 2200, 1800, 1200, 3000]\n",
                "    })\n",
                "    \n",
                "    print(f\"✅ Created sample data: {len(sample_data)} tracts\")\n",
                "    print(\"\\n📊 Sample Data:\")\n",
                "    display(sample_data)\n",
                "    \n",
                "    # Create bivariate choropleth\n",
                "    print(\"\\n🎨 GENERATING BIVARIATE CHOROPLETH...\")\n",
                "    print(\"This may take a moment...\")\n",
                "    \n",
                "    chart = chart_gen.create_bivariate_choropleth(\n",
                "        data=sample_data,\n",
                "        x_column=\"income_category\",\n",
                "        y_column=\"education_category\",\n",
                "        title=\"Income vs Education by Census Tract\",\n",
                "        width=800,\n",
                "        height=600\n",
                "    )\n",
                "    \n",
                "    print(f\"✅ SUCCESS: Choropleth created!\")\n",
                "    print(f\"📊 Chart type: {type(chart)}\")\n",
                "    \n",
                "    # DISPLAY THE ACTUAL CHOROPLETH MAP\n",
                "    print(\"\\n🗺️ DISPLAYING THE BIVARIATE CHOROPLETH MAP:\")\n",
                "    print(\"You should see an interactive map below:\")\n",
                "    \n",
                "    if hasattr(chart, \"_repr_html_\"):\n",
                "        display(chart)\n",
                "        print(\"\\n🎉 SUCCESS! The interactive choropleth map is displayed above!\")\n",
                "    else:\n",
                "        print(\"\\n📋 Chart object created but no HTML representation available\")\n",
                "        print(\"💡 This might be a static image or need to be saved to file\")\n",
                "        \n",
                "        # Try to save the chart\n",
                "        if hasattr(chart, \"save\"):\n",
                "            try:\n",
                "                output_file = \"bivariate_choropleth_output.html\"\n",
                "                chart.save(output_file)\n",
                "                print(f\"💾 Chart saved to: {output_file}\")\n",
                "                print(f\"🌐 Open this file in your browser to view the choropleth\")\n",
                "            except Exception as save_error:\n",
                "                print(f\"⚠️ Could not save chart: {save_error}\")\n",
                "                \n",
                "except Exception as e:\n",
                "    print(f\"❌ Choropleth creation failed: {e}\")\n",
                "    import traceback\n",
                "    traceback.print_exc()\n",
                "\n",
                "print(\"\\n🎯 Step 2 complete - you should see the choropleth map above!\")\n"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.5"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

# Write the notebook
with open('examples/step_by_step_choropleth.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)

print("✅ Created properly formatted notebook with choropleth cell")
