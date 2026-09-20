from __future__ import annotations

from okx_scalper_v3.hard_gates import FEATURE_N, SIGNED_SPEC_VERSION, TIMEFRAME
from okx_scalper_v3.labels import LABEL_FIELD_DICTIONARY, build_label_row
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.regime import classify_regime
from okx_scalper_v3.types import Decision
from tests.conftest import valid_long


REQUIRED = {
    "ts_utc",
    "symbol",
    "timeframe",
    "feature_n",
    "atr_pct",
    "width",
    "slope",
    "eff",
    "brk",
    "regime",
    "side",
    "reason_code",
    "accepted",
    "spec_version",
}


def test_dictionary_covers_signed_research_fields() -> None:
    assert REQUIRED.issubset(LABEL_FIELD_DICTIONARY)
    for key in ("atr_pct", "width", "slope", "eff", "brk"):
        assert key in LABEL_FIELD_DICTIONARY


def test_build_label_row_roundtrip(trend_up_bars) -> None:
    regime, features = classify_regime(trend_up_bars)
    geo = valid_long()
    row = build_label_row(
        ts_utc="2026-01-01T00:00:00+00:00",
        symbol="BTC-USDT-SWAP",
        features=features,
        regime=regime,
        geo=geo,
        decision=Decision(True, ReasonCode.OK),
        risk_pct=0.012,
        open_positions=0,
        open_risk_pct=0.0,
        daily_loss_pct=0.0,
        outcome="open",
    )
    assert set(row) == set(LABEL_FIELD_DICTIONARY)
    assert row["timeframe"] == TIMEFRAME
    assert row["feature_n"] == str(FEATURE_N)
    assert row["spec_version"] == SIGNED_SPEC_VERSION
    assert row["accepted"] == "1"
    assert row["reason_code"] == "OK"


def test_unknown_extra_field_rejected(trend_up_bars) -> None:
    regime, features = classify_regime(trend_up_bars)
    try:
        build_label_row(
            ts_utc="t",
            symbol="X",
            features=features,
            regime=regime,
            geo=valid_long(),
            decision=Decision(False, ReasonCode.REJECT_CHAOS),
            risk_pct=0.0,
            open_positions=0,
            open_risk_pct=0.0,
            daily_loss_pct=0.0,
            extra={"not_a_field": "1"},
        )
    except KeyError:
        return
    raise AssertionError("unknown label field must raise")
