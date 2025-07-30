import pandas as pd
import pathlib

# Load latest audit file
audit_dir = pathlib.Path("audit_reports")
latest = max(audit_dir.glob("complete_audit_trail_*.csv"), key=lambda x: x.stat().st_mtime)
df = pd.read_csv(latest)

print("=== BEFORE CLEANING ===")
print(f"Total rows: {len(df)}")
print(f"Invalid persons: {(~df['person'].isin(['Ryan', 'Jordyn'])).sum()}")

# Clean the data
cleaned_df = df[df['person'].isin(['Ryan', 'Jordyn'])].copy()

# Remove duplicates
cleaned_df = cleaned_df.drop_duplicates(subset=['date', 'person', 'merchant', 'actual_amount', 'allowed_amount'])

print("\n=== AFTER CLEANING ===")
print(f"Total rows: {len(cleaned_df)}")
print(f"Rows removed: {len(df) - len(cleaned_df)}")

# Recalculate balance
ryan_net = cleaned_df[cleaned_df['person'] == 'Ryan']['net_effect'].sum()
jordyn_net = cleaned_df[cleaned_df['person'] == 'Jordyn']['net_effect'].sum()

print(f"\nCleaned Balance:")
print(f"Ryan: ${ryan_net:,.2f}")
print(f"Jordyn: ${jordyn_net:,.2f}")
print(f"Total: ${ryan_net + jordyn_net:,.2f}")

# Save cleaned version
cleaned_df.to_csv("cleaned_audit_trail.csv", index=False)
print("\nCleaned data saved to: cleaned_audit_trail.csv")
