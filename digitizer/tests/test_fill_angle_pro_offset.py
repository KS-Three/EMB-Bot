"""`cfg.extra["fill_angle_pro_offset"]` (2026-11-07, built OFF): every fill
whose angle no review and no global sets sews at the pro's measured one fill
angle, `machine.FILL_ANGLE_PRO_DEG`, instead of on an axis.
`docs/fill-angle-pro-offset-2026-11-07.md` has the pro's distribution.
"""
from __future__ import annotations

import math

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import _comp_axis
from digitizer_core.stage6_fill import FILL_ANGLE_PRO_OFFSET_KEY, pro_offset_fill_angle
from shapely.geometry import box
from tests.conftest import TESTDATA

ALPHA = TESTDATA / "logo_alpha.png"
ON = {FILL_ANGLE_PRO_OFFSET_KEY: True}


def _diff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _fill_angles(plan) -> dict[str, float]:
    """Per shape, the length-weighted doubled-angle mean of its fill runs."""
    acc: dict[str, list[float]] = {}
    for _b, r in plan.iter_runs():
        if r.kind != "fill":
            continue
        c, s, w = acc.setdefault(r.shape_id, [0.0, 0.0, 0.0])
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            if d < 0.05 or d > 12.0:
                continue
            t = 2.0 * math.atan2(b[1] - a[1], b[0] - a[0])
            c += d * math.cos(t)
            s += d * math.sin(t)
            w += d
        acc[r.shape_id] = [c, s, w]
    return {sid: math.degrees(0.5 * math.atan2(s, c)) % 180.0
            for sid, (c, s, w) in acc.items() if w > 20.0}


def _runs(plan):
    return [(r.kind, r.shape_id, tuple(map(tuple, r.points))) for _b, r in plan.iter_runs()]


def test_default_off():
    assert not PipelineConfig().extra.get(FILL_ANGLE_PRO_OFFSET_KEY)
    assert pro_offset_fill_angle(PipelineConfig(), "S1") is None


def test_on_gives_the_measured_angle_off_both_axes():
    a = pro_offset_fill_angle(PipelineConfig(extra=dict(ON)), "S1")
    assert a == machine.FILL_ANGLE_PRO_DEG
    assert min(_diff(a, 0.0), _diff(a, 90.0)) > 10.0


def test_only_the_review_and_the_global_outrank_it():
    assert pro_offset_fill_angle(PipelineConfig(extra=dict(ON), fill_angle_deg=45.0), "S1") is None
    cfg = PipelineConfig(extra=dict(ON), shape_overrides={"S1": {"fill_angle_deg": 70.0}})
    assert pro_offset_fill_angle(cfg, "S1") is None
    assert pro_offset_fill_angle(cfg, "S2") == machine.FILL_ANGLE_PRO_DEG


def test_stage5_comp_axis_reads_the_same_angle_over_the_house():
    """The house angle sits in the fill_angle_deg meta slot; ON outranks it,
    so directional comp pulls along the rows stage 7 sews."""
    r = Region.__new__(Region)
    r.shape_id = "S1"
    r.polygon = box(0, 0, 40, 25)
    r.meta = {"tier": "fill", "fill_angle_deg": 0.0}
    off, off_sat = _comp_axis(r, PipelineConfig(), 10.0, "flat")
    on, on_sat = _comp_axis(r, PipelineConfig(extra=dict(ON)), 10.0, "flat")
    assert (off, off_sat) == (0.0, False)
    assert (on, on_sat) == (machine.FILL_ANGLE_PRO_DEG, False)


def test_on_every_fill_sews_at_the_angle_and_off_is_byte_identical():
    base = dict(target_width_mm=60.0)
    _r0, p0 = digitize(ALPHA, PipelineConfig(**base))
    _r1, p1 = digitize(ALPHA, PipelineConfig(**base, extra={FILL_ANGLE_PRO_OFFSET_KEY: False}))
    assert _runs(p0) == _runs(p1)
    _r2, p2 = digitize(ALPHA, PipelineConfig(**base, extra=dict(ON)))
    sewn = _fill_angles(p2)
    assert sewn, "logo_alpha sews at least one fill"
    for sid, a in sewn.items():
        assert _diff(a, machine.FILL_ANGLE_PRO_DEG) < 3.0, (sid, a)


def test_census_folds_lines_not_vectors():
    from tools.fill_angle_pro_census import _off_axis, _sdiff
    assert _off_axis(20.0) == 20.0
    assert abs(_off_axis(156.6) + 23.4) < 1e-9
    assert abs(_off_axis(72.0) + 18.0) < 1e-9
    assert abs(_sdiff(20.0, 179.0) - 21.0) < 1e-9
    assert abs(_sdiff(0.0, 90.0) - 90.0) < 1e-9
