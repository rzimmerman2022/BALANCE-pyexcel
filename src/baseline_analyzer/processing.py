"""Processing utilities – configuration-backed literal accessors.

This module centralises access to configurable literals such as the *Amount*
column name, *Date* column name, and the minimum baseline floor date.  The
actual values are supplied via the YAML configuration file
``config/balance_analyzer.yaml`` and can be overridden at runtime with
environment variables prefixed ``BA_``.

Public helpers expose these values so that downstream data-frame logic does not
embed hard-coded strings.
"""

from __future__ import annotations

from datetime import datetime, date

from ._settings import Settings, load_config

# --------------------------------------------------------------------------- #
# Internal helper
# --------------------------------------------------------------------------- #
def _cfg(cfg: Settings | None = None) -> Settings:
    """Return an effective :class:`Settings` object.

    If *cfg* is *None*, :func:`~baseline_analyzer._settings.load_config` is
    invoked lazily so callers can omit an explicit configuration object.
    """
    return cfg or load_config()


# --------------------------------------------------------------------------- #
# Public accessors
# --------------------------------------------------------------------------- #
def amount_col(cfg: Settings | None = None) -> str:  # noqa: D401
    """Return the configured *Amount* column name."""
    return _cfg(cfg).amount_col


def date_col(cfg: Settings | None = None) -> str:  # noqa: D401
    """Return the configured *Date* column name."""
    return _cfg(cfg).date_col


def baseline_floor_date(cfg: Settings | None = None) -> date:  # noqa: D401
    """Return the earliest permissible baseline date as a :class:`datetime.date`.

    The raw string from configuration (``baseline_floor_date``) is parsed using
    the format specified by ``baseline_date_format`` for consistency.
    """
    c = _cfg(cfg)
    return datetime.strptime(c.baseline_floor_date, c.baseline_date_format).date()
