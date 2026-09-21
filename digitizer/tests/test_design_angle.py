"""`cfg.design_angle` (quality review 2026-09-08 item 7, built 2026-09-09):
one stitch direction for the design's shapes that have no house of their
own. DEFAULT OFF; off writes no key and changes nothing.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage7_sequence as s7
from digitizer_core.designangle import (META_KEY, fewest_columns_angle,
                                        house_design_angle, set_design_angle)
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage6_fill import best_fill_angle_deg
from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from tests.conftest import TESTDATA

BECKER = TESTDATA / "becker_marine_logo.png"
ALPHA = TESTDATA / "logo_alpha.png"


def _region(sid: str, poly: Polygon, **meta) -> Region:
    r = Region.__new__(Region)
    r.shape_id = sid
    r.polygon = poly
    r.meta = dict(meta)
    return r


def _rect(x0, y0, w, h) -> Polygon:
    return Polygon([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)])


def _sewn_angles(plan, shape_ids):
    """Per shape, the length-weighted doubled-angle mean of its fill runs."""
    out = {}
    for _b, r in plan.iter_runs():
        if r.kind != "fill" or r.shape_id not in shape_ids:
            continue
        c = s = w = 0.0
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            if d < 0.05 or d > 12.0:
                continue
            t = 2.0 * math.atan2(b[1] - a[1], b[0] - a[0])
            c += d * math.cos(t)
            s += d * math.sin(t)
            w += d
        if w > 0:
            prev = out.get(r.shape_id, (0.0, 0.0, 0.0))
            out[r.shape_id] = (prev[0] + c, prev[1] + s, prev[2] + w)
    return {sid: (math.degrees(0.5 * math.atan2(s, c))) % 180.0 for sid, (c, s, _w) in out.items()}


def _diff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def test_default_off_writes_nothing():
    assert PipelineConfig().design_angle is False
    result, _plan = digitize(ALPHA, PipelineConfig(target_width_mm=80.0))
    assert not any(META_KEY in r.meta for r in result.regions)


def test_the_house_angle_is_the_design_angle_when_the_lines_agree():
    regions = [
        _region("a", _rect(0, 0, 10, 2), satin_angle_deg=170.0),
        _region("b", _rect(0, 5, 10, 2), satin_angle_deg=175.0),
        _region("c", _rect(0, 10, 30, 30)),
    ]
    got = house_design_angle(regions)
    assert got is not None and _diff(got, 172.5) < 1.0
    # lines that disagree past the 30 deg lean cap are not one house
    regions[1].meta["satin_angle_deg"] = 60.0
    assert house_design_angle(regions) is None
    assert house_design_angle([regions[2]]) is None


def _comb(x0: float, y0: float, n: int, vertical: bool):
    """A base with `n` teeth: rows along the teeth cut it into one column,
    rows across them into n + 1 -- so the two orientations disagree, which
    two rectangles (one column at every angle) cannot."""
    base = box(x0, y0, x0 + 40, y0 + 6) if vertical else box(x0, y0, x0 + 6, y0 + 40)
    teeth = []
    for i in range(n):
        if vertical:
            tx = x0 + 2 + i * (36 / n)
            teeth.append(box(tx, y0 + 6, tx + 3, y0 + 30))
        else:
            ty = y0 + 2 + i * (36 / n)
            teeth.append(box(x0 + 6, ty, x0 + 30, ty + 3))
    return unary_union([base] + teeth)


def test_fewest_columns_over_the_design_is_one_angle_for_all():
    # teeth up (five) and teeth right (three): alone they pick 90 and 0;
    # together the sum is 1 + 4 columns at 90 against 6 + 1 at 0, so the
    # design takes the angle that costs the fewest columns in TOTAL
    up = _comb(0, 0, 5, True)
    right = _comb(60, 0, 3, False)
    assert best_fill_angle_deg(up, machine.FILL_ROW_MM) == 90.0
    assert best_fill_angle_deg(right, machine.FILL_ROW_MM) == 0.0
    assert fewest_columns_angle([up, right], machine.FILL_ROW_MM) == 90.0
    # one fill: exactly the per-shape answer, PCA candidate included
    tilt = affinity.rotate(box(0, 0, 30, 10), 33.0, origin=(0, 0))
    assert fewest_columns_angle([tilt], machine.FILL_ROW_MM) == best_fill_angle_deg(tilt, machine.FILL_ROW_MM)
    assert fewest_columns_angle([], machine.FILL_ROW_MM) is None


def test_the_pass_skips_review_intent_house_lines_and_other_tiers():
    regions = [
        _region("house", _rect(0, 0, 10, 2), satin_angle_deg=10.0, fill_angle_deg=10.0),
        _region("review", _rect(0, 5, 20, 20), fill_angle_deg=45.0),
        _region("run", _rect(30, 5, 20, 20), tier="run"),
        _region("slab", _rect(0, 30, 60, 20)),
        _region("bar", _rect(70, 0, 3, 40)),
    ]
    cfg = PipelineConfig(design_angle=True)
    got = set_design_angle(regions, cfg, "flat", machine.FILL_ROW_MM)
    assert got is not None and _diff(got, 10.0) < 1e-9      # the house line's angle
    by = {r.shape_id: r.meta for r in regions}
    assert META_KEY not in by["house"] and META_KEY not in by["review"] and META_KEY not in by["run"]
    assert by["slab"][META_KEY] == got
    assert by["bar"][META_KEY] == got                        # non-lettering satin takes it too
    assert by["review"]["fill_angle_deg"] == 45.0


def test_the_gradient_lanes_shared_angle_sits_between_the_house_and_the_objective():
    # no lettering: the lane's own fill-row angle wins over the column
    # objective (its fills sew at it whatever the metadata says); a house
    # that agrees still beats the lane; None falls through to the objective
    slab, bar = _rect(0, 30, 60, 20), _rect(70, 0, 3, 40)
    cfg = PipelineConfig(design_angle=True)
    regions = [_region("slab", slab), _region("bar", bar)]
    got = set_design_angle(regions, cfg, "gradient", machine.FILL_ROW_MM, lane_angle=-37.0)
    assert got == 143.0 and all(r.meta[META_KEY] == 143.0 for r in regions)   # folded to [0, 180)
    regions = [_region("house", _rect(0, 0, 10, 2), satin_angle_deg=10.0, fill_angle_deg=10.0),
               _region("slab", slab), _region("bar", bar)]
    got = set_design_angle(regions, cfg, "gradient", machine.FILL_ROW_MM, lane_angle=-37.0)
    assert got is not None and _diff(got, 10.0) < 1e-9
    regions = [_region("slab", slab), _region("bar", bar)]
    # the bar is satin-tier, so the objective runs over the slab alone
    assert set_design_angle(regions, cfg, "flat", machine.FILL_ROW_MM, lane_angle=None) == \
        fewest_columns_angle([slab], machine.FILL_ROW_MM)


def test_on_becker_every_fill_shares_the_house_and_sews_along_it():
    """The pro's own Becker files hold one fill angle; ours spread to a
    resultant of 0.15 at 95.7 mm with the flag off (plan doc 4). ON, every
    fill-tier shape without a house takes the house, and sews along it."""
    cfg = PipelineConfig(target_width_mm=95.7, design_angle=True)
    fills = {}
    real = s7.stitch_shape

    def spy(poly, shape_id, **kwargs):
        fills[shape_id] = kwargs.get("angle_deg")
        return real(poly, shape_id, **kwargs)

    s7.stitch_shape = spy
    try:
        result, plan = digitize(BECKER, cfg)
    finally:
        s7.stitch_shape = real
    meta = {r.shape_id: r.meta for r in result.regions}
    house = {round(float(m["satin_angle_deg"]), 3) for m in meta.values() if m.get("satin_angle_deg") is not None}
    assert house, "Becker's MARINE carries a house angle"
    design = {round(float(m[META_KEY]), 3) for m in meta.values() if META_KEY in m}
    assert len(design) == 1, design
    (angle,) = design
    assert min(_diff(angle, h) for h in house) < 30.0
    # every fill call got an angle, and the sewn rows follow it
    assert fills and all(a is not None for a in fills.values()), fills
    sewn = _sewn_angles(plan, set(fills))
    took = [sid for sid in fills if META_KEY in meta.get(sid, {})]
    assert took, "at least one non-lettering fill took the design angle"
    for sid in took:
        assert _diff(sewn[sid], angle) < 3.0, (sid, sewn[sid], angle)


def test_off_is_byte_identical_on_becker():
    _r0, p0 = digitize(BECKER, PipelineConfig(target_width_mm=80.0))
    _r1, p1 = digitize(BECKER, PipelineConfig(target_width_mm=80.0, design_angle=False))
    a = [(r.kind, tuple(map(tuple, r.points))) for _b, r in p0.iter_runs()]
    b = [(r.kind, tuple(map(tuple, r.points))) for _b, r in p1.iter_runs()]
    assert a == b
