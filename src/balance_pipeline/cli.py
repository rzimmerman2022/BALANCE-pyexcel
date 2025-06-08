from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys # For sys.exit in case of critical errors
import numpy as np        #  ← add this right after the other imports

# Import from other modules in the pipeline
from .config import AnalysisConfig
from .loaders import DataLoaderV23, merge_expense_and_ledger_data, merge_rent_data
from .processing import process_expense_data, process_rent_data
from .ledger import create_master_ledger
from .recon import triple_reconciliation
from .analytics import perform_advanced_analytics, comprehensive_risk_assessment
from .viz import (
    build_design_theme,
    build_running_balance_timeline, build_waterfall_category_impact,
    build_monthly_shared_trend, build_payer_type_heatmap,
    build_calendar_heatmaps, build_treemap_shared_spending,
    build_anomaly_scatter, build_pareto_concentration,
    build_sankey_settlements, build_data_quality_table_viz
)
from .outputs import generate_all_outputs

# Configure logging for the CLI entry point
# This might be duplicative if other modules also configure basicConfig.
# Consider a central logging setup function if this becomes an issue.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler("financial_analysis_audit_pipeline.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__) # Logger for the CLI module itself

def run_analysis_pipeline(
    expense_file: Path,
    ledger_file: Path,
    rent_alloc_file: Path,
    rent_hist_file: Path,
    config: AnalysisConfig
):
    """
    Orchestrates the full financial analysis pipeline.
    """
    logger.info("Starting analysis pipeline via CLI...")
    
    # --- 0. Initialize ---
    # data_quality_issues_list will be populated by processing functions
    data_quality_issues_list = [] 
    # alt_texts for visualizations will be populated by viz functions
    alt_texts = {} 
    # validation_summary for various checks
    validation_summary = {}
    
    # Build design theme for visualizations
    # This theme object can be passed to Plotly-based visualization functions.
    # Matplotlib styling is global via plt.rcParams.
    plotly_theme = build_design_theme(logger_instance=logger)


    # --- 1. Load Data ---
    logger.info("Stage 1: Loading data...")
    loader = DataLoaderV23() # Instantiating loader from loaders.py
    expense_hist_raw = loader.load_expense_history(expense_file)
    transaction_ledger_raw = loader.load_transaction_ledger(ledger_file)
    rent_alloc_raw = loader.load_rent_allocation(rent_alloc_file)
    rent_hist_raw = loader.load_rent_history(rent_hist_file)

    data_sources_summary = loader.validate_loaded_data(
        expense_hist_raw, transaction_ledger_raw, rent_alloc_raw, rent_hist_raw
    )
    # P0 Blueprint: debug_mode Flag - Snapshot CSVs
    if config.debug_mode:
        output_dir = Path("debug_output")
        output_dir.mkdir(exist_ok=True)
        if not expense_hist_raw.empty: expense_hist_raw.to_csv(output_dir / "01a_expense_history_raw.csv", index=False)
        if not transaction_ledger_raw.empty: transaction_ledger_raw.to_csv(output_dir / "01b_transaction_ledger_raw.csv", index=False)
        if not rent_alloc_raw.empty: rent_alloc_raw.to_csv(output_dir / "01c_rent_allocation_raw.csv", index=False)
        if not rent_hist_raw.empty: rent_hist_raw.to_csv(output_dir / "01d_rent_history_raw.csv", index=False)
        logger.info("Debug mode: Raw data snapshots saved to debug_output/")

    if expense_hist_raw.empty and transaction_ledger_raw.empty:
        logger.error("Critical: Both Expense History and Transaction Ledger are empty. Aborting.")
        # Consider how to handle this error gracefully, e.g., specific exit code or exception
        raise ValueError("Critical expense data sources are missing.")

    # --- 2. Merge Raw Feeds ---
    logger.info("Stage 2: Merging raw data feeds...")
    merged_expenses_ledger = merge_expense_and_ledger_data(expense_hist_raw, transaction_ledger_raw)
    merged_rent_data_full = merge_rent_data(rent_alloc_raw, rent_hist_raw) # Contains budget info

    if config.debug_mode:
        if not merged_expenses_ledger.empty: merged_expenses_ledger.to_csv(output_dir / "02a_merged_expenses_ledger.csv", index=False)
        if not merged_rent_data_full.empty: merged_rent_data_full.to_csv(output_dir / "02b_merged_rent_data_full.csv", index=False)
        logger.info("Debug mode: Merged data snapshots saved.")

    # --- 3. Process Data (Apply Business Logic) ---
    logger.info("Stage 3: Processing data...")
    processed_expenses = process_expense_data(merged_expenses_ledger, config, data_quality_issues_list, logger_instance=logger)
    processed_rent = process_rent_data(merged_rent_data_full, config, data_quality_issues_list, logger_instance=logger)

    if config.debug_mode:
        if not processed_expenses.empty: processed_expenses.to_csv(output_dir / "03a_processed_expenses.csv", index=False)
        if not processed_rent.empty: processed_rent.to_csv(output_dir / "03b_processed_rent.csv", index=False)
        logger.info("Debug mode: Processed data snapshots saved.")

    # --- 4. Build Master Ledger ---
    logger.info("Stage 4: Building master ledger...")
    master_ledger_df = create_master_ledger(processed_rent, processed_expenses, config, logger_instance=logger)
    
    if config.debug_mode and not master_ledger_df.empty:
        master_ledger_df.to_csv(output_dir / "04_master_ledger.csv", index=False)
        logger.info("Debug mode: Master ledger snapshot saved.")

    # --- 5. Reconciliation & Analytics ---
    logger.info("Stage 5: Performing reconciliation and analytics...")
    reconciliation_results = triple_reconciliation(master_ledger_df, config, logger_instance=logger)
    
    # Perform validation against ledger if data available
    if not transaction_ledger_raw.empty and "Running Balance" in transaction_ledger_raw.columns:
        ledger_final_balance = transaction_ledger_raw["Running Balance"].iloc[-1] if not transaction_ledger_raw.empty else 0.0
        master_final_balance = master_ledger_df["RunningBalance"].iloc[-1] if not master_ledger_df.empty else 0.0
        diff = abs(ledger_final_balance - master_final_balance)
        validation_summary["ledger_balance_match"] = "Matched" if diff <= 0.015 else f"Mismatch (Diff: ${diff:,.2f})"
    else:
        validation_summary["ledger_balance_match"] = "Skipped - No Ledger Data"
    validation_summary["reconciliation_match_strict"] = reconciliation_results.get("reconciled", False)


    # Pass processed_rent_df to analytics for rent budget analysis
    analytics_results = perform_advanced_analytics(master_ledger_df, processed_rent, config, logger_instance=logger)
    analytics_results["data_sources_summary"] = data_sources_summary # Add this for reporting
    analytics_results["validation_summary"] = validation_summary # Add validation summary for reporting

    risk_assessment_results = comprehensive_risk_assessment(master_ledger_df, analytics_results, validation_summary, config, logger_instance=logger)

    # --- 6. Generate Visualizations ---
    logger.info("Stage 6: Generating visualizations...")
    # This part will call individual viz functions from viz.py
    # The main `EnhancedSharedExpenseAnalyzer` class used to store `alt_texts` and `visualizations` paths.
    # We'll need a similar mechanism here or pass these dicts around.
    
    visualizations_paths: Dict[str, str] = {} # Store paths to generated viz files

    # Example calls (these will need the data and config they depend on)
    # Some visualizations might depend on analytics_results too.
    if not master_ledger_df.empty:
        try:
            path, alt = build_running_balance_timeline(master_ledger_df.copy(), config, Path("analysis_output"), logger)
            visualizations_paths["running-balance-timeline"] = str(path); alt_texts["running-balance-timeline"] = alt
        except Exception as e: logger.error(f"Failed running balance timeline viz: {e}", exc_info=True)
        
        try:
            path, alt = build_waterfall_category_impact(master_ledger_df.copy(), config, Path("analysis_output"), plotly_theme, logger)
            visualizations_paths["waterfall-category-impact"] = str(path); alt_texts["waterfall-category-impact"] = alt
        except Exception as e: logger.error(f"Failed waterfall viz: {e}", exc_info=True)

        # Add calls for other visualizations, ensuring they get correct data and config
        # build_monthly_shared_trend needs analytics_results
        if "monthly_shared_spending_trend" in analytics_results:
            try:
                path, alt = build_monthly_shared_trend(analytics_results, Path("analysis_output"), logger)
                visualizations_paths["monthly-shared-trend"] = str(path); alt_texts["monthly-shared-trend"] = alt
            except Exception as e: logger.error(f"Failed monthly trend viz: {e}", exc_info=True)

        # ... other visualization calls ...
        # build_payer_type_heatmap, build_calendar_heatmaps, etc.
        # Ensure they are called correctly with their specific data dependencies.
        # For P0, we might not implement all viz calls here immediately but focus on structure.
        logger.info(f"Generated {len(visualizations_paths)} visualizations.")
    else:
        logger.warning("Master ledger is empty, skipping visualization generation.")


    # --- 7. Generate Outputs ---
    logger.info("Stage 7: Generating output reports...")
    # The generate_all_outputs function will take all necessary data and paths.
    # It needs the populated data_quality_issues_list and alt_texts.
    
    # Recommendations are typically generated based on analytics and risk assessment
    # This logic might live in analytics.py or be a separate recommendations.py module.
    # For now, placeholder:
    recommendations_list = [f"Final Balance: {reconciliation_results.get('who_owes_whom','N/A')} ${reconciliation_results.get('amount_owed',0):.2f}"]
    if not reconciliation_results.get('reconciled', True):
        recommendations_list.append("CRITICAL: Triple reconciliation failed!")

    output_file_paths = generate_all_outputs(
        master_ledger=master_ledger_df,
        reconciliation_results=reconciliation_results,
        analytics_results=analytics_results, # This should contain data_sources_summary and validation_summary
        risk_assessment=risk_assessment_results,
        recommendations=recommendations_list,
        visualizations=visualizations_paths,
        alt_texts=alt_texts,
        data_quality_issues=data_quality_issues_list,
        config=config,
        output_dir_path_str="analysis_output", # Default output directory
        logger_instance=logger
    )
    
    logger.info("Analysis pipeline completed successfully.")
    logger.info(f"Output files generated in: {Path('analysis_output').resolve()}")
    for name, path_str in output_file_paths.items():
        logger.info(f"  - {name}: {Path(path_str).name}")
    
    # Log key final results
    logger.info("=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info(f"  Who Owes Whom: {reconciliation_results.get('who_owes_whom', 'N/A')}")
    logger.info(f"  Amount Owed: ${reconciliation_results.get('amount_owed', 0):,.2f}")
    logger.info(f"  Data Quality Score: {analytics_results.get('data_quality_score', 0.0):.1f}%") # Assuming DQ score is in analytics
    logger.info(f"  Overall Risk Level: {risk_assessment_results.get('overall_risk_level', 'N/A')}")
    logger.info("=" * 80)


def main_cli():
    parser = argparse.ArgumentParser(description="BALANCE-pyexcel Shared Expense Analyzer (Pipeline v0.1)")
    parser.add_argument("--expense", type=Path, default=Path("data/Expense_History_20250527.csv"), help="Path to expense history CSV.")
    parser.add_argument("--ledger", type=Path, default=Path("data/Transaction_Ledger_20250527.csv"), help="Path to transaction ledger CSV.")
    parser.add_argument("--rent", type=Path, default=Path("data/Rent_Allocation_20250527.csv"), help="Path to rent allocation CSV.")
    parser.add_argument("--rent-hist", type=Path, default=Path("data/Rent_History_20250527.csv"), help="Path to rent history CSV.")
    
    # Config overrides
    parser.add_argument("--ryan_pct", type=float, help="Ryan's percentage (e.g., 0.43)")
    parser.add_argument("--jordyn_pct", type=float, help="Jordyn's percentage (e.g., 0.57)")
    parser.add_argument("--rent_baseline", type=float, help="Baseline monthly rent amount")
    parser.add_argument("--debug_mode", action="store_true", help="Enable debug mode for snapshot CSVs.")
    # Add other config params as needed

    args = parser.parse_args()

    config = AnalysisConfig()
    if args.ryan_pct is not None: config.RYAN_PCT = args.ryan_pct
    if args.jordyn_pct is not None: config.JORDYN_PCT = args.jordyn_pct
    if args.rent_baseline is not None: config.RENT_BASELINE = args.rent_baseline
    if args.debug_mode: config.debug_mode = True
    
    if not np.isclose(config.RYAN_PCT + config.JORDYN_PCT, 1.0):
        logger.critical("Configuration Error: Ryan's and Jordyn's percentages do not sum to 1.0. Aborting.")
        sys.exit(1)

    files_to_check = [
        (args.expense, "Expense History"), (args.ledger, "Transaction Ledger"),
        (args.rent, "Rent Allocation"), (args.rent_hist, "Rent History")
    ]
    all_files_found = True
    for file_path, file_name in files_to_check:
        if not file_path.exists():
            logger.error(f"{file_name} file not found: {file_path.resolve()}")
            all_files_found = False
    if not all_files_found:
        logger.critical("One or more required data files were not found. Aborting.")
        sys.exit(1)
    
    logger.info(f"Using configuration: {config}")
    logger.info(f"Debug mode: {'ON' if config.debug_mode else 'OFF'}")

    try:
        run_analysis_pipeline(
            expense_file=args.expense,
            ledger_file=args.ledger,
            rent_alloc_file=args.rent,
            rent_hist_file=args.rent_hist,
            config=config
        )
    except ValueError as ve: # Catch specific errors like missing critical data
        logger.critical(f"CLI Aborted - Value Error: {ve}", exc_info=True)
        sys.exit(1)
    except FileNotFoundError as fnfe: # Should be caught by pre-check
        logger.critical(f"CLI Aborted - File Not Found: {fnfe}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.critical(f"CLI Aborted - Unexpected error in pipeline: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main_cli()
