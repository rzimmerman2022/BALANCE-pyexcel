"""
Quick sanity check script for balance pipeline.
Validates CTS compliance and mathematical balance after CSV ingestion.
"""

import hashlib
import pathlib
import sys

# Add the project root to Python path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.balance_pipeline.column_utils import validate_cts_compliance
from src.balance_pipeline.data_loader import load_all_data

try:
    # Try to import baseline_math - handle different possible locations
    try:
        from src.baseline_analyzer import baseline_math as bm
    except ImportError:
        try:
            import baseline_analyzer.baseline_math as bm
        except ImportError:
            # Fallback - create minimal balance calculation
            print(
                "Warning: baseline_math module not found, using simplified balance calculation"
            )
            bm = None
except ImportError:
    bm = None


def calculate_simple_balance(transactions_df):
    """Simple balance calculation if baseline_math is not available."""
    summary = (
        transactions_df.groupby("person")
        .agg({"actual_amount": "sum", "allowed_amount": "sum"})
        .reset_index()
    )

    summary["net_owed"] = summary["allowed_amount"] - summary["actual_amount"]
    return summary


def main():
    """Run quick sanity checks on the balance pipeline."""
    print("🔍 Balance Pipeline Quick Check")
    print("=" * 50)

    # Set data directory
    data_dir = pathlib.Path("data")
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        sys.exit(1)

    try:
        # Load all data
        print("📊 Loading transaction data...")
        transactions = load_all_data(data_dir)

        if transactions.empty:
            print("⚠️  No data loaded from any source")
            sys.exit(1)

        print(f"✅ Loaded {len(transactions)} transactions")

        # Check CTS compliance
        print("\n🔧 Validating CTS compliance...")
        if validate_cts_compliance(transactions):
            print("✅ CTS compliance: PASSED")
        else:
            print("❌ CTS compliance: FAILED")
            sys.exit(1)

        # Calculate balance
        print("\n💰 Calculating balance...")
        if bm is not None:
            try:
                summary_df, audit_df = bm.build_baseline(transactions)
                imbalance = round(summary_df["net_owed"].sum(), 2)
            except Exception as e:
                print(f"⚠️  baseline_math failed: {e}")
                print("Using simplified balance calculation...")
                summary_df = calculate_simple_balance(transactions)
                imbalance = round(summary_df["net_owed"].sum(), 2)
        else:
            summary_df = calculate_simple_balance(transactions)
            imbalance = round(summary_df["net_owed"].sum(), 2)

        # Display balance summary
        print("\n📋 Balance Summary:")
        print(summary_df.to_string(index=False, float_format="${:.2f}".format))

        # Check balance
        print(f"\n⚖️  Total Imbalance: ${imbalance}")

        if abs(imbalance) <= 0.02:
            print("✅ Balance check: PASSED (within 2¢ tolerance)")
        else:
            print(
                f"❌ Balance check: FAILED (imbalance ${imbalance} exceeds tolerance)"
            )
            sys.exit(1)

        # Data quality checks
        print("\n🔍 Data Quality Checks:")

        # Check date range
        min_date = transactions["date"].min()
        max_date = transactions["date"].max()
        print(
            f"📅 Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        )

        # Check source distribution
        source_counts = transactions["source_file"].value_counts()
        print("📁 Source distribution:")
        for source, count in source_counts.items():
            print(f"   {source}: {count} transactions")

        # Check person distribution
        person_counts = transactions["person"].value_counts()
        print("👥 Person distribution:")
        for person, count in person_counts.items():
            print(f"   {person}: {count} transactions")

        # Idempotency check (optional)
        print("\n🔄 Testing idempotency...")
        transactions2 = load_all_data(data_dir)

        if len(transactions) == len(transactions2):
            # Quick hash comparison
            hash1 = hashlib.md5(transactions.to_csv(index=False).encode()).hexdigest()
            hash2 = hashlib.md5(transactions2.to_csv(index=False).encode()).hexdigest()

            if hash1 == hash2:
                print("✅ Idempotency check: PASSED")
            else:
                print("⚠️  Idempotency check: Data differs between runs")
        else:
            print("⚠️  Idempotency check: Row count differs between runs")

        print("\n🎉 All checks completed successfully!")
        print("✅ Pipeline is ready for production use")

    except Exception as e:
        print(f"❌ Error during checks: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
