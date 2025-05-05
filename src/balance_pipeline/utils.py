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

import pandas as pd
import re
import unicodedata
import logging

log = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Function: _strip_accents (Moved from normalize.py)
# ------------------------------------------------------------------------------
def _strip_accents(txt: str | None) -> str:
    """Removes accent marks from characters in a string."""
    if pd.isna(txt):
        return ""
    try:
        txt = str(txt) # Ensure input is string
        return "".join(
            ch for ch in unicodedata.normalize("NFD", txt)
            if unicodedata.category(ch) != "Mn"
        )
    except TypeError:
        log.warning(f"Could not strip accents from non-string input: {type(txt)}. Returning empty string.")
        return ""

# ------------------------------------------------------------------------------
# Function: _clean_desc (Moved from normalize.py)
# ------------------------------------------------------------------------------
def _clean_desc(desc: str | None) -> str:
    """Cleans description text for easier matching and analysis."""
    if pd.isna(desc):
        return ""

    try:
        desc = _strip_accents(str(desc)).upper()
        desc = re.sub(r"[^A-Z0-9 ]+", " ", desc)
        desc = re.sub(r"\s+", " ", desc)
        return desc.strip()
    except Exception as e:
        log.warning(f"Error cleaning description: '{desc}'. Error: {e}. Returning original.")
        return str(desc or '') # Return original string or empty if error

# Add other utility functions here as needed.
