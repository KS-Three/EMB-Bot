"""The line-art guard on the border-from-outline rule (#1078; ON since
2026-10-25, Kent's flip -- `PRE_FLIP` names the OFF arm).

The rule (ON since 2026-10-24, folded into the engine) read Bridge Bar's bowl-and-waves
drawing -- black hairlines, 0.8-1.0 mm, round yellow cells of the disc they
are drawn on -- as an outline, and sewed it the pro's way: one satin loop per
cell at 1.5 mm. The loops fan spikes at the cells' sharp tips and leave the
drawing's own stroke ends (the bowl's tips, the anchor's arms) to a rest-fill
that cannot hold a stroke under `machine.MIN_FILL_WIDTH_MM`, so they are
dropped and the garment shows. The pro's Bridge files carry no drawing at all
(his art was redrawn without it), so the guard is not his rule: it hands a
hairline drawing back to the engine as it was before the rule.

The guard reads two things, and needs BOTH: the outline is a hairline (under
`machine.OUTLINE_LINE_ART_FILL_SHARE` of it is a fill floor across) and its
loops leave strokes (at least `machine.OUTLINE_LINE_ART_DROP_FRAC` of it lies
beyond every loop and is too thin to fill). A hairline that is a pure ring --
To-a-T Machine's 0.8 mm hexagon frame, which the pro widens to a 2.0-2.3 mm
border -- stays an outline; so does every keyline the census reads (Becker,
MFab, Drone: a fill floor across over 0.74 of them).
"""
from __future__ import annotations

import hashlib

from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.art_outline import find_art_outlines, line_art_reading, outline_width_mm
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import _art_outlines
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence
from tests.conftest import FLAG_ENDS_SEAM_2026_11_17_OFF, FLIP_2026_10_23

#: Bridge's bowl, roughly: a 16 x 6 mm cell inside a 0.9 mm hairline, the
#: drawing's two tips and one wave stroke running on past it
CELL = box(-8, -3, 8, 3)
_STROKES = [LineString([(-8.6, 3.6), (-11.0, 7.0)]), LineString([(8.6, 3.6), (11.0, 7.0)]),
            LineString([(8.6, 0.0), (12.5, 1.0)])]
BOWL = unary_union([CELL.buffer(0.9, join_style=2).difference(CELL)]
                   + [s.buffer(0.45, cap_style=2) for s in _STROKES])
#: To-a-T Machine's frame, roughly: a 0.8 mm hairline ring round a white field
FIELD = box(-20, -15, 20, 15)
FRAME = FIELD.buffer(0.8, join_style=2).difference(FIELD)
#: a 2 mm keyline round a 30 x 12 mm face (BECKER's E)
FACE = box(-15, -6, 15, 6)
KEY = FACE.buffer(2.0, join_style=2).difference(FACE)

# The md5s of `_plan` captured on origin/main (82b0bf28) before the guard existed (the bowl with
# the outline rule ON and OFF, the frame ON) pinned an engine without `tie_in_off`,
# `fill_turn_slant` and `fill_underlay_cross`; since 2026-11-20 (flag fold B5) the same three arms
# are computed in-process: the bowl with no outlines handed to the sequencer (the rule off, which
# is no longer a switch: B4 folded `border_from_outline`), the bowl and the frame with the guard OFF
# (no longer a switch either: the guard is unconditional, so the unguarded arm reads the art's
# outlines through `find_art_outlines(..., line_art_guard=False)`).
def _bowl_off():
    return _md5(_plan(BOWL, CELL, outlines=False))


def _bowl_on_unguarded():
    return _md5(_plan(BOWL, CELL, guard=False))


def _frame_on_unguarded():
    return _md5(_plan(FRAME, FIELD, guard=False))


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _pair(outline, body):
    return [_region("Sbody", body, 0, 0), _region("Souter", outline, 1, 1)]


def _unguarded_outlines(regions, cfg):
    """`pipeline._art_outlines` with the line-art guard off."""
    by_id = {r.shape_id: r for r in regions}
    out = {}
    for oid, bodies in find_art_outlines(regions, cfg, line_art_guard=False).items():
        width = outline_width_mm(by_id[oid], [(by_id[bid], hole) for bid, hole in bodies])
        out[oid] = [(bid, hole, width) for bid, hole in bodies]
    return out or None


def _plan(outline, body, *, outlines=True, guard=True, **cfg_kw):
    """The body (layer 0) then its outline (layer 1), both sewn. `outlines=False`
    hands the sequencer no art outlines: the engine without the outline rule.
    `guard=False` reads them with the line-art guard off."""
    b, o = _pair(outline, body)
    planned = [PlannedRegion(region=b, polygon=body, sew_index=0),
               PlannedRegion(region=o, polygon=outline, sew_index=1)]
    # the md5s predate the 2026-10-23 flips (conftest): pinned off
    cfg = PipelineConfig(underlay=False, **{**FLIP_2026_10_23, **FLAG_ENDS_SEAM_2026_11_17_OFF, **cfg_kw})
    read = _art_outlines if guard else _unguarded_outlines
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg,
                         art_outlines=read([b, o], cfg) if outlines else None)
    return [r for blk in blocks for r in blk.runs]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def test_the_thresholds_are_the_census_gaps():
    # the guard is always on (Kent's flip 2026-10-25, folded into the code 2026-11-19)
    assert machine.OUTLINE_LINE_ART_FILL_SHARE == 0.5
    assert machine.OUTLINE_LINE_ART_DROP_FRAC == 0.02


def test_the_bowl_reads_as_line_art():
    b, o = _pair(BOWL, CELL)
    found = find_art_outlines([b, o], line_art_guard=False)
    fill_share, dropped = line_art_reading(o, [(b, h) for _bid, h in found["Souter"]])
    assert fill_share < machine.OUTLINE_LINE_ART_FILL_SHARE
    assert dropped >= machine.OUTLINE_LINE_ART_DROP_FRAC


def test_a_hairline_ring_is_not_line_art():
    # Machine's frame: as thin as the bowl, but every bit of it rings its body
    b, o = _pair(FRAME, FIELD)
    found = find_art_outlines([b, o], line_art_guard=False)
    fill_share, dropped = line_art_reading(o, [(b, h) for _bid, h in found["Souter"]])
    assert fill_share < machine.OUTLINE_LINE_ART_FILL_SHARE
    assert dropped == 0.0


def test_a_keyline_is_not_line_art():
    b, o = _pair(KEY, FACE)
    found = find_art_outlines([b, o], line_art_guard=False)
    fill_share, _dropped = line_art_reading(o, [(b, h) for _bid, h in found["Souter"]])
    assert fill_share > 0.9


def test_guard_drops_the_drawing_and_keeps_the_frame_and_the_keyline():
    cfg = PipelineConfig()
    assert find_art_outlines(_pair(BOWL, CELL), cfg) == {}
    assert find_art_outlines(_pair(BOWL, CELL), line_art_guard=True) == {}
    assert find_art_outlines(_pair(BOWL, CELL), line_art_guard=False)   # guard off: an outline
    for outline, body in ((FRAME, FIELD), (KEY, FACE)):
        assert find_art_outlines(_pair(outline, body), cfg) == find_art_outlines(
            _pair(outline, body), line_art_guard=False)


def test_guard_off_rings_the_bowl():
    assert _bowl_on_unguarded() != _bowl_off()


def test_the_default_sews_the_drawing_as_before_border_from_outline():
    # ON by default: the bowl is the bytes without the rule, the frame keeps its border
    assert _md5(_plan(BOWL, CELL)) == _bowl_off()
    assert _md5(_plan(FRAME, FIELD)) == _frame_on_unguarded()


def test_guard_on_sews_the_drawing_as_the_engine_did_before_the_flag():
    on = _plan(BOWL, CELL)
    assert _md5(on) == _bowl_off()


def test_guard_on_leaves_a_ringed_frame_bordered():
    on = _plan(FRAME, FIELD)
    assert _md5(on) == _frame_on_unguarded()
