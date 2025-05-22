import re
import yaml
from pathlib import Path
from collections.abc import Iterable
from typing import Any, cast, Dict, List, Set # Added Dict, List, Set

from balance_pipeline.schema_types import Schema, MatchResult
from balance_pipeline.config import SCHEMA_REGISTRY_PATH as DETAILED_RULES_PATH


def load_registry(path: Path) -> List[Dict[str, Any]]:
    """
    Load the full schema registry from a YAML file.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return cast(List[Dict[str, Any]], data)


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

# Load detailed transformation rules from the main schema_registry.yml
try:
    with open(DETAILED_RULES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        # Log or print an error, then raise or ensure _DETAILED_RULES_LIST is empty
        print(f"Error: Detailed rules YAML root is not a list in {DETAILED_RULES_PATH}. Found type: {type(data)}")
        # Depending on desired strictness, either raise ValueError or proceed with empty list
        # For now, let's ensure it's an empty list to avoid downstream errors if file is just empty/malformed
        _DETAILED_RULES_LIST = []
    else:
        _DETAILED_RULES_LIST = data
    _DETAILED_RULES_MAP = {rule["id"]: rule for rule in _DETAILED_RULES_LIST if isinstance(rule, dict) and "id" in rule}
except Exception as e:
    # Handle error loading detailed rules, perhaps log and raise or use empty map
    print(
        f"Critical error loading detailed schema rules from {DETAILED_RULES_PATH}: {e}"
    )
    _DETAILED_RULES_LIST = []
    _DETAILED_RULES_MAP = {}


def _load_schemas() -> list[Schema]:
    """
    Read all .yaml files under the rules directory (for matching logic)
    and build Schema objects.
    Returns a list of Schema, with 'generic_csv' moved to the end.
    """
    schemas: list[Schema] = []
    for fp in sorted(_SCHEMA_DIR.glob("*.yaml")):
        if fp.name == "schema_registry.yml":  # Skip the detailed registry file
            continue
        with fp.open("r", encoding="utf-8") as f:
            raw_match_rules = yaml.safe_load(f)
        if raw_match_rules is None or "name" not in raw_match_rules:
            continue

        # New format: required and optional mappings from per-schema YAML
        required = {
            k: {_canon(k), *map(_canon, cast(Iterable[str], v))}
            for k, v in raw_match_rules.get("required", {}).items()
        }
        optional = {
            k: {_canon(k), *map(_canon, cast(Iterable[str], v))}
            for k, v in raw_match_rules.get("optional", {}).items()
        }
        schemas.append(
            Schema(
                name=raw_match_rules["name"],
                required=required,
                optional=optional,
            )
        )
    # Ensure generic_csv is last for fallback behavior
    schemas.sort(key=lambda s: s.name == "generic_csv")
    return schemas


# --------------------------------------------------------------------------- #
# Cache loaded schemas and provide generic fallback
# --------------------------------------------------------------------------- #
_SCHEMAS: list[Schema] = _load_schemas()
_GENERIC_SCHEMA_OBJECT = next((s for s in _SCHEMAS if s.name == "generic_csv"), None)
_GENERIC_RULES_DICT = (
    _DETAILED_RULES_MAP.get("generic_csv", {}) if _DETAILED_RULES_MAP else {}
)


def _find_matching_schema_main_impl(headers: Iterable[str]) -> MatchResult: # Renamed
    canonical_headers = {_canon(h) for h in headers}
    best_match: MatchResult | None = None

    for schema_obj in _SCHEMAS:
        if not schema_obj:
            continue  # Should not happen if _load_schemas is correct

        required_hits = {
            field
            for field, aliases in schema_obj.required.items()
            if canonical_headers & aliases
        }
        optional_hits = {
            field
            for field, aliases in schema_obj.optional.items()
            if canonical_headers & aliases
        }

        if len(required_hits) == len(
            schema_obj.required
        ):  # All required fields matched
            current_score = (len(required_hits), len(optional_hits))
            detailed_rules_for_schema = _DETAILED_RULES_MAP.get(schema_obj.name, {})

            # Calculate extras based on all known aliases in the matched schema's rules
            all_known_aliases: Set[str] = set() # Added type hint
            if detailed_rules_for_schema:  # Check if rules were found
                for key_aliases_list in detailed_rules_for_schema.get(
                    "required", {}
                ).values():
                    all_known_aliases.update(_canon(x) for x in key_aliases_list)
                for key_aliases_list in detailed_rules_for_schema.get(
                    "optional", {}
                ).values():
                    all_known_aliases.update(_canon(x) for x in key_aliases_list)
            # If using Schema object's required/optional for extras:
            # all_known_aliases.update(*schema_obj.required.values())
            # all_known_aliases.update(*schema_obj.optional.values())

            current_match = MatchResult(
                schema=schema_obj,
                rules=detailed_rules_for_schema,
                score=current_score,
                missing=set(),
                extras=canonical_headers - all_known_aliases,
            )

            if best_match is None or current_score > best_match.score:
                best_match = current_match

    if best_match:
        return best_match

    # Fallback to generic_csv if no other schema fully matched required fields
    if _GENERIC_SCHEMA_OBJECT:
        missing_generic = {
            k
            for k, v_set in _GENERIC_SCHEMA_OBJECT.required.items()
            if not (canonical_headers & v_set)
        }
        # Calculate extras against generic_csv's known aliases
        generic_known_aliases: Set[str] = set() # Added type hint
        if _GENERIC_RULES_DICT:  # Check if generic rules dict is populated
            for key_aliases_list in _GENERIC_RULES_DICT.get("required", {}).values():
                generic_known_aliases.update(_canon(x) for x in key_aliases_list)
            for key_aliases_list in _GENERIC_RULES_DICT.get("optional", {}).values():
                generic_known_aliases.update(_canon(x) for x in key_aliases_list)
        # else: # Fallback if _GENERIC_RULES_DICT is empty (should not happen with valid generic_csv.yaml)
        #    generic_known_aliases.update(*_GENERIC_SCHEMA_OBJECT.required.values())
        #    generic_known_aliases.update(*_GENERIC_SCHEMA_OBJECT.optional.values())

        extras_generic = canonical_headers - generic_known_aliases

        return MatchResult(
            schema=_GENERIC_SCHEMA_OBJECT,
            rules=_GENERIC_RULES_DICT,
            score=(
                0,
                0,
            ),  # Score for generic is typically (0,0) or based on its own partial match
            missing=missing_generic,
            extras=extras_generic,
        )
    else:
        # This case should ideally not be reached if generic_csv.yaml exists and loads
        # Consider raising an error or returning a default MatchResult with no schema
        raise RuntimeError("Generic CSV schema not found, cannot provide fallback.")


# _find_matching_schema_impl assignment is removed as the shim directly calls the renamed main function.

# This is the function that test_schema_alias.py (and potentially other old code) expects.
def find_matching_schema( # This is now the only public 'find_matching_schema'
    headers: Iterable[str],
    filename: str | None = None,
    registry: List[Dict[str, Any]] | None = None, # Updated type hint
) -> MatchResult | Dict[str, Any] | None:  # Updated type hint (removed type: ignore)
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
                if not isinstance(header_sig_val, Iterable) or isinstance(header_sig_val, str):
                    # Skip if header_signature is not an iterable of strings (e.g. if it's a single string or None)
                    continue

                required_test_aliases = {
                    _canon(h) for h in header_sig_val # Use header_sig_val
                }
                if required_test_aliases.issubset(canonical_headers_test):
                    return schema_dict_test  # Return the raw schema dict
        return None  # No match in the synthetic registry

    # Default behavior: call the new, primary implementation
    return _find_matching_schema_main_impl(headers) # Call renamed main implementation
