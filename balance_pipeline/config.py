"""Configuration for the balance pipeline."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class AnalysisConfig:
    """Configuration parameters for the analysis."""
    
    RYAN_PCT: float = 0.43
    JORDYN_PCT: float = 0.57
    # Add other config parameters here


class DataQualityFlag(Enum):
    """Enumeration of data quality issues."""
    
    CLEAN = "CLEAN"
    MISSING_DATE = "MISSING_DATE"
    # Add other flags here
