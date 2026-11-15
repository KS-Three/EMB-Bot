"""`cfg.extra["lettering_columns_lean_flat_ends"]` (built OFF 2026-11-14): a
leaned column's end on a flat face of the letter is mitred to the face.

Kent's #11 on Becker hat large, "The letters should be flat": MARINE's N
diagonal foot, re-stationed under the house cross, ended in crosses 10-12 deg
off the baseline. The pro's last cross lies ON the baseline there. Read on the
N as stage 7 handed it to the lane at 101.9 mm
(`testdata/becker_hat_large_lane_N.json`, from the tracked Becker art).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

from digitizer_core import columns, stitches
from digitizer_core.column_lean import _LEAN_FLAT_ENDS, lean_flat_ends_scope

N = Path(__file__).resolve().parent.parent / "testdata" / "becker_hat_large_lane_N.json"


def _n():
    v = json.loads(N.read_text(encoding="utf-8"))["N"]
    kw = {k: (tuple(x) if isinstance(x, list) else x) for k, x in v["kw"].items()}
    return Polygon(v["exterior"], v["holes"]), kw


def _sew(on: bool):
    poly, kw = _n()
    with lean_flat_ends_scope(on):
        runs, _ = columns.lettering_columns_shape(poly, "pin", **kw)
    return poly, runs


def _foot_gap(poly, runs) -> float:
    """Mean distance from the baseline to the lowest needle, per 0.5 mm of
    the right half (the diagonal's foot)."""
    x0, _y0, x1, y1 = poly.bounds
    pts = np.array([p for r in runs if r.kind == stitches.SATIN for p in r.points])
    sel = pts[(pts[:, 1] > y1 - 1.5) & (pts[:, 0] > x0 + 0.45 * (x1 - x0))]
    low: dict[int, float] = {}
    for x, y in sel:
        k = int((x - x0) / 0.5)
        low[k] = max(low.get(k, y), y)
    return float(np.mean([abs(y1 - y) for y in low.values()]))


def test_scope_off_is_the_lane_as_it_was():
    _p, a = _sew(False)
    poly, kw = _n()
    b, _r = columns.lettering_columns_shape(poly, "pin", **kw)
    assert [(r.points, r.kind) for r in a] == [(r.points, r.kind) for r in b]
    assert _LEAN_FLAT_ENDS.get() is False


def test_the_n_foot_lies_flatter_on_the_baseline():
    poly, off = _sew(False)
    _p, on = _sew(True)
    assert _foot_gap(poly, on) < _foot_gap(poly, off) - 0.05
