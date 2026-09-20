"""Shared dataclasses for the offline scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from okx_scalper_v3.reasons import ReasonCode

Side = Literal["long", "short"]
Regime = Literal["chaos", "trend_up", "trend_down", "range"]
Outcome = Literal["open", "tp", "sl", "giveback", "timeout", "reject"]


@dataclass(frozen=True)
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("invalid bar: high below other prices")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("invalid bar: low above other prices")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("prices must be positive")


@dataclass(frozen=True)
class Features:
    atr_pct: float
    width: float
    slope: float
    eff: float
    brk: float
    n: int
    timeframe: str


@dataclass(frozen=True)
class TradeGeometry:
    side: Side
    signal_price: float
    entry: float
    sl: float
    tp: float

    @property
    def sl_distance(self) -> float:
        if self.side == "long":
            return self.entry - self.sl
        return self.sl - self.entry

    @property
    def tp_distance(self) -> float:
        if self.side == "long":
            return self.tp - self.entry
        return self.entry - self.tp

    @property
    def sl_pct(self) -> float:
        return self.sl_distance / self.entry

    @property
    def tp_pct(self) -> float:
        return self.tp_distance / self.entry

    @property
    def rr(self) -> float:
        if self.sl_distance <= 0:
            return 0.0
        return self.tp_distance / self.sl_distance


@dataclass(frozen=True)
class AccountState:
    equity: float
    day_start_equity: float
    daily_pnl: float
    open_positions: int
    open_risk_pct: float
    last_stop_ts: datetime | None
    now: datetime
    # Ignored. Daily-loss 5% has no exemption path.
    exemption: bool = False

    @property
    def daily_loss_pct(self) -> float:
        if self.day_start_equity <= 0:
            return float("inf")
        return -self.daily_pnl / self.day_start_equity


@dataclass(frozen=True)
class Decision:
    ok: bool
    reason: ReasonCode
    details: dict[str, float | int | str | bool] = field(default_factory=dict)

    def as_label_row(self) -> dict[str, str]:
        return {
            "accepted": "1" if self.ok else "0",
            "reason_code": self.reason.value,
        }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
