"""Hard risk gates. Soft params cannot bypass any of these."""

from __future__ import annotations

from datetime import timedelta

from okx_scalper_v3.hard_gates import (
    CHAOS_BLOCKS_NEW_OPENS,
    COOLDOWN_MINUTES,
    DAILY_LOSS_EXEMPTIONS_ALLOWED,
    EDGE_EPS,
    MAX_AGGREGATE_RISK,
    MAX_DAILY_LOSS,
    MAX_PARALLEL,
    MAX_PER_TRADE_RISK,
)
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.types import AccountState, Decision, Regime, TradeGeometry


def check_chaos_new_opens(regime: Regime) -> Decision:
    if CHAOS_BLOCKS_NEW_OPENS and regime == "chaos":
        return Decision(False, ReasonCode.REJECT_CHAOS, {"regime": regime})
    return Decision(True, ReasonCode.OK, {"regime": regime})


def check_daily_loss(account: AccountState) -> Decision:
    if DAILY_LOSS_EXEMPTIONS_ALLOWED:
        return Decision(False, ReasonCode.REJECT_DAILY_LOSS, {"why": "exemption_flag_on"})
    hit = account.daily_loss_pct >= MAX_DAILY_LOSS - EDGE_EPS
    if hit:
        return Decision(
            False,
            ReasonCode.REJECT_DAILY_LOSS,
            {
                "daily_loss_pct": account.daily_loss_pct,
                "max_daily_loss": MAX_DAILY_LOSS,
                "exemption_requested": account.exemption,
                "exemption_honored": False,
            },
        )
    return Decision(True, ReasonCode.OK, {"daily_loss_pct": account.daily_loss_pct})


def check_cooldown(account: AccountState) -> Decision:
    if account.last_stop_ts is None:
        return Decision(True, ReasonCode.OK, {"cooldown": False})
    elapsed = account.now - account.last_stop_ts
    need = timedelta(minutes=COOLDOWN_MINUTES)
    if elapsed < need:
        return Decision(
            False,
            ReasonCode.REJECT_COOLDOWN,
            {
                "elapsed_seconds": elapsed.total_seconds(),
                "required_seconds": need.total_seconds(),
            },
        )
    return Decision(True, ReasonCode.OK, {"elapsed_seconds": elapsed.total_seconds()})


def check_parallel(account: AccountState) -> Decision:
    if account.open_positions >= MAX_PARALLEL:
        return Decision(
            False,
            ReasonCode.REJECT_PARALLEL,
            {"open_positions": account.open_positions, "max_parallel": MAX_PARALLEL},
        )
    return Decision(True, ReasonCode.OK, {"open_positions": account.open_positions})


def trade_risk_pct(account: AccountState, geo: TradeGeometry) -> float:
    """Risk as a fraction of equity for a 1x notional equal to `equity`.

    Callers pass `notional / equity` via details if they size differently;
    the gate consumes an explicit `risk_pct` so tests can lock the 2% edge.
    """
    if account.equity <= 0:
        return float("inf")
    return geo.sl_pct


def check_per_trade_risk(risk_pct: float) -> Decision:
    if risk_pct > MAX_PER_TRADE_RISK + EDGE_EPS:
        return Decision(
            False,
            ReasonCode.REJECT_PER_TRADE_RISK,
            {"risk_pct": risk_pct, "max_per_trade_risk": MAX_PER_TRADE_RISK},
        )
    return Decision(True, ReasonCode.OK, {"risk_pct": risk_pct})


def check_aggregate_risk(account: AccountState, new_risk_pct: float) -> Decision:
    total = account.open_risk_pct + new_risk_pct
    if total > MAX_AGGREGATE_RISK + EDGE_EPS:
        return Decision(
            False,
            ReasonCode.REJECT_AGGREGATE_RISK,
            {
                "open_risk_pct": account.open_risk_pct,
                "new_risk_pct": new_risk_pct,
                "total_risk_pct": total,
                "max_aggregate_risk": MAX_AGGREGATE_RISK,
            },
        )
    return Decision(True, ReasonCode.OK, {"total_risk_pct": total})


def check_risk_gates(
    account: AccountState,
    regime: Regime,
    geo: TradeGeometry,
    risk_pct: float | None = None,
) -> Decision:
    sized = trade_risk_pct(account, geo) if risk_pct is None else risk_pct
    for decision in (
        check_chaos_new_opens(regime),
        check_daily_loss(account),
        check_cooldown(account),
        check_parallel(account),
        check_per_trade_risk(sized),
        check_aggregate_risk(account, sized),
    ):
        if not decision.ok:
            return decision
    return Decision(True, ReasonCode.OK, {"risk_pct": sized})
