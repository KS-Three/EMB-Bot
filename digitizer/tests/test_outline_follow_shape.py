"""`cfg.border_from_outline_follow_shape` (built OFF 2026-11-13, Kent on
Commons "Ahora": "now fix the Ahora gear so it sews as a gear").

`border_from_outline` sews an art outline as a satin loop of ONE width on the
body's edge. Ahora's white gear is a ring round a yellow disc with 17 teeth on
its outer edge, and at every size it sewed a ring of spokes: the loop never
looks at the outer edge. ON, a band that fits one satin everywhere and whose
thickness swings by at least the shortest stitch keeps the loop, but:

  * each cross is cut where it leaves the ART (long on a tooth, short in a
    root), not at one width;
  * the needle is locked to the teeth: every tooth gets the same whole number
    of stitches, none of them on the step between a tooth and a root;
  * the toothed edge itself is drawn by one bean, a needle point on every
    corner.

A band of one width (To-a-T's frame, which the pro widens) and a band too
thick to be a satin (Becker's drop shadow) are left exactly as they were.
"""
from __future__ import annotations

import hashlib
import math

import pytest
from shapely import affinity
from shapely.geometry import Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.art_outline import band_thickness, shaped_stations, shaped_width_mm
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import _art_outlines
from digitizer_core.regions import Region
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


def _plan(band, **cfg_kw):
    b, o = _region("Sbody", DISC, 0, 0), _region("Souter", band, 1, 1)
    planned = [PlannedRegion(region=b, polygon=DISC, sew_index=0),
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


def test_teeth_shorter_than_a_stitch_are_not_a_shape():
    """Ahora's gear at 40 mm swings 0.36 mm: thread cannot show it."""
    assert shaped_width_mm(_gear(r_tip=R_ROOT + 0.3), DISC) is None


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


# --- through stage 7 ----------------------------------------------------------

def test_off_the_gear_sews_a_ring_that_ignores_its_teeth():
    """Today's defect, pinned: the loop is one width, so its crosses reach
    the tips' radius in the roots as well. Hardly any stop at a root."""
    far = _far_radii(_plan(GEAR))
    assert far
    at_root = [r for r in far if abs(r - R_ROOT) < 0.25]
    assert len(at_root) < 0.15 * len(far)
    assert sorted(far)[len(far) // 2] > R_ROOT + 0.5


def test_on_the_gear_sews_long_on_a_tooth_and_short_in_a_root():
    far = _far_radii(_plan(GEAR, **{FLAG: True}))
    tips = [r for r in far if r > (R_ROOT + R_TIP) / 2.0]
    roots = [r for r in far if r <= (R_ROOT + R_TIP) / 2.0]
    assert tips and roots
    assert max(tips) == pytest.approx(R_TIP, abs=0.1) and min(tips) > R_TIP - 0.3
    assert max(roots) < R_ROOT + 0.25 and min(roots) > R_ROOT - 0.25


def test_on_the_toothed_edge_is_drawn_with_a_needle_on_every_corner():
    runs = _plan(GEAR, **{FLAG: True})
    edge = [r for r in runs if r.shape_id == "Souter" and r.kind == stitches.RUN]
    assert len(edge) == 1
    holes = {tuple(p) for p in edge[0].points}
    assert tuple(edge[0].points[0]) == tuple(edge[0].points[-1])          # closed on its first hole
    half = math.pi * R_ROOT / TEETH / 2.0
    for k in range(TEETH):
        for corner in ((-half, R_TIP), (half, R_TIP)):                     # each tooth's two tip corners
            c = affinity.rotate(Point(corner), 360.0 * k / TEETH, origin=(0, 0))
            assert min(math.dist((c.x, c.y), h) for h in holes) < 0.02


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
