"""The A's apex is a HOLE, not an artefact of the instrument that found it.

Kent's pick 2026-09-30, after two instruments disagreed about MASTER_SCOPE
defect 49. `tools/bare_anatomy.py` reported a 3.61 mm2 gap at the apex of
ENTHUSIAST's **A**; `tools/dropped_elements.py`'s `unsewn_frac` read 0.0000 on
that fixture in every arm. A defect nobody can measure twice is a defect
nobody should build against, and the previous build was priced on the wrong
one of these two.

**Both were partly wrong, and the hole is real.** `bare_anatomy` counts satin
crosses and nothing else, so underlay threading the gap is invisible to it and
it over-reports by 1.7x here. `unsewn_frac` cannot fire on this fixture at all
— its on-ink vote is `A_ink[region].mean() > 0.5` and the largest per-region
ink fraction is 0.33, which its own docstring states. What is left when both
corrections land is about 2 mm2 of cloth, a millimetre across, at the peak of
a capital letter, and it survives the 0.50 mm opening that exists to throw
away boundary hairlines.

The reading that IS sensitive here is `uncovered_ink`: a raster mask
difference with no CIEDE2000, no opening and no colour. It shares no code with
`bare_anatomy` and puts its largest component in the whole design within a
third of a millimetre of the apex — which is what makes this two instruments
agreeing rather than one instrument repeated.

Pictures and the full trail: `docs/renders/apex-verdict-2026-09-30/`.

**These are FLOORS on a defect, not targets.** A build that closes the apex
turns them red, and that is the signal to close defect 49 and rewrite this
file — not to loosen a number.

**That build shipped: `cfg.satin_crown_cover`, ON by default since Kent's flip
2026-10-02, and both floors went red on it.** The instrument tests below now
hold the PRE-FLIP engine (`satin_crown_cover=False`), because what they pin is
that the hole was real and how two instruments read it; the last test pins
that the shipped engine closes it.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import LineString
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import (build_generation, finish_generation,
                                     plan_stitches)
from digitizer_core.stage6_satin import strip_splits
from digitizer_core.stitches import strip_ties
from tests.conftest import TESTDATA

FIXTURE = TESTDATA / "photo" / "enthusiast_logo.png"
WIDTH_MM, GARMENT = 80.0, "left_chest"
# The apex, in plan mm. Only ever used as a NEIGHBOURHOOD test, never as a
# pin: a component is "the apex" if it lands within `NEAR_MM` of it.
APEX_MM = (23.05, -3.16)
NEAR_MM = 1.5


def _sewn(**kw):
    cfg = PipelineConfig(target_width_mm=WIDTH_MM, garment_id=GARMENT,
                         max_colors=6, **kw)
    gen = build_generation(str(FIXTURE), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    return result, plan, {r.shape_id: r.polygon for r in result.regions}


@pytest.fixture(scope="module")
def sewn():
    """One digitize of the engine the hole was found on -- the crown cover
    OFF -- shared by the instrument tests."""
    return _sewn(satin_crown_cover=False)


def test_the_shipped_engine_closes_the_apex(sewn):
    """Defect 49, closed: with `satin_crown_cover` ON (the default) the
    largest thread-free component in the design is under the 1.5 mm2 floor
    the pre-flip engine held at the apex, and smaller than it was."""
    from tools.bare_anatomy import components

    assert PipelineConfig().satin_crown_cover is True
    _r0, plan_off, polys_off = sewn
    _r1, plan_on, polys_on = _sewn()
    before = max(components(polys_off, plan_off, all_thread=True))[0]
    after = max(components(polys_on, plan_on, all_thread=True))[0]
    assert before >= 1.5
    assert after < 1.5 and after < before, (before, after)


def test_bare_anatomy_over_reports_because_it_counts_satin_and_nothing_else(sewn):
    """`--all-thread` is not a refinement, it is a correction of scale.

    Underlay, run, travel and fill lay thread on the same cloth. Measured
    2026-09-30 on this fixture: the apex is 3.61 mm2 of satin-free artwork and
    2.17 mm2 of THREAD-free artwork, so the default reading is 1.66x the hole.
    Corpus-wide the ratio runs higher still — becker's worst component is
    54.28 mm2 satin-only and 5.36 mm2 against all thread.
    """
    from tools.bare_anatomy import components

    _res, plan, polys = sewn
    satin_only = components(polys, plan)
    all_thread = components(polys, plan, all_thread=True)
    assert satin_only and all_thread

    assert sum(c[0] for c in all_thread) < sum(c[0] for c in satin_only)
    worst_satin = max(c[0] for c in satin_only)
    worst_all = max(c[0] for c in all_thread)
    assert worst_satin > worst_all, (worst_satin, worst_all)
    # and the correction is large enough to change a build decision
    assert worst_satin / worst_all > 1.4, (worst_satin, worst_all)


def test_what_is_left_is_a_hole_a_millimetre_across_that_an_opening_survives(sewn):
    """The residual, against every thread kind the plan emits.

    `dropped_elements` opens its disagreement mask at 0.50 mm to throw away
    the hairline every shape boundary carries. A gap that survives that is not
    a hairline. Measured 2026-09-30: 2.17 mm2 residual, largest connected part
    1.93 mm2 at 0.464 mm max inscribed half-width, 1.72 mm2 left after the
    opening.
    """
    from tools.bare_anatomy import HAIRLINE_HALF_MM, components
    from tools.dropped_elements import HALO_OPEN_PX
    from tools.artfidelity_self import RES

    _res, plan, polys = sewn
    comps = components(polys, plan, all_thread=True)
    apex = max(comps)
    assert apex[0] >= 1.5, f"apex fell to {apex[0]:.2f} mm2 -- close defect 49"
    assert apex[1] > 3 * HAIRLINE_HALF_MM, apex[1]
    assert apex[2], "the apex is an END gap, not a side gap"

    # and it is thick enough to survive the half-millimetre opening
    open_mm = HALO_OPEN_PX / RES
    geom = _apex_geom(plan, polys, apex[3])
    kept = geom.buffer(-open_mm / 2).buffer(open_mm / 2)
    assert kept.area > 1.0, f"{kept.area:.2f} mm2 survives a {open_mm:.2f} mm opening"


def test_the_coverage_instrument_finds_the_same_hole_and_unsewn_frac_cannot(sewn):
    """Two instruments that share no code, agreeing on where.

    `uncov = A_ink & ~thread` is a raster mask difference over a `stitchviz`
    render — no CIEDE2000, no opening, no colour, nothing in common with the
    shapely subtraction above. Its LARGEST component in the whole design is
    the apex.

    `unsewn_frac` is pinned at 0.0 here and is not evidence of anything: its
    on-ink vote is `A_ink[region].mean() > 0.5` and the largest per-region ink
    fraction on this fixture is 0.33. `uncovered_elements` is 0 for a
    different reason — the apex reads 0.97 mm2 against a `MIN_ELEMENT_MM2` of
    1.0, so the one reading built to name a lost element misses this one by
    three hundredths of a square millimetre.
    """
    import cv2

    from tools.artfidelity_self import RES, art_ink_field, register, \
        stitch_coverage_field
    from tools.dropped_elements import (MIN_ELEMENT_MM2, analyse_design,
                                        art_colour_field)
    from tools.thread_path_render import px_to_plan_mm

    _res, plan, _polys = sewn
    design = plan_to_design(plan)

    r = analyse_design(FIXTURE, design)
    assert r["unsewn_frac"] == 0.0, "the vote fired -- re-read this test"
    assert r["uncovered_worst_mm2"] >= 0.8, r["uncovered_worst_mm2"]
    assert r["uncovered_elements"] == 0, r["uncovered_elements"]
    assert r["uncovered_worst_mm2"] < MIN_ELEMENT_MM2, "it now names an element"

    # rebuild the same mask, to ask WHERE its worst component is
    O_f = stitch_coverage_field(design)
    _s, O_c, _A, dx, dy = register(O_f, art_ink_field(FIXTURE,
                                                      float(design["widthMM"])))
    H, W = O_c.shape
    _argb, art_ink = art_colour_field(FIXTURE, float(design["widthMM"]))
    canvas = np.zeros((H, W), bool)
    oy = (H - art_ink.shape[0]) // 2 + int(round(dy * RES))
    ox = (W - art_ink.shape[1]) // 2 + int(round(dx * RES))
    canvas[oy:oy + art_ink.shape[0], ox:ox + art_ink.shape[1]] = art_ink
    uncov = canvas & ~(O_c >= 0.5)

    n, _lab, st, cent = cv2.connectedComponentsWithStats(uncov.astype(np.uint8), 8)
    worst = max(range(1, n), key=lambda i: st[i, cv2.CC_STAT_AREA])
    # `O_f` sits centred and unshifted on the canvas, so its own origin is the
    # offset to undo before the tool's inverse mapping applies.
    to_mm = px_to_plan_mm(design, RES)
    xm, ym = to_mm(cent[worst][0] - (W - O_f.shape[1]) // 2,
                   cent[worst][1] - (H - O_f.shape[0]) // 2)
    assert math.dist((xm, ym), APEX_MM) < NEAR_MM, (
        f"the largest uncovered component is at ({xm:.2f}, {ym:.2f}) mm, "
        f"not at the apex {APEX_MM}")


def _apex_geom(plan, polys, sid):
    """The shape's largest bare-to-ALL-thread part, as geometry."""
    t = machine.COVERAGE_THREAD_W_MM
    segs = []
    for _b, r in plan.iter_runs():
        pts = strip_splits(strip_ties(list(r.points)))
        step = 2 if (r.kind == "satin" and r.shape_id == sid) else 1
        segs += [LineString([pts[i], pts[i + 1]])
                 for i in range(0, len(pts) - 1, step)
                 if math.dist(pts[i], pts[i + 1]) > 1e-6]
    sewn = unary_union([s.buffer(t / 2.0, cap_style=2) for s in segs])
    bare = polys[sid].difference(sewn)
    return max(getattr(bare, "geoms", [bare]), key=lambda p: p.area)
