# -*- coding: utf-8 -*-
"""
==============================================================================
Module: utils.py
Project: BALANCE-pyexcel
Description: Common utility functions shared across the balance_pipeline package.
==============================================================================

Version: 0.1.0
Last Modified: 2025-05-04
Author: AI Assistant (Cline)
"""

from __future__ import annotations  # For using type hints before full definition
import pandas as pd
import re
import unicodedata
import logging
from typing import TYPE_CHECKING, Any  # Added TYPE_CHECKING and Any
from balance_pipeline.errors import DataConsistencyError

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    Series = pd.Series[Any]  # for static typing only
else:
    Series = pd.Series  # runtime-safe alias


# ------------------------------------------------------------------------------
# Function: _strip_accents (Moved from normalize.py)
# ------------------------------------------------------------------------------
def _strip_accents(txt: str | None) -> str:
    """Removes accent marks from characters in a string."""
    if pd.isna(txt):
        return ""
    try:
        txt = str(txt)  # Ensure input is string
        return "".join(
            ch
            for ch in unicodedata.normalize("NFD", txt)
            if unicodedata.category(ch) != "Mn"
        )
    except TypeError as e:
        raise DataConsistencyError(
            f"Could not strip accents from non-string input: {type(txt)}"
        ) from e


# ------------------------------------------------------------------------------
# Function: _clean_desc (Original, for single string)
# ------------------------------------------------------------------------------
def _clean_desc_single(desc: str | None) -> str:
    """Cleans description text for easier matching and analysis (single string version)."""
    if pd.isna(desc):
        return ""

    try:
        # Step 1: Strip accents and convert to string (applies to single string)
        desc_stripped = _strip_accents(str(desc))
        # Step 2: Convert to uppercase
        desc_upper = desc_stripped.upper()
        # Step 3: Replace non-alphanumeric characters (excluding space) with a space
        desc_alphanum = re.sub(r"[^A-Z0-9 ]+", " ", desc_upper)
        # Step 4: Replace multiple spaces with a single space
        desc_single_space = re.sub(r"\s+", " ", desc_alphanum)
        # Step 5: Strip leading/trailing whitespace
        return desc_single_space.strip()
    except Exception as e:
        raise DataConsistencyError(
            f"Error cleaning description: '{desc}'. Error: {e}"
        ) from e


# ------------------------------------------------------------------------------
# Function: clean_desc_vectorized (New, for pandas Series)
# ------------------------------------------------------------------------------
def clean_desc_vectorized(
    desc_series: Series,
) -> Series:  # Changed pd.Series to Series alias
    """
    Cleans a pandas Series of description strings using vectorized operations.
    """
    if not isinstance(desc_series, pd.Series):
        raise TypeError("Input must be a pandas Series.")

    # Handle NaNs by filling with empty string for processing, then can be reverted if needed
    original_na = desc_series.isna()
    series_filled_na = desc_series.fillna("")

    # Step 1: Strip accents (still needs .apply for unicodedata, but on the series)
    # Ensure series is string type before applying _strip_accents
    stripped_series = series_filled_na.astype(str).apply(_strip_accents)

    # Step 2: Convert to uppercase
    upper_series = stripped_series.str.upper()

    # Step 3: Replace non-alphanumeric characters (excluding space) with a space
    # Regex is applied per element, but .str.replace is vectorized
    alphanum_series = upper_series.str.replace(r"[^A-Z0-9 ]+", " ", regex=True)

    # Step 4: Replace multiple spaces with a single space
    single_space_series = alphanum_series.str.replace(r"\s+", " ", regex=True)

    # Step 5: Strip leading/trailing whitespace
    cleaned_series = single_space_series.str.strip()

    # Restore NaNs if they were originally present
    cleaned_series.loc[original_na] = pd.NA  # Or np.nan if preferred

    return cleaned_series


# Add other utility functions here as needed.
