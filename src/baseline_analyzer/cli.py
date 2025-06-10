import argparse
import logging
import sys
from pathlib import Path
import structlog
from typing import Dict, Any

from .processing import build_baseline


def setup_structured_logging(debug: bool = False) -> structlog.BoundLogger:
    """Setup structured logging with colorized output."""
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure standard logging
    logging.basicConfig(
        level=level,
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


def calculate_data_quality_score(df, stats) -> Dict[str, Any]:
    """Calculate data quality score and metrics."""
    if df.empty:
        return {
            "overall_score": 0.0,
            "metrics": {
                "completeness": 0.0,
                "validity": 0.0,
                "consistency": 1.0
            },
            "issues": ["No data generated"]
        }
    
    total_rows = len(df)
    issues = []
    
    # Completeness: Check for missing lineage
    lineage_complete = df["lineage"].notna().sum()
    completeness_score = lineage_complete / total_rows if total_rows > 0 else 0
    
    if completeness_score < 1.0:
        issues.append(f"{total_rows - lineage_complete} rows missing lineage")
    
    # Validity: Check for valid net_owed values
    valid_amounts = df["net_owed"].notna().sum()
    validity_score = valid_amounts / total_rows if total_rows > 0 else 0
    
    if validity_score < 1.0:
        issues.append(f"{total_rows - valid_amounts} rows with invalid amounts")
    
    # Consistency: Check for zero-sum balance
    total_balance = df["net_owed"].sum()
    consistency_score = 1.0 if abs(total_balance) < 0.01 else max(0, 1 - abs(total_balance) / 1000)
    
    if abs(total_balance) >= 0.01:
        issues.append(f"Balance not zero-sum: ${total_balance:.2f}")
    
    # Data cleaning efficiency
    if hasattr(stats, 'rows_in') and stats.rows_in > 0:
        cleaning_efficiency = stats.rows_out / stats.rows_in
        if stats.duplicates_dropped > 0:
            issues.append(f"{stats.duplicates_dropped} duplicates removed")
        if stats.bad_dates > 0:
            issues.append(f"{stats.bad_dates} bad dates corrected")
    else:
        cleaning_efficiency = 1.0
    
    # Overall score (weighted average)
    overall_score = (
        completeness_score * 0.3 +
        validity_score * 0.3 +
        consistency_score * 0.4
    )
    
    return {
        "overall_score": round(overall_score * 100, 1),
        "metrics": {
            "completeness": round(completeness_score * 100, 1),
            "validity": round(validity_score * 100, 1),
            "consistency": round(consistency_score * 100, 1),
            "cleaning_efficiency": round(cleaning_efficiency * 100, 1) if 'cleaning_efficiency' in locals() else 100.0
        },
        "issues": issues
    }


def print_summary(logger, df, stats, quality_score: Dict[str, Any], duration: float):
    """Print colorized summary of the analysis."""
    logger.info("="*60)
    logger.info("🎯 BASELINE ANALYSIS COMPLETE", 
                duration_seconds=round(duration, 2),
                records_generated=len(df))
    
    if not df.empty:
        # Balance summary
        total_balance = df["net_owed"].sum()
        logger.info("💰 BALANCE SUMMARY")
        for _, row in df.iterrows():
            status = "owes" if row["net_owed"] > 0 else "is owed" 
            amount = abs(row["net_owed"])
            logger.info(f"   {row['person']} {status} ${amount:.2f}")
        
        logger.info(f"   Total net balance: ${total_balance:.2f}")
        
        # Data quality summary
        score = quality_score["overall_score"]
        score_color = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
        logger.info(f"📊 DATA QUALITY SCORE: {score_color} {score}%")
        
        for metric, value in quality_score["metrics"].items():
            logger.info(f"   {metric.title()}: {value}%")
        
        if quality_score["issues"]:
            logger.warning("⚠️  QUALITY ISSUES:")
            for issue in quality_score["issues"]:
                logger.warning(f"   • {issue}")
    
    # Processing stats
    if hasattr(stats, 'rows_in'):
        logger.info("🔄 PROCESSING STATS", 
                   rows_processed=f"{stats.rows_in} → {stats.rows_out}",
                   duplicates_removed=stats.duplicates_dropped,
                   dates_corrected=stats.bad_dates)
    
    logger.info("="*60)


def main():
    """Enhanced CLI entry point for the baseline analyzer."""
    parser = argparse.ArgumentParser(
        description="Generate baseline balance snapshot with lineage tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --debug --inputs-dir data/ --snapshot-dir debug_output/
  %(prog)s --inputs-dir tests/fixtures/ --output test_baseline.csv
        """
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode with detailed snapshots"
    )
    parser.add_argument(
        "--inputs-dir", 
        default="data", 
        help="Directory containing input CSV files (default: data)"
    )
    parser.add_argument(
        "--snapshot-dir", 
        default="debug_output", 
        help="Directory for debug snapshots (default: debug_output)"
    )
    parser.add_argument(
        "--output", "-o", 
        default="baseline_snapshot.csv", 
        help="Output CSV file path (default: baseline_snapshot.csv)"
    )
    
    args = parser.parse_args()
    
    # Setup structured logging
    logger = setup_structured_logging(args.debug)
    
    logger.info("🚀 Starting baseline analyzer", 
                debug_mode=args.debug,
                inputs_dir=args.inputs_dir,
                snapshot_dir=args.snapshot_dir if args.debug else "disabled")
    
    start_time = __import__('time').time()
    
    try:
        # Run baseline analysis
        df = build_baseline(
            debug=args.debug,
            inputs_dir=args.inputs_dir,
            snapshot_dir=args.snapshot_dir
        )
        
        duration = __import__('time').time() - start_time
        
        if df.empty:
            logger.warning("⚠️  No data generated for baseline analysis")
            sys.exit(1)
        
        # Calculate quality metrics
        # Note: We need to get stats from build_baseline - for now create a mock stats object
        class MockStats:
            def __init__(self):
                self.rows_in = len(df)
                self.rows_out = len(df)
                self.duplicates_dropped = 0
                self.bad_dates = 0
        
        stats = MockStats()
        quality_score = calculate_data_quality_score(df, stats)
        
        # Save output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        # Print summary
        print_summary(logger, df, stats, quality_score, duration)
        
        logger.info("✅ Baseline snapshot saved", output_file=str(output_path.resolve()))
        
        # Exit with appropriate code based on quality
        if quality_score["overall_score"] < 70:
            logger.warning("⚠️  Low data quality score - review issues above")
            sys.exit(2)
    
    except KeyboardInterrupt:
        logger.info("❌ Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error("💥 Analysis failed", error=str(e), exc_info=args.debug)
        sys.exit(1)


if __name__ == "__main__":
    main()
