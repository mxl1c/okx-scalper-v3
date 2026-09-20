"""Signed hard gates for okx-scalper-v3.

These constants are the contract. Soft params cannot override them.
Tests lock both the numeric values and the inclusive/exclusive edges so
loosening a gate fails CI.
"""

from __future__ import annotations

from typing import Final

SIGNED_STRATEGY_ID: Final[str] = "okx-scalper-v3"
SIGNED_SPEC_VERSION: Final[str] = "3.0.0"

# Feature contract
TIMEFRAME: Final[str] = "5m"
FEATURE_N: Final[int] = 48

# Position / capital
MAX_PARALLEL: Final[int] = 3
MAX_PER_TRADE_RISK: Final[float] = 0.02
MAX_AGGREGATE_RISK: Final[float] = 0.05
MAX_DAILY_LOSS: Final[float] = 0.05
DAILY_LOSS_EXEMPTIONS_ALLOWED: Final[bool] = False

# Geometry
MIN_RR: Final[float] = 1.5
MIN_SL_PCT: Final[float] = 0.012

# Conduct
CHASE_BANNED: Final[bool] = True
COOLDOWN_MINUTES: Final[int] = 90
CHAOS_BLOCKS_NEW_OPENS: Final[bool] = True

# Giveback: only after activation; fee-aware floor is always no-loss.
GIVEBACK_REQUIRES_ACTIVATION: Final[bool] = True
GIVEBACK_FEE_AWARE_NO_LOSS: Final[bool] = True

# MACD is optional and may only confirm trend_* setups.
MACD_ALLOWED_REGIMES: Final[frozenset[str]] = frozenset({"trend_up", "trend_down"})

# Edge tolerance: signed bounds stay closed, float noise does not flip them.
EDGE_EPS: Final[float] = 1e-12
