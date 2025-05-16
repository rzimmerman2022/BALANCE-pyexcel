import duckdb
import os
from pathlib import Path

# Check if the file exists
parquet_path = Path("data/processed/combined_transactions.parquet")
print(f"Parquet file exists: {os.path.exists(parquet_path)}")

# Query the file if it exists
if os.path.exists(parquet_path):
    con = duckdb.connect(":memory:")
    query = f"SELECT COUNT(*) as row_count FROM '{parquet_path}'"
    result = con.execute(query).fetchall()
    print(f"Row count: {result[0][0]}")
    
    # Show schema
    query = f"DESCRIBE SELECT * FROM '{parquet_path}'"
    schema = con.execute(query).fetchall()
    print("\nSchema:")
    for col in schema:
        print(f"{col[0]}: {col[1]}")
    
    # Show sample data (first 5 rows)
    query = f"SELECT * FROM '{parquet_path}' LIMIT 5"
    data = con.execute(query).fetchall()
    print("\nSample data (first 5 rows):")
    for row in data:
        print(row)
