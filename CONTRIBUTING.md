# Contributing to BALANCE-pyexcel

**Last Updated:** 2025-08-10  
**Version:** 1.0  

Thank you for your interest in contributing to BALANCE-pyexcel! This guide will help you get started with contributing to our gold standard financial analysis pipeline.

---

## 🎯 **Quick Start for Contributors**

### **Prerequisites**
- Python 3.11+ installed
- Poetry package manager
- Git for version control
- Basic understanding of financial data processing

### **Development Setup**
```powershell
# 1. Fork and clone the repository
git clone https://github.com/YOUR-USERNAME/BALANCE-pyexcel.git
cd BALANCE-pyexcel

# 2. Install development dependencies
poetry install --no-root --with dev

# 3. Install pre-commit hooks
poetry run pre-commit install

# 4. Run tests to verify setup
poetry run pytest

# 5. Check pipeline status
.\pipeline.ps1 status
```

---

## 📋 **How to Contribute**

### **Types of Contributions Welcome**
- **🐛 Bug Reports**: Help us identify and fix issues
- **✨ Feature Requests**: Suggest new functionality
- **📝 Documentation**: Improve guides and documentation
- **🧪 Testing**: Add test coverage or improve existing tests
- **🔧 Code Improvements**: Optimize performance or code quality
- **🏗️ Architecture**: Suggest architectural improvements

### **Before You Start**
1. **Check existing issues** to see if your idea/bug is already being tracked
2. **Create an issue** to discuss major changes before implementing
3. **Follow the coding standards** described below
4. **Write tests** for any new functionality

---

## 🛠️ **Development Workflow**

### **1. Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-number-description
```

### **2. Make Your Changes**
- Follow existing code patterns and conventions
- Add comprehensive docstrings to all functions
- Update type hints where appropriate
- Write tests for new functionality

### **3. Test Your Changes**
```powershell
# Run full test suite
poetry run pytest

# Run with coverage
poetry run pytest --cov=balance_pipeline --cov-report=html

# Run specific test categories
poetry run pytest -m "not slow"          # Skip slow tests
poetry run pytest -m "integration"       # Integration tests only

# Test main pipeline functionality
.\pipeline.ps1 process -Debug
.\pipeline.ps1 status
```

### **4. Code Quality Checks**
```powershell
# Linting and formatting
poetry run ruff check .                  # Lint code
poetry run ruff format .                 # Format code
poetry run mypy src/ --strict            # Type checking

# Pre-commit hooks (automatic if installed)
poetry run pre-commit run --all-files    # Run all quality checks
```

### **5. Update Documentation**
- Update relevant documentation in `docs/`
- Add docstrings to new functions
- Update README.md if adding major features
- Update CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format

### **6. Submit Pull Request**
1. Push your branch to your fork
2. Create a pull request with clear title and description
3. Reference any related issues
4. Wait for review and address feedback

---

## 📖 **Code Style Guidelines**

### **Python Code Standards**
- **Formatting**: Use `ruff format` (compatible with Black)
- **Linting**: Use `ruff` for linting (replaces flake8, pylint, etc.)
- **Type Hints**: Add type hints to all public functions
- **Docstrings**: Use Google-style docstrings
- **Line Length**: Maximum 88 characters (Black standard)

### **Example Code Style**
```python
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

def process_financial_data(
    file_path: Path,
    output_format: str = "parquet",
    debug: bool = False
) -> pd.DataFrame:
    """
    Process financial CSV data through the pipeline.
    
    Args:
        file_path: Path to the CSV file to process
        output_format: Format for output ("csv", "parquet", "excel")
        debug: Enable debug logging
        
    Returns:
        Processed DataFrame with normalized financial data
        
    Raises:
        FileNotFoundError: If the input file doesn't exist
        ValueError: If the output format is not supported
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
        
    logger.info(f"Processing financial data from {file_path}")
    
    # Implementation here...
    
    return processed_df
```

### **Documentation Standards**
- Use Markdown for all documentation
- Include table of contents for documents >3 sections
- Add timestamps and version information to document headers
- Use code blocks with language specification
- Validate all external links

---

## 🧪 **Testing Guidelines**

### **Test Organization**
- Place tests in `tests/` directory
- Mirror source code structure in test organization
- Use descriptive test names that explain what is being tested
- Group related tests in classes

### **Test Categories**
- **Unit Tests**: Test individual functions/methods (`test_*.py`)
- **Integration Tests**: Test component interactions (mark with `@pytest.mark.integration`)
- **Smoke Tests**: Quick validation tests (mark with `@pytest.mark.smoke`)
- **Slow Tests**: Long-running tests (mark with `@pytest.mark.slow`)

### **Example Test Structure**
```python
import pytest
from pathlib import Path
from balance_pipeline.csv_consolidator import CSVConsolidator

class TestCSVConsolidator:
    """Test cases for CSV consolidation functionality."""
    
    def test_process_single_file_success(self, tmp_path: Path) -> None:
        """Test successful processing of a single CSV file."""
        # Test implementation
        pass
    
    @pytest.mark.integration
    def test_end_to_end_processing(self) -> None:
        """Test complete pipeline processing flow."""
        # Integration test implementation
        pass
```

---

## 🔧 **Working with the Codebase**

### **Key Architecture Components**
- **`pipeline.ps1`**: Master entry point - handles all user interactions
- **`src/balance_pipeline/main.py`**: Python CLI entry point
- **`src/balance_pipeline/pipeline_v2.py`**: Core pipeline orchestrator
- **`src/balance_pipeline/csv_consolidator.py`**: CSV processing engine
- **`rules/schema_registry.yml`**: Bank format definitions

### **Common Development Tasks**

#### **Adding a New Bank Schema**
1. Add schema definition to `rules/schema_registry.yml`
2. Add test file to `tests/fixtures/`
3. Write test cases in `tests/test_schema_*.py`
4. Update documentation

#### **Adding a New Output Format**
1. Implement format handler in `src/balance_pipeline/export.py`
2. Update `src/balance_pipeline/config.py` with new format
3. Add format option to `pipeline.ps1`
4. Write tests for new format
5. Update documentation

#### **Adding New Analysis Features**
1. Implement feature in `src/balance_pipeline/analytics.py`
2. Add CLI option if needed
3. Write comprehensive tests
4. Update user documentation
5. Add to example workflows

---

## 📞 **Getting Help**

### **Resources**
- **Documentation**: Start with `docs/` directory
- **Architecture Guide**: `docs/ARCHITECTURE.md`
- **Pipeline Commands**: `PIPELINE_COMMANDS.md`
- **Development Setup**: `docs/developer_setup.md`

### **Communication**
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Code Review**: All contributions require review before merging

### **Common Issues**
- **Poetry Issues**: See `docs/developer_setup.md`
- **Test Failures**: Run `.\pipeline.ps1 status` to check environment
- **Import Errors**: Ensure you're using `poetry run` or activate virtual environment

---

## 📄 **Legal**

By contributing to BALANCE-pyexcel, you agree that your contributions will be licensed under the MIT License that covers this project.

---

**Thank you for contributing to BALANCE-pyexcel!** 🎉

Your contributions help make financial analysis more accessible and reliable for everyone.