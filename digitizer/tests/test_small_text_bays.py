"""Keep each bay's mouth open (`cfg.extra["small_text_bay_mouth"]`, W3-02,
2026-10-25, built OFF; `small_text._open_mouths`).

The re-set (`small_text_cap_letter_gap_mm`) grows Fremont's EST 1895 to the
pro's ~4 mm in bold satin, and the widening sews three bays shut: the 5's
bowl tail meets its stem, the S's terminals meet the spine, the E's arm
serifs meet the middle arm -- "BST 1893". Widening the letter does not
open them (to 1.5x, the 5's bowl stays shut: each gap is vertical). The
professional ends the terminal short instead: every E/S/5 mouth of his on
four jobs is open, 0.50 mm visible at the median (`tools/bay_census.py`).
The switch cuts back the terminal that shuts a mouth, along its own stroke,
until the mouth holds that.

The synthetic scene: a ~2 mm line of four glyphs drawn as Fremont's are --
E with arm serifs, S and 5 whose terminals curl to 0.3 mm of their own
stroke, an 8 with two true counters -- on a white raster, one solid polygon
per glyph as the tracer hands them over.
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.regions import Region  # noqa: E402
from digitizer_core.small_text import enlarge_small_text  # noqa: E402
from digitizer_core.stage1_prep import Prep  # noqa: E402

PPM = 24.0
W, H = 960, 480                    # 40 x 20 mm
INK, GROUND = (170, 150, 120), (255, 255, 255)
STROKE = 0.3                       # Fremont's date: 0.27-0.30 mm strokes on a 1.9 mm cap
# the re-set as #1057 sets it (`small_text_cap_max_width_scale` is not read by it)
KW = dict(cap_mm=4.0, min_stroke_mm=0.85, letter_gap_mm=0.25, bold_scale=1.45)


def _arc(cx, cy, r_out, r_in, a0, a1, n=48):
    """An annulus sector, angles in degrees, y down (90 is straight down)."""
    ts = np.radians(np.linspace(a0, a1, n))
    outer = [(cx + r_out * math.cos(t), cy + r_out * math.sin(t)) for t in ts]
    inner = [(cx + r_in * math.cos(t), cy + r_in * math.sin(t)) for t in ts[::-1]]
    return Polygon(outer + inner).buffer(0)


def _e(x0, y0):
    """An E with arm serifs reaching 0.3 mm toward the middle arm."""
    t = STROKE
    parts = [box(x0, y0, x0 + t, y0 + 2.0),                       # stem
             box(x0, y0, x0 + 1.2, y0 + t),                       # top arm
             box(x0, y0 + 0.85, x0 + 0.95, y0 + 0.85 + t),        # middle arm
             box(x0, y0 + 2.0 - t, x0 + 1.2, y0 + 2.0),           # bottom arm
             box(x0 + 1.2 - t, y0, x0 + 1.2, y0 + 0.55),          # top serif, down
             box(x0 + 1.2 - t, y0 + 2.0 - 0.55, x0 + 1.2, y0 + 2.0)]   # bottom serif, up
    return unary_union(parts)


def _s(x0, y0):
    """An S whose terminals curl back to 0.3 mm of the spine."""
    t, r = STROKE, 0.55
    cx = x0 + 0.6
    top = _arc(cx, y0 + r, r, r - t, 90, 380)          # left, over the top, to the right
    bot = _arc(cx, y0 + 2.0 - r, r, r - t, 270, 560)   # right, under the bottom, to the left
    return unary_union([top, bot]).buffer(0)


def _five(x0, y0):
    """A 5: bar, stem, and a bowl whose tail curls up to 0.3 mm of the stem."""
    t, r = STROKE, 0.62
    cx, cy = x0 + 0.62, y0 + 2.0 - r
    bowl = _arc(cx, cy, r, r - t, 205, 505)            # from the stem, round, back up the left
    return unary_union([box(x0 + 0.05, y0, x0 + 1.25, y0 + t),
                        box(x0 + 0.05, y0, x0 + 0.05 + t, y0 + 0.95), bowl]).buffer(0)


def _eight(x0, y0):
    t = STROKE
    return unary_union([Point(x0 + 0.6, y0 + 0.5).buffer(0.5).difference(Point(x0 + 0.6, y0 + 0.5).buffer(0.5 - t)),
                        Point(x0 + 0.6, y0 + 1.42).buffer(0.58).difference(
                            Point(x0 + 0.6, y0 + 1.42).buffer(0.58 - t))]).buffer(0)


GLYPHS = (("E", _e), ("S", _s), ("5", _five), ("8", _eight))


def _px(poly):
    return np.round(np.asarray(poly.exterior.coords) * PPM + (W / 2, H / 2)).astype(np.int32)


def scene():
    """The raster (ink drawn from the polygons, counters and all) and the
    regions a tracer that drops small counters hands over."""
    img = np.full((H, W, 3), GROUND, np.uint8)
    regions = [Region("Sbase", box(-20, -10, 20, 10), 1, "1", 800.0)]
    x = -4.0
    for i, (name, make) in enumerate(GLYPHS):
        g = make(x, -1.0)
        mask = np.zeros((H, W), np.uint8)
        cv2.fillPoly(mask, [_px(g)], 255)
        for ring in g.interiors:
            cv2.fillPoly(mask, [np.round(np.asarray(ring.coords) * PPM + (W / 2, H / 2)).astype(np.int32)], 0)
        img[mask > 0] = INK
        solid = Polygon(g.exterior)
        regions.append(Region(f"Sg{i}", solid, 7, "7", float(solid.area),
                              meta={"rescued_small_shape": True, "text_candidate": True,
                                    "text_cluster_id": "TCbays", "text_cluster_stroke_mm": STROKE / 2.0,
                                    "text_cluster_all_rescued": True, "glyph": name}))
        x += g.bounds[2] - g.bounds[0] + 0.45
    p = Prep(rgb=img, bg_mask=np.zeros((H, W), bool), px_per_mm=PPM, art_bbox=(0, 0, W, H))
    return regions, p


def md5(regions, rep) -> str:
    h = hashlib.md5()
    for r in regions:
        h.update(repr((r.shape_id, r.thread_index, r.polygon.wkb.hex(), sorted(r.meta.items()))).encode())
    h.update(repr(rep).encode())
    return h.hexdigest()


def glyphs(regions):
    return {r.meta["glyph"]: r for r in regions if r.shape_id.startswith("Sg")}


#: md5 of `scene()` re-set WITHOUT the switch -- regions and report --
#: captured on main's engine (c531c7b8), before this switch existed.
OFF_MD5 = "13e6ef069ae0510d191ae73bb720fdce"
LETTERS = Path(__file__).resolve().parents[1] / "testdata" / "bay_mouth_letters.json"
ZIP = Path(__file__).resolve().parents[2] / "Embroidery Files.zip"


def _sewn_mouths(poly, widen, ppm=20.0):
    """The census's reading of a letter's sewn extent (widened, then
    `SEWN_EDGE_MM` out) on the 20 px/mm grid machine files are read on."""
    from digitizer_core import small_text as st
    g = st._widen_keep_counters(poly, widen).buffer(st.SEWN_EDGE_MM)
    x0, y0, x1, y1 = g.bounds
    m = np.zeros((int((y1 - y0 + 2) * ppm), int((x1 - x0 + 2) * ppm)), np.uint8)
    for q in st._polys(g):
        cv2.fillPoly(m, [np.round((np.asarray(q.exterior.coords) - (x0 - 1, y0 - 1)) * ppm).astype(np.int32)], 1)
        for ring in q.interiors:
            cv2.fillPoly(m, [np.round((np.asarray(ring.coords) - (x0 - 1, y0 - 1)) * ppm).astype(np.int32)], 0)
    return [row["mouth_mm"] for row in st.bay_mouths(m > 0, ppm)], g.bounds


def _letters():
    import json
    from shapely import wkt
    doc = json.loads(LETTERS.read_text())
    return {d["char"]: (wkt.loads(d["wkt"]), d["widen_mm"]) for d in doc["letters"]}


# --- OFF -------------------------------------------------------------------------

def test_off_is_byte_identical_to_main():
    a, p = scene()
    rep_a = enlarge_small_text(a, p, **KW)
    b, p = scene()
    rep_b = enlarge_small_text(b, p, **KW, bay_mouth=False)
    assert md5(a, rep_a) == md5(b, rep_b) == OFF_MD5


def test_off_never_reaches_the_mouth_code(monkeypatch):
    from digitizer_core import small_text

    def boom(*_a, **_k):
        raise AssertionError("bay mouth code reached with the switch off")
    monkeypatch.setattr(small_text, "_open_mouths", boom)
    regions, p = scene()
    enlarge_small_text(regions, p, **KW)


def test_off_the_re_set_shuts_the_bays():
    # the defect, on the synthetic line: E's two mouths and the S's sewn shut
    regions, p = scene()
    enlarge_small_text(regions, p, **KW)
    g = glyphs(regions)
    for name in ("E", "S"):
        mouths, _b = _sewn_mouths(g[name].polygon, 0.0)
        assert mouths.count(0.0) >= 2, (name, mouths)


# --- the reader ------------------------------------------------------------------

def test_reader_reads_a_mouth_a_counter_and_no_bay():
    from digitizer_core.small_text import bay_mouths
    ppm = 20.0
    ring = Point(0, 0).buffer(1.2).difference(Point(0, 0).buffer(0.7))

    def mask(g):
        x0, y0, x1, y1 = g.bounds
        m = np.zeros((int((y1 - y0 + 2) * ppm), int((x1 - x0 + 2) * ppm)), np.uint8)
        for q in ([g] if g.geom_type == "Polygon" else list(g.geoms)):
            cv2.fillPoly(m, [np.round((np.asarray(q.exterior.coords) - (x0 - 1, y0 - 1)) * ppm).astype(np.int32)], 1)
            for r in q.interiors:
                cv2.fillPoly(m, [np.round((np.asarray(r.coords) - (x0 - 1, y0 - 1)) * ppm).astype(np.int32)], 0)
        return m > 0
    o = bay_mouths(mask(ring), ppm)
    assert [r["mouth_mm"] for r in o] == [0.0] and o[0]["width_mm"] >= 1.3      # a counter: enclosed
    c = bay_mouths(mask(ring.difference(box(0.0, -0.25, 2.0, 0.25))), ppm)    # a C, 0.5 mm mouth
    assert len(c) == 1 and abs(c[0]["mouth_mm"] - 0.5) <= 0.1 and c[0]["width_mm"] > c[0]["mouth_mm"]
    assert bay_mouths(mask(box(0, 0, 2, 3)), ppm) == []                       # no bay at all


# --- ON, Fremont's own letters ---------------------------------------------------

def test_on_fremont_e_s_5_open_within_the_pros_range():
    from digitizer_core import small_text as st
    for ch, (poly, widen) in _letters().items():
        if ch not in "ES5":
            continue
        off, b0 = _sewn_mouths(poly, widen)
        assert 0.0 in off, (ch, off)                                          # shut OFF
        cut, rows = st._open_mouths(poly, widen)
        assert rows and all("opened_mm" in r for r in rows), (ch, rows)
        on, b1 = _sewn_mouths(cut, widen)
        # the census's range of the professional's E/S/5 (n 18, 0.27-1.20)
        assert on and all(0.25 <= m <= 1.2 for m in on), (ch, on)
        # the letter's height never moves; its width at most by a terminal's end
        assert abs((b1[3] - b1[1]) - (b0[3] - b0[1])) < 1e-6, ch
        assert (b0[2] - b0[0]) - (b1[2] - b1[0]) <= 0.15, ch
        assert cut.area >= (1 - st.MOUTH_MAX_CUT_SHARE) * poly.area


def test_on_true_counters_are_never_cut():
    from digitizer_core import small_text as st
    for ch, (poly, widen) in _letters().items():
        if ch in "89":
            cut, rows = st._open_mouths(poly, widen)
            assert cut is poly and rows == [], (ch, rows)


# --- ON, through the re-set ------------------------------------------------------

def test_on_reports_every_mouth_and_moves_no_letter():
    off, p = scene()
    enlarge_small_text(off, p, **KW)
    on, p = scene()
    rep = enlarge_small_text(on, p, **KW, bay_mouth=True)
    rows = rep[0]["mouths"]
    assert rows and all(("opened_mm" in r) != ("left" in r) for r in rows), rows
    e = [r for r in rows if r["shape"] == "Sg0"]
    assert len(e) == 2 and all("opened_mm" in r for r in e), e     # the E's two mouths opened
    mouths, _b = _sewn_mouths(glyphs(on)["E"].polygon, 0.0)
    assert all(m >= 0.25 for m in mouths), mouths
    go, gn = glyphs(off), glyphs(on)
    assert gn["8"].polygon.equals(go["8"].polygon)                  # two true counters: untouched
    for name in go:                                                 # heights, scale and place kept
        bo, bn = go[name].polygon.bounds, gn[name].polygon.bounds
        assert abs((bo[3] - bo[1]) - (bn[3] - bn[1])) < 1e-6 or any(r["shape"] == gn[name].shape_id
                                                                    and r.get("dh_mm") for r in rows), name
        assert gn[name].meta["small_text_enlarged"] == go[name].meta["small_text_enlarged"]


# --- the constant's provenance ---------------------------------------------------

def test_bay_mouth_constant_is_the_pros_census():
    """`BAY_MOUTH_MM` is the median of the professional's E/S/5 mouths, read
    by `tools/bay_census.py` off his DSTs in the committed zip."""
    import pytest
    pytest.importorskip("pystitch")
    if not ZIP.exists():
        pytest.skip("Embroidery Files.zip not in this checkout")
    from digitizer_core.small_text import BAY_MOUTH_MM
    from tools import bay_census
    c = bay_census.census()
    assert c["n"] == 18, c
    assert abs(c["median"] - BAY_MOUTH_MM) <= 0.005, c


def test_census_splits_the_pros_joined_digits():
    from tools.bay_census import allot
    # Fremont hat's 1895: the 1 alone, then 895 sewn as one piece
    assert allot([3.7, 3.2, 3.8, 2.2, 9.95], 7) == [1, 1, 1, 1, 3]
    assert allot([9.2, 1.9, 8.35], 7) == [3, 1, 3]          # the patch: EST joined too
    assert allot([1.0] * 8, 7) is None                      # more pieces than letters: unread
