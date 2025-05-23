# -*- coding: utf-8 -*-
"""
==============================================================================
Module: merchant.py
Project: BALANCE-pyexcel
Description: Handles normalization of merchant descriptions using a lookup
             table with regular expressions to map raw descriptions to
             canonical names.
==============================================================================

Version: 0.1.0
Last Modified: 2025-05-04
Author: AI Assistant (Cline)
"""

import re
import csv
import logging
from functools import lru_cache
from typing import List, Tuple, Pattern as TypingPattern  # Added List, Tuple, Pattern

# Import config for path settings
from . import config

# Import the cleaning function from the new utils module
from .utils import _clean_desc_single


# --- Setup Logger ---
log = logging.getLogger(__name__)

# --- Load Lookup Table ---
_LOOKUP: List[Tuple[TypingPattern[str], str]] = []  # Updated type hint
# Use the path defined in config.py
_LOOKUP_PATH = config.MERCHANT_LOOKUP_PATH

try:
    log.info(f"Loading merchant lookup table from: {_LOOKUP_PATH}")
    # Ensure the path exists before trying to open it
    if not _LOOKUP_PATH.is_file():
        log.error(
            f"Merchant lookup file not found at configured path: '{_LOOKUP_PATH}'. Merchant normalization will not work."
        )
    else:
        with open(_LOOKUP_PATH, mode="r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or not (
                "pattern" in reader.fieldnames and "canonical" in reader.fieldnames
            ):
                log.error(
                    f"Merchant lookup file '{_LOOKUP_PATH}' missing required columns 'pattern' or 'canonical'. Fieldnames: {reader.fieldnames}"
                )
            else:
                count = 0
                for row in reader:
                    try:
                        # Compile regex with case-insensitivity (re.I)
                        pattern = re.compile(row["pattern"], re.IGNORECASE)
                        # Strip potential inline comments starting with '#' from canonical name
                        canonical = row["canonical"].split("#")[0].strip()
                        _LOOKUP.append((pattern, canonical))
                        count += 1
                    except re.error as e_re:
                        log.warning(
                            f"Invalid regex pattern in lookup file row {reader.line_num}: '{row.get('pattern', '')}'. Error: {e_re}"
                        )
                    except Exception as e_row:
                        log.warning(
                            f"Error processing row {reader.line_num} in lookup file: {e_row}"
                        )
            log.info(f"Successfully loaded and compiled {count} merchant patterns.")

# Removed FileNotFoundError handler as the check is done above
except Exception as e:
    log.error(f"Failed to load or process merchant lookup file '{_LOOKUP_PATH}': {e}")

# --- Normalization Function ---


@lru_cache(maxsize=4096)  # Cache results for frequently seen descriptions
def normalize_merchant(raw_desc: str | None) -> str:
    """
    Normalizes a raw merchant description string.

    1. Applies basic cleaning (accents, case, whitespace) using _clean_desc.
    2. Searches through the compiled regex patterns from merchant_lookup.csv.
    3. Returns the corresponding canonical name if a pattern matches.
    4. If no pattern matches, returns the cleaned description, title-cased.

    Args:
        raw_desc (str | None): The raw merchant description string.

    Returns:
        str: The canonical merchant name or a title-cased cleaned version.
    """
    if raw_desc is None:
        return ""

    # Apply initial cleaning (e.g., accents, extra spaces, uppercase)
    cleaned_desc = _clean_desc_single(str(raw_desc))

    # Check against loaded regex patterns
    for regex_pattern, canonical_name in _LOOKUP:
        if regex_pattern.search(cleaned_desc):
            log.debug(
                f"Matched pattern '{regex_pattern.pattern}' for '{cleaned_desc}', returning '{canonical_name}'"
            )
            return canonical_name

    # If no pattern matched, return the cleaned description, title-cased
    # Title casing makes "MY COFFEE SHOP" look like "My Coffee Shop"
    title_cased_fallback = cleaned_desc.title()
    log.debug(
        f"No pattern matched for '{cleaned_desc}', returning title-cased: '{title_cased_fallback}'"
    )
    return title_cased_fallback


# ==============================================================================
# END OF FILE: merchant.py
# ==============================================================================
