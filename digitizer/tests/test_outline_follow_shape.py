"""`cfg.border_from_outline_follow_shape` (built OFF 2026-11-13, Kent on
Commons "Ahora": "now fix the Ahora gear so it sews as a gear").

`border_from_outline` sews an art outline as a satin loop of ONE width on the
body's edge. Ahora's white gear is a ring round a yellow disc with 17 teeth on
its outer edge, and at every size it sewed a ring of spokes: the loop never
looks at the outer edge. ON, a band that fits one satin everywhere and whose
thickness swings by at least the shortest stitch keeps the loop, but:

  * each cross is cut where it leaves the ART (long on a tooth, short in a
    root), not at one width;
  * a band round ONE body is laid out from its OUTER edge (`shaped_band`,
    Kent the same day: "it's an improvement but not across the board"): a
    needle hole on every corner of it, the density held out there, each side
    wall sewn once, the ring's holes short-stitched where they bunch, and no
    line on top;
  * a band shared by several bodies keeps the ring-cast loop: the needle
    locked to the teeth (`art_outline.shaped_stations`) and one bean on the
    outer edge.

A band of one width (To-a-T's frame, which the pro widens) and a band too
thick to be a satin (Becker's drop shadow) are left exactly as they were.
"""
from __future__ import annotations

import hashlib
import math

import pytest
from shapely import affinity
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core import art_outline
from digitizer_core.art_outline import band_thickness, shaped_stations, shaped_width_mm
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import _art_outlines
from digitizer_core.regions import Region
from digitizer_core.keyline_bean import keyline_width_mm
from digitizer_core.shaped_band import layout, sews_shaped, stepped_share
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence

FLAG = "border_from_outline_follow_shape"

R_HOLE, R_ROOT, R_TIP, TEETH = 3.6, 5.0, 6.0, 12
DISC = Point(0, 0).buffer(R_HOLE, quad_segs=48)


def _gear(r_root=R_ROOT, r_tip=R_TIP, teeth=TEETH, r_hole=R_HOLE):
    """A ring with square teeth on its outer edge, round a disc."""
    core = Point(0, 0).buffer(r_root, quad_segs=48)
    half = math.pi * r_root / teeth / 2.0                     # a tooth as wide as a gap
    tooth = box(-half, r_root - 0.2, half, r_tip)
    cogs = [affinity.rotate(tooth, 360.0 * k / teeth, origin=(0, 0)) for k in range(teeth)]
    return unary_union([core, *cogs]).difference(Point(0, 0).buffer(r_hole, quad_segs=48))


GEAR = _gear()
RING = Point(0, 0).buffer(R_ROOT, quad_segs=48).difference(DISC)        # one width: 1.4 mm


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _frame(half=6.0, t=1.6, notch=0.9):
    """A rectangular frame with square notches cut in its long sides. -> (band, body)."""
    inner = box(-half, -half * 0.6, half, half * 0.6)
    top = half * 0.6 + t
    cuts = [box(x - notch / 2, top - notch, x + notch / 2, top + 1) for x in (-4.5, -1.5, 1.5, 4.5)]
    cuts += [affinity.scale(c, yfact=-1, origin=(0, 0)) for c in cuts]
    return inner.buffer(t, join_style=2).difference(unary_union(cuts)).difference(inner), inner


def _plan(band, body=DISC, **cfg_kw):
    b, o = _region("Sbody", body, 0, 0), _region("Souter", band, 1, 1)
    planned = [PlannedRegion(region=b, polygon=body, sew_index=0),
               PlannedRegion(region=o, polygon=band, sew_index=1)]
    cfg = PipelineConfig(underlay=False, **cfg_kw)
    outlines = _art_outlines([b, o], cfg)
    assert outlines and "Souter" in outlines, "the fixture must read as an art outline"
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg, art_outlines=outlines)
    return [r for blk in blocks for r in blk.runs]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _far_radii(runs):
    """How far from the centre the satin's outer needle points land."""
    out = []
    for r in runs:
        if r.shape_id == "Souter" and r.kind == stitches.SATIN:
            out += [math.hypot(x, y) for x, y in r.points if math.hypot(x, y) > R_HOLE + 0.3]
    return out


# --- the flag and what it leans on -------------------------------------------

def test_built_off():
    assert getattr(PipelineConfig(), FLAG) is False


def test_the_numbers_this_leans_on():
    """No constant of its own: if one of these moves, re-read the rule."""
    assert machine.SATIN_MAX_WIDTH_MM == 5.0
    assert machine.SATIN_MIN_CROSS_MM == 0.5
    assert machine.SATIN_SHORT_STITCH_AT_MM == 0.3


# --- reading the band ---------------------------------------------------------

def test_the_band_is_read_square_to_the_holes_ring():
    t = band_thickness(GEAR, DISC)
    assert min(t) == pytest.approx(R_ROOT - R_HOLE, abs=0.05)
    assert max(t) == pytest.approx(R_TIP - R_HOLE, abs=0.05)
    assert max(band_thickness(RING, DISC)) - min(band_thickness(RING, DISC)) < 0.05


def test_a_gear_is_shaped_and_takes_its_thickest_reading():
    assert shaped_width_mm(GEAR, DISC) == pytest.approx(R_TIP - R_HOLE, abs=0.05)


def test_a_band_of_one_width_is_not_shaped():
    """To-a-T Machine's frame: the pro widens it, and so do we."""
    assert shaped_width_mm(RING, DISC) is None


def test_a_step_two_needle_holes_cannot_show_is_not_a_shape():
    """Two holes nearer than the short-stitch line are one hole. A 0.45 mm
    tooth is a step (it was not while the loop was cast from the ring)."""
    assert art_outline.SHAPED_MIN_SWING_MM == machine.SATIN_SHORT_STITCH_AT_MM
    assert shaped_width_mm(_gear(r_tip=R_ROOT + 0.2), DISC) is None
    assert shaped_width_mm(_gear(r_tip=R_ROOT + 0.45), DISC) is not None


def test_a_line_whose_width_only_wanders_is_not_a_shape():
    """Under the shortest stitch a swing must be STEPPED. A ring round an
    off-centre disc swings as far as small teeth do and has no step in it:
    the pro's widened loop ("(hed) p.e." at 180 mm, 0.57 to 0.92 mm)."""
    lopsided = Point(0.2, 0).buffer(R_HOLE + 0.75, quad_segs=48).difference(DISC)   # 0.55 to 0.95 mm
    t = sorted(band_thickness(lopsided, DISC))
    swing = t[int(0.9 * (len(t) - 1))] - t[int(0.1 * (len(t) - 1))]
    assert machine.SATIN_SHORT_STITCH_AT_MM <= swing < machine.SATIN_MIN_CROSS_MM
    assert stepped_share(lopsided, DISC) < 0.1
    assert shaped_width_mm(lopsided, DISC) is None
    small = _gear(r_tip=R_ROOT + 0.45)
    assert stepped_share(small, DISC) > 0.9


def test_a_band_too_thick_for_one_satin_is_not_shaped():
    """Becker's drop shadow, MFab's and the Drone's bands: past the satin's
    width somewhere, so a cross cannot reach the outer edge."""
    assert shaped_width_mm(_gear(r_tip=R_HOLE + machine.SATIN_MAX_WIDTH_MM + 0.5), DISC) is None


# --- the needle locked to the teeth ------------------------------------------

def test_every_tooth_and_every_root_gets_the_same_whole_number_of_stitches():
    pts = shaped_stations(GEAR, DISC, machine.BORDER_DENSITY_MM)
    assert pts
    pitch = 2.0 * math.pi / TEETH
    # a ray from the ring reads "thick" until it leaves the tooth's side below
    # the middle reading: the step, as an angle off the tooth's centre
    half = math.pi * R_ROOT / TEETH / 2.0
    step = math.asin(half / ((R_ROOT + R_TIP) / 2.0))
    teeth, roots = [0] * TEETH, [0] * TEETH
    for x, y in pts:
        a = math.atan2(x, y) % (2 * math.pi)                 # tooth k is centred k pitches round
        k = int(round(a / pitch)) % TEETH
        off = abs(((a - k * pitch + math.pi) % (2 * math.pi)) - math.pi)
        if off < step:
            teeth[k] += 1
        else:
            roots[int(a / pitch) % TEETH] += 1
        # no needle on the step between a tooth and a root: clear of it by
        # more than a tenth of a stitch, on the ring
        assert abs(off - step) * R_HOLE > 0.04
    assert len(set(teeth)) == 1 and teeth[0] >= 2 and teeth[0] % 2 == 0
    assert len(set(roots)) == 1 and roots[0] >= 2 and roots[0] % 2 == 0
    # and no two needle holes on the ring closer than the short-stitch line
    steps = [math.dist(a, b) for a, b in zip(pts, pts[2:] + pts[:2])]
    assert min(steps) >= machine.SATIN_SHORT_STITCH_AT_MM - 0.02


def test_a_band_with_no_step_has_nothing_to_lock_to():
    assert shaped_stations(RING, DISC, machine.BORDER_DENSITY_MM) is None


# --- laid out from the outer edge (`shaped_band.layout`) -----------------------

def _tooth_corners(r=R_TIP, r_root=R_ROOT, teeth=TEETH):
    half = math.pi * r_root / teeth / 2.0
    out = []
    for k in range(teeth):
        for x in (-half, half):
            c = affinity.rotate(Point(x, r), 360.0 * k / teeth, origin=(0, 0))
            out.append((c.x, c.y))
    return out


def test_every_corner_of_the_outer_edge_is_a_needle_hole():
    outer = [o for _r, o in layout(GEAR, DISC)]
    for c in _tooth_corners():                                 # each tooth's two tip corners
        assert min(math.dist(c, o) for o in outer) < 1e-6
    # ... and the root corners under them: a tooth's side wall, top and bottom
    half = math.pi * R_ROOT / TEETH / 2.0
    root = (half, math.sqrt(R_ROOT ** 2 - half ** 2))
    assert min(math.dist(root, o) for o in outer) < 1e-3       # the root circle is a polygon


def test_every_tooth_gets_the_same_stitches_and_the_density_is_held_outside():
    crosses = layout(GEAR, DISC)
    pitch = 2.0 * math.pi / TEETH
    tips = [0] * TEETH
    for _r, (x, y) in crosses:
        if math.hypot(x, y) > R_TIP - 0.05:
            tips[int(round((math.atan2(x, y) % (2 * math.pi)) / pitch)) % TEETH] += 1
    assert len(set(tips)) == 1 and tips[0] >= 3                # 1.3 mm of tip at 0.4 mm, both corners
    # along a tip and along a root, never further apart than the density allows
    for (_r0, o0), (r1, o1) in zip(crosses, crosses[1:] + crosses[:1]):
        if r1 is not None:
            assert math.dist(o0, o1) <= 1.35 * machine.BORDER_DENSITY_MM


def test_a_side_wall_is_sewn_once():
    """A wall's two ends share a ring point: the second is reached along the
    wall, outer hole to outer hole. Two walls a tooth."""
    crosses = layout(GEAR, DISC)
    assert sum(1 for r, _o in crosses if r is None) == 2 * TEETH
    for (_r0, o0), (r1, o1) in zip(crosses, crosses[1:] + crosses[:1]):
        if r1 is None:
            assert math.dist(o0, o1) == pytest.approx(R_TIP - R_ROOT, abs=0.15)


def test_ring_holes_that_bunch_are_short_stitched_no_further_than_they_must_be():
    crosses = layout(GEAR, DISC)
    ring = [r for r, _o in crosses if r is not None]
    for a, b, c in zip(ring, ring[1:] + ring[:1], ring[2:] + ring[:2]):
        assert math.dist(c, b) >= machine.SATIN_SHORT_STITCH_AT_MM - 1e-6
        assert math.dist(c, a) >= machine.SATIN_SHORT_STITCH_AT_MM - 1e-6
    off = [math.hypot(*r) - R_HOLE for r in ring]
    assert max(off) <= machine.SATIN_SHORT_STITCH_PULL_MAX_MM + 1e-6
    assert sum(1 for d in off if d < 1e-6) >= len(off) // 3     # the ring's edge is still sewn


def test_a_square_corner_of_the_hole_is_fanned():
    """Round the body's corner the outer edge runs on for twice the band's
    thickness: the stitches pivot on the corner and the outer corner has a hole."""
    band, body = _frame()
    crosses = layout(band, body)
    corner_in, corner_out = (6.0, 3.6), (7.6, 5.2)
    assert min(math.dist(corner_out, o) for _r, o in crosses) < 1e-6
    fan = [o for r, o in crosses if r is not None and math.dist(r, corner_in) < 0.65
           and o[0] > 6.0 and o[1] > 3.6]
    assert len(fan) >= 6
    for (_r0, o0), (r1, o1) in zip(crosses, crosses[1:] + crosses[:1]):
        if r1 is not None:
            assert math.dist(o0, o1) <= 1.5 * machine.BORDER_DENSITY_MM


def test_what_cannot_be_laid_out_is_left_to_the_loop():
    assert layout(_gear(r_tip=R_HOLE + machine.SATIN_MAX_WIDTH_MM + 0.5), DISC) is None
    assert layout(GEAR, affinity.translate(DISC, 40.0, 0.0)) is None      # not this band's ring


def test_which_bands_are_sewn_from_the_outer_edge():
    """`sews_shaped`: what the hairline gate asks, so a band with teeth is
    not read as a thin line (2 x area / perimeter, and teeth are perimeter)."""
    assert sews_shaped(GEAR, [DISC])
    assert not sews_shaped(RING, [DISC])                                   # one width: the pro's loop
    assert not sews_shaped(GEAR, [DISC, DISC])                             # shared by two bodies
    small = _gear(R_ROOT * 0.42, R_TIP * 0.42, TEETH, R_HOLE * 0.42)       # 0.59 to 1.0 mm thick
    assert sews_shaped(small, [Point(0, 0).buffer(R_HOLE * 0.42, quad_segs=48)])
    assert keyline_width_mm(small) < 0.6 < 2.0 * small.area / (2 * math.pi * (R_HOLE + R_ROOT) * 0.42)


# --- through stage 7 ----------------------------------------------------------

def test_off_the_gear_sews_a_ring_that_ignores_its_teeth():
    """Today's defect, pinned: the loop is one width, so its crosses reach
    the tips' radius in the roots as well. Hardly any stop at a root."""
    far = _far_radii(_plan(GEAR))
    assert far
    at_root = [r for r in far if abs(r - R_ROOT) < 0.25]
    assert len(at_root) < 0.15 * len(far)
    assert sorted(far)[len(far) // 2] > R_ROOT + 0.5


def _satin(runs):
    return [r for r in runs if r.shape_id == "Souter" and r.kind == stitches.SATIN]


@pytest.mark.parametrize("scale", [1.0, 0.6, 0.45])
def test_on_the_gear_is_one_satin_with_a_hole_on_every_corner_and_no_thread_off_the_art(scale):
    band = _gear(R_ROOT * scale, R_TIP * scale, TEETH, R_HOLE * scale)
    body = Point(0, 0).buffer(R_HOLE * scale, quad_segs=48)
    runs = _plan(band, body, **{FLAG: True})
    assert not [r for r in runs if r.shape_id == "Souter" and r.kind == stitches.RUN]   # no line on top
    satin = _satin(runs)
    assert len(satin) == 1
    pts = [tuple(p) for p in satin[0].points]
    for c in _tooth_corners(R_TIP * scale, R_ROOT * scale):
        assert min(math.dist(c, h) for h in pts) < 1e-6
    # every stitch lies on the art: none across the gap between two teeth,
    # none past a tip
    assert band.buffer(0.05).covers(LineString(pts))


def test_on_the_notched_frame_keeps_its_notches_and_its_corners():
    band, body = _frame()
    off, on = _plan(band, body), _plan(band, body, **{FLAG: True})
    assert not band.buffer(0.05).covers(LineString([tuple(p) for p in _satin(off)[0].points]))
    pts = [tuple(p) for p in _satin(on)[0].points]
    assert band.buffer(0.05).covers(LineString(pts))
    for c in ((7.6, 5.2), (-7.6, 5.2), (7.6, -5.2), (-7.6, -5.2)):
        assert min(math.dist(c, h) for h in pts) < 1e-6


def test_the_real_gear_at_40_mm_is_a_satin_not_a_thin_line():
    """Commons "Ahora" at 40 mm: the gear is 4.8 mm across, its band 0.57 to
    0.93 mm thick. The hairline gate reads 2 x area / perimeter, teeth are
    perimeter, and it sewed as a bean inside its own outline. ON it is a band
    with teeth: one white satin, no white run."""
    from dataclasses import replace
    from pathlib import Path

    from digitizer_core.pipeline import digitize

    art = Path(__file__).resolve().parents[1] / "testdata" / "art" / "commons_lettering" / "logo_ahora.png"
    _result, plan = digitize(art.read_bytes(),
                             replace(PipelineConfig(), target_width_mm=40.0, **{FLAG: True}))
    kinds = {r.kind for b in plan.blocks if min(b.rgb) > 235 for r in b.runs}
    assert stitches.SATIN in kinds and stitches.RUN not in kinds


def test_on_the_body_and_a_band_of_one_width_are_byte_identical():
    off, on = _plan(GEAR), _plan(GEAR, **{FLAG: True})
    assert _md5([r for r in on if r.shape_id == "Sbody"]) == _md5([r for r in off if r.shape_id == "Sbody"])
    assert _md5(_plan(RING, **{FLAG: True})) == _md5(_plan(RING))


def test_on_without_border_from_outline_does_nothing():
    b, o = _region("Sbody", DISC, 0, 0), _region("Souter", GEAR, 1, 1)

    def plan(**kw):
        planned = [PlannedRegion(region=b, polygon=DISC, sew_index=0),
                   PlannedRegion(region=o, polygon=GEAR, sew_index=1)]
        cfg = PipelineConfig(underlay=False, border_from_outline=False, **kw)
        blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg,
                             art_outlines=_art_outlines([b, o], cfg))
        return [r for blk in blocks for r in blk.runs]

    assert _md5(plan(**{FLAG: True})) == _md5(plan())
