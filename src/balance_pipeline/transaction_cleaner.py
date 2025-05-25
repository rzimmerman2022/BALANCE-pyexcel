"""
Transaction Cleaning Module for BALANCE-pyexcel
Provides comprehensive data-driven cleaning for transaction descriptions and merchant names
Based on analysis of actual transaction patterns
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set, Any
import logging
import json
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)


class ComprehensiveTransactionCleaner:
    """
    Comprehensive cleaner that handles all columns needing transformation
    based on the analysis results.
    """
    
    def __init__(self, analysis_results_path: Optional[Path] = None):
        """Initialize with patterns from analysis or defaults"""
        self.analysis_results: Dict[str, Any] = {}
        self.recommendations: Dict[str, Any] = {} # For cleaning_recommendations.json
        self.merchant_standardization: Dict[str, str] = {} # For merchant_variations.json
        self.analysis_results_path: Optional[Path] = analysis_results_path # Store for later use

        if self.analysis_results_path:
            self.load_analysis_results(self.analysis_results_path) # Loads full_column_analysis & recommendations
        
        # Initialize all cleaning patterns
        self.initialize_description_patterns()
        self.initialize_merchant_patterns() # Will use self.analysis_results_path to load merchant_variations
        self.initialize_account_patterns()
        self.initialize_institution_patterns()
    
    def load_analysis_results(self, results_path: Path):
        """Load the comprehensive analysis results"""
        try:
            # Load the full analysis
            analysis_file = results_path / 'full_column_analysis.json'
            if analysis_file.exists():
                with open(analysis_file, 'r') as f:
                    self.analysis_results = json.load(f)
                log.info(f"Loaded analysis results from {analysis_file}")
            else:
                log.warning(f"Full column analysis file not found at {analysis_file}")
            
            # Load cleaning recommendations
            recommendations_file = results_path / 'cleaning_recommendations.json'
            if recommendations_file.exists():
                with open(recommendations_file, 'r') as f:
                    self.recommendations = json.load(f)
                log.info(f"Loaded cleaning recommendations from {recommendations_file}")
            else:
                log.warning(f"Cleaning recommendations file not found at {recommendations_file}")
        except Exception as e:
            log.error(f"Error loading analysis results from {results_path}: {e}")
    
    def initialize_description_patterns(self):
        """Initialize patterns for description cleaning"""
        # Based on your analysis showing common prefixes
        self.description_prefixes = [
            # From your analysis results
            'PURCHASE AUTHORIZED ON',
            'PURCHASE AUTHORIZED',
            'PURCHASE',
            'RECURRING PAYMENT',
            'RECURRING',
            'E-PAYMENT',
            'ONLINE',
            'AUTOMATIC',
            'POS DEBIT',
            'POS PURCHASE',
            'DEBIT CARD',
            'VISA PURCHASE',
            'CHECKCARD',
            'CHECK CARD',
            'ACH DEBIT',
            'ACH CREDIT',
            'ACH',
            'DIRECTDEP',
            'DIRECT DEP',
            'PPD',
        ]
        
        # Patterns to remove from descriptions
        self.description_noise_patterns = [
            r'\b\d{4,6}\*+\d{4}\b',              # Card numbers
            r'CARD\s+\d{4}',                     # CARD 0968
            r'S\d{12,}',                         # Transaction IDs like S303109599173355
            r'REF\s*#?\s*\d{6,}',                # Reference numbers
            r'TRACE\s*#?\s*\d{6,}',              # Trace numbers
            r'AUTH\s*#?\s*\d{6,}',               # Auth codes
            r'\b[A-Z0-9]{15,}\b',                # Very long alphanumeric codes
            r'\b\d{2}/\d{2}\b(?!\d)',            # Dates MM/DD (but not MM/DD/YY)
        ]
    
    def initialize_merchant_patterns(self):
        """Initialize patterns for merchant extraction and standardization"""
        # Special extraction patterns for complex merchants
        self.merchant_extraction_patterns = [
            # P2P services - extract but sanitize personal info
            (r'ZELLE\s+(PAYMENT\s+)?(FROM|TO)\s+([A-Z][A-Z\s]+?)(\s+[A-Z0-9]{8,})', r'ZELLE \2 \3'),
            (r'VENMO\s+(PAYMENT\s+)?(FROM|TO)\s+([A-Z][A-Z\s]+?)(\s+[A-Z0-9]{8,})', r'VENMO \2 \3'),
            
            # Direct deposits
            (r'([A-Z][A-Z\s]+?)\s+DIRECTPAY\s+[A-Z0-9]+\s+[A-Za-z\s]+$', r'\1 DIRECTPAY'),
            (r'DIRECTDEP\s+([A-Z][A-Z\s]+?)\s+PAYROLL.*', r'\1 PAYROLL'),
            
            # TST* prefix (appears to be restaurant/food)
            (r'TST\*\s*(.+)', r'\1'),
        ]
        
        # Standardization rules based on your merchant analysis
        # self.merchant_standardization = { ... } # Removed hardcoded rules

        # Load standardization rules from merchant_variations.json
        self.merchant_standardization = {} # Default to empty
        if self.analysis_results_path:
            merchant_variations_file = self.analysis_results_path / 'merchant_variations.json'
            if merchant_variations_file.exists():
                try:
                    with open(merchant_variations_file, 'r') as f:
                        # Assuming the JSON is a flat dict of pattern: replacement
                        loaded_rules = json.load(f)
                        # The patterns are direct strings, not regex, so we store them as is.
                        # The standardize_merchant method will need to handle this.
                        # For now, let's assume they are regex patterns as keys.
                        # If they are exact strings, standardize_merchant will need adjustment.
                        # Based on user prompt: "Keys are the merchant name patterns/variations found in the data"
                        # "Values are the standardized merchant names"
                        # This implies direct lookup, not regex.
                        self.merchant_standardization = loaded_rules
                    log.info(f"Loaded {len(self.merchant_standardization)} merchant standardization rules from {merchant_variations_file}")
                except Exception as e:
                    log.error(f"Error loading merchant variations from {merchant_variations_file}: {e}")
            else:
                log.warning(f"Merchant variations file not found at {merchant_variations_file}. Standardization rules will be empty.")
        else:
            log.warning("Analysis results path not provided. Merchant standardization rules will be empty.")
    
    def initialize_account_patterns(self):
        """Initialize patterns for account cleaning"""
        # Your analysis shows accounts like "EVERYDAY CHECKING ...3850"
        self.account_cleaning_patterns = [
            (r'\.\.\.(\d{4})$', r'****\1'),  # Convert ...3850 to ****3850
            (r'\(\.\.\.(\d{4})\)', r'****\1'),  # Convert (...3850) to ****3850
            (r'WF\s+', 'Wells Fargo '),  # Expand WF abbreviation
        ]
    
    def initialize_institution_patterns(self):
        """Initialize patterns for institution cleaning"""
        self.institution_cleaning_patterns = [
            (r'WF\s+', 'Wells Fargo '),
            (r'\s+$', ''),  # Remove trailing spaces
            (r'EVERYDAY\s+CHECKING', ''),  # Remove account type from institution
        ]
    
    # TIER 1: OriginalDescription → Description
    def clean_description(self, original_desc: str) -> str:
        """
        Creates human-readable description from original.
        Removes bank prefixes and transaction noise while preserving meaning.
        """
        if pd.isna(original_desc) or not str(original_desc).strip():
            return ""
        
        desc = str(original_desc).strip()
        
        # Remove bank prefixes
        desc_upper = desc.upper()
        for prefix in self.description_prefixes:
            if desc_upper.startswith(prefix.upper()):
                # Preserve original case after prefix
                desc = desc[len(prefix):].strip()
                desc_upper = desc.upper()
        
        # Remove noise patterns
        for pattern in self.description_noise_patterns:
            desc = re.sub(pattern, '', desc, flags=re.IGNORECASE)
        
        # Clean up formatting
        desc = desc.replace('  ', ' ')  # Double spaces
        desc = re.sub(r'\s+([,.])', r'\1', desc)  # Space before punctuation
        desc = re.sub(r'([,.])\s*([,.])', r'\1', desc)  # Multiple punctuation
        
        # Handle ALL CAPS (your analysis shows 74% are all caps)
        if desc.isupper() and len(desc) > 10:
            # Convert to title case but preserve common acronyms
            words = desc.split()
            cleaned_words = []
            acronyms = {'ATM', 'ACH', 'POS', 'USA', 'LLC', 'INC', 'CORP', 'CA', 'AZ', 'TX', 'NY'}
            
            for word in words:
                if word in acronyms or (len(word) <= 3 and word.isalpha()):
                    cleaned_words.append(word)
                else:
                    cleaned_words.append(word.title())
            desc = ' '.join(cleaned_words)
        
        # Intelligent truncation
        if len(desc) > 60:
            # Try to cut at natural boundary
            cut_point = desc.rfind(' ', 0, 60)
            if cut_point > 40:  # Only if we're not cutting too much
                desc = desc[:cut_point] + '...'
            else:
                desc = desc[:57] + '...'
        
        return desc.strip()
    
    # TIER 2A: OriginalDescription → OriginalMerchant
    def extract_original_merchant(self, original_desc: str) -> str:
        """
        Extracts merchant from original description with light cleaning.
        Preserves location and store information for later standardization.
        """
        if pd.isna(original_desc) or not str(original_desc).strip():
            return ""
        
        merchant = str(original_desc).strip()
        
        # Remove light prefixes but keep more info than description cleaning
        light_prefixes = [
            'PURCHASE AUTHORIZED ON',
            'PURCHASE',
            'POS DEBIT',
            'DEBIT CARD',
            'RECURRING',
            'E-PAYMENT,',  # Note the comma
            'ONLINE',
            'AUTOMATIC',
        ]
        
        merchant_upper = merchant.upper()
        for prefix in light_prefixes:
            if merchant_upper.startswith(prefix):
                merchant = merchant[len(prefix):].strip()
                merchant_upper = merchant.upper()
        
        # Remove dates at start (MM/DD format)
        merchant = re.sub(r'^\d{1,2}/\d{1,2}\s+', '', merchant)
        
        # Apply special extraction patterns
        for pattern, replacement in self.merchant_extraction_patterns:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            match = compiled_pattern.search(merchant)
            if match:
                if callable(replacement):
                    merchant = replacement(match)
                else:
                    merchant = compiled_pattern.sub(replacement, merchant)
                break
        
        # Remove trailing transaction data but keep store info
        merchant = re.sub(r'\s+S\d{12,}.*$', '', merchant)  # Transaction IDs
        merchant = re.sub(r'\s+CARD\s+\d{4}$', '', merchant)  # Card numbers
        merchant = re.sub(r'\s+REF#?\s*\d{6,}.*$', '', merchant, flags=re.IGNORECASE)
        
        # Clean up whitespace
        merchant = ' '.join(merchant.split())
        
        return merchant
    
    # TIER 2B: OriginalMerchant → Merchant
    def standardize_merchant(self, original_merchant: str) -> str:
        """
        Standardizes merchant name for reporting and categorization.
        Applies aggressive normalization for consistency.
        """
        if pd.isna(original_merchant) or not str(original_merchant).strip():
            return "Unknown"
        
        merchant = str(original_merchant).strip()
        
        # Priority 1: Direct lookup in loaded merchant_variations.json rules
        # The keys in self.merchant_standardization are the raw merchant strings.
        if merchant in self.merchant_standardization:
            return self.merchant_standardization[merchant]
        
        # Priority 2: Fallback to general regex-based standardization rules (if any were kept or added)
        # For this implementation, we assume merchant_variations.json is comprehensive for known variations.
        # If there were other generic regex rules, they would go here.
        # Example:
        # for pattern, replacement in self.generic_merchant_regex_rules.items(): # Assuming such a dict exists
        #     compiled = re.compile(pattern, re.IGNORECASE)
        #     if compiled.search(merchant):
        #         if callable(replacement):
        #             return replacement(compiled.search(merchant))
        #         else:
        #             return replacement

        # Priority 3: If no specific or regex rule matches, clean up heuristically
        # Remove location data
        merchant = re.sub(r'\s+[A-Z]{2}\s*$', '', merchant)  # State codes
        merchant = re.sub(r'\s+\d{5}(-\d{4})?', '', merchant)  # ZIP codes
        
        # Remove store numbers
        merchant = re.sub(r'\s*#\s*\d{3,}', '', merchant)
        merchant = re.sub(r'\s+STORE\s+\d+', '', merchant, flags=re.IGNORECASE)
        
        # Remove common suffixes
        merchant = re.sub(r'\s+(LLC|INC|CORP|CO|LTD)\.?\s*$', '', merchant, flags=re.IGNORECASE)
        
        # Clean up and format
        merchant = ' '.join(merchant.split())
        
        # Smart title case
        if merchant:
            words = merchant.split()
            result = []
            for word in words:
                if len(word) <= 3 and word.isupper() and word.isalpha():
                    result.append(word)  # Keep short acronyms
                else:
                    result.append(word.title())
            merchant = ' '.join(result)
        
        return merchant if merchant else "Unknown"
    
    def _extract_company_from_payroll(self, payroll_text: str) -> str:
        """Helper to extract company name from payroll entries"""
        # Remove payroll indicators and IDs
        cleaned = re.sub(r'\s+PAYROLL.*', '', payroll_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+\b[A-Z0-9]{8,}\b.*', '', cleaned)  # Remove IDs
        cleaned = ' '.join(cleaned.split())
        
        # Extract company name (usually at the beginning)
        if 'SCIENCE CARE' in cleaned.upper():
            return 'Science Care Payroll'
        
        # Return cleaned name + Payroll
        return cleaned.title() + ' Payroll'
    
    # Additional column cleaning methods
    def clean_account(self, account: str) -> str:
        """Clean account names for consistency"""
        if pd.isna(account) or account == 'Account Description':
            return account
        
        cleaned = str(account).strip()
        
        # Apply cleaning patterns
        for pattern, replacement in self.account_cleaning_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Standardize common account types
        if 'CHECKING' in cleaned.upper():
            if 'EVERYDAY' in cleaned.upper():
                cleaned = re.sub(r'EVERYDAY\s+CHECKING', 'Everyday Checking', cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def clean_institution(self, institution: str) -> str:
        """Clean institution names"""
        if pd.isna(institution) or institution == 'Institution':
            return institution
        
        cleaned = str(institution).strip()
        
        # Apply cleaning patterns
        for pattern, replacement in self.institution_cleaning_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Remove account type info that shouldn't be in institution
        cleaned = re.sub(r'\s*(CHECKING|SAVINGS|CREDIT CARD).*$', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def clean_reference_number(self, ref_num: str) -> str:
        """Clean reference numbers"""
        if pd.isna(ref_num) or ref_num in ['nan', 'Reference Number']:
            return ""
        
        # Just extract the numeric part if present
        match = re.search(r'\d{4,}', str(ref_num))
        return match.group(0) if match else ""
    
    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process entire dataframe through all cleaning stages.
        Creates all missing columns and cleans existing ones.
        """
        log.info("Starting comprehensive transaction data cleaning...")
        
        # Create a copy to avoid modifying original
        cleaned_df = df.copy()
        
        # STAGE 1: Create cleaned Description from OriginalDescription
        if 'OriginalDescription' in cleaned_df.columns:
            log.info("Stage 1: Creating cleaned Description from OriginalDescription...")
            cleaned_df['Description'] = cleaned_df['OriginalDescription'].apply(self.clean_description)
            
            # Log improvement statistics
            orig_lengths = cleaned_df['OriginalDescription'].str.len().mean()
            new_lengths = cleaned_df['Description'].str.len().mean()
            log.info(f"  Average length reduced from {orig_lengths:.1f} to {new_lengths:.1f} characters")
        
        # STAGE 2: Populate OriginalMerchant
        # This column might already exist and be partially populated by schema mapping (e.g., from Monarch, Rocket Money)
        log.info("Stage 2: Populating OriginalMerchant...")
        if 'OriginalMerchant' not in cleaned_df.columns:
            cleaned_df['OriginalMerchant'] = pd.Series([np.nan] * len(cleaned_df), index=cleaned_df.index, dtype=object)

        # Ensure OriginalMerchant is string type for consistency before filling NaNs
        # This handles cases where it might be all NaN and thus float
        cleaned_df['OriginalMerchant'] = cleaned_df['OriginalMerchant'].astype(str).replace('nan', '')


        # Identify rows where OriginalMerchant is missing (NaN or empty string after schema mapping)
        # and OriginalDescription is available.
        if 'OriginalDescription' in cleaned_df.columns:
            missing_original_merchant_mask = (
                pd.isna(cleaned_df['OriginalMerchant']) | (cleaned_df['OriginalMerchant'] == '')
            )
            
            if missing_original_merchant_mask.any():
                log.info("  Extracting OriginalMerchant from OriginalDescription for missing values...")
                cleaned_df.loc[missing_original_merchant_mask, 'OriginalMerchant'] = \
                    cleaned_df.loc[missing_original_merchant_mask, 'OriginalDescription'].apply(
                        self.extract_original_merchant
                    )
        else:
            log.warning("  OriginalDescription column not found, cannot extract OriginalMerchant for missing values.")

        # Ensure OriginalMerchant is not empty, default to "Unknown" if it's still empty after processing
        # However, it's better to let standardize_merchant handle this.
        # cleaned_df['OriginalMerchant'] = cleaned_df['OriginalMerchant'].fillna("").replace("", "Unknown") # Avoid this here

        # STAGE 3: Standardize Merchant from OriginalMerchant
        if 'OriginalMerchant' in cleaned_df.columns:
            log.info("Stage 3: Standardizing Merchant from OriginalMerchant...")
            cleaned_df['Merchant'] = cleaned_df['OriginalMerchant'].apply(self.standardize_merchant)
            
            # Log merchant consolidation statistics
            orig_unique = cleaned_df['OriginalMerchant'].nunique()
            new_unique = cleaned_df['Merchant'].nunique()
            log.info(f"  Merchants consolidated from {orig_unique} to {new_unique} unique values")
        
        # STAGE 4: Clean other columns identified in analysis
        if 'Account' in cleaned_df.columns:
            log.info("Stage 4: Cleaning Account names...")
            cleaned_df['Account'] = cleaned_df['Account'].apply(self.clean_account)
        
        if 'Institution' in cleaned_df.columns:
            log.info("Stage 5: Cleaning Institution names...")
            cleaned_df['Institution'] = cleaned_df['Institution'].apply(self.clean_institution)
        
        if 'ReferenceNumber' in cleaned_df.columns:
            log.info("Stage 6: Cleaning Reference Numbers...")
            cleaned_df['ReferenceNumber'] = cleaned_df['ReferenceNumber'].apply(
                self.clean_reference_number
            )
        
        # Log final statistics
        log.info("\nCleaning complete! Summary of changes:")
        
        # Check key improvements
        if 'Description' in cleaned_df.columns and 'OriginalDescription' in cleaned_df.columns:
            unchanged_desc = (cleaned_df['Description'] == cleaned_df['OriginalDescription']).sum()
            log.info(f"  Descriptions unchanged: {unchanged_desc} ({unchanged_desc/len(cleaned_df)*100:.1f}%)")
        
        if 'Merchant' in cleaned_df.columns:
            top_merchants = cleaned_df['Merchant'].value_counts().head(10)
            log.info("  Top 10 standardized merchants:")
            for merchant, count in top_merchants.items():
                log.info(f"    {merchant}: {count}")
        
        return cleaned_df


# Integration helper for csv_consolidator.py
def apply_comprehensive_cleaning(df: pd.DataFrame, 
                               analysis_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Main entry point for comprehensive cleaning.
    Call this from csv_consolidator.py after schema transformations.
    """
    # Initialize cleaner with analysis results if available
    if analysis_path is None:
        # Try to find analysis results in standard location
        analysis_path = Path('comprehensive_analysis_results')
        if not analysis_path.exists():
            analysis_path = Path('transaction_analysis_results')
    
    cleaner = ComprehensiveTransactionCleaner(analysis_path)
    return cleaner.process_dataframe(df)
