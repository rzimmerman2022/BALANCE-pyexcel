import logging
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast  # Added Dict, List, Set

import yaml
from balance_pipeline.errors import FatalSchemaError  # Added import
from balance_pipeline.schema_types import MatchResult, Schema

# Setup logger for this module
logger = logging.getLogger(__name__)


def load_registry(path: Path) -> list[dict[str, Any]]:
    """
    Load the full schema registry from a YAML file.
    Note: This function is primarily for backward compatibility.
    The main schema loading now happens lazily via _ensure_schemas_loaded().
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return cast(list[dict[str, Any]], data)


# --------------------------------------------------------------------------- #
# Canonicalisation helper for schema keys and aliases
# --------------------------------------------------------------------------- #
_NON_ALNUM = re.compile(r"[^a-z0-9\s]")


def _canon(text: str) -> str:
    """
    Canonicalise a string:
    • lower-case
    • remove non-alphanumeric (except spaces)
    • collapse whitespace to single space
    """
    text = _NON_ALNUM.sub("", text.lower()).strip()
    return re.sub(r"\s+", " ", text)


# --------------------------------------------------------------------------- #
# Load schema definitions from YAML files in rules directory
# --------------------------------------------------------------------------- #
_SCHEMA_DIR = Path(__file__).parent.parent.parent / "rules"

# _DETAILED_RULES_LIST is no longer loaded from schema_registry.yml directly here.
# _DETAILED_RULES_MAP will be populated by _load_and_build_schema_maps.

_ALL_LOADED_SCHEMAS: list[dict[str, Any]] | None = None
_SCHEMAS_RULES_MAP: dict[str, dict[str, Any]] | None = (
    None  # Maps schema id to its rules dict
)
_GENERIC_SCHEMA_RULES: dict[str, Any] | None = None  # Holds the rules for 'generic_csv'
_schemas_loaded = False  # Track whether schemas have been loaded


def _ensure_schemas_loaded() -> None:
    """Ensure schemas are loaded before use."""
    global _schemas_loaded
    if not _schemas_loaded:
        _load_and_build_schema_maps()
        _schemas_loaded = True


def _load_and_build_schema_maps() -> None:
    """
    Reads all individual schema .yaml files from the rules/ directory.
    Populates _ALL_LOADED_SCHEMAS with the content of these files (full schema definitions).
    Populates _SCHEMAS_RULES_MAP mapping schema 'id' to its full rule dictionary.
    Sets _GENERIC_SCHEMA_RULES if 'generic_csv' is found.
    """
    global _ALL_LOADED_SCHEMAS, _SCHEMAS_RULES_MAP, _GENERIC_SCHEMA_RULES
    _ALL_LOADED_SCHEMAS = []
    _SCHEMAS_RULES_MAP = {}

    for fp in sorted(_SCHEMA_DIR.glob("*.yaml")):
        # Skip the old monolithic registry file if it still exists
        if fp.name == "schema_registry.yml":
            logger.info("Skipping schema_registry.yml during individual schema load.")
            continue
        try:
            with fp.open("r", encoding="utf-8") as f:
                schema_content = yaml.safe_load(f)

            if not isinstance(schema_content, dict) or "id" not in schema_content:
                logger.warning(
                    f"Skipping file {fp.name} as it's not a valid schema dictionary or missing 'id'."
                )
                continue

            schema_id = schema_content["id"]
            _ALL_LOADED_SCHEMAS.append(schema_content)
            _SCHEMAS_RULES_MAP[schema_id] = schema_content

            if schema_id == "generic_csv":
                _GENERIC_SCHEMA_RULES = schema_content

        except Exception as e:
            logger.error(f"Failed to load or parse schema file {fp.name}: {e}")

    # Ensure generic_csv (if loaded) is conceptually last for fallback,
    # though matching logic will handle this explicitly.
    # Sorting _ALL_LOADED_SCHEMAS can be done here if a specific order is needed for iteration.
    _ALL_LOADED_SCHEMAS.sort(key=lambda s: s.get("id", "") == "generic_csv")

    if not _GENERIC_SCHEMA_RULES and "generic_csv" in _SCHEMAS_RULES_MAP:
        # This case should ideally be covered by the loop, but as a fallback:
        _GENERIC_SCHEMA_RULES = _SCHEMAS_RULES_MAP["generic_csv"]
    elif not _GENERIC_SCHEMA_RULES:
        logger.warning(
            "generic_csv schema was not found or loaded. Fallback may not work."
        )


# Schema maps are now loaded lazily on first use
# _SCHEMAS is now _ALL_LOADED_SCHEMAS (List[Dict[str,Any]])
# _GENERIC_SCHEMA_OBJECT is effectively represented by _GENERIC_SCHEMA_RULES (Dict[str,Any])
# _DETAILED_RULES_MAP is now _SCHEMAS_RULES_MAP


def _find_matching_schema_main_impl(headers: Iterable[str]) -> MatchResult:  # Renamed
    # Ensure schemas are loaded before use
    _ensure_schemas_loaded()

    canonical_headers = {_canon(h) for h in headers}
    best_match_result: MatchResult | None = None

    # Iterate through all loaded schemas (dictionaries)
    for schema_rules_dict in _ALL_LOADED_SCHEMAS:
        schema_id = schema_rules_dict.get("id", "unknown_schema_id")

        # Skip generic_csv for now, handle as fallback
        if schema_id == "generic_csv":
            continue

        header_signature_raw = schema_rules_dict.get("header_signature", [])
        if not header_signature_raw or not isinstance(header_signature_raw, list):
            # print(f"DEBUG: Schema {schema_id} has no valid header_signature. Skipping.")
            continue

        schema_canonical_signature = {_canon(h) for h in header_signature_raw}

        # Exact match logic: all headers in schema_canonical_signature must be in canonical_headers
        # AND all headers in canonical_headers must be in schema_canonical_signature (for strict match)
        # For a more flexible match (CSV can have extra cols not in signature):
        #   is_match = schema_canonical_signature.issubset(canonical_headers)
        # For task: "explicit schema rather than falling back" -> implies a fairly strict match.
        # Let's try: if all headers in signature are present in the CSV's headers.

        if schema_canonical_signature.issubset(canonical_headers):
            # This schema is a potential match.
            # Score based on how many signature headers were found (should be all of them here)
            # and perhaps how many *extra* headers the CSV has. Fewer extras = better.
            score = len(
                schema_canonical_signature
            )  # Higher score for more specific signatures

            missing_from_csv = (
                schema_canonical_signature - canonical_headers
            )  # Should be empty if subset match
            extras_in_csv = canonical_headers - schema_canonical_signature

            current_match_result = MatchResult(
                # The 'schema' field in MatchResult expects a Schema object.
                # We need to adapt this or create a dummy Schema object.
                # For now, let's create a simple Schema NamedTuple on the fly.
                schema=Schema(
                    name=schema_id, required={}, optional={}
                ),  # Placeholder Schema object
                rules=schema_rules_dict,  # The full rules dictionary
                score=(
                    score,
                    -len(extras_in_csv),
                ),  # Prioritize more matched, fewer extras
                missing=missing_from_csv,
                extras=extras_in_csv,
            )

            if (
                best_match_result is None
                or current_match_result.score > best_match_result.score
            ):
                best_match_result = current_match_result

    if best_match_result:
        return best_match_result
    else:
        # No specific schema matched, and we are not falling back to generic_csv
        raise FatalSchemaError(
            f"No specific schema found for headers: {list(headers)}. "
            "Fallback to generic_csv is disabled by current policy."
        )


# _find_matching_schema_impl assignment is removed as the shim directly calls the renamed main function.


# This is the function that test_schema_alias.py (and potentially other old code) expects.
def find_matching_schema(  # This is now the only public 'find_matching_schema'
    headers: Iterable[str],
    filename: str | None = None,
    registry: list[dict[str, Any]] | None = None,  # Updated type hint
) -> MatchResult | dict[str, Any] | None:  # Updated type hint (removed type: ignore)
    """
    Acts as a shim for tests or older code expecting a different signature or return type.
    - If `registry` is provided (test mode), it performs a basic match against that
      synthetic registry and returns a raw schema dictionary as tests might expect.
    - Otherwise, it calls the main, new `_new_find_matching_schema_impl`.
    """
    if registry is not None:
        # This is the mode test_schema_alias.py uses.
        # It expects a raw dictionary back, not a MatchResult object.
        # Perform a simplified matching based on header_signature from the synthetic registry.
        canonical_headers_test = {_canon(h) for h in headers}
        for schema_dict_test in registry:
            # Ensure schema_dict_test is a dictionary and has 'header_signature'
            if (
                isinstance(schema_dict_test, dict)
                and "header_signature" in schema_dict_test
            ):
                # Ensure the value of "header_signature" is iterable, e.g. list of strings
                header_sig_val = schema_dict_test["header_signature"]
                if not isinstance(header_sig_val, Iterable) or isinstance(
                    header_sig_val, str
                ):
                    # Skip if header_signature is not an iterable of strings (e.g. if it's a single string or None)
                    continue

                required_test_aliases = {
                    _canon(h)
                    for h in header_sig_val  # Use header_sig_val
                }
                if required_test_aliases.issubset(canonical_headers_test):
                    return schema_dict_test  # Return the raw schema dict
        return None  # No match in the synthetic registry

    # Default behavior: call the new, primary implementation
    return _find_matching_schema_main_impl(headers)  # Call renamed main implementation
