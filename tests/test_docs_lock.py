from __future__ import annotations

from pathlib import Path

from okx_scalper_v3.labels import LABEL_FIELD_DICTIONARY
from okx_scalper_v3.reasons import ReasonCode

ROOT = Path(__file__).resolve().parents[1]


def test_strategy_and_risk_docs_exist_and_lock_numbers() -> None:
    strategy = (ROOT / "STRATEGY.md").read_text(encoding="utf-8")
    risk = (ROOT / "RISK.md").read_text(encoding="utf-8")
    for doc in (strategy, risk):
        assert "okx-scalper-v3" in doc
        assert "3.0.0" in doc

    assert "chaos→trend→range" in strategy.replace(" ", "") or "chaos → trend → range" in strategy
    assert "N = 48" in strategy or "N=48" in strategy
    for feat in ("atr_pct", "width", "slope", "eff", "brk"):
        assert feat in strategy
    assert "多空对称" in strategy
    for field in (
        "atr_pct",
        "width",
        "slope",
        "eff",
        "brk",
        "reason_code",
        "accepted",
        "y_r",
        "exit_class",
        "fail_tag",
        "outcome",
        "pnl_pct",
        "net_pnl_pct",
    ):
        assert field in LABEL_FIELD_DICTIONARY
        assert field in strategy
    for token in ("sl", "invalidate", "reverse", "tp", "stale_half", "stale_flat", "replace", "manual"):
        assert token in strategy
    for token in ("stop_out", "fake_break", "regime_wrong", "fee_grind", "early_lock"):
        assert token in strategy
    assert "数值边界见 RISK §软参" in strategy
    assert "flatten-all" in strategy
    assert "只禁止新开仓" in strategy or "只禁止新开" in strategy

    assert "parallel ≤ 3" in risk or "parallel ≤3" in risk
    assert "2%" in risk
    assert "5%" in risk
    assert "MIN_RR ≥ 1.5" in risk or "MIN_RR ≥1.5" in risk
    assert "1.2%" in risk
    assert "90" in risk
    assert "无豁免" in risk
    assert "Chase ban" in risk or "追价" in risk
    assert "giveback" in risk.lower()
    assert "chaos" in risk.lower()
    assert "flatten-all" in risk
    assert "只禁止新开" in risk or "block new opens only" in risk
    assert "§软参" in risk or "软参" in risk


def test_docs_list_every_reason_code() -> None:
    blob = (ROOT / "STRATEGY.md").read_text(encoding="utf-8") + (ROOT / "RISK.md").read_text(
        encoding="utf-8"
    )
    for code in ReasonCode:
        if code is ReasonCode.OK:
            continue
        assert code.value in blob, code.value
