"""`cfg.wide_columns` (quality review 2026-09-08 item 4; plan
`docs/superpowers/plans/2026-09-09-wide-column-policy.md`): the 6.5 mm
ceiling threaded from the classifier to the emitter as one number, and the
fold guard that makes any ceiling past 5.0 safe.

DOCTRINE 2026-09-02 measured both routes past 5.0 breaking something: moved
together, the per-station cap in `_rail_points` moved too and logo_alpha's
`Sf5200f3f` apex crossed itself again; split, the classifier admitted what
the emitter refused. The first test here REPRODUCES that measurement with the
ceiling alone and shows the fold guard closing it.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString

from digitizer_core import PipelineConfig, digitize, machine, run_stages
from digitizer_core import stage6_satin as s6
from digitizer_core.machine import satin_ceiling_mm
from digitizer_core.stage6_satin import satin_shape, strip_splits
from digitizer_core.stitches import strip_ties

from .conftest import TESTDATA

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
from wide_columns import crossing_pairs  # noqa: E402


def test_the_ceiling_is_one_number_and_the_flag_moves_it():
    assert PipelineConfig().wide_columns is False
    assert satin_ceiling_mm(PipelineConfig()) == machine.SATIN_MAX_WIDTH_MM
    assert satin_ceiling_mm(PipelineConfig(wide_columns=True)) == machine.SATIN_WIDE_COLUMN_MAX_MM
    assert satin_ceiling_mm(PipelineConfig(wide_columns=True, satin_max_width_mm=4.0)) == 4.0
    assert machine.SATIN_MAX_WIDTH_MM < machine.SATIN_WIDE_COLUMN_MAX_MM


def _apex_crossings(max_width_mm: float, fold_guard: bool) -> int:
    """`Sf5200f3f` forced through `satin_shape` exactly as
    `test_satin_crosses_do_not_self_overlap_across_a_wide_junction` does."""
    c = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(TESTDATA / "logo_alpha.png", c)
    region = next(r for r in result.regions if r.shape_id == "Sf5200f3f")
    runs, report = satin_shape(region.polygon, region.shape_id,
                               underlay_style="center_run", trim_at_mm=3.0,
                               max_width_mm=max_width_mm, fold_guard=fold_guard)
    assert not report["empty"]
    segs = []
    for run in runs:
        if run.kind != "satin":
            continue
        pts = strip_splits(strip_ties(run.points))
        segs.extend(LineString((a, b)) for a, b in zip(pts, pts[1:]))
    crossings = 0
    for i, si in enumerate(segs):
        if si.length < 1e-6:
            continue
        for sj in segs[i + 2:]:
            if sj.length < 1e-6:
                continue
            if si.intersects(sj):
                crossings += 1
    return crossings


def test_the_fold_guard_closes_what_the_raised_ceiling_reopens():
    """The 2026-09-02 coupled route, reproduced: the wide ceiling alone puts
    logo_alpha's apex back to crossing itself; with the fold guard it does
    not, and the shipped 5.0 stays at zero as it has since 2026-08-05."""
    assert _apex_crossings(machine.SATIN_MAX_WIDTH_MM, False) == 0
    reopened = _apex_crossings(machine.SATIN_WIDE_COLUMN_MAX_MM, False)
    assert reopened > 0, "the ceiling alone should reproduce the measured failure"
    assert _apex_crossings(machine.SATIN_WIDE_COLUMN_MAX_MM, True) == 0


def test_fold_caps_read_the_bend_and_leave_the_straight():
    # a quarter circle of radius 4 mm: every step turns ds / 4 radians
    R = 4.0
    n = 40
    spine = [(R * math.cos(t), R * math.sin(t)) for t in np.linspace(0, math.pi / 2, n)]
    angles = [t + math.pi / 2 for t in np.linspace(0, math.pi / 2, n)]
    caps = s6._fold_caps(spine, angles, False, frac=0.7)
    assert all(abs(c - 0.7 * R) < 0.05 for c in caps[1:-1]), caps[:5]
    straight = [(x, 0.0) for x in np.linspace(0, 20, n)]
    flat = s6._fold_caps(straight, [math.pi / 2] * n, False, frac=0.7)
    assert all(math.isinf(c) for c in flat)


def _bar_png(path: Path, w_mm: float, h_mm: float, px_per_mm: float = 10.0) -> None:
    W, H = int((w_mm + 20) * px_per_mm), int((h_mm + 20) * px_per_mm)
    img = np.full((H, W, 3), 255, np.uint8)
    x0, y0 = int(10 * px_per_mm), int(10 * px_per_mm)
    img[y0:y0 + int(h_mm * px_per_mm), x0:x0 + int(w_mm * px_per_mm)] = (20, 20, 20)
    cv2.imwrite(str(path), img)


def test_a_six_millimetre_bar_sews_satin_only_on_the_flag(tmp_path):
    """The band the policy is for: a 40 x 6 mm bar is tatami at the shipped
    cap and a split-satin column on the flag, with crosses that reach the
    bar's own width instead of stopping at 5.0."""
    art = tmp_path / "bar.png"
    _bar_png(art, 40.0, 6.0)
    kinds = {}
    crosses = {}
    for flag in (False, True):
        # `target_width_mm` is the ARTWORK's width: the bar is the artwork,
        # so 40 mm keeps it 40 x 6.0 (60 would scale it to 60 x 9.0)
        cfg = PipelineConfig(target_width_mm=40.0, wide_columns=flag)
        result, plan = digitize(art, cfg)
        bar = max(result.regions, key=lambda r: r.area_mm2)
        ks = {}
        widths = []
        for _b, run in plan.iter_runs():
            if run.shape_id != bar.shape_id:
                continue
            ks[run.kind] = ks.get(run.kind, 0) + len(run.points)
            if run.kind == "satin":
                pts = strip_splits(strip_ties(run.points))
                widths.extend(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        kinds[flag] = max(ks, key=ks.get) if ks else None
        crosses[flag] = float(np.median(widths)) if widths else 0.0
    assert kinds[False] == "fill", kinds
    assert kinds[True] == "satin", kinds
    assert crosses[True] > 5.5, f"the crosses should reach the bar's width: median {crosses[True]:.2f}"
