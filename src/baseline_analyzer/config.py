from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict

# Design constants
TABLEAU_COLORBLIND_10 = [
    "#007ACC",
    "#FFB000",
    "#FE6100",
    "#785EF0",
    "#64B200",
    "#FF4B97",
    "#00C1FF",
    "#648FFF",
    "#DC267F",
    "#FFB000",
]

@dataclass
class AnalysisConfig:
    """Configuration parameters for the analysis"""

    RYAN_PCT: float = 0.43
    JORDYN_PCT: float = 0.57
    # Split percentages for non-rent shared expenses (default 50/50)
    EXPENSE_RYAN_PCT: float = 0.50
    EXPENSE_JORDYN_PCT: float = 0.50
    CONFIDENCE_LEVEL: float = 0.95
    DATA_QUALITY_THRESHOLD: float = 0.90
    OUTLIER_THRESHOLD: float = 5000.0
    RENT_BASELINE: float = 2100.0
    RENT_VARIANCE_THRESHOLD: float = 0.10  # For rent allocation vs baseline
    RENT_BUDGET_VARIANCE_THRESHOLD_PCT: float = 10.0  # For rent history vs allocation
    LIQUIDITY_STRAIN_THRESHOLD: float = 5000.0
    LIQUIDITY_STRAIN_DAYS: int = 60
    CONCENTRATION_RISK_THRESHOLD: float = 0.40
    CURRENCY_PRECISION: int = 2
    MAX_MEMORY_MB: int = 500
    MAX_PROCESSING_TIME_SECONDS: int = 150  # Increased due to more files and processing
    
    # P0: Observability Enhancement from Blueprint
    debug_mode: bool = False 
    external_business_rules_yaml_path: str = "config/business_rules.yml"


class DataQualityFlag(Enum):
    """Enumeration of data quality issues"""

    CLEAN = "CLEAN"
    MISSING_DATE = "MISSING_DATE"
    MISALIGNED_ROW = "MISALIGNED_ROW"
    DUPLICATE_SUSPECTED = "DUPLICATE_SUSPECTED"
    OUTLIER_AMOUNT = "OUTLIER_AMOUNT"
    MANUAL_CALCULATION_NOTE = "MANUAL_CALCULATION_NOTE"
    NEGATIVE_AMOUNT = "NEGATIVE_AMOUNT"
    RENT_VARIANCE_HIGH = "RENT_VARIANCE_HIGH"  # Used for Rent Alloc vs Baseline
    RENT_BUDGET_VARIANCE_HIGH = (
        "RENT_BUDGET_VARIANCE_HIGH"  # Used for Rent Hist vs Alloc
    )
    NON_NUMERIC_VALUE_CLEANED = "NON_NUMERIC_VALUE_CLEANED"
    BALANCE_MISMATCH_WITH_LEDGER = "BALANCE_MISMATCH_WITH_LEDGER"

# Placeholder for future externalized business rules (P1)
# For now, these could be constants here or loaded if config file exists
DEFAULT_SETTLEMENT_KEYWORDS = ["venmo", "zelle", "cash app", "paypal"]
DEFAULT_CALCULATION_NOTE_TRIGGER = "2x to calculate"

# Placeholder for merchant categorization rules (P1)
# This would ideally be loaded from YAML
DEFAULT_MERCHANT_CATEGORIES = {
    "Groceries": [
        "fry", "safeway", "walmart", "target", "costco", "trader joe", 
        "whole foods", "kroger", "albertsons", "grocery", "sprouts",
    ],
    "Utilities": [
        "electric", "gas", "water", "internet", "phone", "cox", "srp", 
        "aps", "centurylink", "utility", "conservice", "google fi", 
        "t-mobile", "verizon",
    ],
    "Dining Out": [
        "restaurant", "cafe", "coffee", "starbucks", "pizza", "sushi", 
        "mcdonald", "chipotle", "subway", "doordash", "grubhub", 
        "uber eats", "postmates", "culinary dropout", "bar",
    ],
    "Transport": [
        "uber", "lyft", "gas station", "shell", "chevron", "circle k", "qt", 
        "auto repair", "fuel", "parking", "toll", "bird", "lime", "waymo",
    ],
    "Entertainment": [
        "movie", "theater", "netflix", "spotify", "hulu", "disney", 
        "concert", "event", "game", "amc", "cinemark", "ticketmaster", "steam",
    ],
    "Healthcare": [
        "pharmacy", "cvs", "walgreens", "doctor", "medical", "dental", 
        "clinic", "hospital", "optometrist", "vision",
    ],
    "Shopping": [
        "amazon", "best buy", "macys", "nordstrom", "online store", "retail", 
        "clothing", "electronics", "home goods", "ikea",
    ],
    "Travel": [
        "airline", "hotel", "airbnb", "expedia", "booking.com", 
        "southwest", "delta", "united",
    ],
    "Services": [
        "haircut", "gym", "consulting", "legal", "accounting", "cleaning",
    ],
    "Rent": ["rent", "property management", "landlord"],
    "Other Expenses": [] # Fallback
}

# Cached rules to avoid repeated file I/O
_CACHED_RULES: Dict[str, Any] = {}

def load_rules(path: str) -> Dict[str, Any]:
    """
    Load business rules from YAML file with caching.
    
    Args:
        path: Path to the YAML rules file
        
    Returns:
        Dictionary containing the parsed rules
    """
    global _CACHED_RULES
    
    # Return cached version if already loaded
    if path in _CACHED_RULES:
        return _CACHED_RULES[path]
    
    rules_path = Path(path)
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
        
        # Cache the loaded rules
        _CACHED_RULES[path] = rules
        return rules
        
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in rules file {rules_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading rules from {rules_path}: {e}")



# --- YAML Settings loader (BA Sprint 1) ---
class Settings(BaseSettings):
    """Pydantic settings loaded from YAML with optional env overrides (BA_*)"""

    opening_balance_col: str
    baseline_date_format: str
    merchant_lookup_path: str

    model_config = SettingsConfigDict(env_prefix="BA_")

_default_yaml_path = (
    Path(__file__).resolve().parents[2] / "config" / "balance_analyzer.yaml"
)


def load_config(path: Path | None = None) -> Settings:
    """Load Settings from YAML, allowing env var overrides."""
    cfg_path = Path(path) if path else _default_yaml_path
    with open(cfg_path, "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)
    return Settings(**yaml_data)
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict

# Design constants
TABLEAU_COLORBLIND_10 = [
    "#007ACC",
    "#FFB000",
    "#FE6100",
    "#785EF0",
    "#64B200",
    "#FF4B97",
    "#00C1FF",
    "#648FFF",
    "#DC267F",
    "#FFB000",
]

@dataclass
class AnalysisConfig:
    """Configuration parameters for the analysis"""

    RYAN_PCT: float = 0.43
    JORDYN_PCT: float = 0.57
    # Split percentages for non-rent shared expenses (default 50/50)
    EXPENSE_RYAN_PCT: float = 0.50
    EXPENSE_JORDYN_PCT: float = 0.50
    CONFIDENCE_LEVEL: float = 0.95
    DATA_QUALITY_THRESHOLD: float = 0.90
    OUTLIER_THRESHOLD: float = 5000.0
    RENT_BASELINE: float = 2100.0
    RENT_VARIANCE_THRESHOLD: float = 0.10  # For rent allocation vs baseline
    RENT_BUDGET_VARIANCE_THRESHOLD_PCT: float = 10.0  # For rent history vs allocation
    LIQUIDITY_STRAIN_THRESHOLD: float = 5000.0
    LIQUIDITY_STRAIN_DAYS: int = 60
    CONCENTRATION_RISK_THRESHOLD: float = 0.40
    CURRENCY_PRECISION: int = 2
    MAX_MEMORY_MB: int = 500
    MAX_PROCESSING_TIME_SECONDS: int = 150  # Increased due to more files and processing
    
    # P0: Observability Enhancement from Blueprint
    debug_mode: bool = False 
    external_business_rules_yaml_path: str = "config/business_rules.yml"


class DataQualityFlag(Enum):
    """Enumeration of data quality issues"""

    CLEAN = "CLEAN"
    MISSING_DATE = "MISSING_DATE"
    MISALIGNED_ROW = "MISALIGNED_ROW"
    DUPLICATE_SUSPECTED = "DUPLICATE_SUSPECTED"
    OUTLIER_AMOUNT = "OUTLIER_AMOUNT"
    MANUAL_CALCULATION_NOTE = "MANUAL_CALCULATION_NOTE"
    NEGATIVE_AMOUNT = "NEGATIVE_AMOUNT"
    RENT_VARIANCE_HIGH = "RENT_VARIANCE_HIGH"  # Used for Rent Alloc vs Baseline
    RENT_BUDGET_VARIANCE_HIGH = (
        "RENT_BUDGET_VARIANCE_HIGH"  # Used for Rent Hist vs Alloc
    )
    NON_NUMERIC_VALUE_CLEANED = "NON_NUMERIC_VALUE_CLEANED"
    BALANCE_MISMATCH_WITH_LEDGER = "BALANCE_MISMATCH_WITH_LEDGER"

# Placeholder for future externalized business rules (P1)
# For now, these could be constants here or loaded if config file exists
DEFAULT_SETTLEMENT_KEYWORDS = ["venmo", "zelle", "cash app", "paypal"]
DEFAULT_CALCULATION_NOTE_TRIGGER = "2x to calculate"

# Placeholder for merchant categorization rules (P1)
# This would ideally be loaded from YAML
DEFAULT_MERCHANT_CATEGORIES = {
    "Groceries": [
        "fry", "safeway", "walmart", "target", "costco", "trader joe", 
        "whole foods", "kroger", "albertsons", "grocery", "sprouts",
    ],
    "Utilities": [
        "electric", "gas", "water", "internet", "phone", "cox", "srp", 
        "aps", "centurylink", "utility", "conservice", "google fi", 
        "t-mobile", "verizon",
    ],
    "Dining Out": [
        "restaurant", "cafe", "coffee", "starbucks", "pizza", "sushi", 
        "mcdonald", "chipotle", "subway", "doordash", "grubhub", 
        "uber eats", "postmates", "culinary dropout", "bar",
    ],
    "Transport": [
        "uber", "lyft", "gas station", "shell", "chevron", "circle k", "qt", 
        "auto repair", "fuel", "parking", "toll", "bird", "lime", "waymo",
    ],
    "Entertainment": [
        "movie", "theater", "netflix", "spotify", "hulu", "disney", 
        "concert", "event", "game", "amc", "cinemark", "ticketmaster", "steam",
    ],
    "Healthcare": [
        "pharmacy", "cvs", "walgreens", "doctor", "medical", "dental", 
        "clinic", "hospital", "optometrist", "vision",
    ],
    "Shopping": [
        "amazon", "best buy", "macys", "nordstrom", "online store", "retail", 
        "clothing", "electronics", "home goods", "ikea",
    ],
    "Travel": [
        "airline", "hotel", "airbnb", "expedia", "booking.com", 
        "southwest", "delta", "united",
    ],
    "Services": [
        "haircut", "gym", "consulting", "legal", "accounting", "cleaning",
    ],
    "Rent": ["rent", "property management", "landlord"],
    "Other Expenses": [] # Fallback
}

# Cached rules to avoid repeated file I/O
_CACHED_RULES: Dict[str, Any] = {}

def load_rules(path: str) -> Dict[str, Any]:
    """
    Load business rules from YAML file with caching.
    
    Args:
        path: Path to the YAML rules file
        
    Returns:
        Dictionary containing the parsed rules
    """
    global _CACHED_RULES
    
    # Return cached version if already loaded
    if path in _CACHED_RULES:
        return _CACHED_RULES[path]
    
    rules_path = Path(path)
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
        
        # Cache the loaded rules
        _CACHED_RULES[path] = rules
        return rules
        
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in rules file {rules_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading rules from {rules_path}: {e}")



# --- YAML Settings loader (BA Sprint 1) ---
class Settings(BaseSettings):
    """Pydantic settings loaded from YAML with optional env overrides (BA_*)"""

    opening_balance_col: str
    baseline_date_format: str
    merchant_lookup_path: str

    model_config = SettingsConfigDict(env_prefix="BA_")

_default_yaml_path = (
    Path(__file__).resolve().parents[2] / "config" / "balance_analyzer.yaml"
)


def load_config(path: Path | None = None) -> Settings:
    """Load Settings from YAML, allowing env var overrides."""
    cfg_path = Path(path) if path else _default_yaml_path
    with open(cfg_path, "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)
    return Settings(**yaml_data)
