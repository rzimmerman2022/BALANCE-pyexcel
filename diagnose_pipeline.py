import pandas as pd
import yaml
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

print("=== DIAGNOSTIC: Tracing Original Statement Data ===\n")

# Step 1: Confirm the data exists
csv_path = r"C:\BALANCE\CSVs\Ryan\Ryan - Monarch Money - 20250524.csv"
df = pd.read_csv(csv_path)
print("1. CSV loaded successfully")
print("   'Original Statement' column exists:", "Original Statement" in df.columns)
if "Original Statement" in df.columns:
    print("   Sample data:", df["Original Statement"].iloc[0][:50], "...")

# Step 2: Load the active schema
with open(r"rules\ryan_monarch_v1.yaml", encoding="utf-8") as f:
    schema = yaml.safe_load(f)

col_map = schema.get("column_map", {})
print("\n2. Schema loaded successfully")
print("   Mapping defined: Original Statement ->",
      col_map.get("Original Statement", "NOT MAPPED"))

# Step 3: Trace through the pipeline
try:
    from balance_pipeline.csv_consolidator import apply_schema_transformations

    print("\n3. Pipeline modules imported")

    test_df = df.head(3).copy()          # use real sample rows
    before_cols = test_df.columns.tolist()

    transformed = apply_schema_transformations(test_df, schema)
    after_cols = transformed.columns.tolist()

    print("   Columns BEFORE:", before_cols)
    print("   Columns AFTER :", after_cols)
except Exception as e:
    print("\nError during pipeline import:", e)

print("\n=== END DIAGNOSTIC ===")
