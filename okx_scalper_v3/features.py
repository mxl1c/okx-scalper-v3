"""5m N=48 feature block: atr_pct / width / slope / eff / brk."""

from __future__ import annotations

from collections.abc import Sequence

from okx_scalper_v3.hard_gates import FEATURE_N, TIMEFRAME
from okx_scalper_v3.soft_params import SoftParams, default_soft_params
from okx_scalper_v3.types import Bar, Features


def _true_ranges(bars: Sequence[Bar]) -> list[float]:
    out: list[float] = []
    for i, bar in enumerate(bars):
        hl = bar.high - bar.low
        if i == 0:
            out.append(hl)
            continue
        prev = bars[i - 1].close
        out.append(max(hl, abs(bar.high - prev), abs(bar.low - prev)))
    return out


def _linreg_slope(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = 0.0
    den = 0.0
    for i, y in enumerate(values):
        dx = i - x_mean
        num += dx * (y - y_mean)
        den += dx * dx
    return num / den if den else 0.0


def compute_features(
    bars: Sequence[Bar],
    params: SoftParams | None = None,
    n: int = FEATURE_N,
) -> Features:
    if n != FEATURE_N:
        raise ValueError(f"signed feature window is N={FEATURE_N}, got {n}")
    if len(bars) < FEATURE_N:
        raise ValueError(f"need at least {FEATURE_N} bars, got {len(bars)}")

    params = params or default_soft_params()
    window = list(bars[-FEATURE_N:])
    close = window[-1].close
    highs = [b.high for b in window]
    lows = [b.low for b in window]
    closes = [b.close for b in window]

    trs = _true_ranges(window)
    atr_period = min(int(params.atr_period), len(trs))
    atr = sum(trs[-atr_period:]) / atr_period
    atr_pct = atr / close

    width = (max(highs) - min(lows)) / close
    slope = _linreg_slope(closes) / close

    net = abs(closes[-1] - closes[0])
    path = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))
    eff = net / path if path > 0 else 0.0

    prior_high = max(highs[:-1]) if len(highs) > 1 else highs[0]
    prior_low = min(lows[:-1]) if len(lows) > 1 else lows[0]
    if close > prior_high:
        brk = (close - prior_high) / close
    elif close < prior_low:
        brk = (close - prior_low) / close
    else:
        brk = 0.0

    return Features(
        atr_pct=atr_pct,
        width=width,
        slope=slope,
        eff=eff,
        brk=brk,
        n=FEATURE_N,
        timeframe=TIMEFRAME,
    )
