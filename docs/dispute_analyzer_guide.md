# BALANCE Dispute & Refund Analyzer Guide

## Overview

The BALANCE Dispute & Refund Analyzer provides powerful tools for investigating financial discrepancies, verifying refunds, and identifying duplicate charges. Available in both command-line and modern GUI versions.

## Quick Start

### GUI Version (Recommended)
```powershell
cd C:\Projects\BALANCE
python .\scripts\utilities\dispute_analyzer_gui.py
```

### Command-Line Version
```bash
cd C:\Projects\BALANCE
python scripts\utilities\dispute_analyzer.py
```

## GUI Features

### 1. Dashboard Overview
- **Real-time metrics**: Total disputes, dispute amounts, recent activity
- **Visual indicators**: Color-coded cards for quick status assessment
- **Recent disputes table**: Latest 20 potential disputes with scrollable view
- **Date range display**: Shows full span of analyzed transactions

### 2. Find Refunds by Merchant
- **Smart search**: Partial merchant name matching
- **Customizable date range**: Default 90 days, adjustable
- **Credit identification**: Automatically finds positive amounts (refunds)
- **Export capability**: Save results to Excel for further analysis

### 3. Duplicate Charge Detection
- **Intelligent algorithm**: Finds charges with same merchant/amount within specified days
- **Visual cards**: Each duplicate displayed with clear date comparison
- **Configurable window**: Default 3 days, adjustable for different scenarios
- **Prevention insights**: Helps identify recurring billing issues

### 4. Refund Status Verification
- **Specific charge lookup**: Enter merchant, amount, and date
- **60-day search window**: Automatically searches for matching credits
- **Clear status indicators**: ✅ REFUNDED or ❌ NOT REFUNDED
- **Related credits**: Shows other credits from same merchant if exact match not found

### 5. Comprehensive Dispute Analysis
- **Statistical overview**: Total disputes, amounts, date ranges
- **Top merchants**: Ranked list of merchants with most disputes
- **Trend analysis**: Identify patterns in dispute occurrence
- **Visual presentation**: Cards and scrollable lists for easy review

### 6. Advanced Search
- **Multiple filters**:
  - Date range (start and end dates)
  - Amount range (minimum and maximum)
  - Merchant name (contains search)
  - Dispute-only filter
- **Batch export**: Export filtered results to Excel
- **Custom queries**: Support for complex search criteria

### 7. Export Options
- **Pre-configured exports**:
  - All transactions
  - All disputes
  - Last 30 days
  - All refunds (credits)
- **Custom exports**: From any search or filter
- **Excel format**: Compatible with all spreadsheet applications

## Command-Line Features

The CLI version provides the same analytical capabilities through an interactive menu:

1. **Search refunds for specific merchant**
2. **Find potential duplicate charges**
3. **Check if specific charge was refunded**
4. **Show comprehensive dispute analysis**
5. **Export disputes to Excel**
6. **Custom search with pandas queries**

## Data Processing

### Deduplication
- Uses sophisticated 3-stage algorithm
- Removes 30-35% duplicate transactions on average
- Preserves legitimate similar transactions

### Merchant Standardization
- Groups variations (e.g., "AMZN", "Amazon.com" → "Amazon")
- Identifies internal transfers
- Recognizes common payment processors

### Dispute Flagging
Automatically identifies transactions containing:
- REFUND
- RETURN
- REVERSAL
- DISPUTE
- CHARGEBACK
- CREDIT ADJUSTMENT

## Use Cases

### 1. Verify Amazon Return
```
GUI: Find Refunds → Enter "Amazon" → Search
Result: List of all Amazon credits with dates and amounts
```

### 2. Check for Double Charges
```
GUI: Duplicate Charges → Set 3-day window → Find Duplicates
Result: List of potential duplicates requiring investigation
```

### 3. Confirm Specific Refund
```
GUI: Check Refund Status → Enter details → Check Status
Result: Clear confirmation if refund was processed
```

### 4. Monthly Dispute Report
```
GUI: Export Data → All Disputes → Save to Excel
Result: Complete dispute list for accounting review
```

## Technical Details

### Data Source
- Scans `output/` for the most recent Parquet or CSV
- Validates required columns: `date`, `amount`, `merchant_standardized`, `description`, `potential_refund`
- Coerces `date` to datetime and derives `amount_abs`

### Performance
- Handles 5,000+ transactions smoothly
- Real-time search and filtering
- Efficient pandas operations

### UI/UX Design
- **Dark theme**: Reduces eye strain
- **Responsive layout**: Scales with window size
- **Color coding**: Visual feedback for different states
- **Professional typography**: Clear hierarchy

## Troubleshooting

### GUI Won't Launch
```powershell
poetry run pip install customtkinter
```

### No Data Found
```powershell
python .\scripts\utilities\quick_powerbi_prep.py
```

### Export Fails
- Check write permissions in `output/` directory
- Ensure Excel is not blocking the file

## Best Practices

1. **Regular Analysis**: Run dispute analysis monthly
2. **Document Findings**: Export suspicious transactions for review
3. **Follow Up**: Mark resolved disputes in your accounting system
4. **Pattern Recognition**: Look for recurring dispute merchants

## Integration with Power BI

The analyzer works seamlessly with Power BI preparation:
1. Run `quick_powerbi_prep.py` to clean data
2. Use GUI analyzer for detailed investigation
3. Export findings for Power BI reports

## Support

For issues or feature requests, please check:
- `scripts/utilities/README.md` for technical details
- GitHub repository for updates
- BALANCE documentation for overall system guide