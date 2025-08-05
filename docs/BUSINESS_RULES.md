# Business Rules Configuration Guide

**Status**: ✅ **PRODUCTION READY**  
**Version**: 0.3.4  
**Last Updated**: 2025-08-05

---

## Overview

The BALANCE-pyexcel system now supports external business rules configuration through the `config/business_rules.yml` file. This allows you to customize key business logic without modifying code, making the system more flexible and maintainable.

---

## 📋 **Business Rules File Structure**

The `config/business_rules.yml` file contains the following sections:

### **Settlement Keywords**
Keywords that identify settlement transactions between parties:
```yaml
settlement_keywords:
  - venmo
  - zelle
  - cash app
  - paypal
  - apple pay
  - google pay
  - bank transfer
  - e-transfer
```

### **Payer Split Configuration**
Percentage allocation for shared expenses:
```yaml
payer_split:
  ryan_pct: 0.43
  jordyn_pct: 0.57
```

### **Merchant Categories**
Rules for categorizing transactions based on merchant names:
```yaml
merchant_categories:
  Groceries:
    - fry
    - safeway
    - walmart
    - target
    - costco
    - trader joe
    - whole foods
  
  Utilities:
    - electric
    - gas
    - water
    - internet
    - phone
    - cox
    - srp
    - aps
  
  Dining Out:
    - restaurant
    - cafe
    - coffee
    - starbucks
    - pizza
```

### **Outlier Detection**
Thresholds for identifying unusual transactions:
```yaml
outlier_thresholds:
  amount: 5000.0
  z_score: 3.0
```

### **Data Quality Rules**
Rules for data validation and quality control:
```yaml
data_quality:
  max_duplicate_days: 3
  manual_calculation_triggers:
    - "2x to calculate"
    - "manual calc"
    - "adjusted"
```

### **Rent Analysis Rules**
Rent-specific analysis parameters:
```yaml
rent_analysis:
  baseline: 2100.0
  variance_threshold: 0.10
  budget_variance_threshold_pct: 10.0
```

### **Risk Assessment Rules**
Thresholds for financial risk assessment:
```yaml
risk_assessment:
  liquidity_strain_threshold: 5000.0
  liquidity_strain_days: 60
  concentration_risk_threshold: 0.40
```

---

## 🔧 **Customization Examples**

### **Adding New Settlement Methods**
```yaml
settlement_keywords:
  - venmo
  - zelle
  - cash app
  - paypal
  - apple pay
  - google pay
  - bank transfer
  - e-transfer
  - bitcoin       # Add cryptocurrency
  - wire transfer  # Add wire transfers
```

### **Adjusting Payer Splits**
```yaml
payer_split:
  ryan_pct: 0.50   # Changed to 50/50 split
  jordyn_pct: 0.50
```

### **Adding New Merchant Categories**
```yaml
merchant_categories:
  # Existing categories...
  
  Pet Care:        # New category
    - petco
    - petsmart
    - vet
    - animal hospital
    - pet supplies
  
  Home Improvement:  # Another new category
    - home depot
    - lowes
    - ace hardware
    - menards
```

### **Adjusting Risk Thresholds**
```yaml
risk_assessment:
  liquidity_strain_threshold: 3000.0  # Lower threshold
  liquidity_strain_days: 45           # Shorter timeframe
  concentration_risk_threshold: 0.30  # More conservative
```

---

## 🚀 **Using Custom Business Rules**

### **Step 1: Edit the Configuration**
```powershell
# Open the business rules file
notepad config/business_rules.yml

# Make your changes and save
```

### **Step 2: Run the Pipeline**
```powershell
# Process with updated business rules
.\pipeline.ps1 process

# The changes take effect immediately
```

### **Step 3: Verify Changes**
```powershell
# Check the pipeline status
.\pipeline.ps1 status

# Review outputs to confirm rule changes
```

---

## 📊 **Impact of Business Rules**

### **Settlement Keywords**
- **Purpose**: Identifies transactions between parties for balance calculations
- **Impact**: Affects who-owes-who calculations and settlement tracking
- **Example**: Adding "bitcoin" would recognize crypto transfers as settlements

### **Payer Split**
- **Purpose**: Determines how shared expenses are allocated
- **Impact**: Changes the percentage split for all shared transactions
- **Example**: 50/50 split vs 43/57 split affects balance calculations

### **Merchant Categories**
- **Purpose**: Categorizes transactions for analysis and reporting
- **Impact**: Affects category-based reports and spending analysis
- **Example**: Adding "Pet Care" creates a new spending category

### **Outlier Thresholds**
- **Purpose**: Identifies unusual transactions for review
- **Impact**: Affects which transactions are flagged as outliers
- **Example**: Lowering amount threshold catches smaller unusual transactions

### **Data Quality Rules**
- **Purpose**: Controls data validation and duplicate detection
- **Impact**: Affects data cleaning and quality assurance
- **Example**: Shorter duplicate window catches more potential duplicates

### **Rent Analysis**
- **Purpose**: Validates rent payments against expected amounts
- **Impact**: Affects rent-specific analysis and variance reporting
- **Example**: Updating baseline reflects rent increases

### **Risk Assessment**
- **Purpose**: Identifies potential financial risks
- **Impact**: Affects risk reporting and alerts
- **Example**: Lower thresholds provide earlier risk warnings

---

## 🧪 **Testing Business Rules Changes**

### **Before Making Changes**
```powershell
# Run a baseline analysis
.\pipeline.ps1 analyze

# Note current results
```

### **After Making Changes**
```powershell
# Process with new rules
.\pipeline.ps1 process

# Compare results
.\pipeline.ps1 analyze

# Verify expected changes occurred
```

---

## 🔍 **Troubleshooting**

### **Rules Not Taking Effect**
1. Check YAML syntax is valid
2. Ensure file is saved as UTF-8
3. Restart any running processes
4. Run `.\pipeline.ps1 status` to verify configuration

### **Invalid YAML Syntax**
```powershell
# Test YAML validity
python -c "import yaml; yaml.safe_load(open('config/business_rules.yml'))"
```

### **Unexpected Categorization**
1. Check merchant name spelling and case
2. Verify category structure in YAML
3. Test with debug mode: `.\pipeline.ps1 process -Debug`

---

## 📚 **Related Documentation**

- **[Configuration Guide](CONFIGURATION_GUIDE.md)**: Comprehensive configuration documentation
- **[Architecture Guide](ARCHITECTURE.md)**: System architecture overview
- **[Pipeline Commands](../PIPELINE_COMMANDS.md)**: Command reference

---

**The business rules configuration system provides flexible customization while maintaining the reliability and accuracy of the BALANCE-pyexcel financial analysis pipeline.**