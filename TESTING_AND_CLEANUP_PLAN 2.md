# 🧪 Testing and Cleanup Plan for Siege Utilities

## 📋 **Testing Plan**

### **Phase 1: Core Functionality Testing**

#### **1.1 Package Format Generation Functions**
- [ ] **`generate_requirements_txt()`**
  - [ ] Test with valid setup.py
  - [ ] Test with invalid setup.py
  - [ ] Test with missing setup.py
  - [ ] Verify output format correctness
  - [ ] Test custom output paths

- [ ] **`generate_pyproject_toml()`**
  - [ ] Test UV/Setuptools format generation
  - [ ] Verify PEP 621 compliance
  - [ ] Test with all dependency types (core, optional, dev)
  - [ ] Validate metadata extraction
  - [ ] Test error handling

- [ ] **`generate_poetry_toml()`**
  - [ ] Test Poetry-specific format
  - [ ] Verify `[tool.poetry]` sections
  - [ ] Test build system configuration
  - [ ] Validate dependency organization

- [ ] **`generate_uv_toml()`**
  - [ ] Test UV compatibility
  - [ ] Verify delegation to standard generator
  - [ ] Test with various setup.py configurations

#### **1.2 Architecture Analysis Functions**
- [ ] **`analyze_package_structure()`**
  - [ ] Test with siege_utilities package
  - [ ] Test with custom packages
  - [ ] Verify module discovery
  - [ ] Test function counting accuracy

- [ ] **`generate_package_diagram()`**
  - [ ] Test Mermaid diagram generation
  - [ ] Verify diagram syntax
  - [ ] Test with complex package structures

- [ ] **`get_function_signatures()`**
  - [ ] Test signature extraction
  - [ ] Verify parameter parsing
  - [ ] Test with various function types

#### **1.3 Development Utilities**
- [ ] **`create_development_environment()`**
  - [ ] Test environment creation
  - [ ] Verify directory structure
  - [ ] Test with existing directories

- [ ] **`validate_package_structure()`**
  - [ ] Test validation logic
  - [ ] Verify issue detection
  - [ ] Test with valid/invalid packages

### **Phase 2: UV Integration Testing**

#### **2.1 UV Project Creation**
- [ ] **Basic UV Project Setup**
  - [ ] Test `uv init` functionality
  - [ ] Verify pyproject.toml generation
  - [ ] Test Python version specification

- [ ] **Siege Utilities Integration**
  - [ ] Test `uv add --editable ../siege_utilities`
  - [ ] Test with different extras (geo, distributed, analytics, etc.)
  - [ ] Test `uv add --extra all` functionality
  - [ ] Verify dependency resolution

#### **2.2 Dependency Management Testing**
- [ ] **Core Dependencies**
  - [ ] Test requests, pandas, numpy installation
  - [ ] Verify version constraints
  - [ ] Test import functionality

- [ ] **Optional Dependencies**
  - [ ] Test geo extras (geopandas, shapely, folium)
  - [ ] Test distributed extras (pyspark)
  - [ ] Test analytics extras (scipy, scikit-learn)
  - [ ] Test reporting extras (matplotlib, seaborn)
  - [ ] Test streamlit extras (streamlit, altair)
  - [ ] Test export extras (openpyxl, xlsxwriter)
  - [ ] Test performance extras (duckdb, psutil)
  - [ ] Test dev extras (pytest, black, flake8)

#### **2.3 UV Workflow Testing**
- [ ] **Environment Management**
  - [ ] Test `uv run` functionality
  - [ ] Test `uv shell` activation
  - [ ] Test virtual environment isolation

- [ ] **Dependency Operations**
  - [ ] Test `uv tree` visualization
  - [ ] Test `uv add` new packages
  - [ ] Test `uv sync` functionality
  - [ ] Test `uv lock` generation

### **Phase 3: Library Functionality Testing**

#### **3.1 Core Module Testing**
- [ ] **Logging Functions**
  - [ ] Test all 15 logging functions
  - [ ] Verify log level functionality
  - [ ] Test configuration options

- [ ] **String Utilities**
  - [ ] Test string manipulation functions
  - [ ] Verify quote removal functionality
  - [ ] Test edge cases

#### **3.2 File Operations Testing**
- [ ] **File Hashing**
  - [ ] Test hash generation
  - [ ] Verify integrity checking
  - [ ] Test different hash algorithms

- [ ] **File Operations**
  - [ ] Test file manipulation functions
  - [ ] Verify path operations
  - [ ] Test remote operations

#### **3.3 Geospatial Testing**
- [ ] **Census Data Intelligence**
  - [ ] Test dataset selection
  - [ ] Verify analysis patterns
  - [ ] Test geography level handling

- [ ] **Geocoding Functions**
  - [ ] Test address geocoding
  - [ ] Verify coordinate processing
  - [ ] Test spatial transformations

#### **3.4 Distributed Computing Testing**
- [ ] **Spark Utilities**
  - [ ] Test 26+ Spark functions
  - [ ] Verify session creation
  - [ ] Test DataFrame operations

- [ ] **HDFS Operations**
  - [ ] Test HDFS configuration
  - [ ] Verify file operations
  - [ ] Test cluster connectivity

#### **3.5 Analytics Integration Testing**
- [ ] **Google Analytics**
  - [ ] Test connection functionality
  - [ ] Verify data retrieval
  - [ ] Test client association

- [ ] **Database Connections**
  - [ ] Test various database types
  - [ ] Verify connection persistence
  - [ ] Test query execution

#### **3.6 Reporting and Visualization Testing**
- [ ] **Chart Generation**
  - [ ] Test 7+ map types
  - [ ] Verify choropleth generation
  - [ ] Test interactive maps

- [ ] **Report Generation**
  - [ ] Test PDF report creation
  - [ ] Verify PowerPoint integration
  - [ ] Test template functionality

### **Phase 4: Documentation Testing**

#### **4.1 Guide Validation**
- [ ] **UV Package Management Guide**
  - [ ] Test all code examples
  - [ ] Verify installation instructions
  - [ ] Test troubleshooting scenarios

- [ ] **Getting Started Guide**
  - [ ] Test installation methods
  - [ ] Verify first steps examples
  - [ ] Test workflow examples

- [ ] **Development Module README**
  - [ ] Test all function examples
  - [ ] Verify parameter descriptions
  - [ ] Test usage scenarios

#### **4.2 Documentation Accuracy**
- [ ] **Function Count Verification**
  - [ ] Verify 780+ functions claim
  - [ ] Test dynamic discovery accuracy
  - [ ] Validate module organization

- [ ] **Dependency Documentation**
  - [ ] Verify extras documentation
  - [ ] Test installation examples
  - [ ] Validate version constraints

### **Phase 5: Integration Testing**

#### **5.1 End-to-End Workflows**
- [ ] **Complete UV Workflow**
  - [ ] Create new UV project
  - [ ] Add siege_utilities with all extras
  - [ ] Run comprehensive functionality test
  - [ ] Generate reports and visualizations

- [ ] **Package Modernization Workflow**
  - [ ] Use package format generation functions
  - [ ] Convert setup.py to modern formats
  - [ ] Test generated files with UV
  - [ ] Verify compatibility

#### **5.2 Cross-Platform Testing**
- [ ] **macOS Testing**
  - [ ] Test UV installation
  - [ ] Verify all functionality
  - [ ] Test performance

- [ ] **Linux Testing** (if available)
  - [ ] Test UV compatibility
  - [ ] Verify dependency resolution
  - [ ] Test system integration

- [ ] **Windows Testing** (if available)
  - [ ] Test UV installation
  - [ ] Verify path handling
  - [ ] Test PowerShell compatibility

## 🧹 **Cleanup Plan**

### **Phase 1: Identify Cleanup Candidates**

#### **1.1 Temporary/Diagnostic Files** (Move to `purgatory/`)
- [ ] **`check_imports.py`** - Import diagnostic script (temporary)
- [ ] **`diagnose_pyspark.py`** - PySpark diagnostic script (temporary)
- [ ] **`find_test_returns.py`** - Test analysis script (temporary)
- [ ] **`create_notebook.py`** - Notebook creation script (temporary)
- [ ] **`run_tests.py`** - Test runner script (redundant with pytest)

#### **1.2 Historical/Archive Files** (Move to `purgatory/`)
- [ ] **`ANALYSIS_REPORT.md`** - Historical analysis (outdated)
- [ ] **`RESTORATION_COMPLETE.md`** - Historical restoration report (outdated)
- [ ] **`archive/`** - Entire archive directory (old wiki versions)
- [ ] **`siege_utilities.egg-info/`** - Generated package info (can be regenerated)

#### **1.3 Redundant Documentation** (Move to `purgatory/`)
- [ ] **`docs/TESTING_GUIDE.md`** - Redundant with wiki/Testing-Guide.md
- [ ] **`docs/CLIENT_AND_CONNECTION_CONFIG.md`** - Redundant with wiki content
- [ ] **`docs/RELEASE_MANAGEMENT.md`** - Redundant with scripts/README.md
- [ ] **`docs/source/`** - Sphinx documentation (redundant with wiki)

#### **1.4 Example/Test Files** (Move to `purgatory/`)
- [ ] **`examples/`** - Move to purgatory, keep only essential demos
- [ ] **`projects/AP001/`** - Example project (move to purgatory)
- [ ] **`siege_utilities/examples/`** - Redundant examples

#### **1.5 Scripts Directory** (Move to `purgatory/`)
- [ ] **`scripts/`** - Most scripts are outdated or redundant
- [ ] Keep only: `release_manager.py`, `generate_docstrings.py`
- [ ] Move to purgatory: `auto_docs.sh`, `automate_docs_and_deploy.py`, `sync_to_wiki.py`, `update_wiki.py`, `update_wiki.sh`

### **Phase 2: Create Purgatory Structure**

```
purgatory/
├── temporary_files/
│   ├── check_imports.py
│   ├── diagnose_pyspark.py
│   ├── find_test_returns.py
│   ├── create_notebook.py
│   └── run_tests.py
├── historical_docs/
│   ├── ANALYSIS_REPORT.md
│   ├── RESTORATION_COMPLETE.md
│   └── archive/
├── redundant_docs/
│   ├── docs/
│   └── old_wiki_versions/
├── example_files/
│   ├── examples/
│   ├── projects/
│   └── siege_utilities/examples/
└── outdated_scripts/
    └── scripts/
```

### **Phase 3: Cleanup Execution**

#### **3.1 Create Purgatory Directory**
```bash
mkdir -p purgatory/{temporary_files,historical_docs,redundant_docs,example_files,outdated_scripts}
```

#### **3.2 Move Files to Purgatory**
```bash
# Temporary files
mv check_imports.py purgatory/temporary_files/
mv diagnose_pyspark.py purgatory/temporary_files/
mv find_test_returns.py purgatory/temporary_files/
mv create_notebook.py purgatory/temporary_files/
mv run_tests.py purgatory/temporary_files/

# Historical docs
mv ANALYSIS_REPORT.md purgatory/historical_docs/
mv RESTORATION_COMPLETE.md purgatory/historical_docs/
mv archive/ purgatory/historical_docs/

# Redundant docs
mv docs/ purgatory/redundant_docs/

# Example files
mv examples/ purgatory/example_files/
mv projects/ purgatory/example_files/
mv siege_utilities/examples/ purgatory/example_files/

# Outdated scripts (keep only essential ones)
mv scripts/ purgatory/outdated_scripts/
# Then restore essential scripts:
mkdir scripts/
cp purgatory/outdated_scripts/release_manager.py scripts/
cp purgatory/outdated_scripts/generate_docstrings.py scripts/
```

#### **3.3 Clean Up Generated Files**
```bash
# Remove generated package info (can be regenerated)
rm -rf siege_utilities.egg-info/

# Clean up __pycache__ directories
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### **Phase 4: Repository Optimization**

#### **4.1 Update .gitignore**
```gitignore
# Add to .gitignore
purgatory/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
```

#### **4.2 Update Documentation**
- [ ] Update README.md to reflect cleaned structure
- [ ] Update wiki/Getting-Started.md with new structure
- [ ] Create purgatory/README.md explaining what's there

#### **4.3 Final Verification**
- [ ] Verify all essential functionality still works
- [ ] Test that purgatory files are properly isolated
- [ ] Ensure no broken imports or references
- [ ] Verify git status is clean

## 📊 **Success Metrics**

### **Testing Success Criteria**
- [ ] All 4 package format generation functions work correctly
- [ ] UV integration works with all extras
- [ ] 780+ functions are accessible and functional
- [ ] All documentation examples work as written
- [ ] End-to-end workflows complete successfully

### **Cleanup Success Criteria**
- [ ] Repository size reduced by 30%+
- [ ] No broken imports or references
- [ ] Clear separation between active and archived content
- [ ] All essential functionality preserved
- [ ] Documentation reflects new structure

## 🚀 **Execution Timeline**

### **Day 1: Testing Phase 1-2**
- Test package format generation functions
- Test UV integration and dependency management
- Document any issues found

### **Day 2: Testing Phase 3-4**
- Test library functionality across all modules
- Test documentation accuracy and examples
- Complete integration testing

### **Day 3: Cleanup Phase 1-2**
- Create purgatory structure
- Move identified files to purgatory
- Update .gitignore and documentation

### **Day 4: Final Verification**
- Complete cleanup execution
- Verify all functionality still works
- Update documentation and commit changes

---

**Ready to execute! 🚀**
