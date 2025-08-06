from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Schema:
    name: str
    required: dict[str, set[str]]
    optional: dict[str, set[str]]

    def match(self, headers: set[str]) -> tuple[int, int]:
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
    rules: dict[str, Any]  # raw dict from schema_registry.yml
    score: tuple[int, int]
    missing: set[str]
    extras: set[str]
