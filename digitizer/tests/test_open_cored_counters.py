"""`cfg.open_cored_counters` -- a small counter with a page-coloured middle stays open.

MASTER_SCOPE 47's residue (2026-10-19): golden_tee's bevelled O at a 4 and 5 mm
cap. Its counter is a white core (stage 1's `enclosed_mask`) inside a dark keyline,
a grey bevel and two slivers, each under the area floor and under a thread wide.
`resolve_small_regions` gave every band to the O at 5 mm (0.00 open) and kept the
keyline as a ring stage 4 filled to a Silver disc at 4 mm (0.15 open). Built OFF.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from digitizer_core import PipelineConfig, digitize
from digitizer_core.stage3_segment import RegionMask, cored_counters, resolve_small_regions

from .conftest import TESTDATA

PX_PER_MM = 20.0         # floor (1.5 mm x 20)^2 = 900 px; thread 0.4 mm = 8 px
LAYER_LAB = np.array([[78.0, 11.0, 75.0],    # 0 the gold letter
                      [14.0, -7.0, -6.0],    # 1 the dark keyline
                      [77.0, 0.0, 0.0],      # 2 the grey bevel
                      [100.0, 0.0, 0.0],     # 3 the white core
                      [40.0, 0.0, 0.0]])     # 4 a dark detail


def _disc(shape, cy, cx, r):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r


def _o(letter_r=40, counter_r=16, keyline=2, bevel=2, core=True, stroke=None):
    """A gold O (outer radius `letter_r` px) on the page, its counter of radius
    `counter_r` ringed from outside in by a `keyline`-px dark band and a
    `bevel`-px grey band round a white core. -> (regions, core mask).
    `stroke` replaces the O's ring by a band that narrow (the letter itself
    under a thread wide). `core=False` paints the middle grey instead (no page
    colour in it)."""
    shape = (120, 120)
    c = 60
    outer = _disc(shape, c, c, letter_r)
    hole = _disc(shape, c, c, counter_r)
    if stroke is not None:
        outer = _disc(shape, c, c, counter_r + stroke)
    letter = outer & ~hole
    k = hole & ~_disc(shape, c, c, counter_r - keyline)
    b = _disc(shape, c, c, counter_r - keyline) & ~_disc(shape, c, c, counter_r - keyline - bevel)
    mid = _disc(shape, c, c, counter_r - keyline - bevel)
    regions = [RegionMask.from_full(letter, 0), RegionMask.from_full(k, 1),
               RegionMask.from_full(b, 2)]
    if core:
        regions.append(RegionMask.from_full(mid, 3))
        core_mask = mid
    else:
        regions[-1] = RegionMask.from_full(b | mid, 2)
        core_mask = np.zeros(shape, bool)
    return regions, core_mask


def _resolve(regions, core):
    # chain_rescue=False: the gradient lane's call, where golden_tee's bands
    # are lost (the bands and core here sum over the floor and would chain).
    return resolve_small_regions(regions, PipelineConfig(), PX_PER_MM, enclosed_mask=core,
                                 layer_lab=LAYER_LAB, chain_rescue=False, counter_core=core)[0]


def _letter_holes(kept) -> int:
    """Holes in the letter's mask (4-connected components of its complement
    that do not reach the frame's edge)."""
    import cv2
    letter = next(r for r in kept if r.layer == 0)
    full = letter.full_mask()
    pad = np.ones((full.shape[0] + 2, full.shape[1] + 2), np.uint8)
    pad[1:-1, 1:-1] = ~full
    n, lab = cv2.connectedComponents(pad, connectivity=4)
    return n - 2   # minus the page and the background label 0


def test_the_flag_ships_off():
    assert PipelineConfig().open_cored_counters is False


def test_the_scene_is_what_its_docstring_says():
    regions, core = _o()
    floor = (1.5 * PX_PER_MM) ** 2
    assert regions[0].area >= floor                         # the letter is full-size
    assert all(r.area < floor for r in regions[1:])          # every band is sub-floor
    assert core.sum() >= 0.16 * PX_PER_MM ** 2               # the core clears the run floor


def test_off_every_band_stays_in_a_shape_that_sews():
    """OFF, the contrasting bands clear the run floors and are rescued as
    shapes of their own (`keep_thin_strokes`, golden_tee's 4 mm path, where the
    keyline ring became a Silver disc), or are absorbed into the letter (its
    5 mm path). Either way no pixel of a band is left out as a counter."""
    regions, core = _o()
    bands = regions[1].full_mask() | regions[2].full_mask()
    kept = resolve_small_regions(regions, PipelineConfig(), PX_PER_MM, enclosed_mask=core,
                                 layer_lab=LAYER_LAB, chain_rescue=False)[0]
    assert not [r for r in kept if r.source == "counter"]
    sewn = np.zeros_like(bands)
    for r in kept:
        sewn |= r.full_mask()
    assert (bands & ~sewn).sum() == 0


def test_on_every_band_and_the_core_stay_out_of_the_letter():
    regions, core = _o()
    letter_area = regions[0].area
    kept = _resolve(regions, core)
    letter = next(r for r in kept if r.layer == 0)
    assert letter.area == letter_area                        # nothing absorbed
    assert sorted(r.layer for r in kept if r.source == "counter") == [1, 2]
    assert _letter_holes(kept) == 1


def test_cored_counters_names_the_bands_and_walks_past_a_band_encloser():
    regions, core = _o()
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    got = cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 0.4 * PX_PER_MM)
    # the keyline and the bevel (the core is the enclosed guard's already)
    assert {1, 2} <= got
    assert 0 not in got


def test_no_page_colour_in_the_middle_no_counter():
    """A dark detail inside a letter (no enclosed core) is absorbed as before."""
    regions, core = _o(core=False)
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 8.0) == set()
    kept = _resolve(regions, core)
    assert not [r for r in kept if r.source == "counter"]


def test_a_counter_at_or_over_the_floor_is_not_the_floors_to_close():
    regions, core = _o(letter_r=58, counter_r=30)
    floor = (1.5 * PX_PER_MM) ** 2
    assert np.pi * 30 ** 2 >= floor
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 8.0) == set()


def test_a_letter_narrower_than_a_thread_is_a_band_and_ends_the_walk_empty():
    """The innermost non-band shape round the core is the letter; when every
    shape round it is a band, nothing is a counter (the page is not a letter)."""
    regions, core = _o(stroke=3)
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, 0.16 * PX_PER_MM ** 2, 8.0) == set()


def test_a_core_under_the_run_floor_is_noise():
    regions, core = _o()
    floor = (1.5 * PX_PER_MM) ** 2
    small = [i for i, r in enumerate(regions) if r.area < floor]
    assert cored_counters(regions, small, core, floor, float(core.sum()) + 1, 8.0) == set()


# --- OFF is byte-identical on the flat goldens; ON leaves them alone too --------------

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("flag", [False, True])
def test_goldens_are_byte_identical_either_way(fixture, flag):
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            open_cored_counters=flag))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]


# --- #988's two conditions, built OFF behind the same flag (2026-10-19) ---------------
#
# (1) the satin tiers hold off a cored hole: the plain tier (`satin_shape`) and
#     the Column lane (`lettering_columns_shape`) take the shape's cored counters
#     and give THOSE holes the small-print floor's two holds;
# (2) the glyph guard (`pipeline.cored_counter_core`): a core is a counter only
#     inside a shape the taggers call lettering, read off a flag-OFF generation.

from types import SimpleNamespace  # noqa: E402

from shapely.geometry import LineString, Point, Polygon  # noqa: E402

from digitizer_core import pipeline as pipeline_mod, stitches  # noqa: E402
from digitizer_core.columns import counter_hold_polygon, lettering_columns_shape  # noqa: E402
from digitizer_core.stage6_satin import (_cut_runs_off_counters, _hold_off_counters,  # noqa: E402
                                         satin_shape, strip_splits)
from digitizer_core.stitches import StitchRun  # noqa: E402


def _square(cx, cy, half):
    return [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]


def _stream(runs):
    return [[round(x, 6), round(y, 6), r.kind, r.jump, r.trim] for r in runs for x, y in r.points]


def _over(runs, hole: Polygon, kinds=(stitches.SATIN,)) -> int:
    """Needle-down segments of `runs` of those kinds that pass over `hole`
    (shrunk a hair), the hop into a run that is not a jump included."""
    zone = hole.buffer(-stitches.SAME_POINT_MM)
    n = 0
    prev = None
    for r in runs:
        if r.kind in kinds:
            if prev is not None and not r.jump and LineString([prev, r.points[0]]).intersects(zone):
                n += 1
            n += sum(1 for a, b in zip(r.points, r.points[1:]) if LineString([a, b]).intersects(zone))
        prev = r.points[-1]
    return n


def test_the_hold_polygon_names_the_letters_own_ring_of_a_cored_hole_only():
    letter = Polygon(_square(0, 0, 3.0), [_square(-1.2, 0, 0.45), _square(1.2, 0, 0.45)])
    counter = Polygon(_square(-1.2, 0, 0.5))        # the counter region, traced a shade larger
    held = counter_hold_polygon(letter, [counter])
    assert len(held.interiors) == 1
    assert Polygon(held.interiors[0]).equals(Polygon(letter.interiors[0]))   # the letter's ring
    assert held.exterior.equals(letter.exterior)
    assert not counter_hold_polygon(letter, [Polygon(_square(5, 5, 0.5))]).interiors
    assert not counter_hold_polygon(letter, []).interiors


def test_the_column_lane_holds_the_cored_hole_and_sews_the_other_as_before():
    """A 4 mm square letter with two 0.8 mm holes; only the left one is a
    cored counter. The lane's crosses run over the left one with the flag
    off (five of them); with it named, none passes over it, every
    penetration is a half width off it, and the right hole is sewn as the
    lane sews it with the floor off. The floor ON holds both (its own
    reading)."""
    letter = Polygon(_square(0, 0, 2.0), [_square(-0.9, 0, 0.4), _square(0.9, 0, 0.4)])
    left, right = Polygon(letter.interiors[0]), Polygon(letter.interiors[1])
    kw = dict(trim_at_mm=3.0, pull_mm=0.3, pull_floor_mm=1.5)
    plain, _ = lettering_columns_shape(letter, "S1", **kw)
    flag, rep = lettering_columns_shape(letter, "S1", counter_clear_mm=0.2,
                                        counter_holes=[left.buffer(0.02)], **kw)
    floor, _ = lettering_columns_shape(letter, "S1", counter_clear_mm=0.2, **kw)
    assert not rep["empty"] and any(r.kind == stitches.SATIN for r in flag)
    assert _over(plain, left) > 0                                    # the premise: crossed OFF
    assert _over(flag, left, (stitches.SATIN, stitches.UNDERLAY, stitches.TRAVEL)) == 0
    assert _over(flag, right) == _over(plain, right)                 # the other hole: the lane's own
    # the columns on the right hole's side are the lane's own, point for point
    def right_side(runs):
        return [p for r in runs if r.kind == stitches.SATIN for p in r.points if p[0] > 0.5]
    assert right_side(flag) == right_side(plain)
    assert _over(floor, left) == 0 and _over(floor, right) == 0
    for r in flag:
        if r.kind == stitches.SATIN:
            assert all(Point(p).distance(left) >= 0.2 - 1e-6 for p in strip_splits(r.points))
    # named but with no clearance, or with nothing named: the call without it
    assert _stream(lettering_columns_shape(letter, "S1", counter_holes=[left], **kw)[0]) == _stream(plain)
    assert _stream(lettering_columns_shape(letter, "S1", counter_clear_mm=0.2, counter_holes=[],
                                           **kw)[0]) == _stream(floor)


def test_the_plain_tier_holds_the_cored_hole_its_skeleton_read_as_a_pinhole():
    """A 6 x 1.8 mm bar with a 0.7 mm hole: the skeleton reads the hole as
    a pinhole and a cross runs over it with the flag off. Held, no satin,
    underlay or travel stitch passes over the hole, and every rail
    penetration is a half width off it."""
    bar = Polygon([(-3, -0.9), (3, -0.9), (3, 0.9), (-3, 0.9)], [_square(0, 0, 0.35)])
    hole = Polygon(bar.interiors[0])
    kw = dict(underlay_style="zigzag", trim_at_mm=3.0)
    plain, _ = satin_shape(bar, "S1", **kw)
    flag, rep = satin_shape(bar, "S1", counter_holes=[hole.buffer(0.02)], counter_clear_mm=0.2, **kw)
    assert _over(plain, hole) > 0                                    # the premise: crossed OFF
    assert not rep["empty"] and any(r.kind == stitches.SATIN for r in flag)
    assert _over(flag, hole, (stitches.SATIN, stitches.UNDERLAY, stitches.TRAVEL)) == 0
    # every rail penetration is off the hole, and fewer sit within a half
    # width of it (a cross the hold would put under the cross floor keeps
    # its end where it is: the floor's own rule, `_clear_counters`)
    def rails(runs):
        return [p for r in runs if r.kind == stitches.SATIN for p in strip_splits(r.points)]
    assert not any(hole.covers(Point(p)) for p in rails(flag))
    near = [sum(1 for p in rails(x) if Point(p).distance(hole) < 0.2 - 1e-6) for x in (plain, flag)]
    assert near[1] < near[0], near
    # both sides of the hole still sew
    sewn = [p for r in flag if r.kind == stitches.SATIN for p in r.points]
    assert any(p[0] < -0.7 for p in sewn) and any(p[0] > 0.7 for p in sewn)
    # named with no clearance, or nothing named: the call without it
    assert _stream(satin_shape(bar, "S1", counter_holes=[hole], **kw)[0]) == _stream(plain)
    assert _stream(satin_shape(bar, "S1", counter_holes=[], counter_clear_mm=0.2, **kw)[0]) == _stream(plain)


def test_a_column_cut_at_a_counter_keeps_one_underlay_and_its_ends():
    held = Polygon(_square(0, 0, 3.0), [_square(0, 0, 0.45)])
    sts = [((x, -2.0), (x, 2.0)) for x in (-1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2)]
    pts = [p for a, b in sts for p in (a, b)]
    clear = [{"si": 0, "kind": stitches.SATIN, "pts": [(-2.5, -2.0), (-2.5, 2.0), (-2.1, -2.0), (-2.1, 2.0)],
              "free_start": True, "free_end": True}]
    assert _hold_off_counters(clear, held, 0.2, None)[0] is clear[0]
    kept = [{"si": 0, "kind": stitches.SATIN, "pts": pts, "free_start": True, "free_end": True}]
    out = _hold_off_counters(kept, held, 0.2, None)
    assert len(out) >= 2
    assert [k["underlay"] for k in out] == [True] + [False] * (len(out) - 1)
    assert [k["free_start"] for k in out] == [True] + [False] * (len(out) - 1)
    assert [k["free_end"] for k in out] == [False] * (len(out) - 1) + [True]
    hole = Polygon(held.interiors[0]).buffer(-stitches.SAME_POINT_MM)
    for k in out:
        rails = strip_splits(k["pts"])
        assert all(not LineString([a, b]).intersects(hole) for a, b in zip(rails, rails[1:]))
        assert all(Point(p).distance(hole) >= 0.2 - 1e-3 for p in rails)
    # a run of points that is not a plain zigzag is left as it is
    odd = [{"si": 0, "kind": stitches.SATIN, "pts": pts[:-1], "free_start": True, "free_end": True}]
    assert _hold_off_counters(odd, held, 0.2, None)[0] is odd[0]


def test_underlay_and_travel_are_cut_at_the_counter_and_columns_are_not():
    held = Polygon(_square(0, 0, 3.0), [_square(0, 0, 0.45)])
    under = StitchRun(points=[(-3.0, 0.0), (3.0, 0.0)], kind=stitches.UNDERLAY, shape_id="S1")
    column = StitchRun(points=[(-3.0, -1.0), (3.0, -1.0), (-3.0, 1.0)], kind=stitches.SATIN, shape_id="S1")
    short = StitchRun(points=[(-0.9, 0.0), (0.9, 0.0)], kind=stitches.TRAVEL, shape_id="S1")
    out = _cut_runs_off_counters([under, column, short], held, 0.2)
    assert [r.kind for r in out] == [stitches.UNDERLAY, stitches.UNDERLAY, stitches.SATIN]
    assert out[2] is column                      # the column is the hold's (`_hold_off_counters`)
    assert out[0].points[-1][0] == pytest.approx(-0.65) and out[1].points[0][0] == pytest.approx(0.65)
    clear = StitchRun(points=[(-3.0, 2.0), (3.0, 2.0)], kind=stitches.UNDERLAY, shape_id="S1")
    assert _cut_runs_off_counters([clear], held, 0.2)[0] is clear


def test_a_bean_cut_at_a_counter_keeps_every_pass_and_its_direction():
    """A three-pass bean (out, back, out) through the counter: cut stitch by
    stitch, each side keeps all three passes; differenced as one polyline
    GEOS deduplicated the overlapping passes to one (review, 2026-10-19)."""
    held = Polygon(_square(0, 0, 3.0), [_square(0, 0, 0.45)])
    bean = StitchRun(points=[(-3.0, 0.0), (3.0, 0.0), (-3.0, 0.0), (3.0, 0.0)],
                     kind=stitches.RUN, shape_id="S1")
    out = _cut_runs_off_counters([bean], held, 0.2)
    assert all(r.kind == stitches.RUN for r in out)
    length = sum(LineString(r.points).length for r in out)
    assert length == pytest.approx(3 * (6.0 - 1.3), abs=1e-6)          # every pass, less the hold
    assert all(abs(p[0]) >= 0.65 - 1e-9 for r in out for p in r.points)   # nothing inside the hold
    # direction is the run's own: the first piece starts where the bean did
    assert out[0].points[0] == (-3.0, 0.0)
    back = StitchRun(points=[(3.0, 0.0), (-3.0, 0.0)], kind=stitches.UNDERLAY, shape_id="S1")
    assert [r.points[0] for r in _cut_runs_off_counters([back], held, 0.2)] == [(3.0, 0.0), (-0.65, 0.0)]


# --- (2) the glyph guard ---------------------------------------------------------------

def _frame(cores):
    mask = np.zeros((100, 100), bool)
    for x, y, s in cores:
        mask[y:y + s, x:x + s] = True
    return mask


def _prep(mask):
    # 10 px/mm, the art box the whole frame: mm = (px - 50) / 10
    return SimpleNamespace(enclosed_mask=mask, px_per_mm=10.0, art_bbox=(0, 0, 100, 100))


def _ring_glyph():
    # a 5 mm square ring with a 0.5 mm band, px (0..50) less (5..45): thin
    # enough for `is_solid_blob` to pass it, and the core at px (0..5) lies
    # under its corner
    return Polygon(_square(-2.5, -2.5, 2.5), [_square(-2.5, -2.5, 2.0)])


def test_the_guard_keeps_a_core_under_a_glyph_and_drops_one_under_nothing(monkeypatch):
    mask = _frame([(0, 0, 5), (70, 70, 5)])        # 25 px each: over the run floor, under the area floor
    cfg = PipelineConfig(open_cored_counters=True)
    glyph = SimpleNamespace(polygon=_ring_glyph(), meta={"text_candidate": True}, shape_id="S1")
    calls = []

    def fake_build(image, cfg_off, segmenter, exif_source=None):
        calls.append(cfg_off)
        return SimpleNamespace(regions=[glyph], p=_prep(mask))
    monkeypatch.setattr(pipeline_mod, "build_generation", fake_build)
    keep = pipeline_mod.cored_counter_core("img", cfg, None, _prep(mask))
    assert len(calls) == 1 and calls[0].open_cored_counters is False     # asked of the flag-OFF generation
    assert keep is not None
    assert keep[0:5, 0:5].all() and not keep[70:75, 70:75].any()
    assert int(keep.sum()) == 25
    # the second core under a shape no tagger calls lettering (a solid ground
    # covering it), the glyph still there: the vote keeps the first alone
    ground = SimpleNamespace(polygon=Polygon(_square(2.25, 2.25, 1.0)), meta={}, shape_id="S2")
    monkeypatch.setattr(pipeline_mod, "build_generation",
                        lambda *a, **k: SimpleNamespace(regions=[ground, glyph], p=_prep(mask)))
    keep = pipeline_mod.cored_counter_core("img", cfg, None, _prep(mask))
    assert keep is not None and int(keep.sum()) == 25 and keep[0:5, 0:5].all()
    # under a shape no tagger calls lettering, and no glyph anywhere: None
    plain = SimpleNamespace(polygon=_ring_glyph(), meta={}, shape_id="S1")
    monkeypatch.setattr(pipeline_mod, "build_generation",
                        lambda *a, **k: SimpleNamespace(regions=[plain], p=_prep(mask)))
    assert pipeline_mod.cored_counter_core("img", cfg, None, _prep(mask)) is None


def test_the_guard_asks_nothing_when_no_core_is_a_candidate(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the pre-pass ran")
    monkeypatch.setattr(pipeline_mod, "build_generation", boom)
    cfg = PipelineConfig(open_cored_counters=True)
    assert pipeline_mod.cored_counter_core("img", cfg, None, _prep(_frame([]))) is None
    assert pipeline_mod.cored_counter_core("img", cfg, None, _prep(_frame([(10, 10, 3)]))) is None  # 9 px: noise
    assert pipeline_mod.cored_counter_core("img", cfg, None, _prep(_frame([(10, 10, 20)]))) is None  # 400 px: a hole
    assert pipeline_mod.cored_counter_core("img", cfg, None, SimpleNamespace(enclosed_mask=None)) is None


def test_a_kept_counter_is_marked_cored():
    regions, core = _o()
    kept = _resolve(regions, core)
    assert all(r.cored_counter for r in kept if r.source == "counter")
    assert not any(r.cored_counter for r in kept if r.source != "counter")
