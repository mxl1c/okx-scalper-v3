"""okx-scalper-v3 signed strategy scaffold (offline only)."""

from okx_scalper_v3.evaluate import evaluate_candidate
from okx_scalper_v3.hard_gates import (
    SIGNED_SPEC_VERSION,
    SIGNED_STRATEGY_ID,
)
from okx_scalper_v3.reasons import ReasonCode

__all__ = [
    "SIGNED_SPEC_VERSION",
    "SIGNED_STRATEGY_ID",
    "ReasonCode",
    "evaluate_candidate",
]
__version__ = SIGNED_SPEC_VERSION
