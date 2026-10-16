"""`cfg.detail_spokes` (built OFF 2026-10-15): a small detail of another
colour, enclosed by one shape and too small for the run tier's outline, sews
as a spoked mark on top of the shape round it -- the way the professional
sewed the white star in Hotel Fremont's black Wisconsin (one white run of
five spokes, out and back from a common centre, after the black).

Pinned here: the tip finder on a synthetic star, cross, dot, square, pentagon
and triangle, and on the real star's mask at 80 mm; stage 3 keeps the star
only with the flag, tagged, while the host still takes its pixels; the
builder's run (spoke count, out-and-back, the floor, starts and ends at the
centre); the sew order after the host (a later block of the mark's thread,
else a block added); the whole pipeline on Fremont 80 mm (the mark sews white,
after the black, in the edge cap's block); and OFF is byte-identical -- the
three flat goldens and Fremont 80 mm, md5-pinned.
"""
from __future__ import annotations

import hashlib
import json
import math

import cv2
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, digitize, machine
from digitizer_core.detail_spokes import MIN_TIPS, TIP_DEPTH, find_tips, spoke_runs
from digitizer_core.regions import Region
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import _place_spoke_marks, _spoke_host
from digitizer_core.stitches import RUN, StitchBlock, StitchRun
from digitizer_core.threads import chart_for, rgb_to_lab
from digitizer_core.warnings_codes import DETAIL_SPOKES_SEWN

from .conftest import TESTDATA


def test_flag_defaults_off_and_the_floor_is_the_pros():
    """OFF, so neither `PRE_FLIP` nor `flagcost.FLAGS` lists it (both are
    for flags that default ON); the spoke floor is the pro's 1.45 mm."""
    from .conftest import PRE_FLIP
    assert PipelineConfig().detail_spokes is False
    assert "detail_spokes" not in PRE_FLIP
    assert machine.DETAIL_SPOKE_MIN_MM == 1.45
    assert machine.RUN_MIN_LOOP_MM == 2.2 and machine.RUN_MIN_AREA_MM2 == 0.16


# --- the tip finder ----------------------------------------------------------------

def _poly(points, size=40):
    m = np.zeros((size, size), np.uint8)
    cv2.fillPoly(m, [np.array(points, np.int32)], 1)
    return m.astype(bool)


def _star(n=5, ro=12.0, ri=None, c=(20, 20), rot=-90.0):
    ri = ro * 0.382 if ri is None else ri
    pts = []
    for k in range(2 * n):
        r = ro if k % 2 == 0 else ri
        a = math.radians(rot + 180.0 * k / n)
        pts.append((round(c[0] + r * math.cos(a)), round(c[1] + r * math.sin(a))))
    return _poly(pts)


def _cross(arm=12, w=3, c=(20, 20)):
    m = np.zeros((40, 40), bool)
    m[c[1] - w:c[1] + w + 1, c[0] - arm:c[0] + arm + 1] = True
    m[c[1] - arm:c[1] + arm + 1, c[0] - w:c[0] + w + 1] = True
    return m


def _disc(r=10, c=(20, 20)):
    m = np.zeros((40, 40), np.uint8)
    cv2.circle(m, c, r, 1, -1)
    return m.astype(bool)


def _ngon(n, r=12.0):
    return _poly([(round(20 + r * math.cos(math.radians(-90 + 360 * k / n))),
                   round(20 + r * math.sin(math.radians(-90 + 360 * k / n)))) for k in range(n)])


def _angles(res):
    (cx, cy), tips = res
    return [math.degrees(math.atan2(y - cy, x - cx)) for x, y in tips]


def _gaps(angles):
    a = sorted(angles)
    return [(b - q) % 360 for q, b in zip(a, a[1:] + [a[0] + 360])]


def test_a_five_point_star_reads_five_tips_72_degrees_apart():
    res = find_tips(_star())
    assert res is not None and len(res[1]) == 5
    assert all(abs(g - 72) < 8 for g in _gaps(_angles(res))), _gaps(_angles(res))
    assert max(abs(a - b) for a, b in zip(_angles(res), sorted(_angles(res)))) < 1e-9   # angular order


def test_a_cross_reads_four_tips_and_a_fat_arm_is_one_tip_at_its_middle():
    for w in (3, 5):
        res = find_tips(_cross(w=w))
        assert res is not None and len(res[1]) == 4, w
        assert sorted(round(a) for a in _angles(res)) == [-90, 0, 90, 180], w


def test_a_round_dot_a_square_and_a_pentagon_have_no_tips():
    """A square's corners stand 29% proud of its sides, under `TIP_DEPTH`."""
    assert TIP_DEPTH == 0.3
    assert 1 - math.cos(math.radians(45)) < TIP_DEPTH < 0.5
    for m in (_disc(), _disc(4), _ngon(4), _ngon(5), _disc(10) | _disc(6, (28, 20))):
        assert find_tips(m) is None


def test_a_triangle_is_the_smallest_spoked_mark_at_three_and_not_at_four():
    """`MIN_TIPS` 3 is the spec's; 4 is the other candidate (it refuses the
    corpus's one false positive, a three-tipped speck of tyre tread on the
    screenshot design, and keeps every star and cross)."""
    assert MIN_TIPS == 3
    res = find_tips(_ngon(3, 14))
    assert res is not None and len(res[1]) == 3
    assert find_tips(_ngon(3, 14), min_tips=4) is None
    assert len(find_tips(_star(), min_tips=4)[1]) == 5
    assert len(find_tips(_cross(), min_tips=4)[1]) == 4
    assert len(find_tips(_ascii(FREMONT_STAR_80), min_tips=4)[1]) == 5


# The star's own mask in the prep raster at 80 mm (31.25 px/mm): stage 3's
# region i=5, 196 px, 21 x 21, inside the black state (`tools/fremont_triage`
# at the Wisconsin ROI). Pinned so the reading does not depend on a 90 s run.
FREMONT_STAR_80 = """
..........#..........
.........###.........
.........###.........
........####.........
........#####........
........#####........
.......#######.......
......#########......
#####################
.###################.
..#################..
...###############...
....#############....
.....###########.....
.....###########.....
.....###########.....
....#############....
....#############....
....####.....####....
....###.......###....
...#.................
"""


def _ascii(art: str) -> np.ndarray:
    rows = [r for r in art.strip("\n").splitlines()]
    return np.array([[c == "#" for c in r] for r in rows], bool)


def test_fremonts_star_at_80mm_reads_five_tips():
    m = _ascii(FREMONT_STAR_80)
    assert m.sum() == 196
    res = find_tips(m)
    assert res is not None and len(res[1]) == 5
    gaps = _gaps(_angles(res))
    assert all(abs(g - 72) < 8 for g in gaps), gaps


# --- stage 3: the star kept and tagged, the host solid; a dot untouched -----------

PX = 30.0
FRAME = (120, 120)
RGB = np.array([(0, 0, 0), (255, 255, 255), (255, 255, 255)], float)


def _scene():
    """A black panel (layer 0) holding a white 5-point star of radius 11 px
    (0.37 mm, ~0.2 mm²: 2 x max(w, h) = 1.47 mm under the 2.2 loop floor,
    area over 0.16 mm²) and a white 20 px dot (0.33 mm² , 1.33 mm proxy)."""
    star = np.zeros(FRAME, bool)
    s = _star(ro=11.0, c=(20, 20))
    star[20:60, 20:60] = s
    dot = np.zeros(FRAME, bool)
    cv2.circle(dot.view(np.uint8), (85, 85), 10, 1, -1)
    panel = np.zeros(FRAME, bool)
    panel[5:115, 5:115] = True
    panel &= ~star & ~dot
    return [RegionMask.from_full(panel, 0), RegionMask.from_full(star, 1),
            RegionMask.from_full(dot, 2)]


def test_the_scene_is_what_its_docstring_says():
    regions = _scene()
    cfg = PipelineConfig()
    for r in regions[1:]:
        y0, x0, y1, x1 = r.bbox
        assert r.area < (cfg.min_detail_mm * PX) ** 2
        assert r.area >= machine.RUN_MIN_AREA_MM2 * PX ** 2
        assert 2 * max(y1 - y0, x1 - x0) < machine.RUN_MIN_LOOP_MM * PX


def _resolve(on: bool, **kw):
    regions = _scene()
    kept, warnings = resolve_small_regions(regions, PipelineConfig(detail_spokes=on), PX, **kw)
    return regions, kept, warnings


def test_stage3_keeps_the_star_only_on_tagged_with_its_host_solid():
    regions, off, _w = _resolve(False, layer_lab=rgb_to_lab(RGB))
    assert not any(k is regions[1] for k in off)
    assert regions[1].detail_spokes is None
    star_px = int(regions[1].crop.sum())
    regions, on, _w = _resolve(True, layer_lab=rgb_to_lab(RGB))
    star = next(k for k in on if k is regions[1])
    tag = star.detail_spokes
    assert tag is not None and tag["host_layer"] == 0 and len(tag["tips"]) == 5
    cx, cy = tag["centre"]
    assert abs(cx - 40) < 1.5 and abs(cy - 40) < 1.5          # frame coordinates
    # the host took the star's pixels: it sews solid under the mark
    panel = next(k for k in on if k is regions[0])
    assert panel.window(20, 20, 60, 60)[star.crop.shape[0] // 2, star.crop.shape[1] // 2]
    assert int(panel.window(20, 20, 60, 60).sum()) == 40 * 40
    assert star_px == int(star.crop.sum())                    # the mark keeps its own


def test_stage3_absorbs_the_dot_either_way():
    for on in (False, True):
        regions, kept, _w = _resolve(on, layer_lab=rgb_to_lab(RGB))
        assert not any(k is regions[2] for k in kept)


def test_stage3_needs_a_known_colour_and_another_colour():
    regions, kept, _w = _resolve(True)                           # no colours known
    assert not any(k is regions[1] for k in kept)
    same = np.array([(0, 0, 0), (0, 0, 0), (0, 0, 0)], float)    # the star is black too
    regions, kept, _w = _resolve(True, layer_lab=rgb_to_lab(same))
    assert not any(k is regions[1] for k in kept)
    # the raster's own colours serve where the layers' do not (the photo lane)
    lab = np.zeros((*FRAME, 3), np.float32)
    lab[..., 0] = 0.0
    for r in _scene()[1:]:
        lab[r.frame_slice()][r.crop] = (100.0, 0.0, 0.0)
    regions, kept, _w = _resolve(True, lab_img=lab)
    assert any(k is regions[1] for k in kept)


# --- the builder -----------------------------------------------------------------------

def test_the_run_is_one_run_out_and_back_per_tip_from_the_centre():
    c = (3.0, -2.0)
    tips = [(3.4, -2.0), (3.0, -1.6), (2.6, -2.0), (3.0, -2.4), (5.0, 0.0)]   # the last is 2.83 mm out
    runs, rep = spoke_runs(c, tips, "S1")
    assert not rep["empty"] and rep["spokes"] == 5 and len(runs) == 1
    r = runs[0]
    assert r.kind == RUN and r.shape_id == "S1"
    assert r.points[0] == c and r.points[-1] == c
    assert len(r.points) == 1 + 2 * 5
    for k in range(1, len(r.points), 2):
        assert r.points[k + 1] == c                              # back to the centre
        d = math.dist(c, r.points[k])
        assert d >= machine.DETAIL_SPOKE_MIN_MM - 1e-9
    lengths = sorted(round(math.dist(c, r.points[k]), 4) for k in range(1, len(r.points), 2))
    assert lengths == [1.45, 1.45, 1.45, 1.45, round(math.dist(c, (5.0, 0.0)), 4)]
    # each tip's direction is kept, in angular order
    angles = [math.atan2(r.points[k][1] - c[1], r.points[k][0] - c[0]) for k in range(1, len(r.points), 2)]
    assert angles == sorted(angles)
    assert abs(angles[-1] - math.atan2(0.4, 0.0)) < 1e-9 or abs(angles[0] - math.atan2(-2.4 + 2.0, 0.0)) < 1e-9


def test_the_floor_is_an_argument_and_a_tip_at_the_centre_is_no_spoke():
    runs, rep = spoke_runs((0.0, 0.0), [(0.2, 0.0), (0.0, 0.0), (0.0, 0.2), (-0.2, 0.0)], "S", min_mm=0.5)
    assert rep["spokes"] == 3 and len(runs[0].points) == 7
    assert all(abs(math.dist((0, 0), runs[0].points[k]) - 0.5) < 1e-9 for k in (1, 3, 5))
    runs, rep = spoke_runs((0.0, 0.0), [(0.0, 0.0)], "S")
    assert rep["empty"] and runs == []


# --- sew order: after the host ---------------------------------------------------------

def _region(sid, poly, t_index, chart, layer, meta=None):
    return Region(shape_id=sid, polygon=poly, thread_index=t_index,
                  thread_number=chart[t_index].number, area_mm2=float(poly.area),
                  meta={"layer": layer, **(meta or {})})


def _block(chart, t_index, sid, pts):
    return StitchBlock(thread_index=t_index, thread_number=chart[t_index].number,
                       rgb=tuple(chart[t_index].rgb),
                       runs=[StitchRun(points=list(pts), kind=RUN, shape_id=sid, jump=True, trim=True)])


def _mark_scene(trailing_white: bool):
    cfg = PipelineConfig()
    chart = chart_for(cfg)
    white, black, tan = 2, 4, 82
    ground = _region("Sg", Polygon([(-20, -20), (20, -20), (20, 20), (-20, 20)]), white, chart, 0)
    host = _region("Sh", Point(0, 0).buffer(5.0), black, chart, 1)
    other = _region("So", Polygon([(10, 10), (14, 10), (14, 14), (10, 14)]), tan, chart, 2)
    star = Point(0.5, 0.5).buffer(0.35)
    mark = _region("Sm", star, white, chart, 0,
                   {"rescued_small_shape": True,
                    "detail_spokes": {"centre": [0.5, 0.5], "host_layer": 1,
                                      "tips": [[0.5 + 0.35 * math.cos(math.radians(-90 + 72 * k)),
                                                0.5 + 0.35 * math.sin(math.radians(-90 + 72 * k))]
                                               for k in range(5)]}})
    planned = [PlannedRegion(region=ground, polygon=ground.polygon, sew_index=0),
               PlannedRegion(region=host, polygon=host.polygon, sew_index=1),
               PlannedRegion(region=other, polygon=other.polygon, sew_index=2)]
    pm = PlannedRegion(region=mark, polygon=mark.polygon, sew_index=1)
    blocks = [_block(chart, white, "Sg", [(-20, -20), (20, 20)]),
              _block(chart, black, "Sh", [(-5, 0), (5, 0)]),
              _block(chart, tan, "So", [(10, 10), (14, 14)])]
    if trailing_white:
        blocks.append(_block(chart, white, "__edge_cap__", [(-20, 20), (20, -20)]))
    return cfg, chart, planned, pm, blocks


def test_the_host_is_the_shape_of_another_thread_under_the_centre():
    _cfg, _chart, planned, pm, _blocks = _mark_scene(True)
    assert _spoke_host(pm, planned) is planned[1]
    assert _spoke_host(pm, planned[:1] + planned[2:]) is None   # the host deleted in review


def test_the_mark_joins_the_next_block_of_its_thread_after_the_host():
    cfg, chart, planned, pm, blocks = _mark_scene(True)
    before = [b.thread_index for b in blocks]
    rep = _place_spoke_marks([pm], planned, blocks, cfg, trim_at=3.0)
    assert rep == {"count": 1, "spokes": 5, "colour_changes": 0, "ids": ["Sm"]}
    assert [b.thread_index for b in blocks] == before                    # no block added
    cap = blocks[3]
    assert len(cap.runs) == 2 and cap.runs[1].shape_id == "Sm"
    run = cap.runs[1]
    assert run.jump and run.trim                                         # the cap ended 28 mm away
    assert run.points[0] == (0.5, 0.5) and run.points[-1] == (0.5, 0.5)  # tied in and off at the centre
    tie_leg = math.dist(run.points[0], run.points[1])
    assert 0 < tie_leg <= machine.TIE_STITCH_MM < machine.DETAIL_SPOKE_MIN_MM   # the lock lies inside a spoke
    assert sum(1 for q in run.points if q == (0.5, 0.5)) >= 6


def test_without_a_later_block_of_its_thread_the_mark_gets_one_after_the_host():
    cfg, chart, planned, pm, blocks = _mark_scene(False)
    rep = _place_spoke_marks([pm], planned, blocks, cfg, trim_at=3.0)
    assert rep["colour_changes"] == 1 and rep["count"] == 1
    assert [b.thread_index for b in blocks] == [2, 4, 2, 82]            # white, black, WHITE, tan
    added = blocks[2]
    assert added.thread_number == chart[2].number and len(added.runs) == 1
    assert added.runs[0].jump and added.runs[0].trim and added.runs[0].shape_id == "Sm"


def test_a_mark_whose_host_sewed_nothing_sews_last():
    cfg, chart, planned, pm, blocks = _mark_scene(False)
    blocks.pop(1)                                                        # the black sewed nothing
    rep = _place_spoke_marks([pm], planned, blocks, cfg, trim_at=3.0)
    assert rep["colour_changes"] == 1
    assert [b.thread_index for b in blocks] == [2, 82, 2]


# --- the whole pipeline: Fremont 80 mm, the Studio's Hat request ----------------------

# Today's main with the flag OFF (set explicitly): 14,824 stitches / 43 trims,
# the bean-holds-on cell of docs/renders/bean-holds-on/README.md. The stream's
# md5 is PER PLATFORM on this fixture (the goldens' lesson: numerics diverge
# per fixture, counts agree): Kent's Windows box reads `75f44f90`, CI's Linux
# `027d14e6` (PR #980, shard 5/6, same 14,824 / 43). A third platform fails
# here and gets its own pin, not a skip.
FREMONT_80_OFF_MD5 = {
    "win32": "75f44f905f946705695cf6365f2a8d5f",
    "linux": "027d14e68b7a7f91a0a9399077f67847",
}
STAR_MM = (1.28, -12.02)        # the star's centre, design mm, y down


def _stream_md5(plan) -> str:
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.fixture(scope="module")
def fremont_off():
    from tools import fremont_triage as ft
    return ft.run_arm("main", 80.0, None, preflight=False, overrides={"detail_spokes": False})


@pytest.fixture(scope="module")
def fremont_on():
    from tools import fremont_triage as ft
    return ft.run_arm("main", 80.0, None, preflight=False, overrides={"detail_spokes": True})


def test_fremont_80_off_is_byte_identical(fremont_off):
    import sys
    plan = fremont_off["plan"]
    assert (plan.stats.stitch_count, plan.stats.trims) == (14824, 43)
    assert _stream_md5(plan) == FREMONT_80_OFF_MD5[sys.platform]
    assert not [r for r in fremont_off["result"].regions if r.meta.get("detail_spokes")]
    assert not [w for w in plan.warnings if w["code"] == DETAIL_SPOKES_SEWN]


def test_fremont_80_on_sews_the_star_white_after_the_black(fremont_on, fremont_off):
    plan, result = fremont_on["plan"], fremont_on["result"]
    marks = [r for r in result.regions if r.meta.get("detail_spokes")]
    assert len(marks) == 1
    mark = marks[0]
    spec = mark.meta["detail_spokes"]
    assert mark.thread_number == "0015" and len(spec["tips"]) == 5          # white, five spokes
    assert math.dist(spec["centre"], STAR_MM) < 0.3
    assert mark.meta.get("rescued_small_shape") and 0.15 < mark.area_mm2 < 0.3
    # the black state still covers the star: solid underneath
    black = [r for r in result.regions if r.thread_number == "0020"
             and r.polygon.covers(Point(STAR_MM))]
    assert len(black) == 1 and not black[0].polygon.interiors
    # sewn once, in the trailing white block (the bean edge cap), after the black
    where = [(k, r) for k, b in enumerate(plan.blocks) for r in b.runs if r.shape_id == mark.shape_id]
    assert len(where) == 1
    k, run = where[0]
    assert plan.blocks[k].thread_number == "0015"
    assert any(r.shape_id == "__edge_cap__" for r in plan.blocks[k].runs)
    assert k > max(j for j, b in enumerate(plan.blocks) if b.thread_number == "0020")
    assert run.jump and run.trim and run.kind == RUN
    spokes = [q for q in run.points if math.dist(q, spec["centre"]) >= machine.DETAIL_SPOKE_MIN_MM - 1e-6]
    assert len(spokes) == 5
    assert len(plan.blocks) == len(fremont_off["plan"].blocks)              # no colour change added
    w = [w for w in plan.warnings if w["code"] == DETAIL_SPOKES_SEWN]
    assert len(w) == 1 and w[0]["count"] == 1 and w[0]["spokes"] == 5 and w[0]["colour_changes"] == 0
    assert w[0]["ids"] == [mark.shape_id]
    # every other shape sews exactly as OFF
    off_ids = {r.shape_id for r in fremont_off["result"].regions}
    assert {r.shape_id for r in result.regions} - off_ids == {mark.shape_id}

    def digests(run):
        return {r.shape_id: hashlib.md5(json.dumps([[round(x, 4), round(y, 4)] for x, y in r.points]).encode()).hexdigest()
                for b in run["plan"].blocks for r in b.runs if r.shape_id != mark.shape_id}
    assert digests(fremont_on) == digests(fremont_off)


# --- OFF is byte-identical on the flat goldens ----------------------------------------

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("flag", [False, True])
def test_goldens_are_byte_identical_either_way(fixture, flag):
    """OFF is the engine as it was. ON too, on these three: none holds a
    sub-floor detail of another colour with tips."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _stream_md5_coords(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            detail_spokes=flag))
    assert _stream_md5(plan) == GOLDEN_MD5[fixture]


def _stream_md5_coords(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()
