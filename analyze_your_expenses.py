#!/usr/bin/env python3
"""
Analyzer specifically for your expense and rent data format
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
import re

def parse_amount(amount_str):
    """Parse amount string, handling $ and parentheses."""
    if not amount_str:
        return 0.0
    # Remove $ and commas
    cleaned = re.sub(r'[$,]', '', str(amount_str).strip())
    # Handle parentheses as negative
    if '(' in cleaned and ')' in cleaned:
        cleaned = '-' + re.sub(r'[()]', '', cleaned)
    try:
        return float(cleaned)
    except:
        return 0.0

def analyze_rent_allocation(filepath):
    """Analyze rent allocation CSV."""
    print("\n📊 RENT ALLOCATION ANALYSIS")
    print("="*50)
    
    rent_records = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Debug: show actual column names
        print(f"Columns found: {reader.fieldnames[:5]}...")
        
        for row in reader:
            # Handle columns with spaces
            month = row.get('Month', '').strip()
            if not month:
                continue
                
            # Find Ryan's and Jordyn's rent columns (with flexible matching)
            ryan_rent = None
            jordyn_rent = None
            gross_total = None
            
            for key, value in row.items():
                if 'ryan' in key.lower() and 'rent' in key.lower():
                    ryan_rent = parse_amount(value)
                elif 'jordyn' in key.lower() and 'rent' in key.lower():
                    jordyn_rent = parse_amount(value)
                elif 'gross total' in key.lower():
                    gross_total = parse_amount(value)
            
            if ryan_rent and jordyn_rent and gross_total > 0:
                ryan_pct = (ryan_rent / gross_total) * 100
                jordyn_pct = (jordyn_rent / gross_total) * 100
                
                print(f"{month}: Ryan=${ryan_rent:.2f} ({ryan_pct:.1f}%), Jordyn=${jordyn_rent:.2f} ({jordyn_pct:.1f}%)")
                
                rent_records.append({
                    'month': month,
                    'ryan': ryan_rent,
                    'jordyn': jordyn_rent,
                    'total': gross_total
                })
    
    # Calculate average split
    if rent_records:
        total_ryan = sum(r['ryan'] for r in rent_records)
        total_jordyn = sum(r['jordyn'] for r in rent_records)
        total_all = total_ryan + total_jordyn
        
        avg_ryan_pct = (total_ryan / total_all) * 100
        avg_jordyn_pct = (total_jordyn / total_all) * 100
        
        print(f"\n📊 AVERAGE SPLIT:")
        print(f"   Ryan: {avg_ryan_pct:.1f}%")
        print(f"   Jordyn: {avg_jordyn_pct:.1f}%")
        print(f"   Total paid: ${total_all:,.2f}")
        
        return avg_ryan_pct, avg_jordyn_pct
    
    return 43, 57  # default

def analyze_expense_history(filepath):
    """Analyze expense history CSV."""
    print("\n💳 EXPENSE HISTORY ANALYSIS")
    print("="*50)
    
    merchant_patterns = defaultdict(lambda: {"shared": 0, "individual": 0, "total_amount": 0})
    sharing_indicators = defaultdict(int)
    person_totals = defaultdict(float)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        row_count = 0
        for row in reader:
            name = row.get('Name', '').strip()
            merchant = row.get('Merchant', '').strip()
            actual = parse_amount(row.get('Actual Amount', row.get(' Actual Amount ', '0')))
            allowed = parse_amount(row.get('Allowed Amount', row.get(' Allowed Amount ', '0')))
            description = row.get('Description', row.get(' Description ', '')).lower()
            
            if not merchant or actual == 0:
                continue
                
            row_count += 1
            person_totals[name] += actual
            
            # Determine if shared based on various indicators
            is_shared = False
            
            # 1. Partial reimbursement suggests sharing
            if allowed > 0 and allowed < actual:
                is_shared = True
                sharing_indicators['partial_reimbursement'] += 1
            
            # 2. Description contains sharing keywords
            if any(word in description for word in ['split', 'shared', 'both', '50/50', 'half', '2x to calculate']):
                is_shared = True
                sharing_indicators['keyword_in_description'] += 1
            
            # 3. Known shared merchants
            merchant_lower = merchant.lower()
            shared_merchants = ['fry', 'walmart', 'costco', 'target', 'grocery', 'walgreens']
            if any(m in merchant_lower for m in shared_merchants) and 'doordash' not in merchant_lower:
                # Check if it's actually shared based on description
                if allowed > 0 or any(word in description for word in ['laundry', 'tissue', 'household']):
                    is_shared = True
                    sharing_indicators['known_shared_merchant'] += 1
            
            # 4. Utilities and household
            if any(word in merchant_lower for word in ['utility', 'electric', 'water', 'internet']):
                is_shared = True
                sharing_indicators['utility'] += 1
            
            # Track merchant patterns
            if is_shared:
                merchant_patterns[merchant]['shared'] += 1
            else:
                merchant_patterns[merchant]['individual'] += 1
            merchant_patterns[merchant]['total_amount'] += actual
    
    print(f"Processed {row_count} expense records")
    print(f"\n📊 SPENDING BY PERSON:")
    for person, total in person_totals.items():
        print(f"   {person}: ${total:,.2f}")
    
    print(f"\n🔍 SHARING INDICATORS FOUND:")
    for indicator, count in sharing_indicators.items():
        print(f"   {indicator.replace('_', ' ').title()}: {count}")
    
    # Find top shared merchants
    print(f"\n🏪 TOP SHARED MERCHANTS:")
    shared_merchants = []
    for merchant, data in merchant_patterns.items():
        total_transactions = data['shared'] + data['individual']
        if data['shared'] > 0:
            share_pct = (data['shared'] / total_transactions) * 100
            shared_merchants.append((merchant, share_pct, data['shared'], data['total_amount']))
    
    for merchant, pct, count, amount in sorted(shared_merchants, key=lambda x: x[2], reverse=True)[:15]:
        print(f"   {merchant}: {count} shared ({pct:.0f}%), ${amount:,.2f} total")
    
    return merchant_patterns

def generate_sharing_rules(ryan_pct, jordyn_pct, merchant_patterns):
    """Generate sharing rules JSON."""
    
    # Build merchant rules
    merchant_rules = []
    for merchant, data in merchant_patterns.items():
        total = data['shared'] + data['individual']
        if total >= 2 and data['shared'] > 0:
            share_pct = (data['shared'] / total) * 100
            if share_pct >= 50:  # Lower threshold to catch more patterns
                merchant_rules.append({
                    "pattern": merchant.lower(),
                    "action": "shared",
                    "confidence": share_pct,
                    "transaction_count": total
                })
    
    # Sort by confidence
    merchant_rules.sort(key=lambda x: x['confidence'], reverse=True)
    
    rules = {
        "sharing_rules": {
            "default_split": {
                "ryan": round(ryan_pct),
                "jordyn": round(jordyn_pct)
            },
            "merchant_patterns": merchant_rules[:20],  # Top 20 patterns
            "category_patterns": [
                {"category": "Groceries", "action": "shared", "confidence": 85},
                {"category": "Utilities", "action": "shared", "confidence": 100},
                {"category": "Rent", "action": "shared", "confidence": 100},
                {"category": "Household", "action": "shared", "confidence": 90},
                {"category": "Gas/Electric", "action": "shared", "confidence": 100},
                {"category": "Internet", "action": "shared", "confidence": 100}
            ],
            "description_keywords": {
                "shared": [
                    "split", "shared", "both", "50/50", "half", 
                    "groceries", "household", "laundry", "detergent",
                    "tissue", "paper towel", "cleaning", "utilities",
                    "2x to calculate"
                ],
                "ryan": ["ryan only", "ryan's", "ryan personal", "100% ryan"],
                "jordyn": ["jordyn only", "jordyn's", "jordyn personal", "100% jordyn"]
            },
            "always_shared_merchants": [
                "fry's", "frys", "walmart", "costco", "target", 
                "safeway", "albertsons", "whole foods", "trader joe's",
                "utilities", "electric", "water", "gas", "internet"
            ]
        }
    }
    
    return rules

def main():
    csv_dir = Path(r"C:\BALANCE")
    
    print("="*60)
    print("EXPENSE SHARING ANALYZER")
    print("="*60)
    
    # File paths
    rent_file = csv_dir / "New Master - New Joint Couple Finances (2024).xlsx - Rent Allocation.csv"
    expense_file = csv_dir / "New Master - New Joint Couple Finances (2024).xlsx - Expense History.csv"
    
    # Check files exist
    if not rent_file.exists():
        print(f"❌ Rent file not found: {rent_file}")
        ryan_pct, jordyn_pct = 43, 57
    else:
        ryan_pct, jordyn_pct = analyze_rent_allocation(rent_file)
    
    if not expense_file.exists():
        print(f"❌ Expense file not found: {expense_file}")
        merchant_patterns = {}
    else:
        merchant_patterns = analyze_expense_history(expense_file)
    
    # Generate and save rules
    rules = generate_sharing_rules(ryan_pct, jordyn_pct, merchant_patterns)
    
    output_file = csv_dir / "generated_sharing_rules.json"
    with open(output_file, 'w') as f:
        json.dump(rules, f, indent=2)
    
    print(f"\n✅ SHARING RULES SAVED TO: {output_file}")
    print("\n📋 Rules Summary:")
    print(f"   - Default split: Ryan {rules['sharing_rules']['default_split']['ryan']}%, Jordyn {rules['sharing_rules']['default_split']['jordyn']}%")
    print(f"   - Merchant patterns identified: {len(rules['sharing_rules']['merchant_patterns'])}")
    print(f"   - Always shared merchants: {len(rules['sharing_rules']['always_shared_merchants'])}")
    
    print("\n🎯 Next Steps:")
    print("   1. Review the generated_sharing_rules.json file")
    print("   2. Integrate these rules into your BALANCE pipeline")
    print("   3. Use these patterns to auto-populate sharing_status field")

if __name__ == "__main__":
    main()
    input("\nPress Enter to close...")