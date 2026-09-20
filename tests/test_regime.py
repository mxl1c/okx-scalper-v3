from __future__ import annotations

from okx_scalper_v3.hard_gates import FEATURE_N
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.regime import classify_from_features, classify_regime, macd_allowed
from okx_scalper_v3.soft_params import SoftParams
from okx_scalper_v3.types import Features
from tests.conftest import synth_bars


def test_priority_chaos_beats_strong_slope() -> None:
    features = Features(
        atr_pct=0.03,
        width=0.05,
        slope=0.002,
        eff=0.7,
        brk=0.01,
        n=FEATURE_N,
        timeframe="5m",
    )
    assert classify_from_features(features) == "chaos"


def test_trend_up_and_down() -> None:
    up = Features(0.01, 0.02, 0.0008, 0.5, 0.0, FEATURE_N, "5m")
    down = Features(0.01, 0.02, -0.0008, 0.5, 0.0, FEATURE_N, "5m")
    assert classify_from_features(up) == "trend_up"
    assert classify_from_features(down) == "trend_down"


def test_range_fallback() -> None:
    features = Features(0.01, 0.02, 0.00001, 0.15, 0.0, FEATURE_N, "5m")
    assert classify_from_features(features) == "range"


def test_synthetic_series_regimes() -> None:
    up, _ = classify_regime(synth_bars("trend_up"))
    down, _ = classify_regime(synth_bars("trend_down"))
    rng, _ = classify_regime(synth_bars("range"))
    ch, feat = classify_regime(synth_bars("chaos"))
    assert up == "trend_up"
    assert down == "trend_down"
    assert rng == "range"
    assert ch == "chaos"
    assert feat.n == FEATURE_N
    assert set(feat.__dict__) >= {"atr_pct", "width", "slope", "eff", "brk"}


def test_macd_only_on_trend() -> None:
    assert macd_allowed("trend_up", True).ok
    assert macd_allowed("trend_down", True).ok
    assert macd_allowed("range", False).ok
    d = macd_allowed("range", True)
    assert not d.ok and d.reason is ReasonCode.REJECT_MACD_REGIME
    d2 = macd_allowed("chaos", True)
    assert d2.reason is ReasonCode.REJECT_MACD_REGIME


def test_macd_params_still_need_sl_floor() -> None:
    params = SoftParams(macd_enabled=True)
    assert params.macd_enabled is True
    # Classifier itself does not mint a sub-floor stop.
    assert SoftParams().macd_enabled is False
