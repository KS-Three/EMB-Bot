"""`cfg.lettering_columns_corner_fold` (2026-10-23, built OFF): the Column
lane folds ONE satin column round an L-shaped corner the way the
professional's files do, instead of cutting the outline there and butting
two columns.

The cut reads a lone concave corner with a convex apex across it as a
junction and cuts it (a "mitre" to the apex, an "ext" along the longer
edge, an E's "slot" line); the two strokes then sew as two columns, a butt
and a travel between them. The pro's DSTs (Fremont, Drone, Proseal, MFab,
read 2026-10-23) keep one column through every such corner: the crosses
pivot on the inside corner, their outer ends walk the outline round the
apex, the next stroke carries on. He cuts only where two concave corners
face each other (a T junction, a slab serif's root).

`testdata/drone62_band_letters.json`: PRECISION's nine letters as stage 7
handed them to the lane at 62.6 mm Hat (the pro's design width), each with
its kwargs, captured from `tools.pro_pair.digitize` on 2026-10-23.
"""
import json
import math
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, Polygon

from digitizer_core import PipelineConfig, columns
from digitizer_core import outline_cut as oc

W = 1.4
#: an L: a 7 mm stem, a 5 mm foot, both W wide (y down)
L_SHAPE = Polygon([(0, 0), (W, 0), (W, 7 - W), (5, 7 - W), (5, 7), (0, 7)])
#: a C-shape: two L corners on one stem
C_SHAPE = Polygon([(0, 0), (5, 0), (5, W), (W, W), (W, 7 - W), (5, 7 - W), (5, 7), (0, 7)])
#: an E: the two outer corners are L corners, the middle arm's root a T junction
E_SHAPE = Polygon([(0, 0), (5, 0), (5, W), (W, W), (W, 3.0), (4, 3.0), (4, 3.0 + W), (W, 3.0 + W),
                   (W, 7 - W), (5, 7 - W), (5, 7), (0, 7)])
LANE = dict(fold_cuts=True, mitre_ends=True, rail_axis=True)
RUNS = dict(trim_at_mm=3.0, pull_mm=0.4, pull_floor_mm=1.5, underlay_style="none",
            square_ends=True, inside_connectors=True)
DRONE = Path(__file__).resolve().parent.parent / "testdata" / "drone62_band_letters.json"


def _cut(poly, **extra):
    return oc.letter_columns(poly, 0.4, **LANE, **extra)


def _sew(poly, **extra):
    cut = _cut(poly, **extra)
    runs, rep = columns.column_runs(cut.columns, cut.poly, "t", **RUNS)
    return cut, runs, rep


def _drone_letters():
    out = {}
    for sid, v in json.loads(DRONE.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[sid] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def test_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_corner_fold is False


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("corner_fold code reached with the flag off")
    monkeypatch.setattr(oc, "_fold_corners", boom)
    for poly in (L_SHAPE, C_SHAPE, E_SHAPE):
        _cut(poly)
    poly, kw = next(iter(_drone_letters().values()))
    columns.lettering_columns_shape(poly, "off", **kw)


def test_stage7_wires_the_flag_and_nothing_else():
    src = (Path(__file__).resolve().parent.parent / "digitizer_core" / "stage7_sequence.py").read_text(
        encoding="utf-8")
    assert '**({"corner_fold": True} if cfg.lettering_columns_corner_fold else {})' in src


# --- OFF: the defect, pinned ---------------------------------------------------------

def test_off_an_l_is_two_columns_butted_at_a_mitre():
    cut, runs, _rep = _sew(L_SHAPE)
    assert [c.kind for c in cut.columns] == ["straight", "straight"]
    assert [c[2] for c in cut.cuts] == ["mitre"]
    assert sum(1 for r in runs if r.kind == "travel") >= 1


# --- ON ---------------------------------------------------------------------------------

def _outer_rail(col, poly):
    """The folded column's outer-side station ends (the side away from the
    inside corner), in sew order."""
    ring = LineString(poly.exterior.coords)
    ends = [[a, b] for a, b in col.stations]
    # the inner slot is the one whose ends bunch on one point (the corner)
    spread = [max(math.dist(e[s], f[s]) for e, f in zip(ends, ends[1:])) for s in (0, 1)]
    inner = min(range(2), key=lambda s: sum(math.dist(e[s], f[s]) for e, f in zip(ends, ends[1:])))
    return [e[1 - inner] for e in ends], ring, spread


def test_on_an_l_sews_one_column_with_a_continuous_outer_rail_and_no_travel():
    cut, runs, rep = _sew(L_SHAPE, corner_fold=True)
    assert [c.kind for c in cut.columns] == ["folded"]
    assert cut.cuts == []
    assert not [r for r in runs if r.kind == "travel"]
    assert rep["junctions"] == 0 and rep["jumps"] == 0
    outer, ring, _spread = _outer_rail(cut.columns[0], cut.poly)
    # every outer end ON the outline, every step along it at most a pitch
    # (plus a hair): the rail never jumps, never doubles back
    assert all(ring.distance(Point(e)) < 0.06 for e in outer)
    steps = [math.dist(a, b) for a, b in zip(outer, outer[1:])]
    assert max(steps) <= 0.4 + 0.05
    # the fold pivots on the inside corner, through the whole corner
    assert oc.pivot_sweep(cut.columns[0].stations) >= 75.0
    # the apex is reached: a cross lands on it
    assert min(math.dist(e, (0.0, 7.0)) for e in outer) < 0.1


def test_on_the_legs_crosses_are_the_off_ones_so_the_sewn_width_is_unchanged():
    off, on = _cut(L_SHAPE), _cut(L_SHAPE, corner_fold=True)
    off_st = {tuple(map(lambda p: tuple(round(v, 6) for v in p), s)) for c in off.columns for s in c.stations}
    on_st = [tuple(map(lambda p: tuple(round(v, 6) for v in p), s)) for s in on.columns[0].stations]
    kept = [s for s in on_st if s in off_st]
    # all but the corner's crosses are OFF's own, and both legs keep most of theirs
    assert len(kept) >= len(on_st) - 10
    assert len(kept) >= 0.7 * sum(len(c.stations) for c in off.columns)
    off_w = sorted(math.dist(*s) for c in off.columns for s in c.stations)
    on_w = sorted(math.dist(*s) for s in on.columns[0].stations)
    assert abs(off_w[len(off_w) // 2] - on_w[len(on_w) // 2]) < 0.02


def test_on_a_c_shape_folds_both_corners_into_one_column():
    cut, runs, _rep = _sew(C_SHAPE, corner_fold=True)
    assert [c.kind for c in cut.columns] == ["folded"]
    assert not [r for r in runs if r.kind == "travel"]


def test_on_a_t_junction_is_never_folded():
    # the E's middle arm meets the stem between two concave corners: a
    # through pair, cut and butted as OFF; the outer corners fold
    cut, _runs, rep = _sew(E_SHAPE, corner_fold=True)
    assert sorted(c.kind for c in cut.columns) == ["folded", "straight"]
    assert rep["junctions"] == 1


def test_on_the_drone_e_and_c_fold_like_the_pro():
    letters = _drone_letters()
    # PRECISION's E (x -14.6..-7.5) and C (x -6.6..0.8): the pro sews each
    # as one folded column plus (the E) its middle arm
    by_x = sorted((kv for kv in letters.items() if 9.5 < kv[1][0].bounds[1] < 11.0),
                  key=lambda kv: kv[1][0].bounds[0])
    assert len(by_x) == 9
    e_poly, e_kw = by_x[2][1]
    c_poly, c_kw = by_x[3][1]
    for poly, kw, want in ((e_poly, e_kw, 2), (c_poly, c_kw, 1)):
        _off, off_rep = columns.lettering_columns_shape(poly, "e", **kw)
        _on, rep = columns.lettering_columns_shape(poly, "e", **kw, corner_fold=True)
        assert off_rep["columns"] > want
        assert rep["columns"] == want
        assert rep["columns_unsewn"] == 0
        assert rep["jumps"] <= off_rep["jumps"]         # no new jump inside the letter
