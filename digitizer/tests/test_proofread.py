"""The proof-read (`digitizer_core.proofread`) on synthetic jobs: art drawn as
a raster, the plan sewn by hand, so each fault is known before it is read.

Each fixture pairs one art picture with one hand-built plan; the art and the
plan share the pipeline's frame (mm = (px - art bbox centre) / px_per_mm, y
down). Fills are rows 0.3 mm apart, each its own jumped run, so nothing but
the fault differs from the art."""
from __future__ import annotations

from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import proofread as pr
from digitizer_core.stitches import FILL, StitchBlock, StitchPlan, StitchRun

ART_PXMM = 8.0
W_MM, H_MM = 60.0, 40.0
RED = (200, 30, 30)
BLACK = (20, 20, 20)
FABRIC = (235, 232, 223)


def _art(shapes: list[tuple[object, tuple[int, int, int]]]):
    """Paint shapely shapes (mm, plan frame) on a background the bg mask owns."""
    w, h = int(W_MM * ART_PXMM), int(H_MM * ART_PXMM)
    rgb = np.full((h, w, 3), 255, np.uint8)
    bg = np.ones((h, w), bool)

    def px(x, y):
        return [int(round(x * ART_PXMM + w / 2)), int(round(y * ART_PXMM + h / 2))]

    for geom, colour in shapes:
        for g in getattr(geom, "geoms", [geom]):
            m = np.zeros((h, w), np.uint8)
            cv2.fillPoly(m, [np.array([px(x, y) for x, y in g.exterior.coords], np.int32)], 1)
            for hole in g.interiors:
                cv2.fillPoly(m, [np.array([px(x, y) for x, y in hole.coords], np.int32)], 0)
            rgb[m.astype(bool)] = colour
            bg[m.astype(bool)] = False
    return SimpleNamespace(rgb=rgb, bg_mask=bg, art_bbox=(0, 0, w, h), px_per_mm=ART_PXMM)


def _fill_runs(geom, shape_id: str, spacing: float = 0.3) -> list[StitchRun]:
    x0, y0, x1, y1 = geom.bounds
    runs = []
    y = y0 + spacing / 2
    while y < y1:
        cut = geom.intersection(LineString([(x0 - 1, y), (x1 + 1, y)]))
        for seg in getattr(cut, "geoms", [cut]):
            if seg.is_empty or seg.length < 0.05:
                continue
            (ax, _), (bx, _) = seg.coords[0], seg.coords[-1]
            n = max(2, int(abs(bx - ax) / 2.5) + 2)
            pts = [(ax + (bx - ax) * t / (n - 1), y) for t in range(n)]
            runs.append(StitchRun(pts, FILL, jump=True, shape_id=shape_id))
        y += spacing
    return runs


def _plan(sewn: list[tuple[object, tuple[int, int, int], str]]) -> StitchPlan:
    blocks = []
    for geom, colour, sid in sewn:
        blocks.append(StitchBlock(0, "0000", colour, _fill_runs(geom, sid)))
    return StitchPlan(blocks=blocks, palette=[{} for _ in blocks])


def _read(art_shapes, sewn, regions=()):
    p = _art(art_shapes)
    plan = _plan(sewn)
    cfg = SimpleNamespace(garment_rgb=FABRIC)
    result = SimpleNamespace(regions=list(regions), warnings=[])
    return pr.read(p, result, plan, cfg, pull_mm=0.3)


def _kinds(rep, severity="error"):
    return sorted(f["kind"] for f in rep["findings"] if severity is None or f["severity"] == severity)


SQUARE = box(-8, -8, 8, 8)


def test_faithful_square_reads_clean():
    rep = _read([(SQUARE, RED)], [(SQUARE.buffer(0.3, join_style=2), RED, "S1")])
    assert rep["findings"] == [], rep["findings"]
    assert rep["tol_mm"] == pytest.approx(0.5)


def test_rows_a_filament_apart_read_solid():
    """Fill rows 0.45 mm apart leave one-pixel slits on the 10 px/mm grid; a
    faithful bar and its hole read clean, not thin and not closed."""
    holed = box(-8, -3, 8, 3).difference(box(-1.5, -1.5, 1.5, 1.5))
    p = _art([(holed, RED)])
    sewn = holed.buffer(0.3, join_style=2)
    plan = StitchPlan(blocks=[StitchBlock(0, "0000", RED, _fill_runs(sewn, "S1", spacing=0.45))], palette=[{}])
    rep = pr.read(p, SimpleNamespace(regions=[], warnings=[]), plan, SimpleNamespace(garment_rgb=FABRIC), pull_mm=0.3)
    assert rep["findings"] == [], rep["findings"]


def test_square_sewn_3mm_off_is_moved():
    rep = _read([(box(-4, -4, 4, 4), RED)], [(box(-4, -1, 4, 7), RED, "S1")])
    moved = [f for f in rep["findings"] if f["kind"] == "MOVED"]
    assert len(moved) == 1, rep["findings"]
    assert moved[0]["offset_mm"][1] == pytest.approx(3.0, abs=0.2)
    assert moved[0]["offset_mm"][0] == pytest.approx(0.0, abs=0.2)
    assert moved[0]["severity"] == "error"          # nothing in the meta explains it
    assert moved[0]["produced_by"][0]["shape_id"] == "S1"
    assert not [f for f in rep["findings"] if f["kind"] in ("MISSING", "EXTRA")]


def test_letter_moved_inside_a_joined_word_is_moved():
    """The re-set case: the middle letter is sewn 2 mm up and its thread
    touches both neighbours', so no 1:1 partner exists; the local shift
    search still names it moved, and its neighbours are not."""
    a, b, c = box(-7, -1.5, -4, 1.5), box(-1.5, -1.5, 1.5, 1.5), box(4, -1.5, 7, 1.5)
    word = unary_union([a.buffer(0.3, join_style=2), box(-1.5, -3.5, 1.5, -0.5).buffer(0.3, join_style=2),
                        c.buffer(0.3, join_style=2), box(-4.2, -1.0, 4.2, -0.4)])
    rep = _read([(a, RED), (b, RED), (c, RED)], [(word, RED, "W")])
    moved = [f for f in rep["findings"] if f["kind"] == "MOVED"]
    assert len(moved) == 1, rep["findings"]
    assert moved[0]["offset_mm"][1] == pytest.approx(-2.0, abs=0.25)
    assert abs(moved[0]["at_mm"][0]) < 1.0


def _gear(r_in=6.0, r_out=8.0, teeth=8):
    disc = Point(0, 0).buffer(r_in, 64)
    tooth = box(-1.0, 0, 1.0, r_out)
    from shapely import affinity
    parts = [disc] + [affinity.rotate(tooth, 360.0 * k / teeth, origin=(0, 0)) for k in range(teeth)]
    return unary_union(parts)


def test_gear_sewn_as_disc_loses_its_teeth():
    gear = _gear()
    rep = _read([(gear, BLACK)], [(Point(0, 0).buffer(6.3, 64), BLACK, "G")])
    teeth = [f for f in rep["findings"] if f["kind"] == "SHAPE" and f["side"] == "deficit"]
    assert len(teeth) == 8, rep["findings"]
    assert all(f["depth_mm"] >= 1.2 for f in teeth)


def test_gear_sewn_as_ring_reads_closed_or_lost():
    gear = _gear()
    ring = Point(0, 0).buffer(8.0, 64).difference(Point(0, 0).buffer(6.5, 64))
    rep = _read([(gear, BLACK)], [(ring, BLACK, "G")])
    lost = [f for f in rep["findings"] if f["kind"] == "SHAPE" and f["side"] == "deficit"]
    assert lost and max(f["area_mm2"] for f in lost) > 50, rep["findings"]


def test_two_squares_merged():
    a, b = box(-8, -4, -1, 4), box(1, -4, 8, 4)
    rep = _read([(a, RED), (b, RED)], [(box(-8.3, -4.3, 8.3, 4.3), RED, "M")])
    merged = [f for f in rep["findings"] if f["kind"] == "MERGED"]
    assert len(merged) == 1, rep["findings"]
    assert merged[0]["art_gap_half_mm"] == pytest.approx(1.0, abs=0.15)
    assert merged[0]["severity"] == "error"
    assert abs(merged[0]["at_mm"][0]) < 0.3


def test_narrow_gap_closed_by_pull_is_explained():
    a, b = box(-8, -4, -0.35, 4), box(0.35, -4, 8, 4)
    rep = _read([(a, RED), (b, RED)], [(box(-8.3, -4.3, 8.3, 4.3), RED, "M")])
    merged = [f for f in rep["findings"] if f["kind"] == "MERGED"]
    assert merged and all(f["explained_by"] == ["pull_comp"] for f in merged), rep["findings"]


def test_invented_border_is_extra():
    border = SQUARE.buffer(2.0, join_style=2).difference(SQUARE.buffer(0.2, join_style=2))
    rep = _read([(SQUARE, RED)], [(SQUARE.buffer(0.3, join_style=2), RED, "S1"), (border, BLACK, "B1")])
    extra = [f for f in rep["findings"] if f["kind"] == "EXTRA"]
    assert len(extra) == 1, rep["findings"]
    assert extra[0]["thread_rgb"] == list(BLACK)
    assert extra[0]["lies"] == "over_fabric"
    assert extra[0]["produced_by"][0]["shape_id"] == "B1"


def test_border_tag_explains_the_extra():
    from digitizer_core.regions import Region
    border = SQUARE.buffer(2.0, join_style=2).difference(SQUARE.buffer(0.2, join_style=2))
    reg = Region("B1", border, 0, "0000", border.area, meta={"border": True})
    rep = _read([(SQUARE, RED)], [(SQUARE.buffer(0.3, join_style=2), RED, "S1"), (border, BLACK, "B1")],
                regions=[reg])
    extra = [f for f in rep["findings"] if f["kind"] == "EXTRA"]
    assert extra and extra[0]["explained_by"] == ["border"] and extra[0]["severity"] == "misfire"


def test_hole_closed():
    holed = SQUARE.difference(box(-2, -2, 2, 2))
    rep = _read([(holed, RED)], [(SQUARE.buffer(0.3, join_style=2), RED, "S1")])
    closed = [f for f in rep["findings"] if f["kind"] == "CLOSED"]
    assert len(closed) == 1, rep["findings"]
    assert closed[0]["art_half_mm"] == pytest.approx(2.0, abs=0.15)
    assert closed[0]["severity"] == "error"
    assert abs(closed[0]["at_mm"][0]) < 0.5 and abs(closed[0]["at_mm"][1]) < 0.5


def test_missing_shape_of_a_sewn_colour():
    dot = box(-20, -3, -14, 3)
    rep = _read([(SQUARE, RED), (box(12, -3, 18, 3), BLACK), (dot, BLACK)],
                [(SQUARE.buffer(0.3, join_style=2), RED, "S1"), (dot.buffer(0.3, join_style=2), BLACK, "D")])
    missing = [f for f in rep["findings"] if f["kind"] == "MISSING"]
    assert len(missing) == 1 and missing[0]["thread_rgb"] == list(BLACK), rep["findings"]
    assert missing[0]["at_mm"][0] == pytest.approx(15.0, abs=0.3)


def test_missing_colour_no_thread_carries():
    rep = _read([(SQUARE, RED), (box(12, -3, 18, 3), BLACK)], [(SQUARE.buffer(0.3, join_style=2), RED, "S1")])
    missing = [f for f in rep["findings"] if f["kind"] == "MISSING"]
    assert len(missing) == 1 and missing[0]["colour"] == "no_thread_near", rep["findings"]


def test_thin_stroke_width():
    bar = box(-10, -1.0, 10, 1.0)                    # 2 mm drawn
    rep = _read([(bar, BLACK)], [(box(-10.3, -0.4, 10.3, 0.4), BLACK, "T")])
    width = [f for f in rep["findings"] if f["kind"] == "WIDTH"]
    assert len(width) == 1 and width[0]["which"] == "thin", rep["findings"]
    assert width[0]["art_width_mm"] == pytest.approx(2.0, abs=0.3)


def test_keyline_sewn_as_wide_satin_is_thick():
    keyline = SQUARE.buffer(0.2, join_style=2).difference(SQUARE.buffer(-0.2, join_style=2))   # 0.4 mm
    sewn = SQUARE.buffer(0.8, join_style=2).difference(SQUARE.buffer(-0.8, join_style=2))      # 1.6 mm
    rep = _read([(keyline, BLACK)], [(sewn, BLACK, "K")])
    width = [f for f in rep["findings"] if f["kind"] == "WIDTH"]
    assert len(width) == 1 and width[0]["which"] == "thick", rep["findings"]


# --- the flag and the report ----------------------------------------------------

TESTDATA = __import__("pathlib").Path(__file__).resolve().parents[1] / "testdata"
WIRE_ART = TESTDATA / "logo_whitebg.png"


def test_flag_is_off_by_default():
    from digitizer_core.config import PipelineConfig
    assert PipelineConfig().proofread is False


@pytest.fixture(scope="module")
def whitebg_job():
    from digitizer_core.config import PipelineConfig
    from digitizer_core.pipeline import digitize
    return digitize(WIRE_ART, PipelineConfig(target_width_mm=50.0, garment_id="left_chest"))


def test_off_never_reads_and_on_adds_only_metrics(whitebg_job, monkeypatch):
    import json
    from digitizer_core import preflight as pf
    from digitizer_core.config import PipelineConfig
    result, plan = whitebg_job

    def boom(*a, **k):
        raise AssertionError("proofread ran with the flag OFF")

    cfg = dict(target_width_mm=50.0, garment_id="left_chest")
    with monkeypatch.context() as m:
        m.setattr(pr, "read", boom)
        off = pf.run_preflight(result, plan, PipelineConfig(**cfg), image=WIRE_ART)
    on = pf.run_preflight(result, plan, PipelineConfig(proofread=True, **cfg), image=WIRE_ART)
    keys = {k for k in on["metrics"] if k.startswith("proofread")}
    assert not keys & set(off["metrics"])                     # OFF writes no key
    assert {"proofread", "proofread_checked", "proofread_unexplained", "proofread_misfires"} <= keys
    assert on["metrics"]["proofread_checked"] is True
    assert json.dumps(on["findings"], sort_keys=True) == json.dumps(off["findings"], sort_keys=True)
    assert (on["score"], on["grade"]) == (off["score"], off["grade"])
    assert {k: v for k, v in on["metrics"].items() if k not in keys} == off["metrics"]
    json.dumps(on, allow_nan=False)                           # the service's serialiser


def test_on_without_the_artwork_says_unchecked(whitebg_job):
    from digitizer_core import preflight as pf
    from digitizer_core.config import PipelineConfig
    result, plan = whitebg_job
    r = pf.run_preflight(result, plan, PipelineConfig(target_width_mm=50.0, proofread=True))
    assert r["metrics"]["proofread_checked"] is False and "proofread" not in r["metrics"]


def test_the_flag_leaves_a_flat_golden_plan_byte_identical():
    """The flag is read by preflight only: the plan cannot move. One of the
    flat-lane goldens, its md5 as `test_small_print.py` pins it."""
    import hashlib
    import json
    from digitizer_core.config import PipelineConfig
    from digitizer_core.pipeline import digitize
    from tests.conftest import FLAT_GOLDEN_MD5
    fixture = sorted(FLAT_GOLDEN_MD5)[0]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none", sew_enclosed_white=False,
                                            proofread=True))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert hashlib.md5(json.dumps(coords).encode()).hexdigest() == FLAT_GOLDEN_MD5[fixture]


def test_jumped_runs_are_drawn():
    """A run that starts with a jump sews from its first point: every fill
    row here is jumped, and the square reads covered."""
    p = _art([(SQUARE, RED)])
    plan = _plan([(SQUARE.buffer(0.3, join_style=2), RED, "S1")])
    assert all(r.jump for _b, r in plan.iter_runs())
    grid = pr.make_grid(plan, pr.art_mm_box(p.art_bbox, p.px_per_mm))
    top, runs = pr.thread_raster(plan, grid, [0])
    x0, y0 = grid.to_px(-7.5, -7.5)
    x1, y1 = grid.to_px(7.5, 7.5)
    assert (top[y0:y1, x0:x1] >= 0).mean() > 0.99
