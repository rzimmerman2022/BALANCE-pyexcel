from __future__ import annotations

from __future__ import annotations

from pathlib import Path
import re
from enum import Enum, auto
from typing import Any, NamedTuple, Set

import yaml
from balance_pipeline.errors import FatalSchemaError


class MatchLevel(Enum):
    """Enumeration of matching stages."""

    FILENAME = auto()
    SUBSET = auto()
    GENERIC = auto()


class MatchResult(NamedTuple):
    """Result from :func:`find_matching_schema`."""

    schema: dict[str, Any]
    missing: Set[str]
    extra: Set[str]
    level: MatchLevel
    score: float


def _normalize_header(header: str) -> str:
    """Return a normalized representation of ``header``."""

    if not isinstance(header, str):
        return ""
    normalized = header.lower()
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized).strip()
    return re.sub(r"\s+", " ", normalized)


def load_registry(path: Path) -> list[dict]:
    """
    Load the schema registry YAML file from the given path.
    Returns a list of schema definitions.
    Raises FatalSchemaError on file not found, parse errors, or wrong type.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FatalSchemaError(f"Schema registry file not found: {path}") from e
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise FatalSchemaError(f"Error parsing schema registry YAML {path}: {e}") from e
    if not isinstance(data, list):
        raise FatalSchemaError(
            f"Schema registry must be a list of schemas; got {type(data)} from {path}"
        )
    return data


def _parse_schema(schema: dict) -> tuple[list[str], list[str], dict[str, set[str]]]:
    """Return normalized required, optional and alias definitions for ``schema``."""

    if "required" in schema:
        required = [_normalize_header(h) for h in schema.get("required", [])]
    else:
        required = [_normalize_header(h) for h in schema.get("header_signature", [])]

    optional = [_normalize_header(h) for h in schema.get("optional", [])]

    raw_aliases = schema.get("aliases", {})
    norm_aliases: dict[str, set[str]] = {}
    for key, vals in raw_aliases.items():
        norm_aliases[_normalize_header(key)] = {_normalize_header(v) for v in vals}

    return required, optional, norm_aliases


def _evaluate_headers(
    normalized_headers: set[str],
    required: list[str],
    optional: list[str],
    aliases: dict[str, set[str]],
) -> tuple[set[str], set[str]]:
    """Return missing required headers and unknown extras."""

    missing: set[str] = set()
    for req in required:
        candidates = {req} | aliases.get(req, set())
        if not candidates & normalized_headers:
            missing.add(req)

    known = set(required) | set(optional)
    for canon, alts in aliases.items():
        known.add(canon)
        known.update(alts)

    extra = {h for h in normalized_headers if h not in known}
    return missing, extra


def find_matching_schema(
    headers: list[str],
    filename: str,
    registry: list[dict],
) -> MatchResult:
    """Return best schema along with diagnostics for ``headers``."""

    normalized = {_normalize_header(h) for h in headers}
    fname = Path(filename).name

    # Step a: filename match and required headers satisfied
    for schema in registry:
        pattern = schema.get("match_filename")
        if pattern and Path(fname).match(pattern):
            req, opt, alias = _parse_schema(schema)
            missing, extra = _evaluate_headers(normalized, req, opt, alias)
            if not missing:
                return MatchResult(schema, missing, extra, MatchLevel.FILENAME, 1.0)

    # Step b: alias-aware subset matching
    for schema in registry:
        req, opt, alias = _parse_schema(schema)
        missing, extra = _evaluate_headers(normalized, req, opt, alias)
        if not missing:
            return MatchResult(schema, missing, extra, MatchLevel.SUBSET, 1.0)

    # Step c: fallback to generic_checking if >=80% of its required headers match
    generic = next((s for s in registry if s.get("id") == "generic_checking"), None)
    if generic:
        req, opt, alias = _parse_schema(generic)
        missing, extra = _evaluate_headers(normalized, req, opt, alias)
        if req:
            coverage = (len(req) - len(missing)) / len(req)
            if coverage >= 0.8:
                return MatchResult(generic, missing, extra, MatchLevel.GENERIC, coverage)

    raise FatalSchemaError(f"No schema match found for {filename}")
