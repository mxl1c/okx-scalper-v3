from __future__ import annotations

from okx_scalper_v3.reasons import ReasonCode
from okx_scalper_v3.soft_params import (
    ANALYST_BOUNDS,
    SoftParams,
    default_soft_params,
    validate_soft_params,
)


def test_defaults_are_inside_analyst_bounds() -> None:
    d = validate_soft_params(default_soft_params())
    assert d.ok


def test_out_of_bounds_rejected() -> None:
    d = validate_soft_params(SoftParams(chaos_atr_pct=0.09))
    assert d.reason is ReasonCode.REJECT_SOFT_PARAM
    assert d.details["field"] == "chaos_atr_pct"


def test_unknown_key_rejected() -> None:
    d = validate_soft_params(extra={"secret_override": 1})
    assert d.reason is ReasonCode.REJECT_SOFT_PARAM


def test_macd_fast_must_be_slower_than_slow() -> None:
    d = validate_soft_params(SoftParams(macd_fast=16, macd_slow=21))
    assert d.ok
    d2 = validate_soft_params(SoftParams(macd_fast=26, macd_slow=21))
    assert d2.reason is ReasonCode.REJECT_SOFT_PARAM


def test_every_bound_edge_accepted_and_outside_rejected() -> None:
    for name, (lo, hi) in ANALYST_BOUNDS.items():
        base = default_soft_params()
        ok_lo = SoftParams(**{**{f: getattr(base, f) for f in base.__dataclass_fields__}, name: lo})
        ok_hi = SoftParams(**{**{f: getattr(base, f) for f in base.__dataclass_fields__}, name: hi})
        if name == "macd_fast":
            # keep fast < slow
            ok_hi = SoftParams(**{**ok_hi.__dict__, "macd_slow": 30})
        assert validate_soft_params(ok_lo).ok, name
        assert validate_soft_params(ok_hi).ok, name
        below = SoftParams(
            **{**{f: getattr(base, f) for f in base.__dataclass_fields__}, name: lo - 1e-6}
        )
        assert validate_soft_params(below).reason is ReasonCode.REJECT_SOFT_PARAM
