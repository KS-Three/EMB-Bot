"""Curve facets (`stage4_vectorize._densify_curves`, behind
`PipelineConfig.curve_chord_mm`, built None = OFF 2026-11-14;
`docs/curve-facets-2026-11-14.md`).

Geometry first: a 15-degree-faceted circle comes back with small turns and
every new vertex on the circle, a square keeps its four vertices, a straight
run beside an arc gains nothing, the guard refuses a bend the trace does not
have. Then the wiring: OFF is byte-identical, an upscaled source is left to
`outline_redraw_k`, a source at its own resolution gains vertices."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LinearRing, Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from digitizer_core import curve_densify as cd  # noqa: E402


def _turns(P: np.ndarray) -> np.ndarray:
    d = np.roll(P, -1, 0) - P
    a = np.arctan2(d[:, 1], d[:, 0])
    return np.degrees(np.abs((a - np.roll(a, 1) + np.pi) % (2 * np.pi) - np.pi))


def _circle(r: float, n: int, c=(0.0, 0.0)) -> np.ndarray:
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)])


def test_a_faceted_circle_gains_vertices_on_the_circle():
    # a 4 mm bowl at 22 px/mm, written as stage 4's 15-degree chords
    r = 88.0
    raw, ring = _circle(r, 2000), _circle(r, 24)
    out = cd.densify_curves(ring, raw, chord=8.8, guard=1.0)
    assert len(out) > 2 * len(ring)
    assert _turns(out).max() < 7.0 < _turns(ring).max()
    # every vertex on the circle, within the guard; the old ones kept exactly
    assert np.abs(np.hypot(out[:, 0], out[:, 1]) - r).max() < 1.0
    assert all(any(np.allclose(v, w) for w in out) for v in ring)


def test_a_square_keeps_its_four_corners():
    sq = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], float)
    raw = np.asarray(LinearRing(sq).segmentize(1.0).coords)[:-1]
    out = cd.densify_curves(sq, raw, chord=8.8, guard=1.0)
    assert out is sq


def test_a_straight_run_beside_an_arc_gains_nothing():
    """A D: half a 15-degree polygon closed by its diameter. The arc's
    edges split; the diameter and the two corners where it meets the arc
    (90 degrees) are kept, so no vertex lands on the straight run."""
    r = 88.0
    t = np.radians(np.arange(0, 181, 15.0))
    ring = np.column_stack([r * np.cos(t), r * np.sin(t)])
    raw = np.asarray(LinearRing(np.column_stack([r * np.cos(np.radians(np.arange(0, 180.01, 0.1))),
                                                 r * np.sin(np.radians(np.arange(0, 180.01, 0.1)))]))
                     .segmentize(1.0).coords)[:-1]
    out = cd.densify_curves(ring, raw, chord=8.8, guard=1.0)
    assert len(out) > len(ring)
    on_diameter = np.abs(out[:, 1]) < 1e-9
    assert on_diameter.sum() == 2          # the two corners, nothing between
    assert np.abs(out[:, 1]).min() >= 0.0 and (out[:, 1] >= -1e-9).all()


def test_the_guard_refuses_a_bend_the_trace_does_not_have():
    """The polygon turns like a circle, but the trace it came from is the
    polygon itself (a real 24-gon): every bend would leave the trace by
    more than the guard, so nothing is inserted."""
    ring = _circle(88.0, 24)
    raw = np.asarray(LinearRing(ring).segmentize(0.5).coords)[:-1]
    out = cd.densify_curves(ring, raw, chord=8.8, guard=0.2)
    assert out is ring


def test_an_inflection_keeps_its_chord():
    # a zigzag: turns alternate, so no edge bends
    zz = np.array([[0, 0], [40, 6], [80, 0], [120, 6], [120, 60], [0, 60]], float)
    raw = np.asarray(LinearRing(zz).segmentize(1.0).coords)[:-1]
    out = cd.densify_curves(zz, raw, chord=8.8, guard=1.0)
    assert out is zz


def _cfg(**kw):
    from digitizer_core import PipelineConfig
    return PipelineConfig(target_width_mm=60.0, garment_id="left_chest", max_colors=6, **kw)


def _disc_png(tmp_path, w: int, h: int) -> str:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), "white")
    dr = ImageDraw.Draw(im)
    s = w / 90.0
    dr.ellipse([4 * s, 4 * s, 44 * s, 44 * s], fill="black")
    dr.ellipse([16 * s, 16 * s, 32 * s, 32 * s], fill="white")
    dr.polygon([(52 * s, 10 * s), (86 * s, 16 * s), (84 * s, 40 * s), (54 * s, 36 * s)], fill="black")
    out = tmp_path / f"disc_{w}.png"
    im.save(out)
    return str(out)


def test_off_is_the_default_and_byte_identical(tmp_path):
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import run_stages
    assert PipelineConfig().curve_chord_mm is None
    png = _disc_png(tmp_path, 1260, 700)          # 21 px/mm at 60 mm: own resolution
    a = run_stages(png, _cfg())
    b = run_stages(png, _cfg(curve_chord_mm=0.0))
    assert [r.polygon.wkb for r in a.regions] == [r.polygon.wkb for r in b.regions]


def test_on_densifies_a_source_at_its_own_resolution_and_spares_the_quad(tmp_path):
    from digitizer_core.pipeline import run_stages
    png = _disc_png(tmp_path, 1260, 700)
    off = run_stages(png, _cfg())
    on = run_stages(png, _cfg(curve_chord_mm=0.4, curve_chord_stage4=True))
    assert len(on.regions) == len(off.regions)

    def nverts(res, pick):
        rs = [r for r in res.regions if pick(r.polygon)]
        return sum(len(r.polygon.exterior.coords) + sum(len(h.coords) for h in r.polygon.interiors)
                   for r in rs)

    ring_like = lambda p: p.centroid.x < 0            # noqa: E731  (the disc, left)
    quad = lambda p: p.centroid.x > 0                 # noqa: E731  (the quad, right)
    assert nverts(on, ring_like) > 1.5 * nverts(off, ring_like)
    # the quad's straight sides and corners are untouched
    assert nverts(on, quad) == nverts(off, quad)
    # nothing moved past the tracer's tolerance (simplify_tol_mm = 0.2)
    for a, b in zip(sorted(off.regions, key=lambda r: r.polygon.area),
                    sorted(on.regions, key=lambda r: r.polygon.area)):
        assert a.polygon.exterior.hausdorff_distance(b.polygon.exterior) <= 0.2


def test_an_upscaled_source_is_left_to_the_redraw(tmp_path):
    from digitizer_core.pipeline import run_stages
    png = _disc_png(tmp_path, 90, 50)              # 1.5 px/mm: stage 1 upscales
    off = run_stages(png, _cfg())
    on = run_stages(png, _cfg(curve_chord_mm=0.4, curve_chord_stage4=True))
    assert [r.polygon.wkb for r in on.regions] == [r.polygon.wkb for r in off.regions]


def test_turn_helper_matches_a_regular_polygon():
    assert math.isclose(float(_turns(_circle(10.0, 24)).max()), 15.0, abs_tol=1e-6)


def _letter_c() -> Polygon:
    """A 'C' as a fine trace: an 8 mm ring 1.6 mm thick with a 90-degree
    mouth, so the lane cuts it, and both rails are clean arcs."""
    t = np.radians(np.linspace(45.0, 315.0, 540))
    outer = np.column_stack([4.0 * np.cos(t), 4.0 * np.sin(t)])
    inner = np.column_stack([2.4 * np.cos(t), 2.4 * np.sin(t)])[::-1]
    return Polygon(np.vstack([outer, inner]))


def _outer_rail_turns(cut) -> np.ndarray:
    pts = [p for c in cut.columns for st in c.stations for p in st if math.hypot(*p) > 3.2]
    P = np.array(sorted(pts, key=lambda p: math.atan2(p[1], p[0]) % (2 * math.pi)))
    d = np.diff(P, axis=0)
    keep = np.hypot(d[:, 0], d[:, 1]) > 0.05
    a = np.arctan2(d[keep, 1], d[keep, 0])
    return np.degrees(np.abs((np.diff(a) + np.pi) % (2 * np.pi) - np.pi))


def test_column_lane_rails_follow_the_curve_and_keep_the_cuts():
    """The lane simplifies the letter at max(0.12 mm, W/16) before it cuts:
    OFF, the C's outer rail is 2 mm chords and its satin ends turn in jumps.
    ON (`curve_chord_scope`), the same cuts, the same number of columns, and
    the rail's ends turn evenly, each within the guard of the trace."""
    from digitizer_core import outline_cut as oc
    letter = _letter_c()
    off = oc.letter_columns(letter, 0.4)
    with oc.curve_chord_scope(0.4):
        on = oc.letter_columns(letter, 0.4)
    assert [c[:2] for c in on.cuts] == [c[:2] for c in off.cuts]
    assert len(on.columns) == len(off.columns) >= 1
    t_off, t_on = _outer_rail_turns(off), _outer_rail_turns(on)
    assert t_on.max() < t_off.max()
    ends = np.array([p for c in on.columns for st in c.stations for p in st if math.hypot(*p) > 3.2])
    # the satin's ends sit inside the rail inset, near the true circle
    assert np.abs(np.hypot(ends[:, 0], ends[:, 1]) - 4.0).max() < 0.25


def test_column_lane_off_without_the_scope():
    from digitizer_core import outline_cut as oc
    assert oc._CURVE_CHORD.get() is None
    with oc.curve_chord_scope(None):
        assert oc._CURVE_CHORD.get() is None
    with oc.curve_chord_scope(0.4):
        assert oc._CURVE_CHORD.get() == 0.4
    assert oc._CURVE_CHORD.get() is None
