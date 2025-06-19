#--------------------------------------------------------------------------#
#   ██████╗   █████╗  ██╗       █████╗  ███╗   ██╗ ██████╗  ███████╗
#   ██╔══██╗ ██╔══██╗ ██║      ██╔══██╗ ████╗  ██║██╔════╝ ██╔════╝
#   ██████╔╝ ███████║ ██║      ███████║ ██╔██╗ ██║██║      █████╗
#   ██╔══██╗ ██╔══██║ ██║      ██╔══██║ ██║╚██╗██║██║      ██╔══╝
#   ██████╔╝ ██║  ██║ ███████╗ ██║  ██║ ██║ ╚████║╚██████╗ ███████╗
#   ╚═════╝  ╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝
#
#   Ingestion Driver
#--------------------------------------------------------------------------#
"""
run_ingest.py

CLI driver that cleans the four core CSV files from the 'data' directory and
writes the processed data into two tidy Parquet files in the 'artifacts'
directory.

Changelog:
  - 2025-06-18: Initial version. Cleans and combines Expense and Ledger
                data, processes rent allocation and history, and saves
                outputs as Parquet files.

Usage:
  - This script is intended to be run as a module from the project root.
  - Ensure you have an active Poetry shell.

  $ poetry run python -m tools.run_ingest --data-dir data
"""

import argparse
import pathlib
import sys

import pandas as pd

# This try/except block provides a helpful error message if the script
# is not run as a module, which prevents the ModuleNotFoundError.
try:
    from tools.ingest_helpers import (
        expense_history_df,
        rent_allocation_df,
        rent_history_df,
        transaction_ledger_df,
    )
    from baseline_analyzer import inject_opening_balance, load_config
except ModuleNotFoundError:
    print("❌ Error: Could not import helper modules.")
    print("   Please run this script as a module from the project root:")
    print("   $ poetry run python -m tools.run_ingest --data-dir data")
    sys.exit(1)


def main(data_dir: pathlib.Path):
    """
    Main function to orchestrate the data ingestion and cleaning process.

    Args:
        data_dir (pathlib.Path): The directory containing the source CSV files.
    """
    print("⏳ Starting data ingestion...")
    # --- Step 1: Find all required source files ---
    try:
        exp_path = next(data_dir.glob("Expense_History*.csv"))
        led_path = next(data_dir.glob("Transaction_Ledger*.csv"))
        alloc_path = next(data_dir.glob("Rent_Allocation*.csv"))
        hist_path = next(data_dir.glob("Rent_History*.csv"))
        print("   ✔ Found all source CSV files.")
    except StopIteration as e:
        print(f"❌ Error: A required CSV file was not found in '{data_dir}'.")
        print(f"   Missing file pattern: {e}")
        sys.exit(1)

    # --- Step 2: Load and clean each file using helper functions ---
    expense = expense_history_df(exp_path)
    ledger = transaction_ledger_df(led_path)
    rent_alloc = rent_allocation_df(alloc_path)
    rent_hist = rent_history_df(hist_path)
    print("   ✔ Loaded and cleaned data from CSVs.")

    # --- Step 3: Combine ledger data and remove potential duplicates ---
    ledger_full = pd.concat([expense, ledger], ignore_index=True).drop_duplicates(
        subset=["Date", "Person", "Account", "Amount", "Merchant"], keep="first"
    )

    # --- Step 4: Inject opening balance rows from config ---
    cfg = load_config()
    ledger_full = inject_opening_balance(ledger_full, cfg)
    print("   ✔ Combined ledger data and injected opening balances.")

    # --- Step 5: Create output directory and save Parquet files ---
    artifacts_dir = pathlib.Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    ledger_out_path = artifacts_dir / "ledger_full.parquet"
    rents_out_path = artifacts_dir / "rent_tables.parquet"

    ledger_full.to_parquet(ledger_out_path, index=False)
    pd.concat([rent_alloc, rent_hist], ignore_index=True).to_parquet(
        rents_out_path, index=False
    )
    print("   ✔ Saved final data to Parquet files.")

    # --- Final Summary ---
    print("\n✅ Ingest summary")
    print(f"   Ledger rows : {len(ledger_full):,}")
    print(f"   Rent rows   : {len(rent_alloc) + len(rent_hist):,}")
    print(f"   Saved       : {ledger_out_path}")
    print(f"                 {rents_out_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cleans the 4 BALANCE CSVs and writes tidy Parquet files."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        type=pathlib.Path,
        help="Folder containing the four raw CSVs.",
    )
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        print(f"❌ Error: The specified data directory does not exist: {args.data_dir}")
        sys.exit(1)

    main(args.data_dir.resolve())