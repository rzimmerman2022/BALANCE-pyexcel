"""Balance-Analyzer configuration loader (Sprint 1).

This module is intentionally self-contained:
• No dependencies on the bloated legacy ``config.py``.
• Only the three keys introduced in Sprint 1.
• Environment overrides via ``BA_*`` variables handled by pydantic-settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import os

import yaml

# --------------------------------------------------------------------------- #
# Optional dependency handling
# --------------------------------------------------------------------------- #
try:
    # Preferred: lightweight package that ships with Pydantic v2 ecosystem
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    # If *pydantic-settings* is unavailable we create ultra-lightweight stubs
    # so the rest of this module remains importable without adding heavy deps.
    class BaseSettings:  # type: ignore
        """Very small subset replacement for Pydantic ``BaseSettings``."""
        # populated after subclass creation
        model_fields: dict[str, object] = {}

        def __init_subclass__(cls) -> None:
            # capture class annotations as field names
            annotations = getattr(cls, "__annotations__", {})
            cls.model_fields = {name: None for name in annotations}

        def __init__(self, **data: object) -> None:
            # simply assign provided kwargs; no validation
            for field in self.model_fields:
                setattr(self, field, data.get(field))

    class SettingsConfigDict(dict):  # minimal stub to appease type checkers
        """Stand-in for pydantic-settings’ SettingsConfigDict."""
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

# Default YAML location: <repo_root>/config/balance_analyzer.yaml
_DEFAULT_YAML: Path = Path(__file__).parents[2] / "config" / "balance_analyzer.yaml"


class Settings(BaseSettings):
    """Immutable settings object for Balance-Analyzer."""

    opening_balance_col: str
    baseline_date_format: str
    merchant_lookup_path: str
    amount_col: str
    date_col: str
    baseline_floor_date: str

    # Pydantic-settings configuration: env overrides + immutability
    model_config = SettingsConfigDict(env_prefix="BA_", frozen=True)


def load_config(path: str | Path | None = None) -> Settings:
    """Load configuration, giving precedence to BA_* environment variables
    over YAML values.

    Parameters
    ----------
    path:
        Optional custom YAML file to read.  If *None*, the default path
        ``config/balance_analyzer.yaml`` is used.

    Returns
    -------
    Settings
        Frozen, validated settings object.
    """
    yaml_path: Path = Path(path) if path else _DEFAULT_YAML
    yaml_data: dict[str, Any] = {}
    if yaml_path.exists():
        # An empty YAML file yields ``None``; coerce to empty dict.
        yaml_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}

    # Collect BA_* environment overrides
    env_overrides: dict[str, Any] = {}
    for field in Settings.model_fields:
        env_var = f"BA_{field.upper()}"
        if env_var in os.environ and os.environ[env_var]:
            env_overrides[field] = os.environ[env_var]

    merged = {**yaml_data, **env_overrides}  # env wins
    return Settings(**merged)
