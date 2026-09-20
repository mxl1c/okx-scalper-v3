"""Regime classifier with signed priority chaos → trend → range."""

from __future__ import annotations

from collections.abc import Sequence

from okx_scalper_v3.features import compute_features
from okx_scalper_v3.hard_gates import MACD_ALLOWED_REGIMES
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.soft_params import SoftParams, default_soft_params
from okx_scalper_v3.types import Bar, Decision, Features, Regime


def classify_from_features(
    features: Features,
    params: SoftParams | None = None,
) -> Regime:
    params = params or default_soft_params()

    chaotic_vol = features.atr_pct >= params.chaos_atr_pct
    chaotic_chop = (
        features.eff <= params.chaos_eff_max
        and features.width >= params.chaos_width_min
    )
    if chaotic_vol or chaotic_chop:
        return "chaos"

    trending = (
        features.eff >= params.trend_eff_min
        and abs(features.slope) >= params.trend_slope_min
    )
    if trending:
        return "trend_up" if features.slope >= 0 else "trend_down"

    return "range"


def classify_regime(
    bars: Sequence[Bar],
    params: SoftParams | None = None,
) -> tuple[Regime, Features]:
    features = compute_features(bars, params)
    return classify_from_features(features, params), features


def macd_allowed(regime: Regime, macd_enabled: bool) -> Decision:
    if not macd_enabled:
        return Decision(True, ReasonCode.OK, {"macd_enabled": False})
    if regime not in MACD_ALLOWED_REGIMES:
        return Decision(
            False,
            ReasonCode.REJECT_MACD_REGIME,
            {"regime": regime, "macd_enabled": True},
        )
    return Decision(True, ReasonCode.OK, {"regime": regime, "macd_enabled": True})
