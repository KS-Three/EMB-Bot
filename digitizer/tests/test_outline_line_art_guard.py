"""The line-art guard on `cfg.border_from_outline` (built OFF 2026-10-25).

`border_from_outline` (ON since 2026-10-24) read Bridge Bar's bowl-and-waves
drawing -- black hairlines, 0.8-1.0 mm, round yellow cells of the disc they
are drawn on -- as an outline, and sewed it the pro's way: one satin loop per
cell at 1.5 mm. The loops fan spikes at the cells' sharp tips and leave the
drawing's own stroke ends (the bowl's tips, the anchor's arms) to a rest-fill
that cannot hold a stroke under `machine.MIN_FILL_WIDTH_MM`, so they are
dropped and the garment shows. The pro's Bridge files carry no drawing at all
(his art was redrawn without it), so the guard is not his rule: it hands a
hairline drawing back to the engine as it was before the flag.

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
from digitizer_core.art_outline import find_art_outlines, line_art_reading
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import _art_outlines
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence

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

#: md5s of `_plan` captured on origin/main (82b0bf28) before the guard
#: existed: the bowl with `border_from_outline` ON (today's default) and OFF,
#: and the frame ON
BOWL_ON_MD5 = "4793dc521a2e217dce6b8a80a7e5cb2f"
BOWL_OFF_MD5 = "45170ee7d9d549b8f63569b826175f0c"
FRAME_ON_MD5 = "4fc6548342ef77b7fa8b928706962afe"


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _pair(outline, body):
    return [_region("Sbody", body, 0, 0), _region("Souter", outline, 1, 1)]


def _plan(outline, body, **cfg_kw):
    """The body (layer 0) then its outline (layer 1), both sewn."""
    b, o = _pair(outline, body)
    planned = [PlannedRegion(region=b, polygon=body, sew_index=0),
               PlannedRegion(region=o, polygon=outline, sew_index=1)]
    cfg = PipelineConfig(underlay=False, **cfg_kw)
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg,
                         art_outlines=_art_outlines([b, o], cfg))
    return [r for blk in blocks for r in blk.runs]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def test_flag_default_is_off_and_the_thresholds_are_the_census_gaps():
    assert PipelineConfig().border_from_outline_line_art_guard is False
    assert machine.OUTLINE_LINE_ART_FILL_SHARE == 0.5
    assert machine.OUTLINE_LINE_ART_DROP_FRAC == 0.02


def test_the_bowl_reads_as_line_art():
    b, o = _pair(BOWL, CELL)
    found = find_art_outlines([b, o])
    fill_share, dropped = line_art_reading(o, [(b, h) for _bid, h in found["Souter"]])
    assert fill_share < machine.OUTLINE_LINE_ART_FILL_SHARE
    assert dropped >= machine.OUTLINE_LINE_ART_DROP_FRAC


def test_a_hairline_ring_is_not_line_art():
    # Machine's frame: as thin as the bowl, but every bit of it rings its body
    b, o = _pair(FRAME, FIELD)
    found = find_art_outlines([b, o])
    fill_share, dropped = line_art_reading(o, [(b, h) for _bid, h in found["Souter"]])
    assert fill_share < machine.OUTLINE_LINE_ART_FILL_SHARE
    assert dropped == 0.0


def test_a_keyline_is_not_line_art():
    b, o = _pair(KEY, FACE)
    found = find_art_outlines([b, o])
    fill_share, _dropped = line_art_reading(o, [(b, h) for _bid, h in found["Souter"]])
    assert fill_share > 0.9


def test_guard_drops_the_drawing_and_keeps_the_frame_and_the_keyline():
    cfg = PipelineConfig(border_from_outline_line_art_guard=True)
    assert find_art_outlines(_pair(BOWL, CELL), cfg) == {}
    assert find_art_outlines(_pair(BOWL, CELL), line_art_guard=True) == {}
    assert find_art_outlines(_pair(BOWL, CELL))                    # guard off: an outline
    for outline, body in ((FRAME, FIELD), (KEY, FACE)):
        assert find_art_outlines(_pair(outline, body), cfg) == find_art_outlines(_pair(outline, body))


def test_guard_off_is_byte_identical_to_main():
    assert _md5(_plan(BOWL, CELL, border_from_outline=True)) == BOWL_ON_MD5
    assert _md5(_plan(BOWL, CELL, border_from_outline=True,
                      border_from_outline_line_art_guard=False)) == BOWL_ON_MD5
    assert _md5(_plan(FRAME, FIELD, border_from_outline=True)) == FRAME_ON_MD5


def test_guard_on_sews_the_drawing_as_the_engine_did_before_the_flag():
    on = _plan(BOWL, CELL, border_from_outline=True, border_from_outline_line_art_guard=True)
    assert _md5(on) == BOWL_OFF_MD5
    assert _md5(_plan(BOWL, CELL, border_from_outline=False)) == BOWL_OFF_MD5


def test_guard_on_leaves_a_ringed_frame_bordered():
    on = _plan(FRAME, FIELD, border_from_outline=True, border_from_outline_line_art_guard=True)
    assert _md5(on) == FRAME_ON_MD5


def test_guard_needs_the_outline_flag():
    # the guard narrows `border_from_outline`; on its own it changes nothing
    assert _md5(_plan(BOWL, CELL, border_from_outline=False,
                      border_from_outline_line_art_guard=True)) == BOWL_OFF_MD5
