from __future__ import annotations

from okx_scalper_v3.evaluate import evaluate_candidate
from okx_scalper_v3.hard_gates import FEATURE_N
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.soft_params import SoftParams
from tests.conftest import clean_account, synth_bars, valid_long


def test_trend_candidate_accepted(trend_up_bars) -> None:
    d = evaluate_candidate(trend_up_bars, valid_long(), clean_account())
    assert d.ok
    assert d.reason is ReasonCode.OK
    assert d.details["regime"] == "trend_up"


def test_range_candidate_accepted(range_bars) -> None:
    d = evaluate_candidate(range_bars, valid_long(), clean_account())
    assert d.ok
    assert d.details["regime"] == "range"


def test_insufficient_bars_rejected(trend_up_bars) -> None:
    d = evaluate_candidate(trend_up_bars[: FEATURE_N - 1], valid_long(), clean_account())
    assert d.reason is ReasonCode.REJECT_INSUFFICIENT_BARS


def test_macd_on_range_rejected(range_bars) -> None:
    d = evaluate_candidate(
        range_bars,
        valid_long(),
        clean_account(),
        params=SoftParams(macd_enabled=True),
    )
    assert d.reason is ReasonCode.REJECT_MACD_REGIME


def test_macd_on_trend_still_requires_sl_floor() -> None:
    bars = synth_bars("trend_up")
    d = evaluate_candidate(
        bars,
        valid_long(),
        clean_account(),
        params=SoftParams(macd_enabled=True),
    )
    assert d.ok
    assert d.details["sl_pct"] >= 0.012
