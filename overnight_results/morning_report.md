# 🌅 Morning Testing Report

**Generated**: 2025-09-11 02:41:03

## 📊 Summary

- **Total Tests Run**: 8
- **Successful Tests**: 2
- **Failed Tests**: 6
- **Error Rate**: 75.0%

## 📓 Notebook Test Results

- ✅ **step_by_step_choropleth_test_notebook**
- ✅ **function_discovery_guide_test_notebook**
- ❌ **census_bivariate_choropleth_recipe_test_notebook**
  - Error: [siege_utilities] 2025-09-11 02:40:55,014 WARNING: Failed to load user config: could not determine a constructor for the tag 'tag:yaml.org,2002:python/tuple'
  in "/Users/dheerajchand/.siege_utilities...

## 📚 Recipe Test Results

- ❌ **Demographic-Analysis-Pipeline_test_recipe**
  - Error: [siege_utilities] 2025-09-11 02:40:56,751 WARNING: Failed to load user config: could not determine a constructor for the tag 'tag:yaml.org,2002:python/tuple'
  in "/Users/dheerajchand/.siege_utilities...
- ❌ **Business-Intelligence-Site-Selection_test_recipe**
  - Error: [siege_utilities] 2025-09-11 02:40:58,497 WARNING: Failed to load user config: could not determine a constructor for the tag 'tag:yaml.org,2002:python/tuple'
  in "/Users/dheerajchand/.siege_utilities...
- ❌ **Census-Data-Intelligence-Guide_test_recipe**
  - Error:   File "/Users/dheerajchand/Desktop/in_process/code/siege_utilities_verify/overnight_results/Census-Data-Intelligence-Guide_test.py", line 160
    from siege_utilities.geo.census_data_selector import ...
- ❌ **Real-Estate-Market-Intelligence_test_recipe**
  - Error: [siege_utilities] 2025-09-11 02:41:00,353 WARNING: Failed to load user config: could not determine a constructor for the tag 'tag:yaml.org,2002:python/tuple'
  in "/Users/dheerajchand/.siege_utilities...
- ❌ **Advanced-Census-Workflows_test_recipe**
  - Error: [siege_utilities] 2025-09-11 02:41:02,050 WARNING: Failed to load user config: could not determine a constructor for the tag 'tag:yaml.org,2002:python/tuple'
  in "/Users/dheerajchand/.siege_utilities...

## 🔬 Function Test Results

No function tests were run.

## ❌ Errors and Issues

No critical errors occurred.

## 🎯 Recommendations

Based on the overnight testing results:

- 🔴 **High Error Rate**: Focus on fixing critical issues first
- Review failed tests and fix underlying issues
- Update documentation for functions that worked
- Create unit tests for newly validated functions
- Plan next phase of testing based on results

