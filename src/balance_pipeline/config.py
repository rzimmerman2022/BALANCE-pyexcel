from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

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
    # TODO P1: Add path for external business rules YAML


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
