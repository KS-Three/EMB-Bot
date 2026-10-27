"""`cfg.text_cluster_nest_guard` (2026-10-27, built OFF): a frame is not a footprint.

The text tagger drops a letter candidate whose bbox sits inside a larger candidate's
(`textcluster._drop_nested`: real letters in a row never nest, a rescued speck inside a
glyph is a fragment of it). The letter door admits any region up to `LETTER_MAX_HEIGHT_MM`
60 mm, so a design's FRAME passes it as a "glyph" and nests every letter inside away.
Measured on Bridge, one recorded digitize each (`docs/bridge-census-2026-10-27.md`,
memory `bridge-text-nested-2026-10-27`):

  hat   the black wheel, 62.6 x 55.1 mm, bbox holding the design, passes the door: 8 of the
        15 text pieces nested away, none reached the Column lane (2 folds against his 35).
        13.7x the pool's median candidate height (4.01 mm); the next tallest candidate 1.9x.
  LC    the wheel is 65.5 mm, refused at the door: nothing nests, 6 of 9 tag (20 folds).
        Its tallest candidate is 2.7x (median 4.68 mm).

ON: a candidate over `NEST_FOOTPRINT_MAX_X` (6.0) times the median height of the pool's
non-rescued candidates nests nothing. OFF: the engine as it was, byte for byte; the rescued
round and the house-angle group keep calling `_drop_nested` as they did.
"""
from __future__ import annotations

import hashlib
import inspect
import json

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize
from digitizer_core import textcluster as tc
from digitizer_core.regions import Region

from .conftest import FLAT_GOLDEN_MD5, TESTDATA, frozen_cfg


def _region(sid: str, poly, rescued: bool = False) -> Region:
    r = Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
               area_mm2=float(poly.area))
    if rescued:
        r.meta["rescued_small_shape"] = True
    return r


def _cand(sid: str, poly, rescued: bool = False) -> tc._Candidate:
    x0, y0, x1, y1 = poly.bounds
    return tc._Candidate(region=_region(sid, poly, rescued), height_mm=y1 - y0, width_mm=x1 - x0,
                         stroke_mean_mm=1.0, stroke_cv=0.2, cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0)


def _bar(x0: float, y0: float = 10.0, h: float = 6.0, t: float = 1.0):
    return box(x0, y0, x0 + t, y0 + h)


def _ring(w: float, h: float, t: float = 2.0):
    """A frame: an outline `t` thick, w x h, round the origin corner."""
    return box(0.0, 0.0, w, h).difference(box(t, t, w - t, h - t))


def _ids(cands) -> set[str]:
    return {c.region.shape_id for c in cands}


# --- the drop itself ----------------------------------------------------------------

def test_the_basis_numbers():
    assert tc.NEST_FOOTPRINT_MAX_X == 6.0
    # the empty band the constant sits in, measured on Bridge (hat wheel 13.7x, next 1.9x; LC tallest 2.7x)
    assert 2.7 < tc.NEST_FOOTPRINT_MAX_X < 13.7


def test_off_a_frame_nests_every_letter_inside_it_away():
    letters = [_cand(f"L{i}", _bar(10.0 + 3.0 * i)) for i in range(8)]
    frame = _cand("W", _ring(50.0, 40.0))
    kept = tc._drop_nested(letters + [frame])
    assert _ids(kept) == {"W"}                                  # the Bridge hat, in miniature


def test_on_the_frame_is_no_footprint_and_the_letters_stay():
    letters = [_cand(f"L{i}", _bar(10.0 + 3.0 * i)) for i in range(8)]
    frame = _cand("W", _ring(50.0, 40.0))
    kept = tc._drop_nested(letters + [frame], nest_guard=True)
    assert _ids(kept) == {f"L{i}" for i in range(8)} | {"W"}


def test_the_default_is_off():
    assert inspect.signature(tc._drop_nested).parameters["nest_guard"].default is False
    letters = [_cand(f"L{i}", _bar(10.0 + 3.0 * i)) for i in range(3)]
    frame = _cand("W", _ring(50.0, 40.0))
    assert _ids(tc._drop_nested(letters + [frame])) == _ids(tc._drop_nested(letters + [frame], False))


@pytest.mark.parametrize("frame_h, nests", [
    (23.0, True),      # 3.83x the 6 mm median: a big glyph's footprint, still nests (the guard is off its limit)
    (35.0, True),      # 5.83x
    (37.0, False),     # 6.17x: a frame
    (55.1, False),     # the hat's wheel
])
def test_the_six_times_line_on_the_median(frame_h, nests):
    letters = [_cand(f"L{i}", _bar(10.0 + 3.0 * i, y0=10.0, h=6.0)) for i in range(5)]
    frame = _cand("W", _ring(60.0, frame_h))
    kept = _ids(tc._drop_nested(letters + [frame], nest_guard=True))
    assert (kept == {"W"}) is nests


def test_the_median_ignores_rescued_fragments():
    """Six rescued 1 mm specks would drag a median over every candidate to 1 mm and turn every
    glyph into a frame; the median is of the non-rescued ones."""
    letters = [_cand(f"L{i}", _bar(10.0 + 3.0 * i)) for i in range(3)]
    specks = [_cand(f"s{i}", box(10.0 + 3.0 * i + 0.2, 12.0, 10.0 + 3.0 * i + 0.8, 13.0), rescued=True)
              for i in range(3)]
    kept = _ids(tc._drop_nested(letters + specks, nest_guard=True))
    # every speck still rides inside its glyph's footprint and is dropped, ON or OFF
    assert kept == {"L0", "L1", "L2"}
    assert kept == _ids(tc._drop_nested(letters + specks))


def test_a_glyph_sized_footprint_still_nests_a_fragment():
    glyph = _cand("G", box(0.0, 0.0, 4.0, 6.0))
    speck = _cand("s", box(1.0, 1.0, 2.0, 2.0), rescued=True)
    others = [_cand(f"L{i}", _bar(10.0 + 3.0 * i, y0=0.0)) for i in range(3)]
    for on in (False, True):
        assert _ids(tc._drop_nested([glyph, speck] + others, nest_guard=on)) == {"G", "L0", "L1", "L2"}


def test_no_non_rescued_candidate_means_no_frame():
    specks = [_cand("a", box(0.0, 0.0, 10.0, 30.0), rescued=True), _cand("b", box(1.0, 1.0, 2.0, 2.0), rescued=True)]
    assert _ids(tc._drop_nested(specks, nest_guard=True)) == _ids(tc._drop_nested(specks)) == {"a"}


# --- the tagger ---------------------------------------------------------------------

def _scene(frame_h: float = 40.0) -> list[Region]:
    """A frame round three bars of lettering (6 mm tall, three similar bars of one ink)."""
    w = 1.2 * frame_h                                           # aspect 1.2: the letter door admits it
    frame = _region("W", _ring(w, frame_h))
    bars = [_region(f"B{i}", _bar(0.3 * w + 3.0 * i, y0=(frame_h - 6.0) / 2.0)) for i in range(3)]
    return [frame] + bars


def _tags(regions):
    return {r.shape_id: r.meta.get("text_cluster_id") for r in regions}


def test_off_the_frame_swallows_the_line_and_nothing_is_tagged():
    regions = _scene()
    tc.detect_text_clusters(regions, None, wide_letters=True)
    assert all(v is None for v in _tags(regions).values())


@pytest.mark.parametrize("wide", [False, True])
def test_on_the_line_inside_the_frame_is_tagged(wide):
    regions = _scene()
    tc.detect_text_clusters(regions, None, wide_letters=wide, nest_guard=True)
    tags = _tags(regions)
    assert tags["B0"] is not None and tags["B0"] == tags["B1"] == tags["B2"]
    assert tags["W"] is None                                    # the frame is not a letter of the line


def test_on_a_scene_without_a_frame_is_unchanged():
    regions_off = [_region(f"B{i}", _bar(20.0 + 3.0 * i)) for i in range(3)]
    regions_on = [_region(f"B{i}", _bar(20.0 + 3.0 * i)) for i in range(3)]
    tc.detect_text_clusters(regions_off, None)
    tc.detect_text_clusters(regions_on, None, nest_guard=True)
    assert _tags(regions_off) == _tags(regions_on) and _tags(regions_on)["B0"] is not None


def test_on_a_small_frame_still_nests():
    """A 20 mm ring is 3.3x the bars: no guard line crossed, so the letters inside it stay swallowed as today."""
    regions = _scene(frame_h=20.0)
    tc.detect_text_clusters(regions, None, nest_guard=True)
    assert all(v is None for v in _tags(regions).values())


# --- wiring and OFF -----------------------------------------------------------------

def test_the_flag_is_off_and_the_pipeline_passes_nothing_when_off():
    assert PipelineConfig().text_cluster_nest_guard is False
    assert inspect.signature(tc.detect_text_clusters).parameters["nest_guard"].default is False
    from digitizer_core import pipeline
    src = inspect.getsource(pipeline)
    assert '**({"nest_guard": True} if cfg.text_cluster_nest_guard else {})' in src


def test_the_rescued_door_and_the_house_group_keep_todays_drop():
    assert "_drop_nested(raw)\n" in inspect.getsource(tc._candidates)
    assert "_drop_nested(raw)" in inspect.getsource(tc._lettering_groups)
    assert "nest_guard" not in inspect.getsource(tc._lettering_groups)


GOLDEN_MD5 = FLAT_GOLDEN_MD5


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("on", [False, True])
def test_goldens_are_byte_identical_off_and_on(fixture, on):
    """OFF is the engine as it was, on the frozen 2026-10-27 engine. ON too: the three flat
    goldens carry no frame candidate over six times their letters."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             frozen_cfg(target_width_mm=80.0, edge_cap="none", sew_enclosed_white=False,
                                        text_cluster_nest_guard=on))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
