"""`cfg.satin_rail_comp` — pull compensation on the rails, not the polygon.
Built OFF 2026-09-09 (quality review 2026-09-08 item 6); DEFAULT ON since
2026-09-28, Kent's flip on the labelled sitting (docs/kent-review-2026-09-28.md).
OFF is the pre-flip path and is passed explicitly wherever a test needs it.

Stage 5 grows every shape by the fabric's pull with a round join and the
satin tier skeletonises the grown polygon: arcs on every corner, slots
2 x pull narrower, a skeleton that welds across them. ON, a satin-tier shape
keeps its artwork polygon in stage 5 and `_rail_points` moves each rail
outward by the same pull, held back where a counter would close under
`min_detail_mm`. The AMOUNT never changes (gate 1); where it lands does.

What these tests guarantee: ON is the shipped path and OFF stays reachable;
ON sews a satin shape on its artwork with rails one pull outside it and caps
not lengthened; a counter is held open; fills and widened lettering are
untouched; and the price the flip was measured to carry on the lettering
fixture is pinned as a ceiling, so it can only get cheaper.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage6_satin as s6
from digitizer_core import stage7_sequence as s7
from digitizer_core.pipeline import digitize, fabric_for
from digitizer_core.stage5_overlap import widened_lettering
from digitizer_core.stitches import strip_ties
from tests.conftest import TESTDATA

PULL = fabric_for(PipelineConfig(garment_id="left_chest")).pull_comp_mm


def _png(path: Path, ink: np.ndarray, px_per_mm: float = 10.0) -> None:
    cv2.imwrite(str(path), ink)


def _bar_png(path: Path, w_mm: float, h_mm: float, px_per_mm: float = 10.0) -> None:
    W, H = int((w_mm + 20) * px_per_mm), int((h_mm + 20) * px_per_mm)
    img = np.full((H, W, 3), 255, np.uint8)
    x0, y0 = int(10 * px_per_mm), int(10 * px_per_mm)
    img[y0:y0 + int(h_mm * px_per_mm), x0:x0 + int(w_mm * px_per_mm)] = (20, 20, 20)
    _png(path, img)


def _ring_png(path: Path, outer_mm: float, hole_mm: float, px_per_mm: float = 10.0) -> None:
    W = H = int((outer_mm + 20) * px_per_mm)
    img = np.full((H, W, 3), 255, np.uint8)
    o0 = int(10 * px_per_mm)
    img[o0:o0 + int(outer_mm * px_per_mm), o0:o0 + int(outer_mm * px_per_mm)] = (20, 20, 20)
    h0 = o0 + int((outer_mm - hole_mm) / 2 * px_per_mm)
    img[h0:h0 + int(hole_mm * px_per_mm), h0:h0 + int(hole_mm * px_per_mm)] = (255, 255, 255)
    _png(path, img)


def _sewn(path: Path, **kw):
    """-> (result, plan, {shape_id: the polygon satin_shape received})."""
    seen: dict = {}
    real = s6.satin_shape

    def spy(poly, shape_id, **kwargs):
        seen[shape_id] = poly
        return real(poly, shape_id, **kwargs)

    s7.satin_shape = spy
    try:
        result, plan = digitize(path, PipelineConfig(garment_id="left_chest", **kw))
    finally:
        s7.satin_shape = real
    return result, plan, seen


def _satin_points(plan, shape_id: str) -> list:
    """The shape's satin penetrations, lock stitches stripped — a tie is 3 mm
    of thread bounced on one point and would read as an overshoot."""
    return [p for _b, r in plan.iter_runs() if r.kind == "satin" and r.shape_id == shape_id
            for p in strip_ties(r.points)]


def _outside(points, poly: Polygon) -> float:
    """How far the farthest point sits outside the polygon, mm — past its
    outer edge or into one of its counters."""
    return max((poly.boundary.distance(Point(p)) if not poly.covers(Point(p)) else 0.0)
               for p in points)


def test_the_flag_is_on_by_default_since_2026_09_28():
    # Kent flipped it on the labelled sitting (docs/kent-review-2026-09-28.md):
    # after-better on five logos, before-better on none. OFF is the old path.
    assert PipelineConfig().satin_rail_comp is True
    assert PipelineConfig(satin_rail_comp=False).satin_rail_comp is False
    # The amount is gate 1's; where it lands was Kent's on the render.
    assert PULL > 0, "the polo preset stopped carrying a pull, so nothing here is measurable"


def test_a_bar_is_sewn_on_its_artwork_with_rails_one_pull_outside_and_caps_not_lengthened(tmp_path):
    """OFF the bar is sewn on a polygon grown all round — the rails one pull
    outside AND the caps one pull past the artwork's ends. ON the polygon
    is the artwork: the rails still sit one pull outside (the widening the
    fabric's pull earns is untouched) and the caps stop at the artwork."""
    png = tmp_path / "bar.png"
    _bar_png(png, 24.0, 3.0)
    off_r, off_p, off_seen = _sewn(png, target_width_mm=24.0, satin_rail_comp=False)
    on_r, on_p, on_seen = _sewn(png, target_width_mm=24.0, satin_rail_comp=True)
    sid = next(iter(on_seen))
    art = next(r.polygon for r in on_r.regions if r.shape_id == sid)
    assert not off_seen[sid].equals(art), "OFF must still sew the grown polygon"
    assert on_seen[sid].equals(art), "ON must sew the artwork polygon"
    off_pts, on_pts = _satin_points(off_p, sid), _satin_points(on_p, sid)
    assert len(on_pts) > 40 and len(off_pts) > 40
    # rails: one pull outside the artwork, both ways
    assert abs(_outside(on_pts, art) - PULL) < 0.08, _outside(on_pts, art)
    assert abs(_outside(off_pts, art) - PULL) < 0.08, _outside(off_pts, art)
    # caps: OFF reaches a pull past the artwork's ends, ON stops at them
    x0, _y0, x1, _y1 = art.bounds
    off_reach = max(max(p[0] for p in off_pts) - x1, x0 - min(p[0] for p in off_pts))
    on_reach = max(max(p[0] for p in on_pts) - x1, x0 - min(p[0] for p in on_pts))
    assert off_reach > 0.6 * PULL, off_reach
    assert on_reach < 0.12, on_reach


def test_the_hole_guard_keeps_a_small_counter_at_the_detail_floor(tmp_path):
    """A 9 mm ring (3.5 mm wide) with a 2.0 mm counter on a 1.5 mm floor: the
    naive push would leave the counter 1.4 mm across in the file. Held, each
    rail takes a quarter millimetre and the counter keeps its 1.5; a wide
    counter takes the full pull."""
    png = tmp_path / "ring.png"
    _ring_png(png, 9.0, 2.0)
    r, p, seen = _sewn(png, target_width_mm=9.0, satin_rail_comp=True)
    sid = next(iter(seen))
    art = next(rg.polygon for rg in r.regions if rg.shape_id == sid)
    assert seen[sid].equals(art) and len(art.interiors) == 1, "the ring must sew as satin on its artwork"
    hole = Polygon(art.interiors[0])
    cx, cy = hole.centroid.x, hole.centroid.y
    pts = _satin_points(p, sid)
    inner = min(max(abs(q[0] - cx), abs(q[1] - cy)) for q in pts)
    # the counter's half-width (1.0) less the held push (0.25) = 0.75 from centre
    floor_half = PipelineConfig().min_detail_mm / 2.0
    assert inner >= floor_half - 0.06, f"a rail sits {inner:.2f} mm from the counter's centre"
    # and the outside rails carry the full pull
    outer = max(art.exterior.distance(Point(q)) for q in pts if not art.buffer(1e-6).covers(Point(q))
                and hole.exterior.distance(Point(q)) > 0.5)
    assert abs(outer - PULL) < 0.08, outer

    wide = tmp_path / "wide_ring.png"
    _ring_png(wide, 14.0, 8.0)
    r2, p2, seen2 = _sewn(wide, target_width_mm=14.0, satin_rail_comp=True)
    sid2 = next(iter(seen2))
    art2 = next(rg.polygon for rg in r2.regions if rg.shape_id == sid2)
    hole2 = Polygon(art2.interiors[0])
    pts2 = _satin_points(p2, sid2)
    deepest = max(hole2.exterior.distance(Point(q)) for q in pts2 if hole2.covers(Point(q)))
    assert abs(deepest - PULL) < 0.08, f"a wide counter should take the whole pull, took {deepest:.2f}"


def test_the_end_cutback_owes_only_the_push_on_rails(tmp_path):
    """Under directional comp the cutback is `pull + PUSH` because the buffer
    lengthened the column; on the artwork nothing did, so it is PUSH alone --
    and the two land the column's END STATION in the same place, `PUSH` short
    of the artwork cap. Measured by the last cross's midpoint: the crosses
    at a bar's ends lean a few degrees on the skeleton both paths share
    (the skeleton is the grown polygon's under the flag too), so the
    outermost NEEDLE point sits nearer the cap than the station does --
    0.16 mm on this bar, the same OFF and ON -- and is not what the cutback
    positions. The flag moves the column's width, never its length."""
    png = tmp_path / "bar.png"
    _bar_png(png, 24.0, 3.0)
    _r, off_p, off_seen = _sewn(png, target_width_mm=24.0, directional_comp=True, satin_rail_comp=False)
    r, on_p, on_seen = _sewn(png, target_width_mm=24.0, directional_comp=True, satin_rail_comp=True)
    sid = next(iter(on_seen))
    assert set(off_seen) == set(on_seen)
    art = next(rg.polygon for rg in r.regions if rg.shape_id == sid)
    x0, _y0, x1, _y1 = art.bounds

    def short(plan):
        pts = _satin_points(plan, sid)
        mids = [(pts[i][0] + pts[i + 1][0]) / 2.0 for i in range(0, len(pts) - 1, 2)]
        return min(x1 - max(mids), min(mids) - x0)

    assert abs(short(on_p) - machine.PUSH_CUTBACK_MM) < 0.1, short(on_p)
    assert abs(short(on_p) - short(off_p)) < 0.05, (short(off_p), short(on_p))


def test_on_the_wordmark_every_satin_shape_sews_on_its_artwork():
    """The drone wordmark: OFF every satin shape sews on a polygon grown all
    round its artwork; ON the artwork is contained and what lies outside it
    is only the underlap tongue under a later colour (and the clip of an
    earlier one) -- less than half of OFF's growth band on every shape."""
    art = TESTDATA / "photo" / "drone_render.png"
    off_r, _off_p, off_seen = _sewn(art, satin_rail_comp=False)
    on_r, _on_p, on_seen = _sewn(art, satin_rail_comp=True)
    art_by_id = {rg.shape_id: rg.polygon for rg in on_r.regions}
    assert len(on_seen) >= 30 and set(on_seen) == set(off_seen)
    total_off = total_on = 0.0
    for s in on_seen:
        a = art_by_id[s]
        extra_off = off_seen[s].difference(a).area
        extra_on = on_seen[s].difference(a).area
        # never more outside the artwork than the grown polygon had (a
        # letter on an earlier colour is clipped back to it either way)
        assert extra_on <= extra_off + 1e-6, f"{s}: ON carries {extra_on:.2f} mm2 outside its artwork, OFF {extra_off:.2f}"
        total_off += extra_off
        total_on += extra_on
    assert total_on < 0.5 * total_off, (total_on, total_off)


def test_widened_lettering_keeps_its_compensated_column(tmp_path):
    """The column floor's population is classified and sewn on the polygon
    stage 5 grows for it (2026-09-09); rail comp must leave that alone. The
    fixture is the widened-lettering tests' own thin bars."""
    from unittest.mock import patch
    from tests.test_widened_lettering_tier import _thin_bars, FLOOR_MM, _OCR_GATE_PATH
    art = tmp_path / "bars.png"
    _thin_bars(art)
    with patch(_OCR_GATE_PATH, return_value=False):
        r, _p, seen = _sewn(art, target_width_mm=50.0, lettering_min_column_mm=FLOOR_MM,
                            satin_rail_comp=True)
    widened = [rg for rg in r.regions if widened_lettering(rg) and rg.shape_id in seen]
    assert len(widened) >= 5, "the fixture stopped widening any glyph"
    for rg in widened:
        assert not seen[rg.shape_id].equals(rg.polygon), \
            f"{rg.shape_id}: a widened glyph lost its column to rail comp"
        assert seen[rg.shape_id].area > rg.polygon.area * 1.3


def test_the_flip_costs_trims_on_the_lettering_fixture_and_says_so():
    """The one cost the labelled sitting could not show: trims. MARINE at
    80.2 mm (the lettering route's own fixture, `tests/test_stroke_order_euler`)
    sews 9 trims and 1,784 stitches with the pull in the polygon and 22 trims
    and 2,058 stitches with it on the rails (2026-09-29, the day of the flip;
    letter-to-shape hops 3 -> 6, underlay->satin 3 -> 5, satin->underlay
    1 -> 7). The 2026-09-19 levers priced on the grown polygon do not buy it
    back: both levers ON reads 17 trims on the rails against 8 off them.

    Where they come from, by `tools/refused_walks.py`: 11 of the 22 were
    walks refused because the stroke's first run started a half-width off
    the travel web (`target_unsnapped`); the seam fix the same day
    (`test_under_rail_comp_a_strokes_first_run_starts_on_the_travel_web`)
    takes those to 2, but eight of them become cursor-side refusals -- the
    previous column's end sits 3.5 to 7 mm from any node, past `trim_at` --
    so the fixture reads 21 trims at 2,061 stitches. The cursor side is
    `satin_walk_cursor_reach_mm`'s question, parked for cloth (Kent,
    2026-09-20); the rest are letter-to-letter hops and two split webs.

    The junction tuck's floor and reach-in went to sewn terms the same day
    (DOCTRINE 2026-09-29, the C's bowl): a stacked arm reaches its node as
    it does on the grown polygon, which is more thread -- the fixture
    2,061 -> 2,093 stitches (1.155 -> 1.173 of OFF) for bare artwork
    7.38 -> 7.03% at the same 21 trims -- so the stitch ceiling is 1.18.

    **`satin_tip_caps` (ON since 2026-09-29) now rides in BOTH arms, and the
    ceilings moved for that reason alone.** Rail comp's OWN price on this
    fixture did not change: with tip caps off on both sides it still reads
    9 -> 21 trims and 1,784 -> 2,093 stitches, **1.173 of OFF** against the
    1.18 that was pinned here before. What moved is the baseline -- tip caps
    costs the OFF arm 9 -> 11 trims and 1,784 -> 1,928 stitches, and the ON
    arm 21 -> 22 and 2,093 -> 2,354 -- so the pair reads 11 -> 22 at 1.221.
    The 09-19 engine is pinned below as its own arm so that attribution
    cannot rot: if THAT number moves, rail comp's price really has changed.

    Pinned as CEILINGS, the way the underlay lever's own cost is: a cheaper
    build lowers them and this test stays green; a dearer one fails it. The
    direction is recorded here, not asserted -- the day the rails sew the
    word in the typed word's three trims, nothing here should be in the way.
    """
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from tests.test_stroke_order_euler import FIXTURE

    def sewn(**kw):
        c = PipelineConfig(target_width_mm=80.2, garment_id="left_chest", max_colors=6, **kw)
        gen = build_generation(str(FIXTURE), c)
        return plan_stitches(finish_generation(gen.fork(), c), c)

    off, on = sewn(satin_rail_comp=False), sewn()
    assert off.stats.trims <= 11, off.stats.trims           # the grown polygon: 9 on the 09-19 engine, 11 with tip caps
    assert on.stats.trims <= 22, on.stats.trims             # the rails: 21 before tip caps, 22 with them
    assert on.stats.stitch_count <= 1.23 * off.stats.stitch_count, (off.stats.stitch_count, on.stats.stitch_count)

    # Rail comp's own price, isolated on the engine the numbers above were
    # first read on. This is the arm that says whether the ceilings moved
    # because rail comp got dearer or because another flag joined the ride.
    off0 = sewn(satin_rail_comp=False, satin_tip_caps=False)
    on0 = sewn(satin_tip_caps=False)
    assert off0.stats.trims <= 9, off0.stats.trims
    assert on0.stats.trims <= 21, on0.stats.trims
    assert on0.stats.stitch_count <= 1.18 * off0.stats.stitch_count, (
        off0.stats.stitch_count, on0.stats.stitch_count)


def test_under_rail_comp_a_strokes_first_run_starts_on_the_travel_web():
    """The walk's target is the first point of a stroke's first run. Under
    rail comp `_stroke_underlay` runs a free end out to the cap, so that
    point sat about a half-width off the raw spine's end -- the node the
    travel web is built from -- past the walk's strict 0.8 mm target snap,
    and the walk refused (MARINE at 80 mm, 2026-09-29: `target_unsnapped`
    walks 1 -> 11 when the flag went on). Now the run starts at the raw
    end, on the web, and its first stitch carries the needle out to the
    cap under the column -- the same cure `underlay_on_column` carries.
    On this T the first underlay of each stroke used to start 1.58 mm off
    the web on the rails and 0.0 off it on the grown polygon."""
    bar = Polygon([(0, 0), (24, 0), (24, 3), (0, 3)])
    stem = Polygon([(10.5, 3), (13.5, 3), (13.5, 20), (10.5, 20)])
    poly = bar.union(stem).buffer(0)
    strokes, _half, _field = s6.extract_strokes(poly, half_extra_mm=PULL, corner_twigs=True,
                                                 junction_stack=True)
    assert len(strokes) == 2
    ends = [st.spine[0] for st in strokes] + [st.spine[-1] for st in strokes]
    runs, report = s6.satin_shape(poly, "T", underlay_style="center", trim_at_mm=3.0,
                                  rail_comp_mm=PULL, rail_comp_floor_mm=1.5, corner_twigs=True,
                                  junction_stack=True, stroke_order="euler")
    assert not report["empty"]
    # the first run of each stroke is its centre underlay, and it starts on the web
    firsts = [r for i, r in enumerate(runs)
              if r.kind == "underlay" and (i == 0 or runs[i - 1].kind == "satin"
                                           or runs[i - 1].kind == "travel")]
    assert len(firsts) == 2, [r.kind for r in runs]
    for r in firsts:
        miss = min(math.dist(r.points[0], e) for e in ends)
        assert miss < 0.8, f"a stroke's first run starts {miss:.2f} mm off the travel web"
        # and the stitch from there runs out to the cap, not back along the spine
        assert math.dist(r.points[0], r.points[1]) <= 3.0


def test_push_rails_pushes_a_pinched_cross_and_leaves_a_directionless_one():
    """`_push_rails`: a pinched 0.2 mm cross is pushed to 0.8 — the cross the
    grown polygon would have carried, and what the drop check must see; a
    cross whose two rails sit on the same point has nothing to push along
    and stays degenerate."""
    poly = Polygon([(0, 0), (10, 0), (10, 4), (0, 4)])
    a = [(5.0, 2.1), (6.0, 3.0), (7.0, 2.0)]
    b = [(5.0, 1.9), (6.0, 1.0), (7.0, 2.0)]
    pa, pb = s6._push_rails(a, b, poly, 0.3, 1.5)
    assert abs(math.dist(pa[0], pb[0]) - 0.8) < 1e-9
    assert abs(math.dist(pa[1], pb[1]) - (2.0 + 0.6)) < 1e-9
    assert pa[2] == a[2] and pb[2] == b[2]


def test_the_flips_bare_artwork_is_hairlines_on_the_sides_and_a_hole_at_a_tapered_end():
    """WHAT the flip's bare artwork is, which its headline could not say.

    `docs/kent-review-2026-09-28.md` recorded ENTHUSIAST's cost as bare
    artwork 6.27 -> 7.10% with the rise "along the rails (mid-rail 2.06 ->
    4.12%), cause not yet isolated". Isolated 2026-09-29 with
    `tools/bare_anatomy.py`, which splits every bare component by WHERE it
    sits (a disc at a run's terminal cross = an `end` gap, else a `side` gap)
    and HOW THICK it is (max inscribed radius). The two populations want
    opposite responses and the percentage cannot tell them apart:

    - **The mid-rail half is HAIRLINES and is not the defect.** 80% of the
      side area sits in components under 0.10 mm half-width, the worst side
      component is SMALLER on than off (0.45 against 0.50 mm2), and the
      same-rail step distribution barely moves (p50 0.427 -> 0.419 mm, share
      over 0.45 mm 35.1 -> 33.6%, the summed overshoot past the 0.4 mm pitch
      88.2 -> 71.5 mm). A 0.4 mm thread at the 0.4 mm pitch just touches, so
      every rail step over it leaves a sliver the coverage model counts;
      rail comp makes more of them and makes each thinner.
    - **The cloth-visible cost is at a TAPERED END.** The apex of the A
      (`Scd87e08f`) sews to within 0.08 mm of the artwork off the rails and
      stops 1.63 mm short on them, leaving one 3.61 mm2 triangle at 0.71 mm
      half-width -- the largest bare component on the fixture, and under
      preflight's `_UNCOVERED_MIN_PATCH_MM2` (5.0), so nothing reports it.
      Rendered both ways: `docs/renders/rail-comp-bare-anatomy-2026-09-29/`.

    Pinned as CEILINGS and a FLOOR, the way the trims are: the end gap can
    only get smaller, the hairline share can only get purer. A build that
    closes the apex lowers the first and leaves this green; one that turns
    the hairlines into holes fails the third.
    """
    from tools.bare_anatomy import components
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches

    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=6)
    gen = build_generation(str(TESTDATA / "photo" / "enthusiast_logo.png"), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    polys = {r.shape_id: r.polygon for r in result.regions}
    comps = components(polys, plan)
    assert comps

    ends = [c for c in comps if c[2]]
    sides = [c for c in comps if not c[2]]
    assert ends and sides

    # 1. the tapered-end hole, as a ceiling (3.61 mm2 measured 2026-09-29)
    worst_end = max(a for a, _h, _e, _s in ends)
    assert worst_end <= 3.8, f"the flip's worst end gap grew to {worst_end:.2f} mm2"

    # 2. no side gap is a hole (0.45 mm2 measured; OFF's worst is 0.50)
    worst_side = max(a for a, _h, _e, _s in sides)
    assert worst_side <= 0.55, f"a mid-rail gap reached {worst_side:.2f} mm2 — no longer a hairline"

    # 3. and the side population STAYS hairlines (80% measured)
    side_area = sum(a for a, _h, _e, _s in sides)
    hairline = sum(a for a, h, _e, _s in sides if h < 0.10)
    assert hairline / side_area >= 0.70, (
        f"only {100 * hairline / side_area:.0f}% of mid-rail bare is thinner than "
        "0.10 mm half-width — the sides have started opening real gaps")
def test_under_rail_comp_the_skeleton_reads_the_polygon_with_its_seams_closed():
    """Stage 5 hands an on-rails shape its artwork unioned with the underlap
    reach under whatever sews later and cut by whatever sewed earlier, and
    that boundary carries hairline seams a fraction of a pull wide wherever
    the artwork's sub-pixel edge meets a buffered or neighbouring one. The
    medial axis reads each seam as a branch: `logo_golden_tee` at 80 mm sewed
    178 -> 494 strokes and 6,892 -> 11,377 stitches when the flag went on,
    the O of GOLF alone 29 -> 88 (2026-09-29). The grown polygon never had
    them -- a round-joined `buffer(pull)` swallows anything narrower than
    the pull -- so the skeleton now reads the polygon with its seams closed
    (`_close_seams`: what a half-pull closing fills where it is nowhere
    wider than half a pull AND touches a stretch of boundary stage 5 added,
    the on-rails polygon's boundary off the artwork's), while the rails,
    caps and every art reading stay on the polygon itself. A crotch, a
    counter or a notch of the artwork's own stays as the artwork drew it:
    the closing at the pull's radius tried first re-cut MARINE's letters
    37 -> 28 strokes, and the width test alone still cost MARINE four folds
    and ENTHUSIAST an unsewn element from the artwork's own notches.
    """
    from shapely.geometry import box

    bar = box(0.0, 0.0, 24.0, 2.4)
    seam_w = 0.4 * PULL                      # a hairline: under half a pull
    # a notch in the top edge and a hairline hole through the middle
    seamed = (bar.difference(box(6.0, 1.4, 6.0 + seam_w, 2.4))
                 .difference(box(12.0, 0.4, 12.0 + seam_w, 2.0)))
    closed = s6._close_seams(seamed, PULL)
    assert closed.geom_type == "Polygon" and not closed.interiors
    assert closed.symmetric_difference(bar).area < 0.05, closed.symmetric_difference(bar).area

    def strokes(poly):
        return len(s6.extract_strokes(poly, half_extra_mm=PULL, corner_twigs=True,
                                      junction_stack=True)[0])

    assert strokes(bar) == 1
    assert strokes(seamed) > strokes(bar), "the seams must shatter the raw skeleton for this to test anything"
    assert strokes(closed) == strokes(bar)

    # a counter, and a slit wider than half a pull, are artwork and stay
    with_art = (bar.difference(box(17.0, 0.2, 19.0, 2.2))
                   .difference(box(20.0, 0.4, 20.0 + 0.8 * PULL, 2.0))
                   .difference(box(12.0, 0.4, 12.0 + seam_w, 2.0)))
    kept = s6._close_seams(with_art, PULL)
    assert len(kept.interiors) == 2, [Polygon(r).area for r in kept.interiors]
    # the counter keeps its area to within the hairline fillets at its four
    # corners (0.005 mm2 each at a half-pull radius)
    assert abs(max(Polygon(r).area for r in kept.interiors) - 4.0) < 0.05

    # zero pull is the identity, so rail comp OFF cannot be moved by any of this
    assert s6._close_seams(seamed, 0.0) is seamed

    # WHERE the seam is decides: the same seams are the artwork's own when
    # the artwork polygon carries them (nothing closes), and stage 5's when
    # the artwork is the clean bar (they close)
    assert s6._close_seams(seamed, PULL, art_poly=seamed) is seamed
    own = s6._close_seams(seamed, PULL, art_poly=bar)
    assert own.symmetric_difference(bar).area < 0.05

    # and through `satin_shape` the seamed bar sews the clean bar's columns
    def satin_runs(poly):
        runs, _report = s6.satin_shape(poly, "bar", underlay_style="center", trim_at_mm=3.0,
                                       rail_comp_mm=PULL, rail_comp_floor_mm=1.5,
                                       corner_twigs=True, junction_stack=True, stroke_order="euler")
        return sum(1 for r in runs if r.kind == s6.stitches.SATIN)

    assert satin_runs(seamed) == satin_runs(bar) == 1


def test_the_envelope_reaches_the_far_edge_where_the_gap_is_long_and_nowhere_else():
    """`satin_rails_follow_edge="envelope"` (2026-09-30, Kent's pick after
    #561). The symmetric-offset model places both rails at the NEARER edge's
    distance, so wherever the spine sits off-centre the far rail stops short
    -- BECKER's C, golden_tee's bands once their seams were closed. `True`
    cures it at every station and pays in rail roughness (satin wobble std
    +40% on Becker) and overshoot (ENTHUSIAST 0.257 -> 0.290, the headline).
    The envelope extends a rail only where its side is short by at least
    `_ENVELOPE_GAP_MM`, and only to the running minimum of its own edge
    profile over +-`_ENVELOPE_WINDOW` stations, so it cannot overshoot a
    concavity and carries none of the edge's roughness.

    Pinned on Becker at 80 mm, the fixture with the defect (2026-09-30:
    bare 10.22 / 9.48 / 7.24% False / envelope / True, satin std 0.091 /
    0.100 / 0.128, overshoot 0.0127 / 0.0127 / 0.0157): the envelope covers
    more than the symmetric width, at less than a third of True's roughness
    and none of its overshoot. And the design limit, on a synthetic band: a
    2 mm bulge the axis cannot re-centre under is shorter than the window,
    so the envelope keeps the symmetric width there where True reaches --
    corner-sized bare is `satin_cap_recentre`'s question, not this mode's.

    **`satin_tip_caps=False` here, held on the engine this mode was measured
    on** (it was written before that flag was flipped ON, 2026-09-30, and the
    three numbers above are reproduced byte for byte with it OFF). That is not
    bookkeeping: the two cures reach for MUCH of the same bare, and the
    shipped engine makes the envelope's own headroom look small. Re-measured
    2026-09-30 on the merged tree, Becker 80 mm, bare / satin std / stitches:

        tip caps OFF   10.222% / 0.0914 / 5,691   9.484% / 0.0999 / 5,750   7.235% / 0.1281 / 6,079
        tip caps ON     9.483% / 0.0943 / 6,101   9.030% / 0.1108 / 6,219   6.840% / 0.1243 / 6,601
                        ^ False                   ^ envelope                ^ True

    **Tip caps alone take Becker's symmetric-rail bare to 9.483%, which is the
    figure the envelope reached without them (9.484%).** The envelope then
    takes a further 0.45 points, at +17.5% roughness rather than the +9.3% it
    costs on the pre-flip engine. Both assertions below would fail on the
    shipped default for that reason and for no other; pin the mode where it
    was measured, and read the overlap from the table rather than from a
    loosened threshold. What the envelope is worth ON TOP of tip caps is a
    separate question and belongs to its flip decision, not to this test.
    """
    from shapely.geometry import box
    from tools import edge_wobble as EW
    from tools.rail_edge import bare_area

    def arm(mode):
        r, p = digitize(TESTDATA / "becker_marine_logo.png",
                        PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                                       max_colors=6, satin_rails_follow_edge=mode,
                                       satin_tip_caps=False))
        polys = {rg.shape_id: rg.polygon for rg in r.regions}
        num, den = bare_area(polys, p)
        wob = EW.analyse_plan(polys, p, background=set())
        return num / den, wob["by_tier"]["satin"]["wobble_std_mm"], p.stats.stitch_count

    off_bare, off_std, off_st = arm(False)
    env_bare, env_std, env_st = arm("envelope")
    on_bare, on_std, on_st = arm(True)
    assert env_bare < off_bare - 0.005, (off_bare, env_bare)          # it reaches: 10.2 -> 9.5%
    assert env_std <= off_std * 1.15, (off_std, env_std)             # at a tenth more roughness (True: +40%)
    assert on_std > env_std, (on_std, env_std)
    assert off_st < env_st < on_st, (off_st, env_st, on_st)           # and a fraction of True's thread

    band = box(0, 0, 24, 2.4).union(box(11, 2.4, 13, 3.6))            # a 2 mm bulge, 1.2 mm deep
    tops = {}
    for mode in (False, True, "envelope"):
        runs, _ = s6.satin_shape(band, "band", underlay_style="center", trim_at_mm=3.0,
                                 rail_comp_mm=PULL, rail_comp_floor_mm=1.5, corner_twigs=True,
                                 junction_stack=True, stroke_order="euler", rails_follow_edge=mode)
        pts = [q for r in runs if r.kind == s6.stitches.SATIN for q in r.points if 11 <= q[0] <= 13]
        tops[mode] = max(q[1] for q in pts)
    assert tops[False] < 3.3 < 3.6 <= tops[True], tops                # the symmetric rail stops short; True reaches
    assert abs(tops["envelope"] - tops[False]) < 1e-6, tops           # the envelope holds: the bulge is shorter than its window
