#!/usr/bin/env python3
"""
Quick test to verify rent-share rule implementation works correctly
before running the full audit.
"""

import pandas as pd
from baseline_analyzer import baseline_math as bm

# Create test data with a few rent entries
test_expense_data = [
    {"person": "Ryan", "date": "Jan-24", "merchant": "Rent", "allowed": 911.48},
    {"person": "Jordyn", "date": "Feb-24", "merchant": "Groceries", "allowed": 100.00},
]

test_ledger_data = [
    {"person": "Ryan", "date": "Jan-24", "merchant": "Target", "actual": 50.00},
]

expense_df = pd.DataFrame(test_expense_data)
ledger_df = pd.DataFrame(test_ledger_data)

print("🧪 Testing rent-share rule implementation...")
print("📊 Test expense data:")
print(expense_df.to_string(index=False))
print("\n📊 Test ledger data:")
print(ledger_df.to_string(index=False))

# Run baseline analysis
summary_df, audit_df = bm.build_baseline(expense_df, ledger_df)

print("\n📋 Audit results:")
rent_rows = audit_df[audit_df["merchant"] == "Rent"]
print(rent_rows[["person", "merchant", "actual_amount", "allowed_amount", "net_effect", "calculation_notes"]].to_string(index=False))

print("\n🔍 Rent allocation verification:")
if len(rent_rows) > 0:
    ryan_rent = rent_rows[rent_rows["person"] == "Ryan"]
    jordyn_rent = rent_rows[rent_rows["person"] == "Jordyn"]
    
    if len(ryan_rent) > 0 and len(jordyn_rent) > 0:
        ryan_allowed = ryan_rent["allowed_amount"].iloc[0]
        jordyn_allowed = jordyn_rent["allowed_amount"].iloc[0]
        total_rent = ryan_rent["actual_amount"].iloc[0]
        
        ryan_pct = ryan_allowed / total_rent * 100
        jordyn_pct = jordyn_allowed / total_rent * 100
        
        print(f"   Total rent: ${total_rent:.2f}")
        print(f"   Ryan gets: ${ryan_allowed:.2f} ({ryan_pct:.1f}%)")
        print(f"   Jordyn gets: ${jordyn_allowed:.2f} ({jordyn_pct:.1f}%)")
        print("   Expected: Ryan 43%, Jordyn 57%")
        
        # Check integrity equation
        for _, row in rent_rows.iterrows():
            integrity_check = abs(row["allowed_amount"] + row["net_effect"] - row["actual_amount"])
            print(f"   {row['person']} integrity check: {integrity_check:.6f} (should be ~0)")
            
        if abs(ryan_pct - 43) < 1 and abs(jordyn_pct - 57) < 1:
            print("✅ Rent allocation is correct!")
        else:
            print("❌ Rent allocation is incorrect!")
    else:
        print("❌ Missing rent rows for one or both people")
else:
    print("❌ No rent rows found in audit results")

print("\n📊 Summary:")
print(summary_df.to_string(index=False))
