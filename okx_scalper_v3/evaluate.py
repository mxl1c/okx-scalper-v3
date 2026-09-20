"""Offline candidate evaluation. No live trading, no OKX orders."""

from __future__ import annotations

from collections.abc import Sequence

from okx_scalper_v3.geometry import check_geometry
from okx_scalper_v3.hard_gates import EDGE_EPS, FEATURE_N, MIN_SL_PCT
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.regime import classify_regime, macd_allowed
from okx_scalper_v3.risk import check_risk_gates
from okx_scalper_v3.soft_params import SoftParams, default_soft_params, validate_soft_params
from okx_scalper_v3.types import AccountState, Bar, Decision, TradeGeometry


def evaluate_candidate(
    bars: Sequence[Bar],
    geo: TradeGeometry,
    account: AccountState,
    params: SoftParams | None = None,
    risk_pct: float | None = None,
) -> Decision:
    params = params or default_soft_params()
    soft = validate_soft_params(params)
    if not soft.ok:
        return soft

    if len(bars) < FEATURE_N:
        return Decision(
            False,
            ReasonCode.REJECT_INSUFFICIENT_BARS,
            {"have": len(bars), "need": FEATURE_N},
        )

    geometry = check_geometry(geo)
    if not geometry.ok:
        return geometry

    # Optional MACD still cannot relax the signed SL floor.
    if geo.sl_pct < MIN_SL_PCT - EDGE_EPS:
        return Decision(False, ReasonCode.REJECT_SL_FLOOR, {"sl_pct": geo.sl_pct})

    try:
        regime, features = classify_regime(bars, params)
    except ValueError as exc:
        return Decision(False, ReasonCode.REJECT_INSUFFICIENT_BARS, {"why": str(exc)})

    macd = macd_allowed(regime, params.macd_enabled)
    if not macd.ok:
        return macd

    risk = check_risk_gates(account, regime, geo, risk_pct=risk_pct)
    if not risk.ok:
        return risk

    details = {
        "regime": regime,
        "atr_pct": features.atr_pct,
        "width": features.width,
        "slope": features.slope,
        "eff": features.eff,
        "brk": features.brk,
        "rr": geo.rr,
        "sl_pct": geo.sl_pct,
        "side": geo.side,
    }
    return Decision(True, ReasonCode.OK, details)
