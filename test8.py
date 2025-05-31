#!/usr/bin/env python3
"""
Comprehensive analyzer to understand the TRUE financial dynamics
between Ryan and Jordyn based on actual payment patterns
"""

import csv
import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re

def parse_amount(amount_str):
    """Parse amount string, handling $ and parentheses."""
    if not amount_str:
        return 0.0
    # Remove $ and commas
    cleaned = re.sub(r'[$,]', '', str(amount_str).strip())
    # Handle parentheses as negative
    if '(' in str(amount_str) and ')' in str(amount_str):
        cleaned = '-' + re.sub(r'[()]', '', cleaned)
    try:
        return float(cleaned)
    except:
        return 0.0

def analyze_rent_balance_flow(filepath):
    """Analyze rent allocation to understand the balance flow."""
    print("\n" + "="*70)
    print("RENT PAYMENT & BALANCE FLOW ANALYSIS")
    print("="*70)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # First, understand the column structure
        headers = reader.fieldnames
        print(f"\nColumns found: {headers}")
        
        # Track the flow
        rent_flow = []
        
        for row in reader:
            month = row.get('Month', '').strip()
            if not month:
                continue
            
            # Parse all financial columns
            record = {
                'month': month,
                'gross_total': 0,
                'ryan_share': 0,
                'jordyn_share': 0,
                'previous_balance': 0,
                'rent_difference': 0,
                'new_balance': 0
            }
            
            # Find and parse columns
            for key, value in row.items():
                if 'gross total' in key.lower():
                    record['gross_total'] = parse_amount(value)
                elif 'ryan' in key.lower() and 'rent' in key.lower():
                    record['ryan_share'] = parse_amount(value)
                elif 'jordyn' in key.lower() and 'rent' in key.lower():
                    record['jordyn_share'] = parse_amount(value)
                elif 'previous balance' in key.lower():
                    record['previous_balance'] = parse_amount(value)
                elif 'rent difference' in key.lower():
                    record['rent_difference'] = parse_amount(value)
                elif 'new balance' in key.lower():
                    record['new_balance'] = parse_amount(value)
            
            if record['gross_total'] > 0:
                rent_flow.append(record)
        
        # Analyze the pattern
        print("\n📊 RENT PAYMENT PATTERN:")
        print(f"{'Month':<12} {'Total':<10} {'Ryan 43%':<10} {'Jordyn 57%':<12} {'Prev Bal':<12} {'Difference':<12} {'New Bal':<12}")
        print("-" * 90)
        
        for record in rent_flow[:5]:  # Show first 5 months
            print(f"{record['month']:<12} "
                  f"${record['gross_total']:<9.2f} "
                  f"${record['ryan_share']:<9.2f} "
                  f"${record['jordyn_share']:<11.2f} "
                  f"${record['previous_balance']:<11.2f} "
                  f"${record['rent_difference']:<11.2f} "
                  f"${record['new_balance']:<11.2f}")
        
        # Key insights
        print("\n🔑 KEY INSIGHTS FROM RENT DATA:")
        
        # Who's actually paying?
        print("\n1. PAYMENT PATTERN:")
        print("   - Jordyn appears to pay the FULL RENT each month")
        print(f"   - Ryan's monthly share (43%): ~${rent_flow[0]['ryan_share']:.2f}")
        print(f"   - The 'Rent Difference' shows Ryan's monthly debt: ~${abs(rent_flow[0]['rent_difference']):.2f}")
        
        # Balance trend
        if len(rent_flow) > 1:
            balance_trend = "increasing" if rent_flow[-1]['new_balance'] > rent_flow[0]['new_balance'] else "decreasing"
            print(f"\n2. BALANCE TREND: Ryan's debt is {balance_trend}")
            print(f"   - Starting balance: ${rent_flow[0]['previous_balance']:,.2f}")
            print(f"   - Latest balance: ${rent_flow[-1]['new_balance']:,.2f}")
        
        return rent_flow

def analyze_expense_patterns_comprehensive(filepath):
    """Analyze expense history with correct understanding of who pays what."""
    print("\n" + "="*70)
    print("EXPENSE PATTERN ANALYSIS")
    print("="*70)
    
    # Track comprehensive patterns
    payer_patterns = defaultdict(lambda: {
        'total_paid': 0,
        'shared_expenses_paid': 0,
        'personal_expenses': 0,
        'merchants': defaultdict(int)
    })
    
    merchant_analysis = defaultdict(lambda: {
        'ryan_paid': 0,
        'jordyn_paid': 0,
        'shared_count': 0,
        'personal_count': 0,
        'total_amount': 0,
        'examples': []
    })
    
    shared_indicators = defaultdict(list)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            name = row.get('Name', '').strip()
            merchant = row.get('Merchant', '').strip()
            actual = parse_amount(row.get('Actual Amount', row.get(' Actual Amount ', '0')))
            allowed = parse_amount(row.get('Allowed Amount', row.get(' Allowed Amount ', '0')))
            description = row.get('Description', row.get(' Description ', '')).strip()
            
            if not merchant or actual == 0:
                continue
            
            # Track who paid
            payer_patterns[name]['total_paid'] += actual
            payer_patterns[name]['merchants'][merchant] += 1
            
            # Determine if shared
            is_shared = allowed > 0
            
            if is_shared:
                payer_patterns[name]['shared_expenses_paid'] += actual
                merchant_analysis[merchant]['shared_count'] += 1
                shared_indicators['allowed_amount'].append(merchant)
                
                # Track special patterns in descriptions
                desc_lower = description.lower()
                if '2x to calculate' in desc_lower:
                    shared_indicators['2x_calculation'].append((merchant, description))
                if any(term in desc_lower for term in ['split', 'shared', 'both']):
                    shared_indicators['explicit_sharing'].append((merchant, description))
                if '100% jordyn' in desc_lower or '100% ryan' in desc_lower:
                    shared_indicators['explicit_ownership'].append((merchant, description))
            else:
                payer_patterns[name]['personal_expenses'] += actual
                merchant_analysis[merchant]['personal_count'] += 1
            
            # Track by merchant
            if name.lower() == 'ryan':
                merchant_analysis[merchant]['ryan_paid'] += actual
            else:
                merchant_analysis[merchant]['jordyn_paid'] += actual
            
            merchant_analysis[merchant]['total_amount'] += actual
            if len(merchant_analysis[merchant]['examples']) < 3 and description:
                merchant_analysis[merchant]['examples'].append(f"{description} (${allowed:.2f} allowed)")
    
    # Print insights
    print("\n💰 WHO PAYS FOR WHAT:")
    for person, data in payer_patterns.items():
        print(f"\n{person}:")
        print(f"  Total paid: ${data['total_paid']:,.2f}")
        print(f"  Shared expenses paid: ${data['shared_expenses_paid']:,.2f}")
        print(f"  Personal expenses: ${data['personal_expenses']:,.2f}")
        print(f"  Unique merchants: {len(data['merchants'])}")
        
        # Top merchants this person pays
        top_merchants = sorted(data['merchants'].items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"  Top merchants:")
        for merchant, count in top_merchants:
            print(f"    - {merchant}: {count} times")
    
    print("\n🏪 MERCHANT PAYMENT PATTERNS:")
    
    # Find who typically pays for each merchant
    merchant_payers = []
    for merchant, data in merchant_analysis.items():
        total = data['ryan_paid'] + data['jordyn_paid']
        if total > 0:
            ryan_pct = (data['ryan_paid'] / total) * 100
            jordyn_pct = (data['jordyn_paid'] / total) * 100
            primary_payer = 'Ryan' if ryan_pct > jordyn_pct else 'Jordyn'
            
            merchant_payers.append({
                'merchant': merchant,
                'primary_payer': primary_payer,
                'payer_percentage': max(ryan_pct, jordyn_pct),
                'total_amount': total,
                'is_shared': data['shared_count'] > data['personal_count']
            })
    
    # Show merchants by primary payer
    print("\n📊 MERCHANTS BY PRIMARY PAYER:")
    
    ryan_merchants = [m for m in merchant_payers if m['primary_payer'] == 'Ryan']
    jordyn_merchants = [m for m in merchant_payers if m['primary_payer'] == 'Jordyn']
    
    print(f"\nRyan typically pays at ({len(ryan_merchants)} merchants):")
    for m in sorted(ryan_merchants, key=lambda x: x['total_amount'], reverse=True)[:10]:
        shared_tag = " [SHARED]" if m['is_shared'] else " [PERSONAL]"
        print(f"  - {m['merchant']}: {m['payer_percentage']:.0f}% of ${m['total_amount']:,.2f}{shared_tag}")
    
    print(f"\nJordyn typically pays at ({len(jordyn_merchants)} merchants):")
    for m in sorted(jordyn_merchants, key=lambda x: x['total_amount'], reverse=True)[:10]:
        shared_tag = " [SHARED]" if m['is_shared'] else " [PERSONAL]"
        print(f"  - {m['merchant']}: {m['payer_percentage']:.0f}% of ${m['total_amount']:,.2f}{shared_tag}")
    
    # Special indicators
    print("\n🔍 SPECIAL SHARING INDICATORS FOUND:")
    print(f"  - '2x to calculate' found in {len(shared_indicators['2x_calculation'])} transactions")
    if shared_indicators['2x_calculation']:
        for merchant, desc in shared_indicators['2x_calculation'][:3]:
            print(f"    → {merchant}: {desc}")
    
    print(f"  - Explicit sharing keywords in {len(shared_indicators['explicit_sharing'])} transactions")
    print(f"  - Explicit ownership (100% person) in {len(shared_indicators['explicit_ownership'])} transactions")
    
    return payer_patterns, merchant_analysis

def calculate_true_balance(rent_flow, expense_patterns):
    """Calculate the true balance based on all data."""
    print("\n" + "="*70)
    print("TRUE BALANCE CALCULATION")
    print("="*70)
    
    # From rent data
    if rent_flow:
        latest_rent_balance = rent_flow[-1]['new_balance']
        print(f"\n📊 From RENT alone:")
        print(f"   Ryan owes Jordyn: ${latest_rent_balance:,.2f}")
    
    # From expense data
    print(f"\n💳 From OTHER EXPENSES:")
    print("   (This would need transaction-by-transaction analysis)")
    print("   Key principle: When someone pays a shared expense,")
    print("   the other person owes their percentage share")
    
    print("\n" + "="*70)
    print("FINAL INSIGHTS:")
    print("="*70)
    print("\n1. Jordyn is the PRIMARY PAYER for rent (100%)")
    print("2. Ryan owes his 43% share each month")
    print("3. The balance accumulates over time")
    print("4. For other shared expenses (AllowedAmount > 0):")
    print("   - The payer is owed the other person's share")
    print("   - This affects the running balance")

def generate_data_driven_rules(payer_patterns, merchant_analysis):
    """Generate rules based on actual payment patterns."""
    
    rules = {
        "payment_dynamics": {
            "rent": {
                "primary_payer": "Jordyn",
                "payment_method": "Jordyn pays 100%, Ryan owes 43%",
                "monthly_ryan_debt": "~$911-937"
            },
            "balance_direction": {
                "positive": "Ryan owes Jordyn",
                "negative": "Jordyn owes Ryan (rare)",
                "typical_state": "Ryan has ongoing debt to Jordyn"
            }
        },
        "sharing_rules": {
            "primary_indicator": "AllowedAmount > 0 means shared",
            "split_ratio": {"ryan": 43, "jordyn": 57},
            "special_indicators": [
                "2x to calculate - means double the amount for full cost",
                "100% [person] - explicitly assigned to one person"
            ]
        },
        "merchant_patterns": {
            "always_shared": [],
            "usually_shared": [],
            "by_primary_payer": {
                "ryan": [],
                "jordyn": []
            }
        }
    }
    
    # Classify merchants
    for merchant, data in merchant_analysis.items():
        total_trans = data['shared_count'] + data['personal_count']
        if total_trans >= 2:
            share_rate = (data['shared_count'] / total_trans) * 100
            
            merchant_info = {
                "merchant": merchant,
                "transactions": total_trans,
                "share_rate": share_rate,
                "total_amount": data['total_amount']
            }
            
            if share_rate == 100:
                rules["merchant_patterns"]["always_shared"].append(merchant_info)
            elif share_rate >= 75:
                rules["merchant_patterns"]["usually_shared"].append(merchant_info)
            
            # Track by payer
            if data['ryan_paid'] > data['jordyn_paid']:
                rules["merchant_patterns"]["by_primary_payer"]["ryan"].append(merchant)
            else:
                rules["merchant_patterns"]["by_primary_payer"]["jordyn"].append(merchant)
    
    return rules

def main():
    csv_dir = Path(r"C:\BALANCE")
    
    print("="*70)
    print("COMPREHENSIVE FINANCIAL DYNAMICS ANALYSIS")
    print("="*70)
    print("Understanding the TRUE payment and balance patterns")
    
    # File paths
    rent_file = csv_dir / "New Master - New Joint Couple Finances (2024).xlsx - Rent Allocation.csv"
    expense_file = csv_dir / "New Master - New Joint Couple Finances (2024).xlsx - Expense History.csv"
    
    rent_flow = []
    if rent_file.exists():
        rent_flow = analyze_rent_balance_flow(rent_file)
    else:
        print(f"❌ Rent file not found: {rent_file}")
    
    payer_patterns = {}
    merchant_analysis = {}
    if expense_file.exists():
        payer_patterns, merchant_analysis = analyze_expense_patterns_comprehensive(expense_file)
    else:
        print(f"❌ Expense file not found: {expense_file}")
    
    # Calculate true balance
    if rent_flow or payer_patterns:
        calculate_true_balance(rent_flow, payer_patterns)
    
    # Generate rules
    rules = generate_data_driven_rules(payer_patterns, merchant_analysis)
    
    # Save comprehensive analysis
    output_file = csv_dir / "comprehensive_balance_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(rules, f, indent=2)
    
    print(f"\n✅ Comprehensive analysis saved to: {output_file}")
    
    # Save rent flow data
    if rent_flow:
        rent_df = pd.DataFrame(rent_flow)
        rent_output = csv_dir / "rent_balance_flow.csv"
        rent_df.to_csv(rent_output, index=False)
        print(f"✅ Rent flow data saved to: {rent_output}")

if __name__ == "__main__":
    main()
    input("\nPress Enter to close...")