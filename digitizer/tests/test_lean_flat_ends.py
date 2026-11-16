"""`cfg.extra["lettering_columns_lean_flat_ends"]` (built OFF 2026-11-14): a
leaned column's end on a flat face of the letter turns its crosses to that
face, the last cross the face itself.

Kent's #11 on Becker hat large, "The letters should be flat": MARINE's N
diagonal foot, re-stationed under the house cross, ended in crosses 10-12 deg
off the baseline. The pro's last cross lies ON the baseline there. Read on the
N as stage 7 handed it to the lane at 101.9 mm
(`testdata/becker_hat_large_lane_N.json`, from the tracked Becker art).

As first built (`outline_cut._mitre_ends`) the flag moved two other letters
away from the pro (the 11-15 STOP, fixed 11-16), both read here on the lane
input stage 7 handed over, four flip-1 flags ON
(`testdata/lean_flat_ends_lanes.json`, from the tracked Gaulke and Drone art):
- Gaulke hat's Y: its arms' tops are level, and the mitre fanned them to a
  0.35 mm inner-corner chamfer, where the pro sews level crosses to the top;
- Drone's N: the diagonal's foot stepped its needles back up the stem, the
  "upright stub".
"""
from __future__ import annotations

import contextvars
import importlib
import json
import math
from pathlib import Path

import numpy as np
from shapely import wkb
from shapely.geometry import Polygon
from shapely.prepared import prep

from digitizer_core import column_lean, columns, stitches
from digitizer_core.column_lean import _LEAN_FLAT_ENDS, ItalicWord, lean_flat_ends_scope

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
N = TESTDATA / "becker_hat_large_lane_N.json"
LANES = TESTDATA / "lean_flat_ends_lanes.json"


def _n():
    v = json.loads(N.read_text(encoding="utf-8"))["N"]
    kw = {k: (tuple(x) if isinstance(x, list) else x) for k, x in v["kw"].items()}
    return Polygon(v["exterior"], v["holes"]), kw


def _sew(on: bool):
    poly, kw = _n()
    with lean_flat_ends_scope(on):
        runs, _ = columns.lettering_columns_shape(poly, "pin", **kw)
    return poly, runs


def _dec(v):
    if isinstance(v, dict) and "__wkb__" in v:
        return wkb.loads(v["__wkb__"], hex=True)
    if isinstance(v, dict) and "__tuple__" in v:
        return tuple(_dec(x) for x in v["__tuple__"])
    if isinstance(v, list):
        return [_dec(x) for x in v]
    return v


def _sew_lane(name: str, on: bool):
    """The lane on `name`'s input, under the ContextVars the plan had set
    (the four flip-1 flags and the stage-6 ones) and its italic word, if any
    (its area rebuilt from the letter: the lane asks only whether the letter
    lies in it)."""
    v = json.loads(LANES.read_text(encoding="utf-8"))[name]
    poly = wkb.loads(v["poly_wkb"], hex=True)
    kw = {k: _dec(x) for k, x in v["kw"].items()}

    def go():
        for key, val in v["context"].items():
            mod, var = key.split(".")
            getattr(importlib.import_module(f"digitizer_core.{mod}"), var).set(val)
        if v["italic"]:
            line, slant = v["italic"]
            column_lean._ITALIC.set((ItalicWord(line, slant, prep(poly.buffer(column_lean._WORD_REACH_MM))),))
        with lean_flat_ends_scope(on):
            return columns.lettering_columns_shape(poly, v["shape_id"], **kw)[0]
    return poly, contextvars.copy_context().run(go)


def _satin_segments(runs):
    for r in runs:
        if r.kind != stitches.SATIN or r.jump:
            continue
        for a, b in zip(r.points[:-1], r.points[1:]):
            yield np.asarray(a, float), np.asarray(b, float)


def test_scope_off_is_the_lane_as_it_was():
    _p, a = _sew(False)
    poly, kw = _n()
    b, _r = columns.lettering_columns_shape(poly, "pin", **kw)
    assert [(r.points, r.kind) for r in a] == [(r.points, r.kind) for r in b]
    assert _LEAN_FLAT_ENDS.get() is False


def _foot_tilt(poly, runs) -> float:
    """Mean tilt (deg) off the baseline of the long crosses (> 0.5 mm) whose
    middles lie within 0.6 mm of it, in the right half (the diagonal's foot)."""
    x0, _y0, x1, y1 = poly.bounds
    tilt = [math.degrees(math.atan2(abs(b[1] - a[1]), abs(b[0] - a[0])))
            for a, b in _satin_segments(runs)
            if (a[1] + b[1]) / 2 > y1 - 0.6 and (a[0] + b[0]) / 2 > x0 + 0.45 * (x1 - x0)
            and math.dist(a, b) > 0.5]
    assert tilt
    return float(np.mean(tilt))


def test_the_n_foot_lies_on_the_baseline():
    # the end the flag was built for: OFF 13.2 deg, ON 2.1 (the 11-14 mitre 3.3)
    poly, off = _sew(False)
    _p, on = _sew(True)
    assert _foot_tilt(poly, off) > 10.0
    assert _foot_tilt(poly, on) < 3.0


def test_a_level_arm_top_keeps_its_level_crosses():
    # Gaulke hat's Y: the arms' tops are level, their crosses already lie on
    # them; the 11-14 mitre took a 0.35 mm inner-corner chamfer for the face
    # and fanned them (8.4 -> 18.5 against the pro). Nothing to turn: ON is OFF.
    _p, off = _sew_lane("gaulke_hat_Y", False)
    _p, on = _sew_lane("gaulke_hat_Y", True)
    assert [(r.points, r.kind) for r in on] == [(r.points, r.kind) for r in off]


def test_the_drone_n_foot_has_no_upright_stub():
    # The diagonal's foot run, crosses within 1 mm of the baseline: its
    # needles on the stem side walk out to the stem's edge and never step
    # back. The 11-14 mitre ended 13.70 -> 13.88 -> 13.67, its last cross
    # 0.25 mm short of the edge, an upright stub of thread above the corner.
    poly, runs = _sew_lane("drone_N", True)
    x0, _y0, x1, y1 = poly.bounds
    foot = None
    for r in runs:
        if r.kind != stitches.SATIN or r.jump:
            continue
        pts = np.asarray(r.points, float)
        sel = (pts[:, 1] > y1 - 0.3) & (pts[:, 0] > x1 - 0.4 * (x1 - x0))
        if sel.any() and (foot is None or pts[sel, 1].max() > foot[1]):
            foot = (pts, pts[sel, 1].max())
    assert foot is not None
    pts = foot[0]
    crosses = [(a, b) for a, b in zip(pts[:-1], pts[1:]) if (a[1] + b[1]) / 2 > y1 - 1.0]
    right = [max(a[0], b[0]) for a, b in crosses]
    assert len(right) >= 4
    assert all(r1 >= r0 - 0.02 for r0, r1 in zip(right[:-1], right[1:])), right
    assert x1 - right[-1] < 0.12, right
