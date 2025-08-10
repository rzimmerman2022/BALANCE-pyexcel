#!/usr/bin/env python3
###############################################################################
# BALANCE-pyexcel – Enhanced Shared Expense Analyzer (Refactored Orchestrator)
#
# Description : Orchestrates the financial analysis pipeline using modular components.
# Author      : Cline - Refactored from original by Financial Analysis System
# Date        : 2025-06-08
# Version     : 3.0 (Modular)
###############################################################################

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil  # For performance checking

from src.balance_pipeline.analytics import (
    _calculate_data_quality_score,  # Make it public or call via perform_advanced_analytics
    _summarize_data_quality_issues,  # Make it public or call via perform_advanced_analytics
    comprehensive_risk_assessment,
    perform_advanced_analytics,
)

# --- Pipeline Module Imports ---
from src.balance_pipeline.config import (
    AnalysisConfig,  # DataQualityFlag might be used for typing if needed
)
from src.balance_pipeline.ledger import create_master_ledger
from src.balance_pipeline.loaders import (
    DataLoaderV23,
    merge_expense_and_ledger_data,
    merge_rent_data,
)

# Other viz functions can be imported if called directly
from src.balance_pipeline.outputs import generate_all_outputs
from src.balance_pipeline.processing import process_expense_data, process_rent_data
from src.balance_pipeline.recon import triple_reconciliation
from src.balance_pipeline.viz import (
    build_anomaly_scatter,
    build_calendar_heatmaps,
    build_data_quality_table_viz,
    build_design_theme,
    build_monthly_shared_trend,
    build_pareto_concentration,
    build_payer_type_heatmap,
    build_running_balance_timeline,
    build_sankey_settlements,
    build_treemap_shared_spending,
    build_waterfall_category_impact,
)

# Configure logging for this orchestrator module
# Note: cli.py also configures logging. This ensures logs are captured if analyzer.py is imported.
# A more advanced setup might use a shared logging configuration utility.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler("financial_analysis_orchestrator.log", mode="w"), # Separate log for orchestrator
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

class EnhancedSharedExpenseAnalyzer:
    """
    Orchestrates the comprehensive financial analysis pipeline by calling
    modular components for loading, processing, reconciliation, analytics,
    visualization, and output generation.
    """

    def __init__(
        self,
        expense_file: Path,
        ledger_file: Path,
        rent_alloc_file: Path,
        rent_hist_file: Path,
        config: AnalysisConfig | None = None,
    ):
        self.config = config or AnalysisConfig()
        self.expense_file = expense_file
        self.ledger_file = ledger_file
        self.rent_alloc_file = rent_alloc_file
        self.rent_hist_file = rent_hist_file

        # These lists/dicts will be populated during the pipeline execution
        self.data_quality_issues: list[dict[str, Any]] = []
        self.alt_texts: dict[str, str] = {}
        self.validation_summary: dict[str, Any] = {} # For checks like ledger balance match

        self.start_time = datetime.now(UTC)
        self.memory_usage_mb = 0

        logger.info(f"Initialized EnhancedSharedExpenseAnalyzer (Orchestrator) with config: {self.config}")
        logger.info(f"Debug mode is: {'ON' if self.config.debug_mode else 'OFF'}")
        
        # File existence checks (can also be done by the CLI before instantiation)
        for file_path, file_name in [
            (self.expense_file, "Expense History"), (self.ledger_file, "Transaction Ledger"),
            (self.rent_alloc_file, "Rent Allocation"), (self.rent_hist_file, "Rent History"),
        ]:
            if not file_path.exists():
                logger.error(f"{file_name} file not found: {file_path.resolve()}")
                raise FileNotFoundError(f"{file_name} file not found: {file_path.resolve()}")

    def _check_performance(self):
        """Logs processing time and memory usage."""
        elapsed_seconds = (datetime.now(UTC) - self.start_time).total_seconds()
        if elapsed_seconds > self.config.MAX_PROCESSING_TIME_SECONDS:
            logger.warning(
                f"Processing time ({elapsed_seconds:.1f}s) EXCEEDED limit ({self.config.MAX_PROCESSING_TIME_SECONDS}s)."
            )
        try:
            process = psutil.Process()
            self.memory_usage_mb = process.memory_info().rss / (1024 * 1024)
            if self.memory_usage_mb > self.config.MAX_MEMORY_MB:
                logger.warning(
                    f"Memory usage ({self.memory_usage_mb:.1f}MB) EXCEEDED limit ({self.config.MAX_MEMORY_MB}MB)."
                )
        except Exception as e:
            logger.error(f"Could not get memory usage: {e}", exc_info=True)
            self.memory_usage_mb = -1 # Indicate error
        logger.info(f"Performance Check: Time={elapsed_seconds:.2f}s, Memory={self.memory_usage_mb:.2f}MB")

    def analyze(self) -> dict[str, Any]:
        """
        Executes the full analysis pipeline by calling modular functions.
        """
        logger.info("Starting analysis pipeline orchestration...")
        
        # --- 0. Initialization ---
        plotly_theme = build_design_theme(logger_instance=logger)
        output_debug_dir = Path("debug_output")
        if self.config.debug_mode:
            output_debug_dir.mkdir(exist_ok=True)
            logger.info(f"Debug mode enabled. Snapshot CSVs will be saved to: {output_debug_dir.resolve()}")

        # --- 1. Load Data ---
        logger.info("--- Stage 1: Loading Data ---")
        loader = DataLoaderV23()
        expense_hist_raw = loader.load_expense_history(self.expense_file)
        transaction_ledger_raw = loader.load_transaction_ledger(self.ledger_file)
        rent_alloc_raw = loader.load_rent_allocation(self.rent_alloc_file)
        rent_hist_raw = loader.load_rent_history(self.rent_hist_file)

        data_sources_summary = loader.validate_loaded_data(
            expense_hist_raw, transaction_ledger_raw, rent_alloc_raw, rent_hist_raw
        )
        if self.config.debug_mode:
            if not expense_hist_raw.empty: expense_hist_raw.to_csv(output_debug_dir / "01a_expense_history_raw.csv", index=False)
            if not transaction_ledger_raw.empty: transaction_ledger_raw.to_csv(output_debug_dir / "01b_transaction_ledger_raw.csv", index=False)
            if not rent_alloc_raw.empty: rent_alloc_raw.to_csv(output_debug_dir / "01c_rent_allocation_raw.csv", index=False)
            if not rent_hist_raw.empty: rent_hist_raw.to_csv(output_debug_dir / "01d_rent_history_raw.csv", index=False)
            logger.info("Debug mode: Raw data snapshots saved.")

        if expense_hist_raw.empty and transaction_ledger_raw.empty:
            logger.error("Critical data missing: Both Expense History and Transaction Ledger are empty.")
            raise ValueError("Critical expense data sources are missing. Cannot proceed.")

        # --- 2. Merge Raw Feeds ---
        logger.info("--- Stage 2: Merging Raw Data Feeds ---")
        merged_expenses_ledger = merge_expense_and_ledger_data(expense_hist_raw, transaction_ledger_raw)
        merged_rent_data_full = merge_rent_data(rent_alloc_raw, rent_hist_raw)
        if self.config.debug_mode:
            if not merged_expenses_ledger.empty: merged_expenses_ledger.to_csv(output_debug_dir / "02a_merged_expenses_ledger.csv", index=False)
            if not merged_rent_data_full.empty: merged_rent_data_full.to_csv(output_debug_dir / "02b_merged_rent_data_full.csv", index=False)
            logger.info("Debug mode: Merged data snapshots saved.")

        # --- 3. Process Data (Apply Business Logic) ---
        logger.info("--- Stage 3: Processing Data ---")
        # self.data_quality_issues list is passed to processing functions to be populated
        processed_expenses = process_expense_data(merged_expenses_ledger, self.config, self.data_quality_issues, logger_instance=logger)
        processed_rent = process_rent_data(merged_rent_data_full, self.config, self.data_quality_issues, logger_instance=logger)
        if self.config.debug_mode:
            if not processed_expenses.empty: processed_expenses.to_csv(output_debug_dir / "03a_processed_expenses.csv", index=False)
            if not processed_rent.empty: processed_rent.to_csv(output_debug_dir / "03b_processed_rent.csv", index=False)
            logger.info("Debug mode: Processed data snapshots saved.")

        # --- 4. Build Master Ledger ---
        logger.info("--- Stage 4: Building Master Ledger ---")
        master_ledger_df = create_master_ledger(processed_rent, processed_expenses, self.config, logger_instance=logger)
        if self.config.debug_mode and not master_ledger_df.empty:
            master_ledger_df.to_csv(output_debug_dir / "04_master_ledger.csv", index=False)
            logger.info("Debug mode: Master ledger snapshot saved.")
        
        if master_ledger_df.empty:
            logger.warning("Master ledger is empty after build. Analysis will be limited.")
            # Allow to proceed, downstream functions should handle empty DFs gracefully.

        # --- 5. Reconciliation & Analytics ---
        logger.info("--- Stage 5: Performing Reconciliation and Analytics ---")
        reconciliation_results = triple_reconciliation(master_ledger_df, self.config, logger_instance=logger)
        
        # Ledger balance validation (populates self.validation_summary)
        if not transaction_ledger_raw.empty and "Running Balance" in transaction_ledger_raw.columns and not transaction_ledger_raw["Running Balance"].isna().all():
            ledger_final_balance = transaction_ledger_raw["Running Balance"].iloc[-1]
            master_final_balance = master_ledger_df["RunningBalance"].iloc[-1] if not master_ledger_df.empty and "RunningBalance" in master_ledger_df.columns else 0.0
            diff = abs(ledger_final_balance - master_final_balance)
            self.validation_summary["ledger_balance_match"] = "Matched" if diff <= 0.015 else f"Mismatch (Diff: ${diff:,.2f})"
        else:
            self.validation_summary["ledger_balance_match"] = "Skipped - No/Invalid Ledger Data for comparison"
        self.validation_summary["reconciliation_match_strict"] = reconciliation_results.get("reconciled", False)
        
        analytics_results = perform_advanced_analytics(master_ledger_df, processed_rent, self.config, logger_instance=logger)
        analytics_results["data_sources_summary"] = data_sources_summary # Include summary of loaded data
        analytics_results["validation_summary"] = self.validation_summary # Include validation checks
        # Add DQ score and summary to analytics_results for reporting
        analytics_results["data_quality_score"] = _calculate_data_quality_score(master_ledger_df, logger_instance=logger)
        analytics_results["data_quality_issues_summary"] = _summarize_data_quality_issues(master_ledger_df)

        risk_assessment_results = comprehensive_risk_assessment(master_ledger_df, analytics_results, self.validation_summary, self.config, logger_instance=logger)

        # --- 6. Generate Visualizations ---
        logger.info("--- Stage 6: Generating Visualizations ---")
        visualizations_paths: dict[str, str] = {}
        output_viz_dir = Path("analysis_output") # Visualizations are saved here by default
        output_viz_dir.mkdir(exist_ok=True)

        if not master_ledger_df.empty:
            # Call individual visualization functions from viz.py
            # Example:
            try:
                path, alt = build_running_balance_timeline(master_ledger_df.copy(), self.config, output_viz_dir, logger)
                visualizations_paths["running-balance-timeline"] = str(path); self.alt_texts["running-balance-timeline"] = alt
            except Exception as e: logger.error(f"Failed to generate 'running-balance-timeline': {e}", exc_info=True)
            
            try:
                path, alt = build_waterfall_category_impact(master_ledger_df.copy(), self.config, output_viz_dir, plotly_theme, logger)
                visualizations_paths["waterfall-category-impact"] = str(path); self.alt_texts["waterfall-category-impact"] = alt
            except Exception as e: logger.error(f"Failed to generate 'waterfall-category-impact': {e}", exc_info=True)

            if "monthly_shared_spending_trend" in analytics_results:
                 try:
                    path, alt = build_monthly_shared_trend(analytics_results, output_viz_dir, logger)
                    visualizations_paths["monthly-shared-trend"] = str(path); self.alt_texts["monthly-shared-trend"] = alt
                 except Exception as e: logger.error(f"Failed to generate 'monthly-shared-trend': {e}", exc_info=True)
            
            try:
                path, alt = build_payer_type_heatmap(master_ledger_df.copy(), output_viz_dir, plotly_theme, logger)
                visualizations_paths["payer-type-heatmap"] = str(path); self.alt_texts["payer-type-heatmap"] = alt
            except Exception as e: logger.error(f"Failed to generate 'payer-type-heatmap': {e}", exc_info=True)

            try:
                calendar_viz_paths = build_calendar_heatmaps(master_ledger_df.copy(), output_viz_dir, logger)
                for k, (p_val, a_val) in calendar_viz_paths.items():
                     visualizations_paths[f"calendar-heatmap-{k}"] = str(p_val); self.alt_texts[f"calendar-heatmap-{k}"] = a_val
            except Exception as e: logger.error(f"Failed to generate 'calendar-heatmaps': {e}", exc_info=True)
            
            try:
                path, alt = build_treemap_shared_spending(master_ledger_df.copy(), self.config, output_viz_dir, plotly_theme, logger)
                visualizations_paths["treemap-shared-spending"] = str(path); self.alt_texts["treemap-shared-spending"] = alt
            except Exception as e: logger.error(f"Failed to generate 'treemap-shared-spending': {e}", exc_info=True)

            try:
                path, alt = build_anomaly_scatter(master_ledger_df.copy(), output_viz_dir, logger)
                visualizations_paths["anomaly-scatter"] = str(path); self.alt_texts["anomaly-scatter"] = alt
            except Exception as e: logger.error(f"Failed to generate 'anomaly-scatter': {e}", exc_info=True)

            try:
                path, alt = build_pareto_concentration(master_ledger_df.copy(), self.config, output_viz_dir, logger)
                visualizations_paths["pareto-concentration"] = str(path); self.alt_texts["pareto-concentration"] = alt
            except Exception as e: logger.error(f"Failed to generate 'pareto-concentration': {e}", exc_info=True)
            
            try:
                path, alt = build_sankey_settlements(master_ledger_df.copy(), self.config, output_viz_dir, plotly_theme, logger)
                visualizations_paths["sankey-settlements"] = str(path); self.alt_texts["sankey-settlements"] = alt
            except Exception as e: logger.error(f"Failed to generate 'sankey-settlements': {e}", exc_info=True)

            try:
                path, alt = build_data_quality_table_viz(master_ledger_df.copy(), output_viz_dir, plotly_theme, logger)
                visualizations_paths["data-quality-table-viz"] = str(path); self.alt_texts["data-quality-table-viz"] = alt
            except Exception as e: logger.error(f"Failed to generate 'data-quality-table-viz': {e}", exc_info=True)

            logger.info(f"Attempted generation of {len(visualizations_paths)} visualizations.")
        else:
            logger.warning("Master ledger is empty, skipping visualization generation.")

        # --- 7. Generate Outputs ---
        logger.info("--- Stage 7: Generating Output Reports ---")
        # Placeholder for recommendations - ideally, this would be a more sophisticated generation
        recommendations_list = [f"Final Balance: {reconciliation_results.get('who_owes_whom','N/A')} ${reconciliation_results.get('amount_owed',0):.2f}"]
        if not reconciliation_results.get('reconciled', True): 
            recommendations_list.append("CRITICAL: Triple reconciliation failed! Review data and calculations.")
        if self.validation_summary.get("ledger_balance_match") != "Matched" and \
           self.validation_summary.get("ledger_balance_match") != "Skipped - No/Invalid Ledger Data for comparison":
            recommendations_list.append(f"CRITICAL: Ledger balance mismatch: {self.validation_summary['ledger_balance_match']}")
        
        # Add risk-based recommendations
        for risk_detail in risk_assessment_results.get("details", []):
            if risk_detail.get("level") in ["HIGH", "MEDIUM"]:
                recommendations_list.append(f"Risk ({risk_detail.get('risk_type')} - {risk_detail.get('level')}): {risk_detail.get('assessment')}")


        output_file_paths = generate_all_outputs(
            master_ledger=master_ledger_df,
            reconciliation_results=reconciliation_results,
            analytics_results=analytics_results,
            risk_assessment=risk_assessment_results,
            recommendations=recommendations_list,
            visualizations=visualizations_paths,
            alt_texts=self.alt_texts,
            data_quality_issues=self.data_quality_issues,
            config=self.config,
            output_dir_path_str="analysis_output", # Default, can be configured
            logger_instance=logger
        )
        
        self._check_performance() # Log final performance

        final_results_package = {
            "reconciliation": reconciliation_results,
            "analytics": analytics_results,
            "risk_assessment": risk_assessment_results,
            "recommendations": recommendations_list,
            "output_paths": output_file_paths,
            "performance_metrics": {
                "processing_time_seconds": round((datetime.now(UTC) - self.start_time).total_seconds(), 2),
                "memory_usage_mb": round(self.memory_usage_mb, 2),
                "total_transactions_in_master_ledger": len(master_ledger_df) if not master_ledger_df.empty else 0,
            }
        }
        logger.info("Analysis pipeline orchestration completed.")
        return final_results_package

# Note: The original main() function and TestEnhancedAnalyzer class have been removed.
# The primary entry point is now src/balance_pipeline/cli.py `main_cli()`.
# This analyzer.py file, if run directly, would need its own `if __name__ == "__main__":` block
# to instantiate and run the EnhancedSharedExpenseAnalyzer, similar to how cli.py does.
# For now, it's intended to be imported and used by cli.py or other scripts.
