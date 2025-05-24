import pandas as pd
import yaml
from pathlib import Path

# Define the paths
PARQUET_FILE_PATH = Path("output/balance_final.parquet")
CANONICAL_SCHEMA_FILE_PATH = Path("rules/canonical_schema.yml")

def load_canonical_schema(yaml_path: Path) -> tuple[list[str], list[str], list[str]]:
    """Loads metadata, required, and optional column names from the canonical schema YAML."""
    if not yaml_path.exists():
        print(f"ERROR: Canonical schema file not found at {yaml_path}")
        return [], [], []
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        schema_data = yaml.safe_load(f)
    
    metadata_cols = [col['Name'] for col in schema_data.get('metadata_columns', [])]
    required_cols = [col['Name'] for col in schema_data.get('required_columns', [])]
    optional_cols = [col['Name'] for col in schema_data.get('optional_columns', [])]
    
    return metadata_cols, required_cols, optional_cols

def audit_parquet_file(parquet_path: Path, metadata_cols: list, required_cols: list, optional_cols: list):
    """Audits the Parquet file against the canonical schema."""
    if not parquet_path.exists():
        print(f"ERROR: Parquet file not found at {parquet_path}")
        return

    try:
        df = pd.read_parquet(parquet_path)
        print(f"Successfully loaded Parquet file: {parquet_path}")
        print(f"DataFrame shape: {df.shape[0]} rows, {df.shape[1]} columns")
    except Exception as e:
        print(f"ERROR: Could not read Parquet file {parquet_path}: {e}")
        return

    parquet_columns = set(df.columns)
    expected_metadata_cols = set(metadata_cols)
    expected_required_cols = set(required_cols)
    expected_optional_cols = set(optional_cols)
    
    all_expected_canonical_cols = expected_metadata_cols.union(expected_required_cols).union(expected_optional_cols)

    print("\n--- Schema Validation Report ---")

    # 1. Check for presence of all REQUIRED columns
    print("\n1. Required Columns Check:")
    missing_required = []
    for col in expected_required_cols:
        if col not in parquet_columns:
            missing_required.append(col)
            print(f"  - MISSING Required Column: {col}")
        else:
            completeness = (df[col].notna().sum() / len(df)) * 100 if len(df) > 0 else 0
            print(f"  - PRESENT Required Column: {col} (Completeness: {completeness:.2f}%)")
    
    if missing_required:
        print(f"  WARNING: {len(missing_required)} required columns are missing from the Parquet file.")
    else:
        print("  SUCCESS: All required columns are present.")

    # 2. Check for presence of METADATA columns
    print("\n2. Metadata Columns Check:")
    missing_metadata = []
    for col in expected_metadata_cols:
        if col not in parquet_columns:
            missing_metadata.append(col)
            print(f"  - MISSING Metadata Column: {col}")
        else:
            print(f"  - PRESENT Metadata Column: {col}")
    if missing_metadata:
        print(f"  WARNING: {len(missing_metadata)} metadata columns are missing.")
    else:
        print("  SUCCESS: All metadata columns are present.")

    # 3. Report on OPTIONAL columns
    print("\n3. Optional Columns Report:")
    present_optional = []
    absent_optional = []
    for col in expected_optional_cols:
        if col in parquet_columns:
            present_optional.append(col)
            completeness = (df[col].notna().sum() / len(df)) * 100 if len(df) > 0 else 0
            print(f"  - PRESENT Optional Column: {col} (Completeness: {completeness:.2f}%)")
        else:
            absent_optional.append(col)
            print(f"  - ABSENT Optional Column: {col}")
    print(f"  Summary: {len(present_optional)} optional columns present, {len(absent_optional)} optional columns absent.")

    # 4. Identify UNEXPECTED columns
    print("\n4. Unexpected Columns Check:")
    unexpected_columns = parquet_columns - all_expected_canonical_cols
    if unexpected_columns:
        print(f"  WARNING: Found {len(unexpected_columns)} unexpected columns in Parquet file:")
        for col in unexpected_columns:
            print(f"    - {col}")
    else:
        print("  SUCCESS: No unexpected columns found.")
        
    print("\n--- End of Audit Report ---")

if __name__ == "__main__":
    print(f"Starting Parquet audit for: {PARQUET_FILE_PATH}")
    print(f"Using canonical schema from: {CANONICAL_SCHEMA_FILE_PATH}")
    
    meta_cols, req_cols, opt_cols = load_canonical_schema(CANONICAL_SCHEMA_FILE_PATH)
    
    if not req_cols and not meta_cols and not opt_cols:
        print("Could not load canonical schema. Aborting audit.")
    else:
        print(f"Loaded canonical schema: {len(meta_cols)} metadata, {len(req_cols)} required, {len(opt_cols)} optional columns.")
        audit_parquet_file(PARQUET_FILE_PATH, meta_cols, req_cols, opt_cols)
