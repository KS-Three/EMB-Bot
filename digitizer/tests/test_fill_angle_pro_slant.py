"""`cfg.extra["fill_angle_pro_slant"]` (2026-11-07, built OFF): the pro's
20 deg fill angle per shape, +20 else -20, whichever first passes a trims
guard on the shape's column count; a shape neither passes sews as OFF.
`docs/fill-angle-pro-slant-2026-11-07.md` has the sign census and the pass.
"""
from __future__ import annotations

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import _comp_axis
from digitizer_core.stage6_fill import (FILL_ANGLE_PRO_SLANT_KEY, _cols_at_angle,
                                        pro_offset_fill_angle, pro_slant_angle)
from shapely import affinity
from shapely.geometry import box
from shapely.ops import unary_union
from tests.conftest import TESTDATA
from tests.test_fill_angle_pro_offset import _diff, _fill_angles, _runs

ALPHA = TESTDATA / "logo_alpha.png"
ON = {FILL_ANGLE_PRO_SLANT_KEY: True}
PLUS, MINUS = machine.FILL_ANGLE_PRO_DEG, 180.0 - machine.FILL_ANGLE_PRO_DEG


def _comb(rot: float, n: int = 6):
    """A comb (n teeth 2 mm wide, 2 mm apart, 12 mm tall) rotated by `rot`."""
    parts = [box(0, 0, n * 4.0, 3)] + [box(i * 4.0, 3, i * 4.0 + 2.0, 15) for i in range(n)]
    return affinity.rotate(unary_union(parts), rot, origin=(0, 0))


def test_default_off_and_needs_a_polygon():
    assert not PipelineConfig().extra.get(FILL_ANGLE_PRO_SLANT_KEY)
    assert pro_offset_fill_angle(PipelineConfig(), "S1", poly=box(0, 0, 40, 25)) is None
    # ON without the polygon cannot price a candidate: the caller's OFF chain runs
    assert pro_offset_fill_angle(PipelineConfig(extra=dict(ON)), "S1") is None


def test_plus_is_the_prior_when_it_costs_nothing():
    assert pro_offset_fill_angle(PipelineConfig(extra=dict(ON)), "S1", poly=box(0, 0, 40, 25)) == PLUS


def test_minus_when_plus_adds_columns_and_minus_does_not():
    comb = _comb(70.0)
    assert _cols_at_angle(comb, MINUS, machine.FILL_ROW_MM) == 1
    assert _cols_at_angle(comb, PLUS, machine.FILL_ROW_MM) > 3
    assert pro_slant_angle(comb, MINUS) == MINUS


def test_neither_passes_keeps_the_off_angle():
    comb = _comb(0.0)                      # upright teeth: 90 deg sews it as ONE column
    assert pro_slant_angle(comb, None) is None
    assert pro_offset_fill_angle(PipelineConfig(extra=dict(ON)), "S1", poly=comb) is None


def test_review_and_global_still_outrank_it():
    p = box(0, 0, 40, 25)
    assert pro_offset_fill_angle(PipelineConfig(extra=dict(ON), fill_angle_deg=45.0), "S1", poly=p) is None
    cfg = PipelineConfig(extra=dict(ON), shape_overrides={"S1": {"fill_angle_deg": 70.0}})
    assert pro_offset_fill_angle(cfg, "S1", poly=p) is None


def test_stage5_comp_axis_follows_the_guard():
    r = Region.__new__(Region)
    r.shape_id = "S1"
    r.meta = {"tier": "fill"}
    r.polygon = box(0, 0, 40, 25)
    assert _comp_axis(r, PipelineConfig(extra=dict(ON)), 10.0, "flat") == (PLUS, False)
    r.polygon = _comb(0.0)
    off = _comp_axis(r, PipelineConfig(), 10.0, "flat")
    assert _comp_axis(r, PipelineConfig(extra=dict(ON)), 10.0, "flat") == off


def test_on_every_fill_sews_plus_minus_or_its_off_angle_and_off_is_byte_identical():
    base = dict(target_width_mm=60.0)
    _r0, p0 = digitize(ALPHA, PipelineConfig(**base))
    _r1, p1 = digitize(ALPHA, PipelineConfig(**base, extra={FILL_ANGLE_PRO_SLANT_KEY: False}))
    assert _runs(p0) == _runs(p1)
    off = _fill_angles(p0)
    _r2, p2 = digitize(ALPHA, PipelineConfig(**base, extra=dict(ON)))
    sewn = _fill_angles(p2)
    assert sewn, "logo_alpha sews at least one fill"
    for sid, a in sewn.items():
        ok = min(_diff(a, PLUS), _diff(a, MINUS)) < 3.0 or (sid in off and _diff(a, off[sid]) < 3.0)
        assert ok, (sid, a, off.get(sid))


def test_signal_scoring_is_leave_out_and_keeps_the_prior_on_ties():
    from tools.fill_angle_slant_signals import score, slant
    assert slant([20.0, 110.0, 160.0], [1.0, 1.0, 1.0]) > 0     # 20 and 110 are both the + family
    assert slant([0.0, 90.0], [1.0, 1.0]) == 0.0
    # one artwork whose signal flags its own sign perfectly, three jobs of it:
    # leave-one-job-out learns it from its siblings, leave-one-artwork-out cannot
    rows = [{"job": f"becker_{i}", "pro_off": 20.0, **{k: 0.0 for k in
             ("art", "satin", "ourfill", "pca_off", "edges", "cols")}} for i in range(4)]
    rows += [{"job": f"toat_{i}", "pro_off": -20.0, **{k: 0.0 for k in
              ("satin", "ourfill", "pca_off", "edges", "cols")}, "art": 0.5} for i in range(3)]
    res = score(rows)
    assert res["always_plus"] == 4
    assert res["art"]["leave_one_job_out"] == 7
    assert res["art"]["leave_one_artwork_out"] == 4
