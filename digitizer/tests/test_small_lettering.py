"""Small lettering (2026-09-03) — two rules the fine-lettering review found
half-built, both in `docs/design-review-fine-lettering-2026-09-03.md`.

1. **The stitch type can change within one letter.** A stroke inside a satin
   shape whose every cross fell under `SATIN_MIN_CROSS_MM` used to be
   dropped from `kept` and vanish — a letter with a 1.5 mm stem and a 0.4 mm
   bar sewed the stem and lost the bar (defect 24: Hotel Fremont's "THE",
   the E/F/T arms on drone_render; measured pre-change on Fremont at
   92.5 mm: 41 of 282 strokes, 83.5 mm of spine, gone). It now sews as a
   bean run along its spine (`stage6_satin._hairline_stretches`), at the run
   tier's own numbers, and stage 7 says so (`HAIRLINE_STROKES_AS_RUN`).

2. **Small lettering sews bare.** Law 50's first rung — no underlay under a
   5 mm cap — had shipped in the browser lettering engine since its underlay
   ladder landed and NOT in this one, which laid a centre run under every
   satin stroke however small (Fremont: under 0.53-0.98 mm columns). Stage 7
   now passes `underlay_style="none"` for a satin shape whose ARTWORK extent
   is under `machine.SATIN_UNDERLAY_MIN_EXTENT_MM`.

Fixtures are synthetic and shaped like the failure: a T whose bar is a
hairline, a bar that is all hairline, and a two-bar image where one bar is
under the rung and one is over it.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize, machine, stitches
from digitizer_core.stage6_satin import satin_shape
from digitizer_core.warnings_codes import HAIRLINE_STROKES_AS_RUN


# --- Rule 1: the hairline stroke, at the satin_shape seam ------------------

def _t_shape(stem_w: float = 1.5, bar_w: float = 0.4, height: float = 8.0,
             width: float = 6.0):
    """A T: a stem the satin can carry and a crossbar it cannot."""
    stem = box(-stem_w / 2, 0.0, stem_w / 2, height)
    bar = box(-width / 2, height - bar_w, width / 2, height)
    return unary_union([stem, bar])


def _kinds(runs):
    out = {}
    for r in runs:
        out[r.kind] = out.get(r.kind, 0) + 1
    return out


def test_a_hairline_bar_on_a_satin_stem_sews_as_a_run_instead_of_vanishing():
    """THE defect. Pre-change this shape returned satin for the stem only —
    every cross on the 0.4 mm bar fell under the floor and the bar was gone
    with nothing said. Watched go red against the pre-change tree."""
    runs, report = satin_shape(_t_shape(), "T", underlay_style="none", trim_at_mm=3.0)
    assert not report["empty"]
    kinds = _kinds(runs)
    assert kinds.get(stitches.SATIN, 0) >= 1, kinds
    assert kinds.get(stitches.RUN, 0) >= 1, f"the bar must sew as a run: {kinds}"
    bar = [p for r in runs if r.kind == stitches.RUN for p in r.points]
    xs = [p[0] for p in bar]
    ys = [p[1] for p in bar]
    assert max(xs) - min(xs) >= 4.5, "the run must span the bar, not a stub of it"
    assert min(ys) >= 7.0 and max(ys) <= 8.3, "and lie on the bar, not the stem"
    stem = [p for r in runs if r.kind == stitches.SATIN for p in r.points]
    assert max(abs(p[0]) for p in stem) <= 1.0, "the satin stays on the stem"


def test_the_run_is_a_bean_at_the_run_tier_s_own_numbers():
    """Three passes at BEAN_STITCH_MM: the corpus-measured light tier, not a
    new constant. The walk covers the bar three times over."""
    runs, _ = satin_shape(_t_shape(), "T", underlay_style="none", trim_at_mm=3.0)
    run = next(r for r in runs if r.kind == stitches.RUN)
    pts = run.points
    length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    span = max(p[0] for p in pts) - min(p[0] for p in pts)
    assert length >= machine.BEAN_PASSES * span * 0.9, (length, span)
    steps = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    assert max(steps) <= machine.MAX_STITCH_MM
    # stations sit about one bean stitch apart
    assert abs(np.median(steps) - machine.BEAN_STITCH_MM) < 0.2, np.median(steps)


def test_a_shape_that_is_all_hairline_sews_as_runs_not_empty():
    """A 0.4 mm bar has no satin at all. It used to report empty and fall to
    fill (which cannot hold it either) and then to an outline rescue tracing
    both edges of a stroke narrower than the thread. Now: one run, its spine."""
    runs, report = satin_shape(box(-0.2, 0.0, 0.2, 8.0), "I", underlay_style="none",
                               trim_at_mm=3.0)
    assert not report["empty"]
    kinds = _kinds(runs)
    assert kinds.get(stitches.SATIN, 0) == 0, kinds
    assert kinds.get(stitches.RUN, 0) >= 1, kinds
    assert kinds.get(stitches.UNDERLAY, 0) == 0, "a hairline carries no underlay"
    ys = [p[1] for r in runs if r.kind == stitches.RUN for p in r.points]
    assert max(ys) - min(ys) >= 7.0, "the run reaches both caps"


def test_a_hairline_shorter_than_three_bean_stations_is_left_to_the_rescue():
    """Under three stations the needle is re-entering its own holes — the run
    tier's own floor. Empty is honest; stage 7's outline rescue owns it."""
    runs, report = satin_shape(box(-0.2, 0.0, 0.2, 1.0), "dot", underlay_style="none",
                               trim_at_mm=3.0)
    assert report["empty"] and not runs


def test_a_plain_satin_bar_is_byte_identical_to_before():
    """Nothing here touches a stroke that keeps its crosses."""
    poly = box(-1.0, 0.0, 1.0, 12.0)
    runs, report = satin_shape(poly, "bar", underlay_style="center_run", trim_at_mm=3.0)
    assert not report["empty"]
    kinds = _kinds(runs)
    assert kinds.get(stitches.RUN, 0) == 0, kinds
    assert kinds.get(stitches.SATIN, 0) >= 1 and kinds.get(stitches.UNDERLAY, 0) >= 1


# --- Both rules, through the real pipeline ---------------------------------

def _scale_bar(img: np.ndarray) -> None:
    """A 700 px wordmark bar so the artwork bbox pins the scale at 8.75 px/mm
    for an 80 mm target — the same trick tests/test_run_tier.py relies on."""
    img[40:80, 50:750] = (40, 40, 40)


def _two_bars_image() -> np.ndarray:
    """Two satin bars: 12 x 120 px (1.4 x 13.7 mm — over the 5 mm rung) and
    8 x 34 px (0.9 x 3.9 mm — under it, but big enough to satin)."""
    img = np.full((300, 800, 3), 255, np.uint8)
    _scale_bar(img)
    img[120:240, 200:212] = (40, 40, 40)          # tall bar
    img[150:184, 500:508] = (40, 40, 40)          # short bar
    return img


def _shapes_left_to_right(result):
    return sorted(result.regions, key=lambda r: r.polygon.bounds[0])


def test_stage_7_reports_hairline_strokes_sewn_as_runs():
    """The seam: stage 7 counts the runs `satin_shape` sewed for hairline
    stretches and says so. Driven at the `sequence()` level with the sewing
    polygon equal to the artwork, the way tests/test_run_tier.py drives the
    outline rescue — through `digitize()` every fabric preset's pull
    compensation grows a 0.4 mm bar past the floor first, which is stage 5's
    business, not this rule's (the hairlines real art reaches stage 6 with
    are the ones compensation could not grow: Hotel Fremont at 92.5 mm).
    """
    from digitizer_core.fabrics import fabric_for_garment
    from digitizer_core.regions import Region
    from digitizer_core.stage5_overlap import PlannedRegion
    from digitizer_core.stage7_sequence import sequence

    t = _t_shape()
    reg = Region(shape_id="ST", polygon=t, thread_index=0, thread_number="0134",
                 area_mm2=t.area, source="test", meta={"layer": 0})
    planned = [PlannedRegion(region=reg, polygon=t, sew_index=0)]
    blocks, warnings = sequence(planned, fabric_for_garment("left_chest"),
                                PipelineConfig(underlay=False))
    codes = {w["code"]: w for w in warnings}
    assert HAIRLINE_STROKES_AS_RUN in codes, sorted(codes)
    assert codes[HAIRLINE_STROKES_AS_RUN]["count"] >= 1
    assert codes[HAIRLINE_STROKES_AS_RUN]["shapes"] == 1
    kinds = {}
    for b in blocks:
        for run in b.runs:
            kinds[run.kind] = kinds.get(run.kind, 0) + 1
    assert kinds.get(stitches.SATIN, 0) >= 1 and kinds.get(stitches.RUN, 0) >= 1, kinds


def test_no_underlay_under_a_letter_under_the_5_mm_rung_and_underlay_over_it():
    result, plan = digitize(_two_bars_image(), PipelineConfig(target_width_mm=80.0,
                                                              garment_id="left_chest"))
    shapes = _shapes_left_to_right(result)
    assert len(shapes) == 3, [s.shape_id for s in shapes]
    tall, short = shapes[1], shapes[2]
    tx0, ty0, tx1, ty1 = tall.polygon.bounds
    sx0, sy0, sx1, sy1 = short.polygon.bounds
    assert max(tx1 - tx0, ty1 - ty0) >= machine.SATIN_UNDERLAY_MIN_EXTENT_MM
    assert max(sx1 - sx0, sy1 - sy0) < machine.SATIN_UNDERLAY_MIN_EXTENT_MM
    kinds = {tall.shape_id: {}, short.shape_id: {}}
    for _b, run in plan.iter_runs():
        if run.shape_id in kinds:
            kinds[run.shape_id][run.kind] = kinds[run.shape_id].get(run.kind, 0) + 1
    # both are satin, so the comparison is like for like
    assert kinds[tall.shape_id].get(stitches.SATIN, 0) >= 1, kinds
    assert kinds[short.shape_id].get(stitches.SATIN, 0) >= 1, kinds
    assert kinds[tall.shape_id].get(stitches.UNDERLAY, 0) >= 1, "the 13.7 mm bar keeps its centre run"
    assert kinds[short.shape_id].get(stitches.UNDERLAY, 0) == 0, "the 3.9 mm bar sews bare"


def test_the_rung_is_the_browser_engine_s_number():
    """One published number, two engines: `src/satinfont.js` has sewn by
    UNDERLAY_CAP_MIN_MM = 5 since the ladder landed."""
    assert machine.SATIN_UNDERLAY_MIN_EXTENT_MM == 5.0


def test_a_needle_pull_comp_grew_out_of_nothing_is_not_a_hairline():
    """Hotel Fremont at 92.5 mm, after the run fallback landed: a 1 mm long,
    0.04 mm wide vectorization needle on a black sliver of the hexagon band
    sewed as a visible tick. The needle is under the outline tolerance stage
    4 simplifies to (`config.simplify_tol_mm`, 0.2 mm), so the artwork never
    promised it -- but stage 5's pull compensation grew it into a 0.44 mm
    "stroke", and its spine then cleared the run tier's floor.

    A hairline earns a bean only where the ART has ink: `satin_shape` trims a
    stretch at both ends while the cross spans less than the tolerance of
    the region's own uncompensated polygon. Same shape, same pull, floor off:
    the tick sews, which is what this guards against."""
    bar = box(-0.6, 0.0, 0.6, 8.0)
    needle = box(-0.02, 8.0, 0.02, 10.0)
    art = unary_union([bar, needle])
    grown = art.buffer(0.2)                      # stage 5's round-join pull comp

    def runs_above_the_bar(**kw):
        runs, report = satin_shape(grown, "needle", underlay_style="none",
                                   trim_at_mm=10.0, **kw)
        assert not report["empty"]
        return [r for r in runs if r.kind == stitches.RUN
                and max(y for _x, y in r.points) > 8.3]

    assert runs_above_the_bar(), "precondition: without the art floor the needle sews as a bean"
    assert runs_above_the_bar(art_poly=art, hairline_floor_mm=0.2) == [], (
        "a needle the outline tolerance never promised must not sew")
