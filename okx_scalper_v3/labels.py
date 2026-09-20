"""Offline label field dictionary for research / replay."""

from __future__ import annotations

from typing import Any, Mapping

from okx_scalper_v3.hard_gates import EDGE_EPS, FEATURE_N, SIGNED_SPEC_VERSION, TIMEFRAME
from okx_scalper_v3.types import Decision, Features, TradeGeometry

# Closed enums for research labels. outcome/pnl_* stay; these do not replace them.
EXIT_CLASSES: frozenset[str] = frozenset(
    {
        "sl",
        "invalidate",
        "reverse",
        "tp",
        "stale_half",
        "stale_flat",
        "replace",
        "manual",
        "other",
        "reject",
    }
)
FAIL_TAGS: frozenset[str] = frozenset(
    {
        "stop_out",
        "fake_break",
        "regime_wrong",
        "chase",
        "fee_grind",
        "early_lock",
        "other",
    }
)

# name -> description. Values are written as strings in the offline table.
LABEL_FIELD_DICTIONARY: dict[str, str] = {
    "ts_utc": "UTC timestamp of the decision bar close (ISO-8601).",
    "symbol": "Instrument id, e.g. DOGE-USDT-SWAP (pool excludes BTC/ETH).",
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
    "outcome": "open | tp | sl | giveback | timeout | reject. Kept; not a substitute for exit_class.",
    "pnl_pct": "Gross pnl / entry (signed, side-aware). Kept; not a substitute for y_r.",
    "net_pnl_pct": "pnl_pct minus fee_pct_rt. Kept; y_r is this quantity in R units.",
    "y_r": "Fee-aware net PnL / 1R, where 1R = sl_pct. Empty until pnl is known.",
    "exit_class": (
        "Single exit enum: sl|invalidate|reverse|tp|stale_half|stale_flat|"
        "replace|manual|other|reject."
    ),
    "fail_tag": (
        "Multi-select fail tags joined by '|': stop_out|fake_break|regime_wrong|"
        "chase|fee_grind|early_lock|other."
    ),
    "label_horizon_bars": "Forward bars used to assign outcome (offline).",
    "spec_version": "Signed spec version string.",
}


def empty_label_row() -> dict[str, str]:
    return {key: "" for key in LABEL_FIELD_DICTIONARY}


def compute_y_r(net_pnl_pct: float, sl_pct: float) -> float:
    """Fee-aware net PnL expressed in R multiples (1R = signed SL distance)."""
    if sl_pct <= EDGE_EPS:
        raise ValueError("1R is sl_pct; cannot be zero or negative")
    return net_pnl_pct / sl_pct


def parse_fail_tags(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    tags = tuple(part for part in raw.split("|") if part)
    unknown = [tag for tag in tags if tag not in FAIL_TAGS]
    if unknown:
        raise ValueError(f"unknown fail_tag: {unknown}")
    return tags


def validate_exit_class(exit_class: str) -> str:
    if exit_class == "":
        return ""
    if exit_class not in EXIT_CLASSES:
        raise ValueError(f"unknown exit_class: {exit_class}")
    return exit_class


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
    y_r: float | None = None,
    exit_class: str = "",
    fail_tag: str = "",
    label_horizon_bars: int = 0,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    if features.n != FEATURE_N or features.timeframe != TIMEFRAME:
        raise ValueError("label features must use signed 5m N=48 contract")

    net_pnl_pct: float | None
    if pnl_pct is None:
        net_pnl_pct = None
    else:
        net_pnl_pct = pnl_pct - fee_pct_rt

    if y_r is None and net_pnl_pct is not None:
        y_r = compute_y_r(net_pnl_pct, geo.sl_pct)

    if not decision.ok and exit_class == "":
        exit_class = "reject"
    exit_class = validate_exit_class(exit_class)
    fail_tag = "|".join(parse_fail_tags(fail_tag))

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
            "net_pnl_pct": "" if net_pnl_pct is None else f"{net_pnl_pct:.10f}",
            "y_r": "" if y_r is None else f"{y_r:.10f}",
            "exit_class": exit_class,
            "fail_tag": fail_tag,
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
