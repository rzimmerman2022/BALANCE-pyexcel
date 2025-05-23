import pandas as pd
import os
from pathlib import Path
from scripts.process_pdfs import append_to_master

# Create a test directory if it doesn't exist
out_path = Path("data/processed")
out_path.mkdir(parents=True, exist_ok=True)

# Delete existing Parquet file if it exists
parquet_file = out_path / "combined_transactions.parquet"
if os.path.exists(parquet_file):
    os.remove(parquet_file)

print(f"Parquet file exists before test: {os.path.exists(parquet_file)}")

# Create a sample DataFrame with all required columns
data = {
    "TransDate": ["2024-07-29", "2024-07-30"],
    "PostDate": ["07/29", "07/30"],
    "RawMerchant": ["TEST MERCHANT 1", "TEST MERCHANT 2"],
    "Amount": [-12.34, -45.67],
    "AccountLast4": ["1234", "5678"],
    "ReferenceNumber": ["REF123", "REF456"],
    "Owner": ["TestOwner", "TestOwner"],
}
test_df = pd.DataFrame(data)

print(f"Test DataFrame shape: {test_df.shape}, columns: {list(test_df.columns)}")

# Call the append_to_master function with both required parameters
append_to_master(test_df, "TestOwner")

print(f"Parquet file exists after append: {os.path.exists(parquet_file)}")

# Now read the Parquet file back to confirm it contains our test data
try:
    import duckdb

    con = duckdb.connect(":memory:")
    query = f"SELECT COUNT(*) as row_count FROM '{parquet_file}'"
    result = con.execute(query).fetchall()
    print(f"Row count in Parquet file: {result[0][0]}")

    query = f"SELECT * FROM '{parquet_file}'"
    data = con.execute(query).fetchall()
    print("\nData in Parquet file:")
    for row in data:
        print(row)

    # Describe schema
    query = f"DESCRIBE SELECT * FROM '{parquet_file}'"
    schema = con.execute(query).fetchall()
    print("\nSchema:")
    for col in schema:
        print(f"{col[0]}: {col[1]}")

except Exception as e:
    print(f"Error reading Parquet file: {e}")
