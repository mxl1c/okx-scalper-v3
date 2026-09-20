"""Offline label field dictionary for research / replay."""

from __future__ import annotations

from typing import Any, Mapping

from okx_scalper_v3.hard_gates import FEATURE_N, SIGNED_SPEC_VERSION, TIMEFRAME
from okx_scalper_v3.types import Decision, Features, TradeGeometry

# name -> description. Values are written as strings in the offline table.
LABEL_FIELD_DICTIONARY: dict[str, str] = {
    "ts_utc": "UTC timestamp of the decision bar close (ISO-8601).",
    "symbol": "Instrument id, e.g. BTC-USDT-SWAP.",
    "timeframe": "Signed bar size. Always 5m.",
    "feature_n": "Signed lookback. Always 48.",
    "atr_pct": "ATR / close over the feature window.",
    "width": "(window high - window low) / close.",
    "slope": "OLS close slope per bar, divided by close.",
    "eff": "Kaufman efficiency |net| / path over N bars.",
    "brk": "Signed breakout of close vs prior N-1 range, / close.",
    "regime": "chaos | trend_up | trend_down | range.",
    "side": "long | short. Rules are symmetric.",
    "signal_price": "Reference price of the setup. Chase is measured vs this.",
    "entry": "Proposed entry. Must not be worse than signal_price.",
    "sl": "Stop-loss price.",
    "tp": "Take-profit price.",
    "sl_pct": "Stop distance / entry. Hard floor 1.2%.",
    "tp_pct": "Target distance / entry.",
    "rr": "tp_distance / sl_distance. Hard floor 1.5.",
    "risk_pct": "Account risk of this order as a fraction of equity.",
    "open_positions": "Count of already-open positions at decision time.",
    "open_risk_pct": "Sum of open position risk fractions.",
    "daily_loss_pct": "Abs daily loss / day-start equity (0 if green).",
    "reason_code": "Primary ReasonCode string.",
    "accepted": "1 if all hard gates passed, else 0.",
    "macd_used": "1 if optional MACD confirm was requested.",
    "giveback_armed": "1 if giveback activation R was reached.",
    "mfe_pct": "Max favorable excursion / entry after fill (offline).",
    "mae_pct": "Max adverse excursion / entry after fill (offline).",
    "fee_pct_rt": "Round-trip fee fraction used for no-loss giveback.",
    "outcome": "open | tp | sl | giveback | timeout | reject.",
    "pnl_pct": "Gross pnl / entry (signed, side-aware).",
    "net_pnl_pct": "pnl_pct minus fee_pct_rt.",
    "label_horizon_bars": "Forward bars used to assign outcome (offline).",
    "spec_version": "Signed spec version string.",
}


def empty_label_row() -> dict[str, str]:
    return {key: "" for key in LABEL_FIELD_DICTIONARY}


def build_label_row(
    *,
    ts_utc: str,
    symbol: str,
    features: Features,
    regime: str,
    geo: TradeGeometry,
    decision: Decision,
    risk_pct: float,
    open_positions: int,
    open_risk_pct: float,
    daily_loss_pct: float,
    macd_used: bool = False,
    giveback_armed: bool = False,
    mfe_pct: float | None = None,
    mae_pct: float | None = None,
    fee_pct_rt: float = 0.0,
    outcome: str = "reject",
    pnl_pct: float | None = None,
    label_horizon_bars: int = 0,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    if features.n != FEATURE_N or features.timeframe != TIMEFRAME:
        raise ValueError("label features must use signed 5m N=48 contract")

    row = empty_label_row()
    row.update(
        {
            "ts_utc": ts_utc,
            "symbol": symbol,
            "timeframe": TIMEFRAME,
            "feature_n": str(FEATURE_N),
            "atr_pct": f"{features.atr_pct:.10f}",
            "width": f"{features.width:.10f}",
            "slope": f"{features.slope:.10f}",
            "eff": f"{features.eff:.10f}",
            "brk": f"{features.brk:.10f}",
            "regime": regime,
            "side": geo.side,
            "signal_price": f"{geo.signal_price:.10f}",
            "entry": f"{geo.entry:.10f}",
            "sl": f"{geo.sl:.10f}",
            "tp": f"{geo.tp:.10f}",
            "sl_pct": f"{geo.sl_pct:.10f}",
            "tp_pct": f"{geo.tp_pct:.10f}",
            "rr": f"{geo.rr:.10f}",
            "risk_pct": f"{risk_pct:.10f}",
            "open_positions": str(open_positions),
            "open_risk_pct": f"{open_risk_pct:.10f}",
            "daily_loss_pct": f"{daily_loss_pct:.10f}",
            "reason_code": decision.reason.value,
            "accepted": "1" if decision.ok else "0",
            "macd_used": "1" if macd_used else "0",
            "giveback_armed": "1" if giveback_armed else "0",
            "mfe_pct": "" if mfe_pct is None else f"{mfe_pct:.10f}",
            "mae_pct": "" if mae_pct is None else f"{mae_pct:.10f}",
            "fee_pct_rt": f"{fee_pct_rt:.10f}",
            "outcome": outcome if decision.ok else "reject",
            "pnl_pct": "" if pnl_pct is None else f"{pnl_pct:.10f}",
            "net_pnl_pct": (
                ""
                if pnl_pct is None
                else f"{(pnl_pct - fee_pct_rt):.10f}"
            ),
            "label_horizon_bars": str(label_horizon_bars),
            "spec_version": SIGNED_SPEC_VERSION,
        }
    )
    if extra:
        for key, value in extra.items():
            if key not in LABEL_FIELD_DICTIONARY:
                raise KeyError(f"unknown label field: {key}")
            row[key] = str(value)
    return row
