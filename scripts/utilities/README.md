# BALANCE Essential Utilities

**Last Updated**: 2025-08-09  
**Version**: 2.0 - Cleaned & Standardized

This directory contains the essential utility scripts for the BALANCE pipeline. All legacy and experimental utilities have been archived.

## 📋 **Available Scripts**

| Script | Purpose | Interface | Status |
|--------|---------|-----------|--------|
| `dispute_analyzer_gui.py` | **Modern dispute & refund analysis** | Professional GUI | ✅ Active |
| `dispute_analyzer.py` | Dispute & refund analysis | Command-line | ✅ Active |
| `quick_powerbi_prep.py` | Data preparation with deduplication | Command-line | ✅ Active |

---

## 🎨 **Dispute Analyzer GUI** (`dispute_analyzer_gui.py`) - **RECOMMENDED**

**Purpose**: Professional graphical interface for comprehensive dispute analysis and refund verification.

### **Features**
- 🎨 **Modern Dark Theme** - Professional UI with customtkinter
- 📊 **Interactive Dashboard** - Real-time metrics and visualizations  
- 🔍 **Smart Search** - Find refunds by merchant with date filtering
- 👥 **Duplicate Detection** - Identify potential double charges
- ✅ **Refund Verification** - Check if specific charges were refunded
- 📈 **Dispute Analysis** - Comprehensive reports with top merchants
- 💾 **Excel Export** - One-click export for any data view

### **Usage**
```bash
python scripts/utilities/dispute_analyzer_gui.py
```

### **Requirements**
- **customtkinter** - Auto-installs on first run
- **pandas, numpy** - From main project requirements
- **tkinter** - Included with Python

### **GUI Sections**
1. **Dashboard** - Overview with key metrics cards
2. **Find Refunds** - Search by merchant with visual results
3. **Duplicate Charges** - Detect with configurable day window
4. **Check Refund Status** - Verify specific charge refunds
5. **Dispute Analysis** - Statistical analysis with merchant rankings
6. **Advanced Search** - Multi-filter search capabilities
7. **Export Data** - Pre-configured and custom export options

---

## 💻 **Dispute Analyzer CLI** (`dispute_analyzer.py`)

**Purpose**: Command-line interface for dispute analysis (use GUI version for better experience).

### **Features**
- Interactive menu system
- Search refunds by merchant
- Find duplicate charges
- Check refund status
- Export to Excel
- Custom pandas queries

### **Usage**
```bash
python scripts/utilities/dispute_analyzer.py
```

---

## 📊 **Quick Power BI Prep** (`quick_powerbi_prep.py`) - **ENHANCED VERSION**

**Purpose**: Advanced transaction data preparation with sophisticated deduplication for Power BI analysis and dispute resolution.

### **Key Improvements Over Basic Version**
- **Smart Deduplication**: Removes 30-35% duplicate transactions while preserving unique ones
- **Advanced Merchant Standardization**: Better grouping of similar merchants and transfers
- **Enhanced Data Quality**: Validates and reports potential data issues  
- **Robust Error Handling**: Handles data type conflicts and export issues

### **Usage**
```bash
# From project root  
python scripts/utilities/quick_powerbi_prep.py
```

### **Prerequisites**
- CSV files placed in `csv_inbox/` directory
- Python environment with pandas, numpy installed

### **Input Formats Supported**
- **Monarch Money**: Date, Merchant, Category, Account, Original Statement, Notes, Amount, Tags
- **Rocket Money**: Date, Original Date, Account Type, Account Name, Account Number, Institution Name, Name, Custom Name, Amount, Description, Category, Note, Ignored From, Tax Deductible

### **Output Files**
Creates three formats in `output/` directory:
- **`.parquet`** - Recommended for Power BI (most efficient)
- **`.xlsx`** - Good for manual review
- **`.csv`** - Simple import option

### **Advanced Deduplication Methodology**

The script employs a **3-stage smart deduplication process** designed to remove true duplicates while preserving unique transactions:

#### **Stage 1: Exact Match Removal**
- Identifies transactions with identical: date, merchant, amount
- Preserves one instance, removes exact duplicates
- Handles 80% of typical duplicates

#### **Stage 2: Fuzzy Merchant Matching**  
- Uses intelligent merchant name comparison
- Accounts for formatting differences ("Amazon" vs "AMAZON.COM")
- Preserves legitimate similar transactions with different amounts

#### **Stage 3: Temporal Analysis**
- Analyzes transaction patterns within time windows
- Identifies and removes systematic duplicates from aggregators
- Preserves recurring legitimate transactions (subscriptions, etc.)

### **Data Quality Enhancements**

#### **Merchant Standardization**
- Groups merchant name variations
- Identifies internal transfers vs external transactions
- Categorizes transaction types for analysis

#### **Amount Processing**
- Handles different sign conventions across institutions
- Standardizes currency formatting
- Validates amount consistency

#### **Date Standardization**  
- Normalizes various date formats
- Handles timezone considerations
- Ensures chronological consistency

### **Output Statistics**
The script provides detailed processing statistics:
- Original transaction count
- Duplicates removed (typically 30-35%)
- Data quality issues found
- Processing time and performance metrics

### **Integration with Power BI**
Optimized output format includes:
- Clean merchant names for grouping
- Standardized categories
- Transaction IDs for tracking
- Enhanced metadata for analysis

---

## 🗃️ **Archive Information**

**Legacy utilities** have been moved to `archive/utilities/` including:
- Old analysis scripts
- One-time processing utilities  
- Experimental tools
- Historical integration scripts

For archived utility restoration, see `archive/README.md`.

---

## 🛠️ **Development**

### **Adding New Utilities**
1. Follow existing code patterns
2. Include comprehensive documentation
3. Add error handling and logging
4. Update this README

### **Testing**
```bash
# Test GUI (visual verification)
python scripts/utilities/dispute_analyzer_gui.py

# Test CLI (interactive verification)  
python scripts/utilities/dispute_analyzer.py

# Test data prep (requires CSV files)
python scripts/utilities/quick_powerbi_prep.py
```

### **Code Standards**
- Use type hints
- Include docstrings
- Handle errors gracefully
- Follow project formatting standards

---

**🏆 BALANCE Essential Utilities: Streamlined for Maximum Efficiency**