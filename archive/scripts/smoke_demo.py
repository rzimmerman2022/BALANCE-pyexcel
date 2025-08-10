from io import StringIO

import pandas as pd

# Import the library function under test
from baseline_analyzer.baseline_math import build_baseline

# ---------- fabricate tiny CSVs ----------
exp_csv = (
    "Name,Date,Allowed Amount,Description\n"
    "Ryan,2025-06-18,30,Groceries"
)

led_csv = """Name,Date,Actual Amount,Description
Ryan,2025-06-18,50,"Lunch 2x Ryan"
Ryan,2025-06-18,50,"Gift for Jordyn"
Ryan,2025-06-18,40,"Service fee $40 (2x)"
Ryan,2025-06-18,50,"Lunch split"
"""

# Load into DataFrames
exp_df = pd.read_csv(StringIO(exp_csv))
led_df = pd.read_csv(StringIO(led_csv))

# Run build_baseline
summary, audit = build_baseline(exp_df, led_df)

# Display results
print("--- Markdown summary ---")
print(summary.to_markdown(index=False))

print("\n--- First 8 audit rows ---")
cols = [
    "source_file",
    "row_id",
    "person",
    "date",
    "merchant",
    "allowed_amount",
    "net_effect",
    "pattern_flags",
    "calculation_notes",
]
print(audit[cols].head(8).to_markdown(index=False))
