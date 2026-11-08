"""`direction` compares a satin and a tatami on ONE axis (2026-11-07).

The question #1321 left open: toat_beanie (-0.292), Fremont hat (-0.38) and
MFab LC (-0.31) read direction kappa well below chance, near perpendicular.
If the scorer took a satin's angle from its rails (the column axis) and a
fill's from its rows, every satin-vs-fill cell would read 90 deg off and a
correctly matched pair would score 0.

These tests build one pair by hand: the pro sews a rectangle as tatami rows
at angle t, ours sews the SAME rectangle as one satin column whose crosses
run at t (so the thread on the fabric lies the same way). Rotated 0/45/90 deg,
`score_design` must read +1, and the 90-deg control must read 0 with its
histogram peak in the last bin. `docs/direction-kappa-axis-2026-11-07.md`
has the corpus half.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "pro_parity_scorecard_axis",
    Path(__file__).resolve().parent.parent / "tools" / "pro_parity" / "scorecard.py",
)
sc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sc)

W = 10.0     # mm, across the thread (the satin's cross length, the fill's row length)
L = 16.0     # mm, along the column axis / the row-advance direction
PITCH = 0.4  # mm, satin advance per cross and fill row spacing
STITCH = 3.4  # mm, longest fill stitch (a row is never one 10 mm needle move)


def _rot(pts, deg, cx=30.0, cy=30.0):
    """Rotate local (u, v) points by `deg` and place them at (cx, cy). u runs
    ALONG the thread, v across it (the advance)."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(cx + u * c - v * s, cy + u * s + v * c) for (u, v) in pts]


def tatami(deg):
    """Rows of length W at angle `deg`, PITCH apart, sewn boustrophedon, each row
    broken into <= STITCH mm stitches with a brick stagger."""
    pts, flip, k = [], False, 0
    n = int(math.ceil(W / STITCH))
    v = -L / 2
    while v <= L / 2 + 1e-9:
        off = (k % 3) * STITCH / 3
        us = sorted({-W / 2, W / 2, *[-W / 2 + off + i * STITCH for i in range(n)
                                       if -W / 2 < -W / 2 + off + i * STITCH < W / 2]})
        row = [(u, v) for u in (reversed(us) if flip else us)]
        pts += row
        flip = not flip
        v += PITCH
        k += 1
    return _rot(pts, deg)


def satin(deg):
    """One satin column: rails at u = -W/2 and u = +W/2, advancing along v, so
    every cross (rail to rail) lies along u -- the same way the tatami rows do."""
    pts, top = [], True
    v = -L / 2
    while v <= L / 2 + 1e-9:
        pts.append(((W / 2 if top else -W / 2), v))
        top = not top
        v += PITCH / 2
    return _rot(pts, deg)


def _write(path: Path, pts):
    with open(path, "w") as f:
        f.write("block,run,trim,jump,x_mm,y_mm\n")
        for x, y in pts:
            f.write(f"0,0,0,0,{x:.3f},{y:.3f}\n")


def _pair(tmp_path: Path, pro_pts, our_pts, name="axis") -> Path:
    d = tmp_path / name
    d.mkdir()
    _write(d / "pro_stitches.csv", pro_pts)
    _write(d / "ours_stitches.csv", our_pts)
    for side in ("pro", "ours"):
        (d / f"{side}_blocks.json").write_text('[{"block": 0, "rgb": [0, 0, 0]}]')
    return d


def _types(d: Path):
    """Majority stitch type per side over the scored cells (0 run, 1 satin, 2 fill)."""
    _r, pro, _s, _t = sc.load_side(d, "pro", d.name)
    _r, our, _s, _t = sc.load_side(d, "ours", d.name)
    dx, dy, _ = sc.register(pro, our, sc.bounds(pro, our))
    our_r = sc.shifted(our, dx, dy)
    bb = sc.bounds(pro, our_r)
    _c, sp, so, _det = sc.coverage_component(pro, our_r, bb, [], [])
    _pa, pt, _oa, ot, both = sc.direction_cells(pro, our_r, bb, sp, so)
    return np.bincount(pt[both], minlength=3).argmax(), np.bincount(ot[both], minlength=3).argmax()


@pytest.mark.parametrize("deg", [0.0, 45.0, 90.0])
def test_satin_crosses_and_tatami_rows_that_agree_read_plus_one(tmp_path, deg):
    d = _pair(tmp_path, tatami(deg), satin(deg))
    # The pair really is a fill against a satin, or the test proves nothing.
    assert _types(d) == (2, 1)
    s = sc.score_design(d)
    assert s["detail"]["shared_cells"] >= 6
    assert s["parts_raw"]["direction"] > 0.97
    assert s["parts"]["direction"] > 0.95       # chance-corrected kappa, floor 0.5
    h = sc.direction_histogram(d)
    assert h["mode_deg"] == [0.0, 15.0]
    assert h["near_perpendicular"] is False
    assert h["kappa_unclamped"] > 0.95


@pytest.mark.parametrize("deg", [0.0, 45.0])
def test_a_satin_sewn_across_the_rows_reads_zero_and_peaks_at_ninety(tmp_path, deg):
    """The control: ours' crosses turned 90 deg against the pro's rows -- what an
    axis-convention bug would make every satin-vs-fill cell look like."""
    d = _pair(tmp_path, tatami(deg), satin(deg + 90.0))
    s = sc.score_design(d)
    assert s["parts_raw"]["direction"] < 0.2      # row-end connectors and the rectangles' corners
    assert s["parts"]["direction"] == 0.0       # clamped at the floor
    h = sc.direction_histogram(d)
    assert h["mode_deg"] == [75.0, 90.0]
    assert h["near_perpendicular"] is True
    assert h["kappa_unclamped"] < -0.6


def test_the_histogram_reads_the_cells_score_design_scores(tmp_path):
    """Same registration, mask and grid: the cell count and the raw agreement
    match `score_design`'s, so the histogram explains the scored number."""
    d = _pair(tmp_path, tatami(30.0), satin(80.0))
    s = sc.score_design(d)
    h = sc.direction_histogram(d)
    assert h["cells"] == s["detail"]["shared_cells"]
    assert h["raw"] == pytest.approx(s["parts_raw"]["direction"], abs=1e-3)
    assert sum(h["counts"]) == h["cells"]
    # 50 deg apart: the mode is the 45-60 bin, not the perpendicular one.
    assert h["mode_deg"] == [45.0, 60.0]
    assert h["near_perpendicular"] is False
