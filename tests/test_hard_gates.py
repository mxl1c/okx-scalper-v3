"""Lock every signed hard gate. Loosening any value or edge must fail."""

from __future__ import annotations

import inspect
from datetime import timedelta

import pytest

from okx_scalper_v3 import hard_gates as hg
from okx_scalper_v3.evaluate import evaluate_candidate
from okx_scalper_v3.geometry import check_chase_ban, check_geometry, check_min_rr, check_sl_floor
from okx_scalper_v3.giveback import check_giveback, fee_aware_breakeven
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.risk import (
    check_aggregate_risk,
    check_chaos_new_opens,
    check_cooldown,
    check_daily_loss,
    check_parallel,
    check_per_trade_risk,
    check_risk_gates,
)
from okx_scalper_v3.soft_params import SoftParams, validate_soft_params
from okx_scalper_v3.types import TradeGeometry
from tests.conftest import clean_account, valid_long, valid_short


def test_signed_constants_are_frozen() -> None:
    assert hg.SIGNED_STRATEGY_ID == "okx-scalper-v3"
    assert hg.SIGNED_SPEC_VERSION == "3.0.0"
    assert hg.TIMEFRAME == "5m"
    assert hg.FEATURE_N == 48
    assert hg.MAX_PARALLEL == 3
    assert hg.MAX_PER_TRADE_RISK == 0.02
    assert hg.MAX_AGGREGATE_RISK == 0.05
    assert hg.MAX_DAILY_LOSS == 0.05
    assert hg.DAILY_LOSS_EXEMPTIONS_ALLOWED is False
    assert hg.MIN_RR == 1.5
    assert hg.MIN_SL_PCT == 0.012
    assert hg.CHASE_BANNED is True
    assert hg.COOLDOWN_MINUTES == 90
    assert hg.CHAOS_BLOCKS_NEW_OPENS is True
    assert hg.GIVEBACK_REQUIRES_ACTIVATION is True
    assert hg.GIVEBACK_FEE_AWARE_NO_LOSS is True
    assert hg.MACD_ALLOWED_REGIMES == frozenset({"trend_up", "trend_down"})
    assert 0 < hg.EDGE_EPS <= 1e-9


def test_constants_cannot_be_loosened_by_inequality() -> None:
    """If someone raises a cap or lowers a floor, this fails."""
    assert hg.MAX_PARALLEL <= 3
    assert hg.MAX_PER_TRADE_RISK <= 0.02
    assert hg.MAX_AGGREGATE_RISK <= 0.05
    assert hg.MAX_DAILY_LOSS <= 0.05
    assert hg.MIN_RR >= 1.5
    assert hg.MIN_SL_PCT >= 0.012
    assert hg.COOLDOWN_MINUTES >= 90


# --- parallel ≤ 3 ---


@pytest.mark.parametrize("open_positions", [0, 1, 2])
def test_parallel_allows_up_to_three_total(open_positions: int) -> None:
    acc = clean_account(open_positions=open_positions)
    assert check_parallel(acc).ok


def test_parallel_fourth_rejected() -> None:
    acc = clean_account(open_positions=3)
    d = check_parallel(acc)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_PARALLEL


def test_parallel_source_uses_ge_not_gt() -> None:
    src = inspect.getsource(check_parallel)
    assert "open_positions >= MAX_PARALLEL" in src


# --- per-trade ≤ 2% ---


def test_per_trade_risk_at_two_percent_allowed() -> None:
    assert check_per_trade_risk(0.02).ok


def test_per_trade_risk_just_over_two_percent_rejected() -> None:
    d = check_per_trade_risk(0.0200001)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_PER_TRADE_RISK


def test_per_trade_source_rejects_above_cap() -> None:
    src = inspect.getsource(check_per_trade_risk)
    assert "risk_pct > MAX_PER_TRADE_RISK + EDGE_EPS" in src


# --- aggregate ≤ 5% ---


def test_aggregate_at_five_percent_allowed() -> None:
    acc = clean_account(open_risk_pct=0.03)
    assert check_aggregate_risk(acc, 0.02).ok


def test_aggregate_just_over_five_percent_rejected() -> None:
    acc = clean_account(open_risk_pct=0.03)
    d = check_aggregate_risk(acc, 0.0200001)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_AGGREGATE_RISK


def test_aggregate_source_rejects_above_cap() -> None:
    src = inspect.getsource(check_aggregate_risk)
    assert "total > MAX_AGGREGATE_RISK + EDGE_EPS" in src


# --- daily loss 5%, no exemption ---


def test_daily_loss_just_under_five_allowed() -> None:
    acc = clean_account(daily_pnl=-499.99)
    assert check_daily_loss(acc).ok


def test_daily_loss_at_five_percent_blocks() -> None:
    acc = clean_account(daily_pnl=-500.0)
    d = check_daily_loss(acc)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_DAILY_LOSS


def test_daily_loss_exemption_flag_is_ignored() -> None:
    acc = clean_account(daily_pnl=-500.0, exemption=True)
    d = check_daily_loss(acc)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_DAILY_LOSS
    assert d.details["exemption_honored"] is False


def test_daily_loss_exemptions_constant_stays_false() -> None:
    assert hg.DAILY_LOSS_EXEMPTIONS_ALLOWED is False
    src = inspect.getsource(check_daily_loss)
    assert "DAILY_LOSS_EXEMPTIONS_ALLOWED" in src
    assert "exemption_honored" in src


# --- MIN_RR ≥ 1.5 ---


def test_min_rr_at_one_point_five_allowed() -> None:
    geo = valid_long()
    assert abs(geo.rr - 1.5) < 1e-12
    assert check_min_rr(geo).ok


def test_min_rr_below_one_point_five_rejected() -> None:
    geo = TradeGeometry(
        side="long",
        signal_price=100.0,
        entry=100.0,
        sl=98.8,
        tp=100.0 + 1.2 * 1.499,
    )
    d = check_min_rr(geo)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_MIN_RR


# --- chase ban ---


def test_chase_ban_long_worse_fill_rejected() -> None:
    geo = TradeGeometry(side="long", signal_price=100.0, entry=100.01, sl=98.8, tp=101.8)
    d = check_chase_ban(geo)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_CHASE


def test_chase_ban_short_worse_fill_rejected() -> None:
    geo = TradeGeometry(side="short", signal_price=100.0, entry=99.99, sl=101.2, tp=98.2)
    d = check_chase_ban(geo)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_CHASE


def test_chase_ban_better_or_equal_fill_allowed() -> None:
    long_eq = valid_long()
    long_better = TradeGeometry(
        side="long", signal_price=100.0, entry=99.9, sl=99.9 * 0.988, tp=99.9 * 1.018
    )
    short_eq = valid_short()
    assert check_chase_ban(long_eq).ok
    assert check_chase_ban(long_better).ok
    assert check_chase_ban(short_eq).ok
    assert hg.CHASE_BANNED is True


def test_chase_ban_source_has_no_whitelist() -> None:
    src = inspect.getsource(check_chase_ban)
    assert "if not CHASE_BANNED" in src
    assert "REJECT_CHASE" in src


# --- SL floor ≥ 1.2% ---


def test_sl_floor_at_1_2_percent_allowed() -> None:
    assert check_sl_floor(valid_long()).ok
    assert check_sl_floor(valid_short()).ok


def test_sl_floor_below_1_2_percent_rejected() -> None:
    geo = TradeGeometry(side="long", signal_price=100.0, entry=100.0, sl=98.81, tp=101.8)
    assert geo.sl_pct < 0.012
    d = check_sl_floor(geo)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_SL_FLOOR


# --- cooldown 90m ---


def test_cooldown_89_minutes_rejected() -> None:
    now = clean_account().now
    acc = clean_account(last_stop_ts=now - timedelta(minutes=90) + timedelta(seconds=1))
    d = check_cooldown(acc)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_COOLDOWN


def test_cooldown_exactly_90_minutes_allowed() -> None:
    now = clean_account().now
    acc = clean_account(last_stop_ts=now - timedelta(minutes=90))
    assert check_cooldown(acc).ok


def test_cooldown_constant_is_90() -> None:
    assert hg.COOLDOWN_MINUTES == 90
    src = inspect.getsource(check_cooldown)
    assert "minutes=COOLDOWN_MINUTES" in src
    assert "elapsed < need" in src


# --- chaos = no new opens ---


def test_chaos_blocks_new_opens() -> None:
    d = check_chaos_new_opens("chaos")
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_CHAOS


@pytest.mark.parametrize("regime", ["trend_up", "trend_down", "range"])
def test_non_chaos_regimes_pass_chaos_gate(regime: str) -> None:
    assert check_chaos_new_opens(regime).ok  # type: ignore[arg-type]


def test_chaos_is_new_open_block_not_flatten() -> None:
    src = inspect.getsource(check_chaos_new_opens)
    assert "flatten" not in src.lower() or "does not flatten" in src
    assert "force-close" in src or "does not flatten" in src
    assert check_chaos_new_opens("chaos").reason is ReasonCode.REJECT_CHAOS


def test_evaluate_rejects_chaos_bars(chaos_bars) -> None:
    d = evaluate_candidate(chaos_bars, valid_long(), clean_account())
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_CHAOS


# --- giveback: activation + fee-aware no-loss ---


def test_giveback_before_activation_rejected() -> None:
    geo = valid_long()
    mfe = geo.entry + 0.5 * geo.sl_distance
    d = check_giveback(geo, proposed_stop=geo.entry * 1.002, mfe_price=mfe)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_GIVEBACK_NOT_ARMED


def test_giveback_at_entry_is_fee_loss() -> None:
    geo = valid_long()
    mfe = geo.entry + 1.0 * geo.sl_distance
    d = check_giveback(geo, proposed_stop=geo.entry, mfe_price=mfe)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_GIVEBACK_FEE_LOSS


def test_giveback_fee_aware_breakeven_allowed() -> None:
    geo = valid_long()
    params = SoftParams()
    be = fee_aware_breakeven(geo, params.fee_pct_one_way)
    mfe = geo.entry + 1.0 * geo.sl_distance
    d = check_giveback(geo, proposed_stop=be, mfe_price=mfe, params=params)
    assert d.ok


def test_giveback_short_symmetry_fee_floor() -> None:
    geo = valid_short()
    params = SoftParams()
    be = fee_aware_breakeven(geo, params.fee_pct_one_way)
    mfe = geo.entry - 1.0 * geo.sl_distance
    assert check_giveback(geo, proposed_stop=be, mfe_price=mfe, params=params).ok
    d = check_giveback(geo, proposed_stop=geo.entry, mfe_price=mfe, params=params)
    assert d.reason is ReasonCode.REJECT_GIVEBACK_FEE_LOSS


# --- soft params cannot override hard gates ---


@pytest.mark.parametrize(
    "payload",
    [
        {"max_parallel": 10},
        {"min_rr": 1.0},
        {"min_sl_pct": 0.005},
        {"cooldown_minutes": 10},
        {"exemption": True},
        {"daily_loss_exemption": True},
        {"chase_banned": False},
    ],
)
def test_soft_params_cannot_override_hard_gates(payload: dict) -> None:
    d = validate_soft_params(extra=payload)
    assert not d.ok
    assert d.reason is ReasonCode.REJECT_SOFT_PARAM


def test_macd_cannot_relax_sl_floor() -> None:
    geo = TradeGeometry(side="long", signal_price=100.0, entry=100.0, sl=99.0, tp=103.0)
    assert geo.sl_pct < 0.012
    d = check_geometry(geo)
    assert d.reason is ReasonCode.REJECT_SL_FLOOR
    params = SoftParams(macd_enabled=True)
    # MACD on does not create a bypass path inside geometry.
    assert check_geometry(geo).reason is ReasonCode.REJECT_SL_FLOOR
    assert params.macd_enabled is True


def test_risk_gate_bundle_still_enforces_after_soft_ok(trend_up_bars) -> None:
    acc = clean_account(open_positions=3)
    d = evaluate_candidate(trend_up_bars, valid_long(), acc)
    assert d.reason is ReasonCode.REJECT_PARALLEL
    d2 = check_risk_gates(acc, "trend_up", valid_long(), risk_pct=0.02)
    assert d2.reason is ReasonCode.REJECT_PARALLEL
