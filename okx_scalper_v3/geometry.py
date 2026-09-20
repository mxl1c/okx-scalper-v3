"""Geometry checks: SL floor, MIN_RR, chase ban, long/short symmetry."""

from __future__ import annotations

from okx_scalper_v3.hard_gates import CHASE_BANNED, EDGE_EPS, MIN_RR, MIN_SL_PCT
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.types import Decision, TradeGeometry


def check_side_geometry(geo: TradeGeometry) -> Decision:
    if geo.side not in {"long", "short"}:
        return Decision(False, ReasonCode.REJECT_SIDE, {"side": str(geo.side)})
    if min(geo.signal_price, geo.entry, geo.sl, geo.tp) <= 0:
        return Decision(False, ReasonCode.REJECT_GEOMETRY, {"why": "non_positive_price"})

    if geo.side == "long":
        ordered = geo.sl < geo.entry < geo.tp
    else:
        ordered = geo.tp < geo.entry < geo.sl
    if not ordered or geo.sl_distance <= 0 or geo.tp_distance <= 0:
        return Decision(
            False,
            ReasonCode.REJECT_GEOMETRY,
            {"side": geo.side, "why": "wrong_side_or_flat"},
        )
    return Decision(True, ReasonCode.OK)


def check_sl_floor(geo: TradeGeometry) -> Decision:
    if geo.sl_pct < MIN_SL_PCT - EDGE_EPS:
        return Decision(
            False,
            ReasonCode.REJECT_SL_FLOOR,
            {"sl_pct": geo.sl_pct, "min_sl_pct": MIN_SL_PCT},
        )
    return Decision(True, ReasonCode.OK, {"sl_pct": geo.sl_pct})


def check_min_rr(geo: TradeGeometry) -> Decision:
    if geo.rr < MIN_RR - EDGE_EPS:
        return Decision(
            False,
            ReasonCode.REJECT_MIN_RR,
            {"rr": geo.rr, "min_rr": MIN_RR},
        )
    return Decision(True, ReasonCode.OK, {"rr": geo.rr})


def check_chase_ban(geo: TradeGeometry) -> Decision:
    if not CHASE_BANNED:
        return Decision(False, ReasonCode.REJECT_CHASE, {"why": "chase_ban_disabled"})
    chased = (
        geo.entry > geo.signal_price
        if geo.side == "long"
        else geo.entry < geo.signal_price
    )
    if chased:
        return Decision(
            False,
            ReasonCode.REJECT_CHASE,
            {
                "side": geo.side,
                "entry": geo.entry,
                "signal_price": geo.signal_price,
            },
        )
    return Decision(True, ReasonCode.OK)


def check_geometry(geo: TradeGeometry) -> Decision:
    for fn in (check_side_geometry, check_chase_ban, check_sl_floor, check_min_rr):
        decision = fn(geo)
        if not decision.ok:
            return decision
    return Decision(
        True,
        ReasonCode.OK,
        {"sl_pct": geo.sl_pct, "tp_pct": geo.tp_pct, "rr": geo.rr},
    )


def mirror_geometry(geo: TradeGeometry) -> TradeGeometry:
    """Reflect a long/short setup through the signal price. Used for symmetry tests."""
    pivot = geo.signal_price
    other = "short" if geo.side == "long" else "long"
    return TradeGeometry(
        side=other,
        signal_price=pivot,
        entry=2 * pivot - geo.entry,
        sl=2 * pivot - geo.sl,
        tp=2 * pivot - geo.tp,
    )
