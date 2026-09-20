from __future__ import annotations

import pytest

from okx_scalper_v3.hard_gates import FEATURE_N, SIGNED_SPEC_VERSION, TIMEFRAME
from okx_scalper_v3.labels import (
    EXIT_CLASSES,
    FAIL_TAGS,
    LABEL_FIELD_DICTIONARY,
    build_label_row,
    compute_y_r,
    parse_fail_tags,
    validate_exit_class,
)
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
    "y_r",
    "exit_class",
    "fail_tag",
    "outcome",
    "pnl_pct",
    "net_pnl_pct",
}


def test_dictionary_covers_signed_research_fields() -> None:
    assert REQUIRED.issubset(LABEL_FIELD_DICTIONARY)
    for key in ("atr_pct", "width", "slope", "eff", "brk"):
        assert key in LABEL_FIELD_DICTIONARY
    # Analyst sign-off fields sit beside — not instead of — outcome/pnl_*.
    assert {"outcome", "pnl_pct", "net_pnl_pct", "y_r", "exit_class", "fail_tag"} <= set(
        LABEL_FIELD_DICTIONARY
    )


def test_exit_class_enum_is_closed() -> None:
    expected = {
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
    assert EXIT_CLASSES == expected
    for name in expected:
        assert validate_exit_class(name) == name
    with pytest.raises(ValueError):
        validate_exit_class("flatten_all")


def test_fail_tag_multiselect() -> None:
    expected = {
        "stop_out",
        "fake_break",
        "regime_wrong",
        "chase",
        "fee_grind",
        "early_lock",
        "other",
    }
    assert FAIL_TAGS == expected
    assert parse_fail_tags("stop_out|fake_break") == ("stop_out", "fake_break")
    assert parse_fail_tags("") == ()
    with pytest.raises(ValueError):
        parse_fail_tags("stop_out|not_a_tag")


def test_y_r_is_fee_aware_net_over_one_r() -> None:
    sl_pct = 0.012
    fee_rt = 0.001
    pnl_pct = 0.018
    net = pnl_pct - fee_rt
    assert compute_y_r(net, sl_pct) == pytest.approx(net / sl_pct)
    with pytest.raises(ValueError):
        compute_y_r(net, 0.0)


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
        pnl_pct=0.018,
        fee_pct_rt=0.001,
        exit_class="tp",
        fail_tag="",
    )
    assert set(row) == set(LABEL_FIELD_DICTIONARY)
    assert row["timeframe"] == TIMEFRAME
    assert row["feature_n"] == str(FEATURE_N)
    assert row["spec_version"] == SIGNED_SPEC_VERSION
    assert row["accepted"] == "1"
    assert row["reason_code"] == "OK"
    assert row["outcome"] == "open"
    assert row["pnl_pct"] != ""
    assert row["net_pnl_pct"] != ""
    assert row["y_r"] == f"{compute_y_r(0.017, geo.sl_pct):.10f}"
    assert row["exit_class"] == "tp"
    assert row["fail_tag"] == ""


def test_label_row_rejects_unknown_exit_class(trend_up_bars) -> None:
    regime, features = classify_regime(trend_up_bars)
    with pytest.raises(ValueError, match="exit_class"):
        build_label_row(
            ts_utc="t",
            symbol="X",
            features=features,
            regime=regime,
            geo=valid_long(),
            decision=Decision(True, ReasonCode.OK),
            risk_pct=0.012,
            open_positions=0,
            open_risk_pct=0.0,
            daily_loss_pct=0.0,
            exit_class="flatten_all",
        )


def test_rejected_candidate_defaults_exit_class_reject(trend_up_bars) -> None:
    regime, features = classify_regime(trend_up_bars)
    row = build_label_row(
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
        fail_tag="regime_wrong|chase",
    )
    assert row["outcome"] == "reject"
    assert row["exit_class"] == "reject"
    assert row["fail_tag"] == "regime_wrong|chase"
    assert row["y_r"] == ""


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
