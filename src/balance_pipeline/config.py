from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_resource_path(relative_path: str | Path) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        # Not frozen, running in normal Python environment
        base_path = Path(__file__).parent.parent.parent  # Go up to project root
    return base_path / relative_path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_INBOX_DEFAULT = Path(
    os.getenv("CSV_INBOX", PROJECT_ROOT / "csv_inbox")
).expanduser()
SCHEMA_REGISTRY_PATH = Path(
    os.getenv("SCHEMA_REGISTRY", get_resource_path("rules/schema_registry.yml"))
)
MERCHANT_LOOKUP_PATH = Path(
    os.getenv("MERCHANT_LOOKUP", get_resource_path("rules/merchant_lookup.csv"))
)

# Default output formats and paths
DEFAULT_OUTPUT_FORMAT = "parquet"
SUPPORTED_OUTPUT_FORMATS = ["excel", "parquet", "csv", "powerbi"]

# Schema configuration
SCHEMA_MODE = os.getenv("SCHEMA_MODE", "strict").lower()
if SCHEMA_MODE not in ["strict", "flexible"]:
    SCHEMA_MODE = "strict"

# Core Required Columns - must match CORE_FOUNDATION_COLUMNS from foundation.py
CORE_REQUIRED_COLUMNS = [
    "TxnID",  # Unique transaction identifier
    "Owner",  # Owner of the transaction (Ryan/Jordyn)
    "Date",  # Transaction date
    "Amount",  # Transaction amount
    "Merchant",  # Cleaned merchant name
    "Description",  # Cleaned, human-readable transaction description
    "Category",  # Transaction category
    "Account",  # Account identifier
    "sharing_status",  # Sharing status ('individual', 'shared', 'split')
]

# Optional Column Groups - defines which columns are grouped together
# These groups help determine which columns to include in flexible mode
OPTIONAL_COLUMN_GROUPS = {
    "accounting": [
        "AccountType",
        "AccountLast4",
        "Bank",
        "PostDate",
    ],
    "metadata": [
        "DataSourceName",
        "Source",
        "data_quality_flag",
        "LineageNotes",
    ],
    "sharing": [
        "PayerBalance",
        "Jordyn_Balance",
        "Ryan_Balance",
        "Jordyn_Effective_Share",
        "Ryan_Effective_Share",
    ],
    "settlement": [
        "is_settlement",
        "settlement_summary",
    ],
}

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
        "fry",
        "safeway",
        "walmart",
        "target",
        "costco",
        "trader joe",
        "whole foods",
        "kroger",
        "albertsons",
        "grocery",
        "sprouts",
    ],
    "Utilities": [
        "electric",
        "gas",
        "water",
        "internet",
        "phone",
        "cox",
        "srp",
        "aps",
        "centurylink",
        "utility",
        "conservice",
        "google fi",
        "t-mobile",
        "verizon",
    ],
    "Dining Out": [
        "restaurant",
        "cafe",
        "coffee",
        "starbucks",
        "pizza",
        "sushi",
        "mcdonald",
        "chipotle",
        "subway",
        "doordash",
        "grubhub",
        "uber eats",
        "postmates",
        "culinary dropout",
        "bar",
    ],
    "Transport": [
        "uber",
        "lyft",
        "gas station",
        "shell",
        "chevron",
        "circle k",
        "qt",
        "auto repair",
        "fuel",
        "parking",
        "toll",
        "bird",
        "lime",
        "waymo",
    ],
    "Entertainment": [
        "movie",
        "theater",
        "netflix",
        "spotify",
        "hulu",
        "disney",
        "concert",
        "event",
        "game",
        "amc",
        "cinemark",
        "ticketmaster",
        "steam",
    ],
    "Healthcare": [
        "pharmacy",
        "cvs",
        "walgreens",
        "doctor",
        "medical",
        "dental",
        "clinic",
        "hospital",
        "optometrist",
        "vision",
    ],
    "Shopping": [
        "amazon",
        "best buy",
        "macys",
        "nordstrom",
        "online store",
        "retail",
        "clothing",
        "electronics",
        "home goods",
        "ikea",
    ],
    "Travel": [
        "airline",
        "hotel",
        "airbnb",
        "expedia",
        "booking.com",
        "southwest",
        "delta",
        "united",
    ],
    "Services": [
        "haircut",
        "gym",
        "consulting",
        "legal",
        "accounting",
        "cleaning",
    ],
    "Rent": ["rent", "property management", "landlord"],
    "Other Expenses": [],  # Fallback
}

# Cached rules to avoid repeated file I/O
_CACHED_RULES: dict[str, Any] = {}
_CACHE_LOCK = threading.RLock()  # Reentrant lock for thread safety


def load_rules(path: str) -> dict[str, Any]:
    """
    Load business rules from YAML file with thread-safe caching.

    Args:
        path: Path to the YAML rules file

    Returns:
        Dictionary containing the parsed rules
    """
    global _CACHED_RULES

    # Fast path: return cached version if already loaded (with lock for read)
    with _CACHE_LOCK:
        if path in _CACHED_RULES:
            return _CACHED_RULES[path].copy()  # Return a copy to prevent mutation

    # Slow path: load from file
    rules_path = Path(path)
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

    try:
        with open(rules_path, encoding="utf-8") as f:
            rules = yaml.safe_load(f)

        # Cache the loaded rules with thread safety
        with _CACHE_LOCK:
            _CACHED_RULES[path] = rules

        return rules.copy() if isinstance(rules, dict) else rules

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in rules file {rules_path}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error loading rules from {rules_path}: {e}") from e
