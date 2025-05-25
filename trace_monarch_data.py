import pandas as pd
import yaml
import sys
from pathlib import Path

# Make <repo>/src importable no matter where you launch the script
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root / "src"))

print("=== STEP 1: Reading CSV ===")
csv_path = r"C:\BALANCE\CSVs\Ryan\Ryan - Monarch Money - 20250524.csv"
df = pd.read_csv(csv_path)
print(f"Columns in CSV: {df.columns.tolist()}")
print(f"'Original Statement' exists: {'Original Statement' in df.columns}")
if "Original Statement" in df.columns:
    print("Sample Original Statement:",
          df["Original Statement"].iloc[0][:50], "...")

print("\n=== STEP 2: Loading Schema ===")
with open(repo_root / r"rules\ryan_monarch_v1.yaml", encoding="utf-8") as f:
    schema = yaml.safe_load(f)

column_map = schema.get("column_map", {})
print(f"Column-map contains 'Original Statement': {'Original Statement' in column_map}")
print("Original Statement maps to:",
      column_map.get("Original Statement", "NOT MAPPED"))

print("\n=== STEP 3: Checking Pipeline Behavior ===")
try:
    from balance_pipeline.csv_consolidator import apply_schema_transformations

    print("Successfully imported transformation function")

    print("\nBefore transformation:")
    print("  OriginalDescription in df:",
          "OriginalDescription" in df.columns)
    print("  Original Statement  in df:",
          "Original Statement"  in df.columns)

    transformed = apply_schema_transformations(df.copy(), schema)

    print("\nAfter transformation:")
    print("  OriginalDescription in transformed:",
          "OriginalDescription" in transformed.columns)
    print("  Original Statement  in transformed:",
          "Original Statement"  in transformed.columns)

except Exception as e:
    print(f"Could not import pipeline functions: {e}")
