"""Cap sew order (`cfg.cap_center_out`, default OFF).

A cap front is a curved, seamed, stretching object with a raised centre seam.
The craft rule (machine-physics playbook Law 34, [P] Melco x2, [T] ASI) is to
sew **bottom-up and centre-out**, so the fabric's distortion radiates
symmetrically away from the seam instead of being pushed ahead of the needle
across it.

**The browser lane has done this since before this file existed** —
`src/digitize.js`'s `capMode` sorts a colour block's shapes by
`|x - designCentreX|` ascending, tiebreaking `y` descending. The Python
digitizer — the lane every auto-digitized design actually goes through — did
not: `cfg.garment_id` reached `fabrics.py` for pull compensation, underlay,
density and trim distance and stopped there. `stage7_sequence` mentioned the
word "garment" twice, both times in prose. So a hat job got cap PHYSICS and
no cap ORDER, and the two lanes disagreed about the same garment.

This file closes that split and nothing else. The rest of Law 34 — sectioned
cap-front fills, seam-parallel stitching, lettering last, the ~57 mm height
ceiling, extra pull comp across the seam — is deliberately out of scope
(Kent's call, 2026-09-19).

**Do not confuse `cap_center_out` with `edge_cap`.** They share three letters
and nothing else: `edge_cap` is the design's outer silhouette (stage 6's
border work, `tests/test_edge_cap.py`); this is the order shapes sew in on a
hat.

**Why the centreline is `x = 0` and not a computed design centre.** Stage 4
emits millimetres with the origin at the artwork bbox centre and the y-axis
DOWN (`stage4_vectorize` line 93, `stitches.py`'s module docstring). So the
design's own vertical centreline IS `x = 0` in the frame stage 7 sees — the
same point the browser lane calls `cx`, and the same point DST calls (0, 0).
And because y runs DOWN, "bottom of the garment first" is DESCENDING y, which
is exactly what `capMode`'s `cents[b].y - cents[a].y` does in the browser's
own y-down frame. That y-down convention is not an assumption here: it was
settled by rendering a professionally digitized third-party file y-down and
getting upright text (`export.py`'s own docstring).

**Default OFF, byte-identical off** (Kent, 2026-09-19): the flip waits on a
render of a real hat fixture, so the ordering rule and the goldens it moves
never arrive in the same change.
"""
from __future__ import annotations

from types import SimpleNamespace

from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, digitize, export, get_fabric
from digitizer_core.machine import SATIN_MAX_WIDTH_MM
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_satin import is_satin_candidate
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART
from tests.conftest import TESTDATA, cfg

FAB = get_fabric("structured_cap")


def bar(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def region(poly: Polygon, sid: str, thread: int, layer: int,
           meta: dict | None = None) -> Region:
    m = {"layer": layer}
    m.update(meta or {})
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta=m)


def plan_for(regions: list[Region], **cfg_kw):
    """Stage 5 then stage 7, one cone, the way `test_borders_last.py` does it.

    `edge_cap="none"` for the same reason that file gives: these are synthetic
    bars whose subject is the ORDER they sew in, and a silhouette cap would add
    a thread and a shape id to every expectation without testing anything this
    file is about.
    """
    cfg_kw.setdefault("edge_cap", "none")
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c)
    return SimpleNamespace(blocks=blocks, warnings=warnings)


def sew_rank(plan) -> dict[str, int]:
    """shape_id -> first-sewn rank, from the emitted runs."""
    order: dict[str, int] = {}
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id and r.shape_id not in order:
                order[r.shape_id] = len(order)
    return order


# Three compact blocks on one cone, at known distances from the centreline.
# All the same size and tier, so the only thing that can separate them is
# position — if the classifier ever demotes one the sanity test below fails
# rather than this file quietly becoming vacuous.
LEFT = bar(8, 8, cx=-20.0)
CENTRE = bar(8, 8, cx=0.0)
RIGHT = bar(8, 8, cx=20.0)


def _three_across():
    return [region(LEFT, "L", 3, 0),
            region(CENTRE, "C", 3, 0),
            region(RIGHT, "R", 3, 0)]


def test_the_fixture_shapes_are_all_one_tier():
    """No shape here may reach satin, or `borders_last` would be doing the
    sorting and every assertion below would be about the wrong rule."""
    for poly in (LEFT, CENTRE, RIGHT):
        assert not is_satin_candidate(poly, SATIN_MAX_WIDTH_MM)


def test_cap_center_out_defaults_off():
    """Kent's 2026-09-19 call, recorded as a failing test the day the default
    silently changes."""
    assert PipelineConfig().cap_center_out is False


def test_off_is_byte_identical_on_a_cap_garment():
    """The flag existing must not move a single stitch of a hat job that never
    asked for it. Pinned on exported DST bytes, not a stitch count: a count can
    stay equal while geometry moves.
    """
    a = digitize(TESTDATA / "logo_whitebg.png", cfg(garment_id="hat_front"))[1]
    b = digitize(TESTDATA / "logo_whitebg.png",
                 cfg(garment_id="hat_front", cap_center_out=False))[1]
    assert export.export_dst(a) == export.export_dst(b)


def test_cap_order_starts_at_the_centerline():
    """The whole rule, in one assertion pair.

    OFF, the first pick is the shape FARTHEST from the group's centroid (stage
    7's "start at an extreme so the sweep never comes back"), which on this
    fixture is an outer block. ON, it is the block ON the seam.
    """
    off = sew_rank(plan_for(_three_across(), garment_id="hat_front"))
    assert off["C"] != 0, \
        "flag OFF keeps the travel-only start: an outer block sews first"

    on = sew_rank(plan_for(_three_across(), garment_id="hat_front",
                           cap_center_out=True))
    assert on["C"] == 0, "flag ON: the shape on the centreline sews first"
    assert on["L"] > on["C"] and on["R"] > on["C"], \
        "and both outer blocks sew after it, working outward"


def test_cap_order_tiebreak_is_bottom_up():
    """Two blocks the same distance from the seam, one low on the cap and one
    high. The low one sews first — bottom-up, toward the crown.

    y runs DOWN in this frame, so "low on the garment" is the LARGER y.
    """
    regs = [region(bar(8, 8, cx=-20.0, cy=-20.0), "HIGH", 3, 0),
            region(bar(8, 8, cx=20.0, cy=20.0), "LOW", 3, 0)]
    on = sew_rank(plan_for(regs, garment_id="hat_front", cap_center_out=True))
    assert on["LOW"] < on["HIGH"], \
        "equidistant from the seam, the bill end sews before the crown end"


def test_a_sew_order_pin_still_beats_the_cap_order():
    """The precedence every review-screen override gets, unchanged."""
    regs = _three_across()
    regs[2].meta["sew_order"] = 0        # "R", the far right block
    on = sew_rank(plan_for(regs, garment_id="hat_front", cap_center_out=True))
    assert on["R"] == 0, \
        "an explicit pin outranks the craft default, the way it outranks every other bias"


def test_a_non_cap_garment_is_untouched():
    """The flag is ON and the garment is a polo: nothing may move."""
    off = sew_rank(plan_for(_three_across(), garment_id="left_chest"))
    on = sew_rank(plan_for(_three_across(), garment_id="left_chest",
                           cap_center_out=True))
    assert on == off


def test_borders_last_still_outranks_the_cap_order():
    """The two biases COMPOSE, and this is the order they compose in.

    `borders_last` filters the pool (satin waits for every fill in its group);
    the cap rule then orders whatever is left. So a satin ribbon sitting right
    on the seam still sews after a fill block 20 mm off it — the craft reason
    is that borders-last came off Kent's own sewn garment, while centre-out is
    about distortion, and deferring the ribbon costs the ribbon nothing.

    Pinned because it is a CHOICE, not a consequence: keying the whole group
    on distance from the seam first would have inverted it.
    """
    regs = [region(bar(8, 8, cx=-20.0), "FIL", 3, 0),
            region(bar(30, 2, cx=0.0), "SAT", 3, 0)]
    assert is_satin_candidate(regs[1].polygon, SATIN_MAX_WIDTH_MM), \
        "the ribbon must reach satin or this test is about nothing"

    cap_only = sew_rank(plan_for(regs, garment_id="hat_front",
                                 cap_center_out=True, borders_last=False))
    assert cap_only["SAT"] < cap_only["FIL"], \
        "cap order alone: the shape on the seam goes first, satin or not"

    both = sew_rank(plan_for(regs, garment_id="hat_front",
                             cap_center_out=True, borders_last=True))
    assert both["FIL"] < both["SAT"], \
        "with both on, the fill still sews before the satin that sits on the seam"


def test_a_beanie_counts_as_a_cap():
    """`src/digitize.js` treats `hat_front` and `beanie` alike; the two lanes
    must not disagree about which garments are caps."""
    on = sew_rank(plan_for(_three_across(), garment_id="beanie",
                           cap_center_out=True))
    assert on["C"] == 0
