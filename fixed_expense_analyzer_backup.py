#!/usr/bin/env python3

"""
Enhanced Shared Expense Analyzer - Institutional Grade (FIXED VERSION)
=====================================================
Fortune 500 / Big 4 standard financial reconciliation system with
comprehensive data quality management, triple reconciliation, and
production-ready features.

Author: Financial Analysis System
Date: 2025-05-27
Version: 2.1 (Fixed)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import unittest
from dataclasses import dataclass
from enum import Enum

# Configure logging for audit trail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('financial_analysis_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class AnalysisConfig:
    """Configuration parameters for the analysis"""
    RYAN_PCT: float = 0.43
    JORDYN_PCT: float = 0.57
    CONFIDENCE_LEVEL: float = 0.95
    DATA_QUALITY_THRESHOLD: float = 0.95
    OUTLIER_THRESHOLD: float = 5000.0
    RENT_BASELINE: float = 2100.0
    RENT_VARIANCE_THRESHOLD: float = 0.10
    LIQUIDITY_STRAIN_THRESHOLD: float = 5000.0
    LIQUIDITY_STRAIN_DAYS: int = 60
    CONCENTRATION_RISK_THRESHOLD: float = 0.40
    CURRENCY_PRECISION: int = 2
    MAX_MEMORY_MB: int = 500
    MAX_PROCESSING_TIME_SECONDS: int = 5

class DataQualityFlag(Enum):
    """Enumeration of data quality issues"""
    CLEAN = "CLEAN"
    MISSING_DATE = "MISSING_DATE"
    MISALIGNED_ROW = "MISALIGNED_ROW"
    DUPLICATE_SUSPECTED = "DUPLICATE_SUSPECTED"
    OUTLIER_AMOUNT = "OUTLIER_AMOUNT"
    MANUAL_CALCULATION_NOTE = "MANUAL_CALCULATION_NOTE"
    NEGATIVE_AMOUNT = "NEGATIVE_AMOUNT"
    RENT_VARIANCE_HIGH = "RENT_VARIANCE_HIGH"
    MISSING_ALLOWED_AMOUNT = "MISSING_ALLOWED_AMOUNT"

class EnhancedSharedExpenseAnalyzer:
    """
    Comprehensive financial analyzer implementing institutional-grade standards
    for shared expense reconciliation with full audit trail and risk assessment.
    """
    
    def __init__(self, rent_file: Path, expense_file: Path, config: AnalysisConfig = None):
        """
        Initialize the analyzer with configuration and file paths
        
        Args:
            rent_file: Path to rent allocation CSV
            expense_file: Path to expense history CSV
            config: Analysis configuration (uses defaults if None)
        """
        self.config = config or AnalysisConfig()
        self.rent_file = rent_file
        self.expense_file = expense_file
        
        # Initialize tracking
        self.data_quality_issues: List[Dict[str, Any]] = []
        self.audit_trail: List[Dict[str, Any]] = []
        self.validation_results: Dict[str, bool] = {}
        
        # Performance tracking
        self.start_time = datetime.now(timezone.utc)
        self.memory_usage_mb = 0
        
        logger.info(f"Initialized analyzer with config: {self.config}")
        
    def analyze(self) -> Dict[str, Any]:
        """Execute comprehensive analysis pipeline"""
        try:
            # 1. Load and clean data with quality tracking
            logger.info("Loading data files...")
            rent_df = self._load_and_clean_rent_data()
            expense_df = self._load_and_clean_expense_data()
            
            # 2. Create master ledger with full audit columns
            logger.info("Creating master ledger...")
            master_ledger = self._create_master_ledger(rent_df, expense_df)
            
            # 3. Perform triple reconciliation
            logger.info("Performing triple reconciliation...")
            reconciliation_results = self._triple_reconciliation(master_ledger)
            
            # 4. Advanced analytics
            logger.info("Running advanced analytics...")
            analytics_results = self._perform_advanced_analytics(master_ledger)
            
            # 5. Risk assessment
            logger.info("Assessing risks...")
            risk_assessment = self._comprehensive_risk_assessment(master_ledger, analytics_results)
            
            # 6. Generate visualizations
            logger.info("Creating visualizations...")
            visualizations = self._create_visualizations(master_ledger, analytics_results, reconciliation_results)
            
            # 7. Formulate recommendations
            logger.info("Generating recommendations...")
            recommendations = self._generate_recommendations(
                analytics_results, risk_assessment, reconciliation_results
            )
            
            # 8. Validate results
            logger.info("Validating results...")
            self._validate_results(reconciliation_results, master_ledger)
            
            # 9. Generate outputs
            logger.info("Generating output files...")
            output_paths = self._generate_outputs(
                master_ledger, reconciliation_results, analytics_results,
                risk_assessment, recommendations, visualizations
            )
            
            # Performance check
            self._check_performance()
            
            return {
                'reconciliation': reconciliation_results,
                'analytics': analytics_results,
                'risk_assessment': risk_assessment,
                'recommendations': recommendations,
                'data_quality_score': self._calculate_data_quality_score(master_ledger),
                'validation_results': self.validation_results,
                'output_paths': output_paths,
                'performance_metrics': {
                    'processing_time_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds(),
                    'memory_usage_mb': self.memory_usage_mb,
                    'total_transactions': len(master_ledger)
                }
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            raise
    
    def _load_and_clean_rent_data(self) -> pd.DataFrame:
        """Load and clean rent data with comprehensive quality checks"""
        df = pd.read_csv(self.rent_file)
        df.columns = df.columns.str.strip()
        
        # Track original row count
        original_count = len(df)
        
        # Clean monetary columns
        money_cols = ['Gross Total', "Ryan's Rent (43%)", "Jordyn's Rent (57%)"]
        for col in money_cols:
            if col in df.columns:
                df[col] = self._clean_money(df[col])
        
        # Parse dates
        df['Date'] = pd.to_datetime(df['Month'], errors='coerce')
        
        # Data quality checks
        for idx, row in df.iterrows():
            quality_flags = []
            
            # Check for missing date
            if pd.isna(row['Date']):
                quality_flags.append(DataQualityFlag.MISSING_DATE)
                df.loc[idx, 'Date'] = self._impute_missing_date(df, idx)
            
            # Check rent variance
            gross_total_val = row['Gross Total']
            if pd.notna(gross_total_val) and isinstance(gross_total_val, (int, float)):
                variance = abs(gross_total_val - self.config.RENT_BASELINE) / self.config.RENT_BASELINE
                if variance > self.config.RENT_VARIANCE_THRESHOLD:
                    quality_flags.append(DataQualityFlag.RENT_VARIANCE_HIGH)
            
            # Add quality flag column
            df.loc[idx, 'DataQualityFlag'] = ','.join([flag.value for flag in quality_flags]) or DataQualityFlag.CLEAN.value
            
            # Log issues
            if quality_flags:
                self._log_data_quality_issue('rent', idx, row.to_dict(), quality_flags)
        
        # Add audit columns
        df['TransactionType'] = 'RENT'
        df['Payer'] = 'Jordyn'
        df['IsShared'] = True
        df['AllowedAmount'] = pd.to_numeric(df['Gross Total'], errors='coerce').fillna(0)
        df["Ryan's Rent (43%)"] = pd.to_numeric(df["Ryan's Rent (43%)"], errors='coerce').fillna(0)
        df['RyanOwes'] = df["Ryan's Rent (43%)"]
        df['JordynOwes'] = 0.0
        df['BalanceImpact'] = pd.to_numeric(df['RyanOwes'], errors='coerce').fillna(0)
        
        # Create audit note
        def create_rent_audit_note(row):
            try:
                gross_total_float = float(row['Gross Total']) if pd.notna(row['Gross Total']) else 0.0
                ryan_owes_float = float(row['RyanOwes']) if pd.notna(row['RyanOwes']) else 0.0
                note = f"Rent payment of ${gross_total_float:.2f} by Jordyn. " \
                       f"Ryan owes 43% (${ryan_owes_float:.2f}). " \
                       f"Data Quality: {row['DataQualityFlag']}"
            except (ValueError, TypeError):
                note = f"Rent payment data unprocessable. Data Quality: {row['DataQualityFlag']}"
            return note

        df['AuditNote'] = df.apply(create_rent_audit_note, axis=1)
        
        logger.info(f"Loaded {len(df)} rent records from {original_count} original rows")
        return df
    
    def _load_and_clean_expense_data(self) -> pd.DataFrame:
        """Load and clean expense data with comprehensive quality checks"""
        df = pd.read_csv(self.expense_file)
        df.columns = df.columns.str.strip()

        # Standardize column names - handle the space in 'Allowed Amount' and 'Actual Amount'
        column_mapping = {
            'Allowed Amount': 'AllowedAmount',
            'Actual Amount': 'ActualAmount'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Remove unnamed columns
        df = df[[col for col in df.columns if not col.lower().startswith('unnamed')]]
        
        # Filter empty rows and header-like rows
        df = df[df['Name'].notna() & (df['Name'] != '') & ~df['Name'].str.contains('September', na=False)]
        
        # Track which entries had "$ -" (explicitly marked as personal)
        explicitly_personal = df['AllowedAmount'].astype(str).str.strip().str.match(r'^\$\s*-\s*
        
        # Clean monetary columns
        df['ActualAmount'] = pd.to_numeric(self._clean_money(df['ActualAmount']), errors='coerce')
        
        # Handle AllowedAmount column - respect explicit "$ -" as personal expenses
        if 'AllowedAmount' not in df.columns:
            logger.warning("'AllowedAmount' column missing in expense data. Creating based on ActualAmount.")
            df['AllowedAmount'] = df['ActualAmount']
        else:
            # First clean the AllowedAmount column
            df['AllowedAmount'] = pd.to_numeric(self._clean_money(df['AllowedAmount']), errors='coerce')
            
            # For explicitly personal items (marked with "$ -"), keep as 0
            df.loc[explicitly_personal, 'AllowedAmount'] = 0
            
            # FIX #1: Fill truly blank AllowedAmount with ActualAmount (treating blanks as fully shared)
            # But NOT for items explicitly marked as personal with "$ -"
            mask_to_fill = originally_blank_allowed & ~explicitly_personal
            df.loc[mask_to_fill, 'AllowedAmount'] = df.loc[mask_to_fill, 'ActualAmount']
        
        # Parse dates
        df['Date'] = pd.to_datetime(df['Date of Purchase'], format='%m/%d/%Y', errors='coerce')

        # Ensure 'Description' column exists
        if 'Description' not in df.columns:
            df['Description'] = ""
        else:
            df['Description'] = df['Description'].fillna("")

        # Calculate personal portion
        df["PersonalPortion"] = (df["ActualAmount"] - df["AllowedAmount"]).round(self.config.CURRENCY_PRECISION)

        # Create clear explanations
        who_paid = df["Name"]
        actual = df["ActualAmount"].map("${:,.2f}".format)
        allowed = df["AllowedAmount"].map("${:,.2f}".format)
        desc = df["Description"].str.strip()

        df["CrystalClearExplanation"] = np.select(
            [
                df["AllowedAmount"] == 0,
                df["PersonalPortion"].abs() < 0.01
            ],
            [
                who_paid + " paid " + actual + " | PERSONAL EXPENSE – not shared",
                who_paid + " paid " + actual + " | FULLY SHARED"
            ],
            default=(
                who_paid + " paid " + actual +
                " | PARTIALLY SHARED: only " + allowed + " is shared" +
                " | REASON: " + np.where(desc.eq(""), "no note provided", desc)
            )
        )

        # Calculate sharing and balance impact
        is_shared = df["AllowedAmount"] > 0
        paid_by_ryan = is_shared & (df["Name"] == "Ryan")
        paid_by_jordyn = is_shared & (df["Name"] == "Jordyn")

        df["IsShared"] = is_shared
        df["RyanOwes"] = 0.0
        df["JordynOwes"] = 0.0
        df["BalanceImpact"] = 0.0

        # Calculate who owes whom
        df.loc[paid_by_ryan, "JordynOwes"] = df.loc[paid_by_ryan, "AllowedAmount"] * self.config.JORDYN_PCT
        df.loc[paid_by_jordyn, "RyanOwes"] = df.loc[paid_by_jordyn, "AllowedAmount"] * self.config.RYAN_PCT

        # FIX #3: Correct BalanceImpact calculation
        # When Ryan pays, Jordyn owes him (negative balance impact = Ryan is owed)
        # When Jordyn pays, Ryan owes her (positive balance impact = Ryan owes)
        df.loc[paid_by_ryan, "BalanceImpact"] = -df.loc[paid_by_ryan, "JordynOwes"]
        df.loc[paid_by_jordyn, "BalanceImpact"] = df.loc[paid_by_jordyn, "RyanOwes"]
        
        # Handle "2x to calculate" notes
        df = self._handle_calculation_notes(df)
        
        # Detect duplicates
        df = self._detect_duplicates(df)
        
        # Data quality checks
        if 'DataQualityFlag' not in df.columns:
            df['DataQualityFlag'] = pd.Series([pd.NA] * len(df), index=df.index, dtype="string")

        for idx, row in df.iterrows():
            quality_flags_for_this_row = []
            
            # Check for missing date
            if pd.isna(row['Date']):
                quality_flags_for_this_row.append(DataQualityFlag.MISSING_DATE)
                df.loc[idx, 'Date'] = self._impute_missing_date(df, idx)
            
            # Check if AllowedAmount was originally blank (not explicitly personal)
            if idx in originally_blank_allowed[originally_blank_allowed].index:
                quality_flags_for_this_row.append(DataQualityFlag.MISSING_ALLOWED_AMOUNT)
            
            # Check for outliers
            if row['ActualAmount'] > self.config.OUTLIER_THRESHOLD:
                quality_flags_for_this_row.append(DataQualityFlag.OUTLIER_AMOUNT)
            
            # Check for negative amounts
            if row['ActualAmount'] < 0:
                quality_flags_for_this_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
            
            # Consolidate DataQualityFlag
            existing_flags_value = df.loc[idx, 'DataQualityFlag']
            
            if pd.isna(existing_flags_value) or existing_flags_value == DataQualityFlag.CLEAN.value:
                current_flags_list = []
            else:
                current_flags_list = str(existing_flags_value).split(',')
            
            for flag_enum in quality_flags_for_this_row:
                if flag_enum.value not in current_flags_list:
                    current_flags_list.append(flag_enum.value)
            
            if not current_flags_list:
                df.loc[idx, 'DataQualityFlag'] = DataQualityFlag.CLEAN.value
            else:
                df.loc[idx, 'DataQualityFlag'] = ','.join(current_flags_list)
            
            if quality_flags_for_this_row:
                self._log_data_quality_issue('expense_row_check', idx, row.to_dict(), quality_flags_for_this_row)

        # Create audit notes
        df["AuditNote"] = (
            df["CrystalClearExplanation"] +
            " | DataQuality: " + df["DataQualityFlag"].fillna(DataQualityFlag.CLEAN.value)
        )
        
        # Add transaction type and payer
        df['TransactionType'] = 'EXPENSE'
        df['Payer'] = df['Name']
        
        logger.info(f"Loaded {len(df)} expense records")
        return df
    
    def _create_master_ledger(self, rent_df: pd.DataFrame, expense_df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive master ledger with all transactions"""
        # Combine dataframes
        master = pd.concat([rent_df, expense_df], ignore_index=True)
        
        # FIX #2: Ensure AllowedAmount is numeric after concatenation
        # This prevents the "only $2000" issue where string concatenation fails
        master['AllowedAmount'] = pd.to_numeric(master['AllowedAmount'], errors='coerce').fillna(0)
        
        # Sort by date
        master = master.sort_values('Date').reset_index(drop=True)
        
        # Calculate running balance
        master['RunningBalance'] = master['BalanceImpact'].cumsum()
        
        # Add transaction ID for tracking
        master['TransactionID'] = master.apply(
            lambda row: self._generate_transaction_id(row),
            axis=1
        )
        
        # Add lineage information
        master['DataLineage'] = master.apply(
            lambda row: f"Source: {'Rent' if row['TransactionType'] == 'RENT' else 'Expense'} | "
                       f"Row: {row.name} | "
                       f"Processing: v2.1",
            axis=1
        )
        
        # Log summary
        logger.info(f"Created master ledger with {len(master)} transactions")
        logger.info(f"Date range: {master['Date'].min()} to {master['Date'].max()}")
        
        return master
    
    def _triple_reconciliation(self, master_ledger: pd.DataFrame) -> Dict[str, Any]:
        """Perform triple reconciliation for maximum confidence"""
        shared_only = master_ledger[master_ledger['IsShared']]
        
        # Method 1: Transaction-by-transaction running balance
        method1_balance = master_ledger['RunningBalance'].iloc[-1] if len(master_ledger) > 0 else 0
        
        # Method 2: Total overpayment method
        total_shared = shared_only['AllowedAmount'].sum()
        ryan_fair_share = total_shared * self.config.RYAN_PCT
        jordyn_fair_share = total_shared * self.config.JORDYN_PCT
        
        ryan_paid = shared_only[shared_only['Payer'] == 'Ryan']['AllowedAmount'].sum()
        jordyn_paid = shared_only[shared_only['Payer'] == 'Jordyn']['AllowedAmount'].sum()
        
        ryan_variance = ryan_paid - ryan_fair_share
        jordyn_variance = jordyn_paid - jordyn_fair_share
        
        method2_balance = -ryan_variance  # Negative because if Ryan underpaid, he owes
        
        # Method 3: Category-sum method
        category_balances = []
        
        for trans_type in ['RENT', 'EXPENSE']:
            type_data = shared_only[shared_only['TransactionType'] == trans_type]
            if len(type_data) > 0:
                type_total = type_data['AllowedAmount'].sum()
                type_ryan_paid = type_data[type_data['Payer'] == 'Ryan']['AllowedAmount'].sum()
                type_jordyn_paid = type_data[type_data['Payer'] == 'Jordyn']['AllowedAmount'].sum()
                
                type_ryan_should_pay = type_total * self.config.RYAN_PCT
                type_balance = -(type_ryan_paid - type_ryan_should_pay)
                
                category_balances.append({
                    'Category': trans_type,
                    'Total': type_total,
                    'RyanPaid': type_ryan_paid,
                    'JordynPaid': type_jordyn_paid,
                    'RyanShouldPay': type_ryan_should_pay,
                    'CategoryBalance': type_balance
                })
        
        method3_balance = sum(cat['CategoryBalance'] for cat in category_balances)
        
        # Check reconciliation
        tolerance = 0.01
        reconciled = (
            abs(method1_balance - method2_balance) <= tolerance and
            abs(method2_balance - method3_balance) <= tolerance and
            abs(method1_balance - method3_balance) <= tolerance
        )
        
        # Log results
        logger.info(f"Triple Reconciliation Results:")
        logger.info(f"  Method 1 (Running Balance): ${method1_balance:.2f}")
        logger.info(f"  Method 2 (Variance Method): ${method2_balance:.2f}")
        logger.info(f"  Method 3 (Category Sum): ${method3_balance:.2f}")
        logger.info(f"  Reconciled: {reconciled}")
        
        return {
            'method1_running_balance': round(method1_balance, 2),
            'method2_variance': round(method2_balance, 2),
            'method3_category_sum': round(method3_balance, 2),
            'reconciled': reconciled,
            'max_difference': round(max(
                abs(method1_balance - method2_balance),
                abs(method2_balance - method3_balance),
                abs(method1_balance - method3_balance)
            ), 2),
            'total_shared': round(total_shared, 2),
            'ryan_fair_share': round(ryan_fair_share, 2),
            'jordyn_fair_share': round(jordyn_fair_share, 2),
            'ryan_paid': round(ryan_paid, 2),
            'jordyn_paid': round(jordyn_paid, 2),
            'ryan_variance': round(ryan_variance, 2),
            'jordyn_variance': round(jordyn_variance, 2),
            'category_details': category_balances,
            'final_balance': round(method1_balance, 2),
            'who_owes_whom': 'Ryan owes Jordyn' if method1_balance > 0 else 'Jordyn owes Ryan',
            'amount_owed': round(abs(method1_balance), 2)
        }
    
    def _calculate_data_quality_score(self, master_ledger: pd.DataFrame) -> float:
        """Calculate overall data quality score"""
        total_rows = len(master_ledger)
        # FIX #4: Correctly count only rows that are exactly CLEAN
        clean_rows = (master_ledger['DataQualityFlag'] == DataQualityFlag.CLEAN.value).sum()
        
        return (clean_rows / total_rows * 100) if total_rows > 0 else 0
    
    def _create_visualizations(self, master_ledger: pd.DataFrame, 
                             analytics: Dict[str, Any],
                             reconciliation: Dict[str, Any]) -> Dict[str, str]:
        """Create all required visualizations with enhanced treemap"""
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        viz_paths = {}
        
        # Set style
        plt.style.use('seaborn-v0_8-whitegrid')
        sns.set_palette("husl")
        
        # 1. Running Balance Timeline
        fig1, ax1 = plt.subplots(figsize=(14, 8))
        
        balance_data = master_ledger.set_index('Date')['RunningBalance']
        balance_data.plot(ax=ax1, linewidth=2, color='darkblue')
        
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Zero Balance')
        
        # Annotate major events
        balance_changes = master_ledger['BalanceImpact'].abs()
        major_events = master_ledger.nlargest(5, 'BalanceImpact')
        
        for _, event in major_events.iterrows():
            ax1.annotate(
                f"${event['BalanceImpact']:.0f}\n{event['TransactionType']}",
                xy=(event['Date'], event['RunningBalance']),
                xytext=(10, 20), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )
        
        ax1.fill_between(balance_data.index, 0, balance_data, 
                        where=(balance_data > 0), alpha=0.3, color='green', 
                        label='Ryan Owes Jordyn')
        ax1.fill_between(balance_data.index, 0, balance_data, 
                        where=(balance_data < 0), alpha=0.3, color='red', 
                        label='Jordyn Owes Ryan')
        
        ax1.set_title('Running Balance Over Time with Major Events', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Balance ($)', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        viz_paths['running_balance'] = str(output_dir / 'running_balance_timeline.png')
        plt.savefig(viz_paths['running_balance'], dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Monthly Spend Heatmap
        fig2, ax2 = plt.subplots(figsize=(12, 8))
        
        monthly_data = master_ledger[master_ledger['IsShared']].copy()
        monthly_data['Month'] = monthly_data['Date'].dt.month
        monthly_data['Year'] = monthly_data['Date'].dt.year
        
        pivot = monthly_data.pivot_table(
            values='AllowedAmount', 
            index='Month', 
            columns='Year', 
            aggfunc='sum'
        ).fillna(0)
        
        if not pivot.empty:
            sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', 
                       cbar_kws={'label': 'Shared Expenses ($)'}, ax=ax2)
            
            month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            ax2.set_yticklabels([month_labels[i-1] for i in pivot.index], rotation=0)
            ax2.set_title('Monthly Shared Expenses Heatmap', fontsize=16, fontweight='bold')
            ax2.set_xlabel('Year', fontsize=12)
            ax2.set_ylabel('Month', fontsize=12)
        
        plt.tight_layout()
        viz_paths['monthly_heatmap'] = str(output_dir / 'monthly_spend_heatmap.png')
        plt.savefig(viz_paths['monthly_heatmap'], dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Enhanced Category Distribution Treemap
        if 'category_analysis' in analytics:
            category_data = []
            
            # Add rent as a category
            rent_total = master_ledger[master_ledger['TransactionType'] == 'RENT']['AllowedAmount'].sum()
            category_data.append({'Category': 'Rent', 'Amount': rent_total})
            
            # Add expense categories
            cat_summary = analytics['category_analysis']['summary']
            for cat in cat_summary.index:
                amount = cat_summary.loc[cat, ('AllowedAmount', 'sum')]
                category_data.append({'Category': cat, 'Amount': amount})
        else:
            # Simple categorization if detailed analysis not available
            category_data = []
            rent_total = master_ledger[
                (master_ledger['TransactionType'] == 'RENT') & 
                (master_ledger['IsShared'])
            ]['AllowedAmount'].sum()
            expense_total = master_ledger[
                (master_ledger['TransactionType'] == 'EXPENSE') & 
                (master_ledger['IsShared'])
            ]['AllowedAmount'].sum()
            
            if rent_total > 0:
                category_data.append({'Category': 'Rent', 'Amount': rent_total})
            if expense_total > 0:
                category_data.append({'Category': 'Other Expenses', 'Amount': expense_total})
        
        # Create main treemap
        if category_data:
            fig3 = go.Figure(go.Treemap(
                labels=[d['Category'] for d in category_data],
                values=[d['Amount'] for d in category_data],
                parents=[''] * len(category_data),
                texttemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percentParent}',
                marker=dict(colorscale='Viridis'),
                branchvalues="total"  # Use percent of entire root
            ))
            
            fig3.update_layout(
                title='Expense Category Distribution',
                width=1000,
                height=600
            )
            
            viz_paths['category_treemap'] = str(output_dir / 'category_treemap.html')
            fig3.write_html(viz_paths['category_treemap'])
            
            # Create discretionary spending treemap (excluding rent)
            discretionary_data = [d for d in category_data if d['Category'] != 'Rent']
            if discretionary_data:
                fig3b = go.Figure(go.Treemap(
                    labels=[d['Category'] for d in discretionary_data],
                    values=[d['Amount'] for d in discretionary_data],
                    parents=[''] * len(discretionary_data),
                    texttemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percentParent}',
                    marker=dict(colorscale='Viridis')
                ))
                
                fig3b.update_layout(
                    title='Discretionary Spending Distribution (Excluding Rent)',
                    width=1000,
                    height=600
                )
                
                viz_paths['discretionary_treemap'] = str(output_dir / 'discretionary_treemap.html')
                fig3b.write_html(viz_paths['discretionary_treemap'])
        
        # Continue with other visualizations...
        logger.info(f"Created {len(viz_paths)} visualizations")
        return viz_paths
    
    # Include all other methods from the original script...
    # (Due to length constraints, I'm including only the key fixed methods)
    # All other methods remain the same as in the original script
    
    def _clean_money(self, series: pd.Series) -> pd.Series:
        """Clean monetary values from various formats"""
        cleaned_series = (
            series.astype(str)
            .str.replace(r'[$,()]', '', regex=True)
            .str.replace(r'\s+', '', regex=True)
            .replace(['', '-', 'nan'], np.nan)
        )
        
        def to_float_safe(x):
            if pd.isna(x):
                return np.nan
            try:
                return float(x)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert '{x}' to float in _clean_money. Returning NaN.")
                return np.nan
        
        return cleaned_series.apply(to_float_safe).astype('float64', errors='ignore')
    
    def _handle_calculation_notes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle special calculation notes like '2x to calculate'"""
        if 'Description' in df.columns:
            mask = df['Description'].str.contains('2x to calculate', case=False, na=False)
            df.loc[mask, 'AllowedAmount'] *= 2
            
            # Update or set DataQualityFlag for these rows
            for idx in df[mask].index:
                existing_flags = df.loc[idx, 'DataQualityFlag']
                if pd.isna(existing_flags) or existing_flags == DataQualityFlag.CLEAN.value:
                    df.loc[idx, 'DataQualityFlag'] = DataQualityFlag.MANUAL_CALCULATION_NOTE.value
                elif DataQualityFlag.MANUAL_CALCULATION_NOTE.value not in existing_flags:
                    df.loc[idx, 'DataQualityFlag'] = existing_flags + ',' + DataQualityFlag.MANUAL_CALCULATION_NOTE.value
            
            # Log these adjustments
            for idx in df[mask].index:
                self._log_data_quality_issue(
                    'expense', idx, df.loc[idx].to_dict(), 
                    [DataQualityFlag.MANUAL_CALCULATION_NOTE]
                )
        
        return df
    
    def _detect_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect potential duplicate transactions"""
        dup_cols = ['Date', 'Name', 'Merchant', 'ActualAmount']
        available_cols = [col for col in dup_cols if col in df.columns]
        
        if available_cols:
            duplicates = df.duplicated(subset=available_cols, keep='first')
            
            # Update DataQualityFlag for duplicates
            for idx in df[duplicates].index:
                existing_flags = df.loc[idx, 'DataQualityFlag']
                if pd.isna(existing_flags) or existing_flags == DataQualityFlag.CLEAN.value:
                    df.loc[idx, 'DataQualityFlag'] = DataQualityFlag.DUPLICATE_SUSPECTED.value
                elif DataQualityFlag.DUPLICATE_SUSPECTED.value not in existing_flags:
                    df.loc[idx, 'DataQualityFlag'] = existing_flags + ',' + DataQualityFlag.DUPLICATE_SUSPECTED.value
            
            # Log duplicates
            for idx in df[duplicates].index:
                self._log_data_quality_issue(
                    'expense', idx, df.loc[idx].to_dict(), 
                    [DataQualityFlag.DUPLICATE_SUSPECTED]
                )
        
        return df
    
    def _impute_missing_date(self, df: pd.DataFrame, idx: int) -> pd.Timestamp:
        """Impute missing date based on surrounding transactions"""
        window = 5
        start_idx = max(0, idx - window)
        end_idx = min(len(df), idx + window + 1)
        
        nearby_dates = df.iloc[start_idx:end_idx]['Date'].dropna()
        
        if len(nearby_dates) > 0:
            return pd.Timestamp(nearby_dates.astype(np.int64).median())
        else:
            return pd.Timestamp.now().replace(day=1) + pd.DateOffset(months=1) - pd.DateOffset(days=1)
    
    def _categorize_merchant(self, merchant: str) -> str:
        """Categorize merchant into standard categories"""
        if pd.isna(merchant):
            return 'Other'
        
        merchant_lower = str(merchant).lower()
        
        categories = {
            'Groceries': ['fry', 'safeway', 'walmart', 'target', 'costco', 'trader', 
                         'whole foods', 'kroger', 'albertsons'],
            'Utilities': ['electric', 'gas', 'water', 'internet', 'phone', 'cox', 
                         'srp', 'aps', 'centurylink'],
            'Dining': ['restaurant', 'cafe', 'coffee', 'starbucks', 'pizza', 'sushi',
                      'mcdonald', 'chipotle', 'subway', 'nypd', 'mastro', 'tocaya'],
            'Transport': ['uber', 'lyft', 'gas station', 'shell', 'chevron', 'auto', 'toll'],
            'Entertainment': ['movie', 'theater', 'netflix', 'spotify', 'hulu', 'disney', 'game', 'baldur'],
            'Healthcare': ['pharmacy', 'cvs', 'walgreens', 'doctor', 'medical', 'dental'],
            'Shopping': ['amazon', 'best buy', 'mall', 'store']
        }
        
        for category, keywords in categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category
        
        return 'Other'
    
    def _generate_transaction_id(self, row: pd.Series) -> str:
        """Generate unique transaction ID for tracking"""
        key_data = f"{row['Date']}_{row['Payer']}_{row.get('Merchant', 'NA')}_{row['AllowedAmount']}"
        return hashlib.md5(key_data.encode()).hexdigest()[:12]
    
    def _log_data_quality_issue(self, source: str, row_idx: int, 
                               row_data: Dict[str, Any], flags: List[DataQualityFlag]):
        """Log data quality issues for audit trail"""
        issue = {
            'source': source,
            'row_index': row_idx,
            'flags': [flag.value for flag in flags],
            'row_data': row_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.data_quality_issues.append(issue)
        logger.warning(f"Data quality issue in {source} row {row_idx}: {[f.value for f in flags]}")

    # Continue with all remaining methods from the original script...
    # (Due to length, I'm focusing on the key fixes)

def main():
    """Main execution function"""
    print("Enhanced Shared Expense Analyzer - Institutional Grade (FIXED)")
    print("Version: 2.1")
    print("-" * 80)
    
    # Configuration
    config = AnalysisConfig()

    # Setup command-line argument parsing with correct default filenames
    parser = argparse.ArgumentParser(description="Enhanced Shared Expense Analyzer - Institutional Grade (Fixed)")
    parser.add_argument(
        "--rent", 
        type=Path, 
        default=Path('Rent_Allocation_20250526.csv'), 
        help="Path to the rent allocation CSV file."
    )
    parser.add_argument(
        "--expense", 
        type=Path, 
        default=Path('Expense_History_20250526.csv'), 
        help="Path to the expense history CSV file."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode to print data samples"
    )
    args = parser.parse_args()

    rent_file = args.rent
    expense_file = args.expense
    
    # Verify files exist
    if not rent_file.exists():
        print(f"Error: Rent file not found at {rent_file}")
        return
    if not expense_file.exists():
        print(f"Error: Expense file not found at {expense_file}")
        return
        
    print(f"Using rent file: {rent_file}")
    print(f"Using expense file: {expense_file}")

    # Run analysis
    analyzer = EnhancedSharedExpenseAnalyzer(rent_file, expense_file, config)
    results = analyzer.analyze()
    
    # Display results
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    print(f"\nFinal Balance: ${results['reconciliation']['amount_owed']:,.2f}")
    print(f"Who Owes: {results['reconciliation']['who_owes_whom']}")
    print(f"Total Shared Expenses: ${results['reconciliation']['total_shared']:,.2f}")
    print(f"Data Quality Score: {results['data_quality_score']:.1f}%")
    print(f"Overall Risk Level: {results['risk_assessment']['overall_assessment']['risk_level']}")
    
    print("\nOutput Files Generated:")
    for name, path in results['output_paths'].items():
        print(f"  - {name}: {path}")
    
    print("\nValidation Results:")
    for check, passed in results['validation_results'].items():
        print(f"  - {check}: {'PASSED' if passed else 'FAILED'}")
    
    print("\nPerformance Metrics:")
    print(f"  - Processing Time: {results['performance_metrics']['processing_time_seconds']:.1f}s")
    print(f"  - Memory Usage: {results['performance_metrics']['memory_usage_mb']:.1f}MB")
    print(f"  - Transactions Processed: {results['performance_metrics']['total_transactions']}")

if __name__ == "__main__":
    main()
, na=False)
        
        # Track original blank/missing AllowedAmount status (but not "$ -" entries)
        originally_blank_allowed = df['AllowedAmount'].isna() | (df['AllowedAmount'] == '')
        originally_blank_allowed = originally_blank_allowed & ~explicitly_personal
        
        # Clean monetary columns
        df['Actual Amount'] = pd.to_numeric(self._clean_money(df['Actual Amount']), errors='coerce')
        
        # Handle AllowedAmount column
        if 'AllowedAmount' not in df.columns:
            logger.warning("'AllowedAmount' column missing in expense data. Creating based on Actual Amount.")
            df['AllowedAmount'] = df['Actual Amount']
        else:
            # First clean the AllowedAmount column
            df['AllowedAmount'] = pd.to_numeric(self._clean_money(df['AllowedAmount']), errors='coerce')
            
            # FIX #1: Fill blank AllowedAmount with ActualAmount (treating blanks as fully shared)
            # This is the key fix for the 98% rent issue
            df['AllowedAmount'] = df['AllowedAmount'].fillna(df['Actual Amount'])
        
        # Parse dates
        df['Date'] = pd.to_datetime(df['Date of Purchase'], errors='coerce')

        # Ensure 'Description' column exists
        if 'Description' not in df.columns:
            df['Description'] = ""
        else:
            df['Description'] = df['Description'].fillna("")

        # Calculate personal portion
        df["PersonalPortion"] = (df["Actual Amount"] - df["AllowedAmount"]).round(self.config.CURRENCY_PRECISION)

        # Create clear explanations
        who_paid = df["Name"]
        actual = df["Actual Amount"].map("${:,.2f}".format)
        allowed = df["AllowedAmount"].map("${:,.2f}".format)
        desc = df["Description"].str.strip()

        df["CrystalClearExplanation"] = np.select(
            [
                df["AllowedAmount"] == 0,
                df["PersonalPortion"].abs() < 0.01
            ],
            [
                who_paid + " paid " + actual + " | PERSONAL EXPENSE – not shared",
                who_paid + " paid " + actual + " | FULLY SHARED"
            ],
            default=(
                who_paid + " paid " + actual +
                " | PARTIALLY SHARED: only " + allowed + " is shared" +
                " | REASON: " + np.where(desc.eq(""), "no note provided", desc)
            )
        )

        # Calculate sharing and balance impact
        is_shared = df["AllowedAmount"] > 0
        paid_by_ryan = is_shared & (df["Name"] == "Ryan")
        paid_by_jordyn = is_shared & (df["Name"] == "Jordyn")

        df["IsShared"] = is_shared
        df["RyanOwes"] = 0.0
        df["JordynOwes"] = 0.0
        df["BalanceImpact"] = 0.0

        # Calculate who owes whom
        df.loc[paid_by_ryan, "JordynOwes"] = df.loc[paid_by_ryan, "AllowedAmount"] * self.config.JORDYN_PCT
        df.loc[paid_by_jordyn, "RyanOwes"] = df.loc[paid_by_jordyn, "AllowedAmount"] * self.config.RYAN_PCT

        # FIX #3: Correct BalanceImpact calculation
        # When Ryan pays, Jordyn owes him (negative balance impact = Ryan is owed)
        # When Jordyn pays, Ryan owes her (positive balance impact = Ryan owes)
        df.loc[paid_by_ryan, "BalanceImpact"] = -df.loc[paid_by_ryan, "JordynOwes"]
        df.loc[paid_by_jordyn, "BalanceImpact"] = df.loc[paid_by_jordyn, "RyanOwes"]
        
        # Handle "2x to calculate" notes
        df = self._handle_calculation_notes(df)
        
        # Detect duplicates
        df = self._detect_duplicates(df)
        
        # Data quality checks
        if 'DataQualityFlag' not in df.columns:
            df['DataQualityFlag'] = pd.Series([pd.NA] * len(df), index=df.index, dtype="string")

        for idx, row in df.iterrows():
            quality_flags_for_this_row = []
            
            # Check for missing date
            if pd.isna(row['Date']):
                quality_flags_for_this_row.append(DataQualityFlag.MISSING_DATE)
                df.loc[idx, 'Date'] = self._impute_missing_date(df, idx)
            
            # Check if AllowedAmount was originally blank
            if originally_blank_allowed.loc[idx]:
                quality_flags_for_this_row.append(DataQualityFlag.MISSING_ALLOWED_AMOUNT)
            
            # Check for outliers
            if row['Actual Amount'] > self.config.OUTLIER_THRESHOLD:
                quality_flags_for_this_row.append(DataQualityFlag.OUTLIER_AMOUNT)
            
            # Check for negative amounts
            if row['Actual Amount'] < 0:
                quality_flags_for_this_row.append(DataQualityFlag.NEGATIVE_AMOUNT)
            
            # Consolidate DataQualityFlag
            existing_flags_value = df.loc[idx, 'DataQualityFlag']
            
            if pd.isna(existing_flags_value) or existing_flags_value == DataQualityFlag.CLEAN.value:
                current_flags_list = []
            else:
                current_flags_list = str(existing_flags_value).split(',')
            
            for flag_enum in quality_flags_for_this_row:
                if flag_enum.value not in current_flags_list:
                    current_flags_list.append(flag_enum.value)
            
            if not current_flags_list:
                df.loc[idx, 'DataQualityFlag'] = DataQualityFlag.CLEAN.value
            else:
                df.loc[idx, 'DataQualityFlag'] = ','.join(current_flags_list)
            
            if quality_flags_for_this_row:
                self._log_data_quality_issue('expense_row_check', idx, row.to_dict(), quality_flags_for_this_row)

        # Create audit notes
        df["AuditNote"] = (
            df["CrystalClearExplanation"] +
            " | DataQuality: " + df["DataQualityFlag"].fillna(DataQualityFlag.CLEAN.value)
        )
        
        # Add transaction type and payer
        df['TransactionType'] = 'EXPENSE'
        df['Payer'] = df['Name']
        
        logger.info(f"Loaded {len(df)} expense records")
        return df
    
    def _create_master_ledger(self, rent_df: pd.DataFrame, expense_df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive master ledger with all transactions"""
        # Combine dataframes
        master = pd.concat([rent_df, expense_df], ignore_index=True)
        
        # FIX #2: Ensure AllowedAmount is numeric after concatenation
        # This prevents the "only $2000" issue where string concatenation fails
        master['AllowedAmount'] = pd.to_numeric(master['AllowedAmount'], errors='coerce').fillna(0)
        
        # Sort by date
        master = master.sort_values('Date').reset_index(drop=True)
        
        # Calculate running balance
        master['RunningBalance'] = master['BalanceImpact'].cumsum()
        
        # Add transaction ID for tracking
        master['TransactionID'] = master.apply(
            lambda row: self._generate_transaction_id(row),
            axis=1
        )
        
        # Add lineage information
        master['DataLineage'] = master.apply(
            lambda row: f"Source: {'Rent' if row['TransactionType'] == 'RENT' else 'Expense'} | "
                       f"Row: {row.name} | "
                       f"Processing: v2.1",
            axis=1
        )
        
        # Log summary
        logger.info(f"Created master ledger with {len(master)} transactions")
        logger.info(f"Date range: {master['Date'].min()} to {master['Date'].max()}")
        
        return master
    
    def _triple_reconciliation(self, master_ledger: pd.DataFrame) -> Dict[str, Any]:
        """Perform triple reconciliation for maximum confidence"""
        shared_only = master_ledger[master_ledger['IsShared']]
        
        # Method 1: Transaction-by-transaction running balance
        method1_balance = master_ledger['RunningBalance'].iloc[-1] if len(master_ledger) > 0 else 0
        
        # Method 2: Total overpayment method
        total_shared = shared_only['AllowedAmount'].sum()
        ryan_fair_share = total_shared * self.config.RYAN_PCT
        jordyn_fair_share = total_shared * self.config.JORDYN_PCT
        
        ryan_paid = shared_only[shared_only['Payer'] == 'Ryan']['AllowedAmount'].sum()
        jordyn_paid = shared_only[shared_only['Payer'] == 'Jordyn']['AllowedAmount'].sum()
        
        ryan_variance = ryan_paid - ryan_fair_share
        jordyn_variance = jordyn_paid - jordyn_fair_share
        
        method2_balance = -ryan_variance  # Negative because if Ryan underpaid, he owes
        
        # Method 3: Category-sum method
        category_balances = []
        
        for trans_type in ['RENT', 'EXPENSE']:
            type_data = shared_only[shared_only['TransactionType'] == trans_type]
            if len(type_data) > 0:
                type_total = type_data['AllowedAmount'].sum()
                type_ryan_paid = type_data[type_data['Payer'] == 'Ryan']['AllowedAmount'].sum()
                type_jordyn_paid = type_data[type_data['Payer'] == 'Jordyn']['AllowedAmount'].sum()
                
                type_ryan_should_pay = type_total * self.config.RYAN_PCT
                type_balance = -(type_ryan_paid - type_ryan_should_pay)
                
                category_balances.append({
                    'Category': trans_type,
                    'Total': type_total,
                    'RyanPaid': type_ryan_paid,
                    'JordynPaid': type_jordyn_paid,
                    'RyanShouldPay': type_ryan_should_pay,
                    'CategoryBalance': type_balance
                })
        
        method3_balance = sum(cat['CategoryBalance'] for cat in category_balances)
        
        # Check reconciliation
        tolerance = 0.01
        reconciled = (
            abs(method1_balance - method2_balance) <= tolerance and
            abs(method2_balance - method3_balance) <= tolerance and
            abs(method1_balance - method3_balance) <= tolerance
        )
        
        # Log results
        logger.info(f"Triple Reconciliation Results:")
        logger.info(f"  Method 1 (Running Balance): ${method1_balance:.2f}")
        logger.info(f"  Method 2 (Variance Method): ${method2_balance:.2f}")
        logger.info(f"  Method 3 (Category Sum): ${method3_balance:.2f}")
        logger.info(f"  Reconciled: {reconciled}")
        
        return {
            'method1_running_balance': round(method1_balance, 2),
            'method2_variance': round(method2_balance, 2),
            'method3_category_sum': round(method3_balance, 2),
            'reconciled': reconciled,
            'max_difference': round(max(
                abs(method1_balance - method2_balance),
                abs(method2_balance - method3_balance),
                abs(method1_balance - method3_balance)
            ), 2),
            'total_shared': round(total_shared, 2),
            'ryan_fair_share': round(ryan_fair_share, 2),
            'jordyn_fair_share': round(jordyn_fair_share, 2),
            'ryan_paid': round(ryan_paid, 2),
            'jordyn_paid': round(jordyn_paid, 2),
            'ryan_variance': round(ryan_variance, 2),
            'jordyn_variance': round(jordyn_variance, 2),
            'category_details': category_balances,
            'final_balance': round(method1_balance, 2),
            'who_owes_whom': 'Ryan owes Jordyn' if method1_balance > 0 else 'Jordyn owes Ryan',
            'amount_owed': round(abs(method1_balance), 2)
        }
    
    def _calculate_data_quality_score(self, master_ledger: pd.DataFrame) -> float:
        """Calculate overall data quality score"""
        total_rows = len(master_ledger)
        # FIX #4: Correctly count only rows that are exactly CLEAN
        clean_rows = (master_ledger['DataQualityFlag'] == DataQualityFlag.CLEAN.value).sum()
        
        return (clean_rows / total_rows * 100) if total_rows > 0 else 0
    
    def _create_visualizations(self, master_ledger: pd.DataFrame, 
                             analytics: Dict[str, Any],
                             reconciliation: Dict[str, Any]) -> Dict[str, str]:
        """Create all required visualizations with enhanced treemap"""
        output_dir = Path('analysis_output')
        output_dir.mkdir(exist_ok=True)
        viz_paths = {}
        
        # Set style
        plt.style.use('seaborn-v0_8-whitegrid')
        sns.set_palette("husl")
        
        # 1. Running Balance Timeline
        fig1, ax1 = plt.subplots(figsize=(14, 8))
        
        balance_data = master_ledger.set_index('Date')['RunningBalance']
        balance_data.plot(ax=ax1, linewidth=2, color='darkblue')
        
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Zero Balance')
        
        # Annotate major events
        balance_changes = master_ledger['BalanceImpact'].abs()
        major_events = master_ledger.nlargest(5, 'BalanceImpact')
        
        for _, event in major_events.iterrows():
            ax1.annotate(
                f"${event['BalanceImpact']:.0f}\n{event['TransactionType']}",
                xy=(event['Date'], event['RunningBalance']),
                xytext=(10, 20), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )
        
        ax1.fill_between(balance_data.index, 0, balance_data, 
                        where=(balance_data > 0), alpha=0.3, color='green', 
                        label='Ryan Owes Jordyn')
        ax1.fill_between(balance_data.index, 0, balance_data, 
                        where=(balance_data < 0), alpha=0.3, color='red', 
                        label='Jordyn Owes Ryan')
        
        ax1.set_title('Running Balance Over Time with Major Events', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Balance ($)', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        viz_paths['running_balance'] = str(output_dir / 'running_balance_timeline.png')
        plt.savefig(viz_paths['running_balance'], dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Monthly Spend Heatmap
        fig2, ax2 = plt.subplots(figsize=(12, 8))
        
        monthly_data = master_ledger[master_ledger['IsShared']].copy()
        monthly_data['Month'] = monthly_data['Date'].dt.month
        monthly_data['Year'] = monthly_data['Date'].dt.year
        
        pivot = monthly_data.pivot_table(
            values='AllowedAmount', 
            index='Month', 
            columns='Year', 
            aggfunc='sum'
        ).fillna(0)
        
        if not pivot.empty:
            sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', 
                       cbar_kws={'label': 'Shared Expenses ($)'}, ax=ax2)
            
            month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            ax2.set_yticklabels([month_labels[i-1] for i in pivot.index], rotation=0)
            ax2.set_title('Monthly Shared Expenses Heatmap', fontsize=16, fontweight='bold')
            ax2.set_xlabel('Year', fontsize=12)
            ax2.set_ylabel('Month', fontsize=12)
        
        plt.tight_layout()
        viz_paths['monthly_heatmap'] = str(output_dir / 'monthly_spend_heatmap.png')
        plt.savefig(viz_paths['monthly_heatmap'], dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Enhanced Category Distribution Treemap
        if 'category_analysis' in analytics:
            category_data = []
            
            # Add rent as a category
            rent_total = master_ledger[master_ledger['TransactionType'] == 'RENT']['AllowedAmount'].sum()
            category_data.append({'Category': 'Rent', 'Amount': rent_total})
            
            # Add expense categories
            cat_summary = analytics['category_analysis']['summary']
            for cat in cat_summary.index:
                amount = cat_summary.loc[cat, ('AllowedAmount', 'sum')]
                category_data.append({'Category': cat, 'Amount': amount})
        else:
            # Simple categorization if detailed analysis not available
            category_data = []
            rent_total = master_ledger[
                (master_ledger['TransactionType'] == 'RENT') & 
                (master_ledger['IsShared'])
            ]['AllowedAmount'].sum()
            expense_total = master_ledger[
                (master_ledger['TransactionType'] == 'EXPENSE') & 
                (master_ledger['IsShared'])
            ]['AllowedAmount'].sum()
            
            if rent_total > 0:
                category_data.append({'Category': 'Rent', 'Amount': rent_total})
            if expense_total > 0:
                category_data.append({'Category': 'Other Expenses', 'Amount': expense_total})
        
        # Create main treemap
        if category_data:
            fig3 = go.Figure(go.Treemap(
                labels=[d['Category'] for d in category_data],
                values=[d['Amount'] for d in category_data],
                parents=[''] * len(category_data),
                texttemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percentParent}',
                marker=dict(colorscale='Viridis'),
                branchvalues="total"  # Use percent of entire root
            ))
            
            fig3.update_layout(
                title='Expense Category Distribution',
                width=1000,
                height=600
            )
            
            viz_paths['category_treemap'] = str(output_dir / 'category_treemap.html')
            fig3.write_html(viz_paths['category_treemap'])
            
            # Create discretionary spending treemap (excluding rent)
            discretionary_data = [d for d in category_data if d['Category'] != 'Rent']
            if discretionary_data:
                fig3b = go.Figure(go.Treemap(
                    labels=[d['Category'] for d in discretionary_data],
                    values=[d['Amount'] for d in discretionary_data],
                    parents=[''] * len(discretionary_data),
                    texttemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percentParent}',
                    marker=dict(colorscale='Viridis')
                ))
                
                fig3b.update_layout(
                    title='Discretionary Spending Distribution (Excluding Rent)',
                    width=1000,
                    height=600
                )
                
                viz_paths['discretionary_treemap'] = str(output_dir / 'discretionary_treemap.html')
                fig3b.write_html(viz_paths['discretionary_treemap'])
        
        # Continue with other visualizations...
        logger.info(f"Created {len(viz_paths)} visualizations")
        return viz_paths
    
    # Include all other methods from the original script...
    # (Due to length constraints, I'm including only the key fixed methods)
    # All other methods remain the same as in the original script
    
    def _clean_money(self, series: pd.Series) -> pd.Series:
        """Clean monetary values from various formats"""
        cleaned_series = (
            series.astype(str)
            .str.replace(r'[$,()]', '', regex=True)
            .str.replace(r'\s+', '', regex=True)
            .replace(['', '-', 'nan'], np.nan)
        )
        
        def to_float_safe(x):
            if pd.isna(x):
                return np.nan
            try:
                return float(x)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert '{x}' to float in _clean_money. Returning NaN.")
                return np.nan
        
        return cleaned_series.apply(to_float_safe).astype('float64', errors='ignore')
    
    def _handle_calculation_notes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle special calculation notes like '2x to calculate'"""
        if 'Description' in df.columns:
            mask = df['Description'].str.contains('2x to calculate', case=False, na=False)
            df.loc[mask, 'AllowedAmount'] *= 2
            
            # Update or set DataQualityFlag for these rows
            for idx in df[mask].index:
                existing_flags = df.loc[idx, 'DataQualityFlag']
                if pd.isna(existing_flags) or existing_flags == DataQualityFlag.CLEAN.value:
                    df.loc[idx, 'DataQualityFlag'] = DataQualityFlag.MANUAL_CALCULATION_NOTE.value
                elif DataQualityFlag.MANUAL_CALCULATION_NOTE.value not in existing_flags:
                    df.loc[idx, 'DataQualityFlag'] = existing_flags + ',' + DataQualityFlag.MANUAL_CALCULATION_NOTE.value
            
            # Log these adjustments
            for idx in df[mask].index:
                self._log_data_quality_issue(
                    'expense', idx, df.loc[idx].to_dict(), 
                    [DataQualityFlag.MANUAL_CALCULATION_NOTE]
                )
        
        return df
    
    def _detect_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect potential duplicate transactions"""
        dup_cols = ['Date', 'Name', 'Merchant', 'Actual Amount']
        available_cols = [col for col in dup_cols if col in df.columns]
        
        if available_cols:
            duplicates = df.duplicated(subset=available_cols, keep='first')
            
            # Update DataQualityFlag for duplicates
            for idx in df[duplicates].index:
                existing_flags = df.loc[idx, 'DataQualityFlag']
                if pd.isna(existing_flags) or existing_flags == DataQualityFlag.CLEAN.value:
                    df.loc[idx, 'DataQualityFlag'] = DataQualityFlag.DUPLICATE_SUSPECTED.value
                elif DataQualityFlag.DUPLICATE_SUSPECTED.value not in existing_flags:
                    df.loc[idx, 'DataQualityFlag'] = existing_flags + ',' + DataQualityFlag.DUPLICATE_SUSPECTED.value
            
            # Log duplicates
            for idx in df[duplicates].index:
                self._log_data_quality_issue(
                    'expense', idx, df.loc[idx].to_dict(), 
                    [DataQualityFlag.DUPLICATE_SUSPECTED]
                )
        
        return df
    
    def _impute_missing_date(self, df: pd.DataFrame, idx: int) -> pd.Timestamp:
        """Impute missing date based on surrounding transactions"""
        window = 5
        start_idx = max(0, idx - window)
        end_idx = min(len(df), idx + window + 1)
        
        nearby_dates = df.iloc[start_idx:end_idx]['Date'].dropna()
        
        if len(nearby_dates) > 0:
            return pd.Timestamp(nearby_dates.astype(np.int64).median())
        else:
            return pd.Timestamp.now().replace(day=1) + pd.DateOffset(months=1) - pd.DateOffset(days=1)
    
    def _categorize_merchant(self, merchant: str) -> str:
        """Categorize merchant into standard categories"""
        if pd.isna(merchant):
            return 'Other'
        
        merchant_lower = str(merchant).lower()
        
        categories = {
            'Groceries': ['fry', 'safeway', 'walmart', 'target', 'costco', 'trader', 
                         'whole foods', 'kroger', 'albertsons'],
            'Utilities': ['electric', 'gas', 'water', 'internet', 'phone', 'cox', 
                         'srp', 'aps', 'centurylink'],
            'Dining': ['restaurant', 'cafe', 'coffee', 'starbucks', 'pizza', 'sushi',
                      'mcdonald', 'chipotle', 'subway', 'nypd', 'mastro', 'tocaya'],
            'Transport': ['uber', 'lyft', 'gas station', 'shell', 'chevron', 'auto', 'toll'],
            'Entertainment': ['movie', 'theater', 'netflix', 'spotify', 'hulu', 'disney', 'game', 'baldur'],
            'Healthcare': ['pharmacy', 'cvs', 'walgreens', 'doctor', 'medical', 'dental'],
            'Shopping': ['amazon', 'best buy', 'mall', 'store']
        }
        
        for category, keywords in categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category
        
        return 'Other'
    
    def _generate_transaction_id(self, row: pd.Series) -> str:
        """Generate unique transaction ID for tracking"""
        key_data = f"{row['Date']}_{row['Payer']}_{row.get('Merchant', 'NA')}_{row['AllowedAmount']}"
        return hashlib.md5(key_data.encode()).hexdigest()[:12]
    
    def _log_data_quality_issue(self, source: str, row_idx: int, 
                               row_data: Dict[str, Any], flags: List[DataQualityFlag]):
        """Log data quality issues for audit trail"""
        issue = {
            'source': source,
            'row_index': row_idx,
            'flags': [flag.value for flag in flags],
            'row_data': row_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.data_quality_issues.append(issue)
        logger.warning(f"Data quality issue in {source} row {row_idx}: {[f.value for f in flags]}")

    # Continue with all remaining methods from the original script...
    # (Due to length, I'm focusing on the key fixes)

def main():
    """Main execution function"""
    print("Enhanced Shared Expense Analyzer - Institutional Grade (FIXED)")
    print("Version: 2.1")
    print("-" * 80)
    
    # Configuration
    config = AnalysisConfig()

    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(description="Enhanced Shared Expense Analyzer - Institutional Grade (Fixed)")
    parser.add_argument(
        "--rent", 
        type=Path, 
        default=Path('Rent_Allocation_20250526.csv'), 
        help="Path to the rent allocation CSV file."
    )
    parser.add_argument(
        "--expense", 
        type=Path, 
        default=Path('Expense_History_20250526.csv'), 
        help="Path to the expense history CSV file."
    )
    args = parser.parse_args()

    rent_file = args.rent
    expense_file = args.expense
    
    # Verify files exist
    if not rent_file.exists():
        print(f"Error: Rent file not found at {rent_file}")
        return
    if not expense_file.exists():
        print(f"Error: Expense file not found at {expense_file}")
        return
        
    print(f"Using rent file: {rent_file}")
    print(f"Using expense file: {expense_file}")

    # Run analysis
    analyzer = EnhancedSharedExpenseAnalyzer(rent_file, expense_file, config)
    results = analyzer.analyze()
    
    # Display results
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    print(f"\nFinal Balance: ${results['reconciliation']['amount_owed']:,.2f}")
    print(f"Who Owes: {results['reconciliation']['who_owes_whom']}")
    print(f"Total Shared Expenses: ${results['reconciliation']['total_shared']:,.2f}")
    print(f"Data Quality Score: {results['data_quality_score']:.1f}%")
    print(f"Overall Risk Level: {results['risk_assessment']['overall_assessment']['risk_level']}")
    
    print("\nOutput Files Generated:")
    for name, path in results['output_paths'].items():
        print(f"  - {name}: {path}")
    
    print("\nValidation Results:")
    for check, passed in results['validation_results'].items():
        print(f"  - {check}: {'PASSED' if passed else 'FAILED'}")
    
    print("\nPerformance Metrics:")
    print(f"  - Processing Time: {results['performance_metrics']['processing_time_seconds']:.1f}s")
    print(f"  - Memory Usage: {results['performance_metrics']['memory_usage_mb']:.1f}MB")
    print(f"  - Transactions Processed: {results['performance_metrics']['total_transactions']}")

if __name__ == "__main__":
    main()
