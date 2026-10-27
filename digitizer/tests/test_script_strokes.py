"""A script word sews as the pen wrote it (`cfg.script_strokes`, built OFF
2026-10-26).

The fixtures: LOOPS, a joined cursive line (a prolate cycloid, three loops,
0.9 mm pen) -- what the door must take; a FRAME (a ring round other art), a
BAR and a SWOOSH -- what it must refuse. CROSS, two strokes crossing: the pen
goes THROUGH a crossing, one stroke each. KNEE, a stroke turning 120 deg: a
cusp, two strokes. OFF is byte-identical (md5 pinned on main's engine,
27636c98).
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from shapely.geometry import LineString, Point, box

from digitizer_core import PipelineConfig, stitches
from digitizer_core import script_strokes as SS
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.machine import satin_ceiling_mm
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_hairline import InkSource
from digitizer_core.stage7_sequence import _sews_satin, sequence


def _loops(r=1.2, d=2.4, turns=3, w=0.9):
    n = int(turns * 2 * math.pi / 0.05) + 1
    return LineString([(r * t - d * math.sin(t), d * math.cos(t))
                       for t in (i * 0.05 for i in range(n))]).buffer(w / 2)


LOOPS = _loops()
FRAME = box(0, 0, 30, 12).difference(box(1.2, 1.2, 28.8, 10.8))
BAR = box(0, 0, 30, 3)
SWOOSH = LineString([(x * 0.5, 3 * math.sin(x * 0.5 / 6)) for x in range(80)]).buffer(0.4)
CROSS = LineString([(0, 0), (12, 12)]).buffer(0.7).union(LineString([(0, 12), (12, 0)]).buffer(0.7))
KNEE = LineString([(0, 0), (8, 0), (4, 6.9)]).buffer(0.6, join_style=2)

#: the OFF md5s of `_runs(...)`, captured on main's engine (27636c98)
OFF_MD5 = {"loops": "ad8bbbd5365e853c43fd8334b6c93028", "swoosh": "f9bde1428c3ad733da644eff8083ee3d"}


def _region(poly, **meta) -> Region:
    return Region(shape_id="Sword", polygon=poly, thread_index=0, thread_number="0020",
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def _runs(poly, **cfg_kw):
    cfg = PipelineConfig(**cfg_kw)
    reg = _region(poly)
    blocks, _ = sequence([PlannedRegion(region=reg, polygon=poly, sew_index=0)],
                         fabric_for_garment("hat_front"), cfg)
    return [r for b in blocks for r in b.runs if r.shape_id == "Sword"]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((str(r.kind), r.jump, r.trim,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


# ------------------------------------------------------------------- default
def test_default_off():
    assert PipelineConfig().script_strokes is False


def test_off_is_byte_identical():
    assert _md5(_runs(LOOPS)) == OFF_MD5["loops"]
    assert _md5(_runs(SWOOSH)) == OFF_MD5["swoosh"]


# ------------------------------------------------------------------ the door
def test_the_door_takes_a_joined_word_and_nothing_else():
    assert SS.script_reading(LOOPS).is_script
    for refused in (FRAME, BAR, SWOOSH):
        assert not SS.script_reading(refused).is_script
    on = PipelineConfig(script_strokes=True)
    assert SS.script_word(_region(LOOPS), on)
    assert not SS.script_word(_region(LOOPS), PipelineConfig())          # flag off: never read
    assert not SS.script_word(_region(LOOPS, tier="fill"), on)           # a pinned tier stands
    assert not SS.script_word(_region(LOOPS, text_candidate=True), on)   # text is the Column lane's


def test_prediction_agrees_with_the_emitter():
    """`_sews_satin` (borders-last, seam ownership) says satin where the word sews it."""
    cfg = PipelineConfig(script_strokes=True)
    assert _sews_satin(_region(LOOPS), cfg, satin_ceiling_mm(cfg), "flat")
    kinds = {str(r.kind) for r in _runs(LOOPS, script_strokes=True) if r.points}
    assert "satin" in kinds and "fill" not in kinds


# ------------------------------------------------------------ the pen strokes
def test_the_pen_goes_through_a_crossing():
    strokes, _half = SS.pen_strokes(SS.polygon_grid(CROSS))
    assert len(strokes) == 2
    for s in strokes:
        (x0, y0), (x1, y1) = s.spine[0], s.spine[-1]
        assert math.dist((x0, y0), (x1, y1)) > 12.0       # each runs corner to corner


def test_a_cusp_is_two_strokes():
    strokes, _half = SS.pen_strokes(SS.polygon_grid(KNEE))
    assert len(strokes) == 2


def test_crosses_are_square_to_the_stroke_and_reach_its_drawn_width():
    stem = LineString([(0, 0), (6, -16)]).buffer(1.0, cap_style=2)     # a 2 mm italic stem
    cols, _strokes, grid = SS.script_columns(stem, 0.4)
    assert grid.source == "polygon" and len(cols) == 1
    u = (6 / math.hypot(6, 16), -16 / math.hypot(6, 16))
    devs, widths = [], []
    for a, b in cols[0].stations[5:-5]:
        L = math.dist(a, b)
        dot = abs((b[0] - a[0]) * u[0] + (b[1] - a[1]) * u[1]) / L
        devs.append(math.degrees(math.asin(min(1.0, dot))))      # 0 = square to the stem
        widths.append(L)
    assert max(devs) < 5.0                      # square to the stroke, not to the text line
    assert abs(float(np.median(widths)) - 2.0) < 0.1


def test_a_word_sews_one_column_per_stroke_with_no_cut_inside():
    runs = _runs(LOOPS, script_strokes=True)
    satin = [r for r in runs if r.kind == stitches.SATIN and r.points]
    assert 1 <= len(satin) <= 6
    # the first run's jump is the needle arriving; every move after it,
    # inside the word, is sewn under thread
    assert not any(r.jump or r.trim for r in runs[1:])


# ---------------------------------------------------------------------- ink
def _ink(poly, holes_open, px_per_mm=8.0):
    """An `InkSource` that draws `poly` red on yellow at `px_per_mm`, with
    the polygons in `holes_open` drawn yellow again: counters the TRACE
    closed but the artwork has."""
    import cv2
    x0, y0, x1, y1 = poly.bounds
    W, H = int((x1 - x0 + 6) * px_per_mm), int((y1 - y0 + 6) * px_per_mm)
    rgb = np.zeros((H, W, 3), np.uint8)
    rgb[:] = (230, 240, 90)
    origin = (W / 2.0 - (x0 + x1) / 2 * px_per_mm, H / 2.0 - (y0 + y1) / 2 * px_per_mm)

    def px(c):
        return np.array([[x * px_per_mm + origin[0], y * px_per_mm + origin[1]] for x, y in c], np.int32)

    cv2.fillPoly(rgb, [px(poly.exterior.coords)], (230, 30, 40))
    for h in holes_open:
        cv2.fillPoly(rgb, [px(h.exterior.coords)], (230, 240, 90))
    return InkSource(rgb=rgb, alpha=None, bg=None, upscale=(1.0, 1.0),
                     px_per_mm=px_per_mm, origin_px=origin)


def test_a_counter_the_trace_closed_is_not_fanned_across_but_patched_under():
    # an "o" whose 1.2 mm counter the trace filled: the polygon is a disc
    ring = Point(0, 0).buffer(2.4)
    counter = Point(0, 0).buffer(0.9)
    word = ring.union(box(2.0, -0.5, 14.0, 0.5))           # with a tail, so it is one shape
    cols, strokes, grid = SS.script_columns(word, 0.4, _ink(word, [counter]))
    assert grid.source == "ink"
    loop = max(cols, key=lambda c: sum(1 for a, b in c.stations
                                      if Point(a).distance(Point(0, 0)) < 2.6))
    inner = [min(Point(a).distance(Point(0, 0)), Point(b).distance(Point(0, 0)))
             for a, b in loop.stations if Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2).distance(Point(0, 0)) < 2.2]
    assert inner and float(np.median(inner)) > 0.6      # stops at the drawn counter, no fan to the centre
    rest = SS.uncovered(word, cols)
    assert any(r.distance(Point(0, 0)) < 0.5 for r in rest)    # the closed counter is patched
    runs, report = SS.script_strokes_shape(word, "Sword", trim_at_mm=3.0, spacing_mm=0.4,
                                           pull_mm=0.4, ink=_ink(word, [counter]))
    assert report["script_patches"] >= 1 and report["script_path_ink"] == 1
    satin = [r for r in runs if r.kind == stitches.SATIN]

    def centre(r):
        return Point(float(np.mean([p[0] for p in r.points])), float(np.mean([p[1] for p in r.points])))
    # the closed counter is SEWN (a patch), not left bare where the ground is knocked out
    assert any(centre(r).distance(Point(0, 0)) < 0.6 for r in satin)
