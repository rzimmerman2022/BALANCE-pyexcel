from dataclasses import dataclass
from typing import Dict, Set, Tuple, Any


@dataclass(frozen=True, slots=True)
class Schema:
    name: str
    required: Dict[str, Set[str]]
    optional: Dict[str, Set[str]]

    def match(self, headers: set[str]) -> Tuple[int, int]:
        """
        Return a tuple (#required_hits, #optional_hits) indicating how many
        required and optional fields were matched in the provided headers set.
        """
        req_hits = {
            field for field, aliases in self.required.items() if headers & aliases
        }
        opt_hits = {
            field for field, aliases in self.optional.items() if headers & aliases
        }
        return (len(req_hits), len(opt_hits))


@dataclass(frozen=True, slots=True)
class MatchResult:
    schema: Schema  # new dataclass (name/required/optional)
    rules: Dict[str, Any]  # raw dict from schema_registry.yml
    score: Tuple[int, int]
    missing: Set[str]
    extras: Set[str]
