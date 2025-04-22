# -*- coding: utf-8 -*-
"""
==============================================================================
Module: utils.py
Project: BALANCE-pyexcel
Description: Contains shared, general-purpose utility functions used across
             different modules within the balance_pipeline package.
             These helpers typically have no side effects and don't belong
             to a specific data processing stage (like ingest or normalize).
==============================================================================

Version: 0.1.0
Last Modified: 2025-04-21 # Placeholder date
Author: Your Name / AI Assistant
"""

# ==============================================================================
# 0. IMPORTS
# ==============================================================================
from __future__ import annotations # Allows type hint usage like str | None
import hashlib                   # For SHA-256 hashing
import unicodedata             # For Unicode normalization (accent stripping)
import re                      # For regular expressions (whitespace cleaning)
import pandas as pd              # For pd.isna() check

# ==============================================================================
# 1. TEXT HELPER FUNCTIONS
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: strip_accents
# ------------------------------------------------------------------------------
def strip_accents(text: str | None) -> str:
    """
    Removes accent marks (diacritics) from characters in a string.
    Useful for creating reliable matches, e.g., 'CAFÉ' becomes 'CAFE'.

    Args:
        text (str | None): The input string (or None/NaN).

    Returns:
        str: The text with accents removed, or an empty string if input was None/NaN.
    """
    # Handle potential None or pandas NA values gracefully.
    if pd.isna(text):
        return ""
    try:
        # Ensure input is treated as a string.
        text = str(text)
        # Normalize to NFD (Canonical Decomposition) to separate accents.
        # Then, keep only characters that are not 'Mn' (Mark, Nonspacing).
        return "".join(
            ch
            for ch in unicodedata.normalize("NFD", text)
            if unicodedata.category(ch) != "Mn"
        )
    except TypeError:
        # Fallback if input cannot be converted to string.
        return ""

# ------------------------------------------------------------------------------
# Function: clean_whitespace
# ------------------------------------------------------------------------------
def clean_whitespace(text: str | None) -> str:
    """
    Cleans text by stripping accents, uppercasing, trimming, and squashing multiple spaces.

    Args:
        text (str | None): The input string (or None/NaN).

    Returns:
        str: The cleaned and standardized string, or an empty string if input was None/NaN.
    """
    if pd.isna(text):
        # Handle missing or NaN input.
        return ""
    try:
        # Apply accent stripping first, then convert to uppercase.
        text = strip_accents(str(text)).upper()
        # Replace one or more whitespace characters (\s+) with a single space.
        text = re.sub(r"\s+", " ", text)
        # Remove leading and trailing whitespace.
        return text.strip()
    except Exception as e:
        # Fallback in case of unexpected errors during cleaning.
        # Consider logging this if it happens frequently.
        # logging.warning(f"Could not clean whitespace for text '{text}': {e}")
        return str(text or '') # Return original string or empty

# ==============================================================================
# 2. HASHING HELPER FUNCTIONS
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: sha256_hex
# ------------------------------------------------------------------------------
def sha256_hex(s: str, length: int = 16) -> str:
    """
    Calculates the SHA-256 hash of a string and returns its hexadecimal digest,
    optionally truncated to a specific length.

    Args:
        s (str): The input string to hash.
        length (int, optional): The desired length of the output hash string.
                                Defaults to 16. Set to 64 for the full hash.

    Returns:
        str: The truncated hexadecimal representation of the SHA-256 hash.
    """
    # Ensure the input string is encoded to bytes (using UTF-8) before hashing.
    # Calculate the SHA-256 hash.
    # Get the hexadecimal representation of the hash digest.
    # Truncate the hex digest to the specified length.
    try:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:length]
    except Exception as e:
        # Handle potential errors during hashing (though unlikely for strings)
        # Consider logging this error.
        # logging.error(f"Could not generate SHA-256 hash for input: {e}")
        return "error_hashing" # Return a placeholder or raise error

# ==============================================================================
# END OF FILE: utils.py
# ==============================================================================