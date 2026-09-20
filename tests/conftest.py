from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from okx_scalper_v3.hard_gates import FEATURE_N
from okx_scalper_v3.types import AccountState, Bar, TradeGeometry


def _bar(ts: datetime, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(ts=ts, open=o, high=h, low=l, close=c, volume=1.0)


def synth_bars(kind: str, n: int = FEATURE_N, start: float = 100.0) -> list[Bar]:
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = start
    for i in range(n):
        ts = t0 + timedelta(minutes=5 * i)
        if kind == "trend_up":
            price = start * (1.0 + 0.0012 * i)
            o, c = price * 0.9994, price
            h, l = c * 1.0004, o * 0.9994
        elif kind == "trend_down":
            price = start * (1.0 - 0.0012 * i)
            o, c = price * 1.0006, price
            h, l = o * 1.0004, c * 0.9994
        elif kind == "range":
            wave = 0.0015 if i % 2 == 0 else -0.0015
            price = start * (1.0 + wave)
            o, c = start, price
            h, l = max(o, c) * 1.0006, min(o, c) * 0.9994
        elif kind == "chaos":
            # Wide, mean-reverting swings → high ATR / width, low efficiency.
            wave = 0.028 if i % 2 == 0 else -0.028
            price = start * (1.0 + wave)
            o = start * (1.0 - wave)
            c = price
            h, l = max(o, c) * 1.012, min(o, c) * 0.988
        else:
            raise ValueError(kind)
        bars.append(_bar(ts, o, h, l, c))
    return bars


@pytest.fixture
def trend_up_bars() -> list[Bar]:
    return synth_bars("trend_up")


@pytest.fixture
def range_bars() -> list[Bar]:
    return synth_bars("range")


@pytest.fixture
def chaos_bars() -> list[Bar]:
    return synth_bars("chaos")


def valid_long(entry: float = 100.0) -> TradeGeometry:
    sl_pct = 0.012
    rr = 1.5
    return TradeGeometry(
        side="long",
        signal_price=entry,
        entry=entry,
        sl=entry * (1.0 - sl_pct),
        tp=entry * (1.0 + sl_pct * rr),
    )


def valid_short(entry: float = 100.0) -> TradeGeometry:
    sl_pct = 0.012
    rr = 1.5
    return TradeGeometry(
        side="short",
        signal_price=entry,
        entry=entry,
        sl=entry * (1.0 + sl_pct),
        tp=entry * (1.0 - sl_pct * rr),
    )


def clean_account(**overrides: object) -> AccountState:
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    base = dict(
        equity=10_000.0,
        day_start_equity=10_000.0,
        daily_pnl=0.0,
        open_positions=0,
        open_risk_pct=0.0,
        last_stop_ts=None,
        now=now,
        exemption=False,
    )
    base.update(overrides)
    return AccountState(**base)  # type: ignore[arg-type]
