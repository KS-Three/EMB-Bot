"""`cfg.outline_frame_guard` (built OFF 2026-11-14): an art outline is a thin
band round what it holds; a holder bigger than what it holds is a FIELD round
a knockout (`art_outline.FRAME_AREA_RATIO`).

Kent's `lt_k_line` at 80 mm (3 pins): the red box with a white K knocked out
of it passed `border_from_outline`'s band test (0.999 of it near the K) and
sewed as the K's art outline: a satin loop hugging the K, the box's corners
left to fill scraps at another angle. Holder area over hole area, measured on
the real designs: To a T's frame 0.05, MFab's keyline 0.67, Becker's 0.72;
the k_line box 1.90, Ahora's pink ground 2.10. ON, a field keeps its bodies
(plain fills, as before), gets no loop, and sews on the fill tier.
"""
from __future__ import annotations

from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, stitches
from digitizer_core.art_outline import FRAME_AREA_RATIO, find_art_outlines
from tests.test_border_from_outline import FACE, KEY, _md5, _plan, _region

#: a 38 x 20 mm box with the 30 x 12 mm face knocked out of it: every part
#: of it within 4 mm of the face (a band by the reach rule), but 400 mm2 of
#: box round a 360 mm2 face -- the k_line box, in rectangles
FIELD = Polygon(box(-19, -10, 19, 10).exterior, [FACE.exterior])


def test_default_is_on_and_the_line_is_one():
    # Kent 2026-11-15, review pack (review-1115): ticked ON
    assert PipelineConfig().outline_frame_guard is True
    assert FRAME_AREA_RATIO == 1.0


def test_a_field_round_a_knockout_is_tagged_and_keeps_its_body():
    b, o = _region("Sbody", FACE, 0, 0), _region("Souter", FIELD, 1, 1)
    off = find_art_outlines([b, o], PipelineConfig(outline_frame_guard=False))
    assert list(off) == ["Souter"] and "framed_field" not in o.meta
    on = find_art_outlines([b, o], PipelineConfig(outline_frame_guard=True))
    assert on == off                                     # its body is still its body
    assert o.meta["framed_field"] == round(FIELD.area / FACE.area, 2) == 1.11


def test_a_keyline_is_not_a_field():
    b, o = _region("Sbody", FACE, 0, 0), _region("Souter", KEY, 1, 1)
    find_art_outlines([b, o], PipelineConfig(outline_frame_guard=True))
    assert "framed_field" not in o.meta                  # 184 mm2 round 360: 0.51


def test_a_field_gets_no_loop_and_sews_as_a_fill():
    off = _plan(FIELD, FACE, outline_frame_guard=False)
    on = _plan(FIELD, FACE, outline_frame_guard=True)
    loops_off = [r for r in off if r.shape_id == "Souter" and r.kind == stitches.SATIN]
    assert loops_off                                     # the loop hugging the knockout
    assert not [r for r in on if r.shape_id == "Souter" and r.kind == stitches.SATIN]
    assert [r for r in on if r.shape_id == "Souter" and r.kind == stitches.FILL]
    # the knockout still sews as a plain fill, never satin
    assert not [r for r in on if r.shape_id == "Sbody" and r.kind == stitches.SATIN]
    assert [r for r in on if r.shape_id == "Sbody" and r.kind == stitches.FILL]


def test_a_keyline_plan_is_byte_identical_on():
    assert (_md5(_plan(KEY, FACE, outline_frame_guard=False))
            == _md5(_plan(KEY, FACE, outline_frame_guard=True)))
