"""`cfg.fill_turn_slant` (built OFF 2026-10-21): fill rows turn on a slant.

The settings audit (`docs/settings-vs-pro-2026-10-21.md` row 24) found our
fill rows step straight across into the next row -- one row spacing, 0.10-
0.22 mm at the 0.15 row -- where the pro lands the next row's first
penetration ~0.7 mm along it. True pulls in the inner of the two boundary
points each turn joins (`stage6_fill._slant_turns`) until the turn runs
`machine.FILL_TURN_ALONG_MM` along the row.

Fixtures are shapely polygons so a traced raster's platform noise cannot
move them.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box

from digitizer_core import PipelineConfig, machine, stitches
import digitizer_core.stage6_fill as sf
from digitizer_core.stage6_fill import _slant_turns, clear_fill_reorder_memo, stitch_shape

ROW, STITCH = machine.FILL_ROW_MM, machine.FILL_STITCH_MM
_BOX = box(0, 0, 20, 10)
_DISC = Point(0, 0).buffer(8, 128)
_HOLED = Polygon([(0, 0), (24, 0), (24, 14), (0, 14)],
                 [[(8, 4), (16, 4), (16, 10), (8, 10)]])


def _sew(poly, on, angle=0.0, technique="tatami", **kw):
    clear_fill_reorder_memo()
    runs, _ = stitch_shape(poly, "S1", angle_deg=angle, row_mm=ROW, stitch_mm=STITCH,
                           underlay_style="none", trim_at_mm=3.0, technique=technique,
                           slant_turns=on, **kw)
    return runs


def _fill_steps(runs):
    out = []
    for r in runs:
        if r.kind == stitches.FILL and len(r.points) > 1:
            p = np.array(r.points)
            d = np.hypot(*np.diff(p, axis=0).T)
            out.extend(d[d > 1e-9].tolist())
    return np.array(out)


def _digest(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(f"{r.kind}|{r.jump}|{r.trim}|".encode())
        for x, y in r.points:
            h.update(f"{x:.9f},{y:.9f};".encode())
    return h.hexdigest()


def test_default_is_off_and_off_is_the_old_call():
    assert PipelineConfig().fill_turn_slant is False
    for poly in (_BOX, _DISC, _HOLED):
        clear_fill_reorder_memo()
        old, _ = stitch_shape(poly, "S1", angle_deg=30.0, row_mm=ROW, stitch_mm=STITCH,
                              underlay_style="edge_run", trim_at_mm=3.0,
                              under_cover=True, cut_bridges=True)
        clear_fill_reorder_memo()
        new, _ = stitch_shape(poly, "S1", angle_deg=30.0, row_mm=ROW, stitch_mm=STITCH,
                              underlay_style="edge_run", trim_at_mm=3.0,
                              under_cover=True, cut_bridges=True, slant_turns=False)
        assert _digest(old) == _digest(new)


def test_off_steps_straight_across_on_a_square_edge():
    steps = _fill_steps(_sew(_BOX, False))
    # Every turn on a box's square ends is one row spacing.
    assert (np.abs(steps - ROW) < 1e-6).sum() >= 60


def test_on_no_fill_stitch_under_the_tiny_floor_on_a_box_and_a_disc():
    for poly in (_BOX, _DISC):
        off, on = _fill_steps(_sew(poly, False)), _fill_steps(_sew(poly, True))
        assert (off < machine.TINY_STITCH_MM).sum() > 50
        assert (on < machine.TINY_STITCH_MM).sum() == 0


def test_on_the_turn_lands_its_along_offset():
    """On the box's square ends every turn is (FILL_TURN_ALONG_MM along,
    ROW across): the pro's turn length, p50 0.71-0.82 mm."""
    steps = _fill_steps(_sew(_BOX, True))
    want = math.hypot(machine.FILL_TURN_ALONG_MM, ROW)
    assert (np.abs(steps - want) < 1e-6).sum() >= 60
    assert 0.7 <= want <= 0.85


def test_on_keeps_the_row_grid():
    """Row spacing unchanged: the same set of row ys, at 0 and 30 degrees."""
    for angle in (0.0, 30.0):
        def rows(runs):
            ys = set()
            for r in runs:
                if r.kind != stitches.FILL:
                    continue
                rp = affinity.rotate(LineString(r.points), -angle, origin=(0, 0))
                ys.update(round(y, 6) for _x, y in rp.coords)
            return ys
        assert rows(_sew(_BOX, False, angle)) == rows(_sew(_BOX, True, angle))


def test_on_every_edge_takes_a_penetration_every_second_row():
    """On a box's square ends each turn keeps one of its two points on the
    edge, so each edge is penetrated every second row."""
    pts = [q for r in _sew(_BOX, True) if r.kind == stitches.FILL for q in r.points]
    for x in (0.0, 20.0):
        ys = sorted({round(q[1], 6) for q in pts if abs(q[0] - x) < 1e-6})
        gaps = np.diff(ys)
        assert len(ys) > 25
        assert np.median(gaps) == pytest.approx(2 * ROW)
        # The column's last turn pulls the row above instead: one gap of three.
        assert gaps.max() <= 3 * ROW + 1e-6


def _parallelogram(deg, h=2.5, w=6.0):
    t = math.tan(math.radians(deg))
    return Polygon([(0, 0), (w, 0), (w + h / t, h), (h / t, h)])


def _bare_mm2(poly, on):
    from shapely.ops import unary_union
    lines = [LineString(r.points) for r in _sew(poly, on)
             if r.kind == stitches.FILL and len(r.points) > 1]
    return poly.difference(unary_union([ln.buffer(0.2) for ln in lines])).area


@pytest.mark.parametrize("deg", [20, 45, 75])
def test_on_sloped_edges_keep_their_line(deg):
    """The first build pulled every ENTRY in, which on a widening edge bared
    the outer corner and drew a staircase (rendered 2026-10-21). Pulling the
    inner point instead keeps the bare area under a 0.4 mm thread within
    0.05 mm2 of OFF on both edges of a parallelogram."""
    poly = _parallelogram(deg)
    assert _bare_mm2(poly, True) <= _bare_mm2(poly, False) + 0.05
    steps = _fill_steps(_sew(poly, True))
    assert (steps < machine.TINY_STITCH_MM).sum() == 0


def test_on_coverage_of_the_shape_is_unchanged():
    """The union of thread (0.4 mm) covers the box the same within 0.5%."""
    def cover(runs):
        lines = [LineString(r.points) for r in runs
                 if r.kind == stitches.FILL and len(r.points) > 1]
        from shapely.ops import unary_union
        return unary_union([ln.buffer(0.2) for ln in lines]).intersection(_BOX).area / _BOX.area
    assert abs(cover(_sew(_BOX, True)) - cover(_sew(_BOX, False))) < 0.005


def test_on_a_narrow_sloped_strip_falls_back_to_the_other_end():
    """Rows ~2 mm long cannot lose 0.7 mm at both ends. When the preferred
    row cannot afford its pull, the turn's other end is pulled instead; the
    widening-only rule without that fallback left 305 more sub-0.5 mm
    stitches on Fremont (2026-10-21)."""
    steps = _fill_steps(_sew(_parallelogram(45, h=4.0, w=2.0), True))
    assert (steps < machine.TINY_STITCH_MM).sum() == 0


def test_slant_turns_rules():
    a = machine.FILL_TURN_ALONG_MM
    sq = [(0, 0.0, 0.0, 10.0), (1, ROW, 0.0, 10.0), (2, 2 * ROW, 0.0, 10.0),
          (3, 3 * ROW, 0.0, 10.0)]
    # Square ends: row 1's entry (right) and row 2's entry (left) move in;
    # the last turn pulls row 2's exit instead, so row 3 keeps its corner.
    got = _slant_turns(sq)
    assert got[0] == (0.0, 10.0)
    assert got[1] == (0.0, 10.0 - a)
    assert got[2] == (a, 10.0 - a)
    assert got[3] == (0.0, 10.0)
    # Narrowing edge: the next row's entry, by the rest of the offset.
    got = _slant_turns([(0, 0.0, 0.0, 10.0), (1, ROW, 0.0, 9.7), (2, 2 * ROW, 0.0, 9.4)])
    assert math.isclose(got[1][1], 9.7 - (a - 0.3))
    # Widening edge: the previous row's exit, back along it.
    got = _slant_turns([(0, 0.0, 0.0, 9.7), (1, ROW, 0.0, 10.0), (2, 2 * ROW, 0.0, 10.0)])
    assert math.isclose(got[0][1], 9.7 - (a - 0.3)) and got[1][1] == 10.0
    # Already that far along the row: untouched.
    assert _slant_turns([(0, 0.0, 0.0, 10.0), (1, ROW, 0.0, 9.0)]) == [(0.0, 10.0), (0.0, 9.0)]
    # A row too short to keep MIN_STITCH_MM after the pull: untouched.
    assert _slant_turns([(0, 0.0, 0.0, 1.5), (1, ROW, 0.0, 1.5), (2, 2 * ROW, 0.0, 1.5)]) ==         [(0.0, 1.5)] * 3


def test_on_reaches_the_two_pass_fills_and_the_row_techniques():
    for kw in ({"technique": "crosshatch"}, {"technique": "brick"},
               {"technique": "wave"}, {"density_boost": True}):
        tech = kw.pop("technique", "tatami")
        off = _fill_steps(_sew(_BOX, False, technique=tech, **kw))
        on = _fill_steps(_sew(_BOX, True, technique=tech, **kw))
        assert (on < machine.TINY_STITCH_MM).sum() < (off < machine.TINY_STITCH_MM).sum()


def test_underlay_is_never_slanted():
    clear_fill_reorder_memo()
    a, _ = stitch_shape(_BOX, "S1", angle_deg=0.0, row_mm=ROW, stitch_mm=STITCH,
                        underlay_style="cross_tatami", trim_at_mm=3.0, slant_turns=False)
    clear_fill_reorder_memo()
    b, _ = stitch_shape(_BOX, "S1", angle_deg=0.0, row_mm=ROW, stitch_mm=STITCH,
                        underlay_style="cross_tatami", trim_at_mm=3.0, slant_turns=True)
    ua = [r.points for r in a if r.kind == stitches.UNDERLAY]
    ub = [r.points for r in b if r.kind == stitches.UNDERLAY]
    assert ua and ua == ub


def test_the_config_reaches_every_fill_call_site():
    """Same reach as `fill_order_sewn_paths`: stage 7's six tatami calls and
    the blend tier's two."""
    from pathlib import Path
    root = Path(sf.__file__).parent
    s7 = (root / "stage7_sequence.py").read_text(encoding="utf-8")
    sb = (root / "stage6_blend.py").read_text(encoding="utf-8")
    assert s7.count("slant_turns=cfg.fill_turn_slant") == \
        s7.count("sewn_paths_only=cfg.fill_order_sewn_paths") == 6
    assert sb.count("slant_turns=cfg.fill_turn_slant") == \
        sb.count("sewn_paths_only=cfg.fill_order_sewn_paths") == 2
