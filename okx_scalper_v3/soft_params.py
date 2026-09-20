"""Analyst-bounded soft parameters. Cannot override hard gates."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping

from okx_scalper_v3.hard_gates import FEATURE_N, MIN_SL_PCT
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.types import Decision

# Inclusive analyst bounds. Values outside reject as REJECT_SOFT_PARAM.
ANALYST_BOUNDS: dict[str, tuple[float, float]] = {
    "atr_period": (7, 21),
    "chaos_atr_pct": (0.012, 0.040),
    "chaos_eff_max": (0.12, 0.28),
    "chaos_width_min": (0.020, 0.080),
    "trend_eff_min": (0.32, 0.55),
    "trend_slope_min": (0.00015, 0.0020),
    "range_width_max": (0.015, 0.060),
    "macd_fast": (8, 16),
    "macd_slow": (21, 30),
    "macd_signal": (7, 12),
    "giveback_activation_r": (0.8, 1.5),
    "fee_pct_one_way": (0.0001, 0.0010),
}

# Names that must never be accepted as soft overrides.
HARD_GATE_ALIASES: frozenset[str] = frozenset(
    {
        "max_parallel",
        "per_trade_risk",
        "max_per_trade_risk",
        "aggregate_risk",
        "max_aggregate_risk",
        "daily_loss",
        "max_daily_loss",
        "min_rr",
        "sl_floor",
        "min_sl_pct",
        "cooldown_minutes",
        "chase_banned",
        "feature_n",
        "exemption",
        "daily_loss_exemption",
    }
)


@dataclass(frozen=True)
class SoftParams:
    atr_period: int = 14
    chaos_atr_pct: float = 0.022
    chaos_eff_max: float = 0.20
    chaos_width_min: float = 0.035
    trend_eff_min: float = 0.38
    trend_slope_min: float = 0.00035
    range_width_max: float = 0.030
    macd_enabled: bool = False
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    giveback_activation_r: float = 1.0
    fee_pct_one_way: float = 0.0005

    @property
    def lookback_n(self) -> int:
        return FEATURE_N

    @property
    def round_trip_fee_pct(self) -> float:
        return 2.0 * self.fee_pct_one_way


def default_soft_params() -> SoftParams:
    return SoftParams()


def _in_bounds(name: str, value: float) -> bool:
    lo, hi = ANALYST_BOUNDS[name]
    return lo <= float(value) <= hi


def validate_soft_params(
    params: SoftParams | Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Decision:
    raw: dict[str, Any] = {}
    if isinstance(params, SoftParams):
        raw.update({f.name: getattr(params, f.name) for f in fields(params)})
    elif params is not None:
        raw.update(dict(params))
    if extra:
        raw.update(dict(extra))

    for key in raw:
        if key in HARD_GATE_ALIASES:
            return Decision(
                False,
                ReasonCode.REJECT_SOFT_PARAM,
                {"field": key, "why": "hard_gate_override"},
            )
        if key == "macd_enabled":
            continue
        if key not in ANALYST_BOUNDS and key not in {f.name for f in fields(SoftParams)}:
            return Decision(
                False,
                ReasonCode.REJECT_SOFT_PARAM,
                {"field": key, "why": "unknown_soft_param"},
            )

    if not raw:
        params = default_soft_params()
    elif not isinstance(params, SoftParams):
        try:
            params = SoftParams(
                **{
                    k: raw[k]
                    for k in (f.name for f in fields(SoftParams))
                    if k in raw
                }
            )
        except TypeError as exc:
            return Decision(False, ReasonCode.REJECT_SOFT_PARAM, {"why": str(exc)})

    assert isinstance(params, SoftParams)
    if params.macd_fast >= params.macd_slow:
        return Decision(
            False,
            ReasonCode.REJECT_SOFT_PARAM,
            {"field": "macd_fast", "why": "macd_fast_ge_slow"},
        )

    for name in ANALYST_BOUNDS:
        value = getattr(params, name)
        if not _in_bounds(name, value):
            lo, hi = ANALYST_BOUNDS[name]
            return Decision(
                False,
                ReasonCode.REJECT_SOFT_PARAM,
                {"field": name, "value": float(value), "lo": lo, "hi": hi},
            )

    # Soft params may tighten SL but never go below the signed floor.
    if MIN_SL_PCT < 0.012:
        return Decision(False, ReasonCode.REJECT_SL_FLOOR, {"why": "hard_floor_broken"})

    return Decision(True, ReasonCode.OK, {"soft_ok": True})
