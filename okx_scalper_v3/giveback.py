"""Giveback (profit lock) — only after activation, fee-aware no-loss."""

from __future__ import annotations

from okx_scalper_v3.hard_gates import (
    EDGE_EPS,
    GIVEBACK_FEE_AWARE_NO_LOSS,
    GIVEBACK_REQUIRES_ACTIVATION,
)
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.soft_params import SoftParams, default_soft_params
from okx_scalper_v3.types import Decision, TradeGeometry


def fee_aware_breakeven(geo: TradeGeometry, fee_pct_one_way: float) -> float:
    rt = 2.0 * fee_pct_one_way
    if geo.side == "long":
        return geo.entry * (1.0 + rt)
    return geo.entry * (1.0 - rt)


def activation_r(geo: TradeGeometry, mfe_price: float) -> float:
    if geo.sl_distance <= 0:
        return 0.0
    if geo.side == "long":
        mfe = mfe_price - geo.entry
    else:
        mfe = geo.entry - mfe_price
    return mfe / geo.sl_distance


def check_giveback(
    geo: TradeGeometry,
    proposed_stop: float,
    mfe_price: float,
    params: SoftParams | None = None,
    activated: bool | None = None,
) -> Decision:
    params = params or default_soft_params()
    if not GIVEBACK_REQUIRES_ACTIVATION or not GIVEBACK_FEE_AWARE_NO_LOSS:
        return Decision(
            False,
            ReasonCode.REJECT_GIVEBACK_NOT_ARMED,
            {"why": "signed_giveback_flags_disabled"},
        )

    r_mult = activation_r(geo, mfe_price)
    is_armed = r_mult >= params.giveback_activation_r - EDGE_EPS
    if activated is False or not is_armed:
        return Decision(
            False,
            ReasonCode.REJECT_GIVEBACK_NOT_ARMED,
            {
                "r_multiple": r_mult,
                "need_r": params.giveback_activation_r,
                "activated": False,
            },
        )

    be = fee_aware_breakeven(geo, params.fee_pct_one_way)
    if geo.side == "long":
        locks_loss = proposed_stop < be - EDGE_EPS
    else:
        locks_loss = proposed_stop > be + EDGE_EPS

    if locks_loss:
        return Decision(
            False,
            ReasonCode.REJECT_GIVEBACK_FEE_LOSS,
            {
                "proposed_stop": proposed_stop,
                "breakeven": be,
                "side": geo.side,
            },
        )

    return Decision(
        True,
        ReasonCode.OK,
        {"r_multiple": r_mult, "breakeven": be, "proposed_stop": proposed_stop},
    )
