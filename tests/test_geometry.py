from __future__ import annotations

from okx_scalper_v3.evaluate import evaluate_candidate
from okx_scalper_v3.geometry import check_geometry, mirror_geometry
from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.types import TradeGeometry
from tests.conftest import clean_account, valid_long, valid_short


def test_long_short_symmetry_metrics() -> None:
    long_geo = valid_long()
    short_geo = mirror_geometry(long_geo)
    assert short_geo.side == "short"
    assert abs(long_geo.sl_pct - short_geo.sl_pct) < 1e-12
    assert abs(long_geo.tp_pct - short_geo.tp_pct) < 1e-12
    assert abs(long_geo.rr - short_geo.rr) < 1e-12
    assert check_geometry(long_geo).reason is check_geometry(short_geo).reason


def test_evaluate_symmetric_on_trend(trend_up_bars) -> None:
    long_d = evaluate_candidate(trend_up_bars, valid_long(), clean_account())
    short_d = evaluate_candidate(trend_up_bars, valid_short(), clean_account())
    assert long_d.ok and short_d.ok
    assert long_d.reason is short_d.reason


def test_wrong_side_stops_rejected() -> None:
    geo = TradeGeometry(side="long", signal_price=100, entry=100, sl=101, tp=102)
    assert check_geometry(geo).reason is ReasonCode.REJECT_GEOMETRY
    geo2 = TradeGeometry(side="short", signal_price=100, entry=100, sl=99, tp=98)
    assert check_geometry(geo2).reason is ReasonCode.REJECT_GEOMETRY


def test_valid_short_helper_passes() -> None:
    assert check_geometry(valid_short()).ok
