"""`cfg.satin_house_from_line` — the house angle's THIRD reading
(`textcluster._cluster_house_angle_deg`, 2026-09-19).

The fixture is a real font's own word, built at test time from the committed
`src/fonts/manga_impact.json`: each glyph's filled shape is the union of its
satin columns' ribbon polygons (rail A, then rail B reversed), laid out with
the font's advances, rasterised with a 4x anti-alias downscale — the review's
construction (`docs/lettering-route-review-2026-09-19.md`). "KAYAK" at 80 mm
groups as one line and BOTH votes refuse it with margin (doubled-angle nR^2
3.9 against the 6.9 bar; four-fold R4 0.06 under the 0.25 floor): its
verticals and horizontals cancel in doubled-angle space and its diagonals
hold the four-fold resultant down. The review's "MARINE" refuses too, but on
a knife edge (5.0 from the shipped binary's quantised rails, 11.2 from the
source rails at the same 80 mm, 4.5 at 60 mm), which is its own finding
about the vote; "MARINE" at 127 mm passes the doubled-angle vote and pins the
"untouched" contract.

The contracts. OFF, the refused word carries no `satin_angle_deg` (the
fail-open behaviour before the flip, byte for byte). ON — the default since
Kent's flip the day it was built — every letter of it carries ONE angle, the
line of text's own direction. A word either vote accepts is untouched by the
flag. A group with no line of text still fails open.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core import textcluster as tc
from digitizer_core.pipeline import build_generation, finish_generation

FONT = Path(__file__).resolve().parents[2] / "src" / "fonts" / "manga_impact.json"
WORD = "KAYAK"
PASSING_WORD = "MARINE"


def _column_polygon(a, b) -> Polygon | None:
    best = None
    for pts in (list(a) + list(reversed(b)), list(a) + list(b)):
        if len(pts) < 3:
            continue
        p = Polygon(pts)
        if not p.is_valid:
            p = p.buffer(0)
        if p.is_empty:
            continue
        if best is None or p.area > best.area:
            best = p
    return best


def _word_raster(word: str, width_mm: float, px_per_mm: float = 12.0, *,
                 font_path: Path = FONT, rotate_deg: float = 0.0) -> np.ndarray:
    """`word` set in the font at `font_path` (a committed `src/fonts/*.json`),
    `width_mm` wide, black on white at `px_per_mm`; `rotate_deg` turns the
    finished raster counter-clockwise as displayed (a positive angle puts the
    line of text at `-rotate_deg` in the pipeline's y-down frame)."""
    font = json.loads(font_path.read_text())
    x = 0.0
    shapes = []
    for ch in word:
        g = font["glyphs"][ch]
        parts = [_column_polygon(c["railA"], c["railB"]) for c in g["cols"]]
        u = unary_union([p for p in parts if p is not None and p.area > 0])
        shapes.append(translate(u, xoff=x))
        x += g["adv"]
    allg = unary_union(shapes)
    x0, y0, x1, y1 = allg.bounds
    scale = width_mm / (x1 - x0)
    pad = 4.0
    w = int((x1 - x0) * scale * px_per_mm + 2 * pad * px_per_mm)
    h = int((y1 - y0) * scale * px_per_mm + 2 * pad * px_per_mm)
    canvas = np.full((h * 4, w * 4), 255, np.uint8)
    for p in (list(allg.geoms) if isinstance(allg, MultiPolygon) else [allg]):
        ext = np.round(((np.asarray(p.exterior.coords) - (x0, y0)) * scale * px_per_mm + pad * px_per_mm) * 4).astype(np.int32)
        cv2.fillPoly(canvas, [ext.reshape(-1, 1, 2)], 0)
        for r in p.interiors:
            hole = np.round(((np.asarray(r.coords) - (x0, y0)) * scale * px_per_mm + pad * px_per_mm) * 4).astype(np.int32)
            cv2.fillPoly(canvas, [hole.reshape(-1, 1, 2)], 255)
    canvas = cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA)
    if rotate_deg:
        side = int(math.hypot(w, h)) + 2
        big = np.full((side, side), 255, np.uint8)
        oy, ox = (side - h) // 2, (side - w) // 2
        big[oy:oy + h, ox:ox + w] = canvas
        m = cv2.getRotationMatrix2D((side / 2.0, side / 2.0), rotate_deg, 1.0)
        canvas = cv2.warpAffine(big, m, (side, side), flags=cv2.INTER_LINEAR, borderValue=255)
    return canvas


# The third reading is tried only when a group is NOT anchored (plan step 1,
# `satin_house_anchor`, ON since the same day), so every run in this file
# turns the anchor off to test the reading it is about.
PRE_ANCHOR = dict(satin_house_anchor=False)


@pytest.fixture(scope="module")
def refused_word(tmp_path_factory) -> Path:
    """The word both votes refuse: KAYAK at 80 mm."""
    p = tmp_path_factory.mktemp("word") / "kayak80.png"
    cv2.imwrite(str(p), _word_raster(WORD, 80.2))
    return p


@pytest.fixture(scope="module")
def refused_off(refused_word):
    """One digitize of the refused word with the flag OFF, shared by the
    tests that only read it."""
    return _run(refused_word, 80.2, satin_house_from_line=False, **PRE_ANCHOR)


@pytest.fixture(scope="module")
def accepted_word(tmp_path_factory) -> Path:
    """A word the doubled-angle vote accepts (MARINE at 127 mm)."""
    p = tmp_path_factory.mktemp("word") / "marine127.png"
    cv2.imwrite(str(p), _word_raster(PASSING_WORD, 127.4))
    return p


def _run(art: Path, width_mm: float, **kw):
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest", max_colors=6, **kw)
    gen = build_generation(str(art), cfg)
    return finish_generation(gen.fork(), cfg)


def _letters(art: Path, width_mm: float, **kw):
    return [r for r in _run(art, width_mm, **kw).regions if r.meta.get("text_candidate")]


def _angle_gap(a: float, b: float) -> float:
    return abs((a - b + 90.0) % 180.0 - 90.0)


def test_the_flag_is_on_by_default():
    """Kent's flip, 2026-09-19, the day it was built."""
    assert PipelineConfig().satin_house_from_line is True


def test_both_votes_refuse_the_word_at_80mm_and_off_it_keeps_no_house(refused_off):
    result = refused_off
    letters = [r for r in result.regions if r.meta.get("text_candidate")]
    assert len(letters) >= len(WORD), len(letters)
    groups = tc._lettering_groups(result.regions)
    assert len(groups) == 1, len(groups)
    ids = {r.shape_id for r in groups[0]}
    assert all(r.shape_id in ids for r in letters)
    assert tc._cluster_house_angle_deg(groups[0], fourfold=True) is None
    assert tc._cluster_house_angle_deg(groups[0], fourfold=True, from_line=False) is None
    assert all("satin_angle_deg" not in r.meta for r in groups[0])


def test_on_the_refused_word_takes_one_cross_along_its_line_of_text(refused_word):
    result = _run(refused_word, 80.2, **PRE_ANCHOR)                              # from_line at its default, ON
    group = tc._lettering_groups(result.regions)[0]
    letters = [r for r in result.regions if r.meta.get("text_candidate")]
    angles = [r.meta.get("satin_angle_deg") for r in group]
    assert all(a is not None for a in angles), angles
    assert all(r.meta.get("satin_angle_deg") == angles[0] for r in letters)
    assert max(angles) - min(angles) < 1e-9                      # one house for the whole word
    line = tc._line_of_text_deg(group)
    assert line is not None
    assert _angle_gap(angles[0], line) < 0.5                      # the cross runs along the line
    assert _angle_gap(angles[0], 0.0) < 2.0                       # a horizontal word: a horizontal cross
    assert all(r.meta.get("fill_angle_deg") == angles[0] for r in group)


def test_a_word_a_vote_accepts_is_untouched_by_the_flag(accepted_word):
    off = _letters(accepted_word, 127.4, satin_house_from_line=False, **PRE_ANCHOR)
    on = _letters(accepted_word, 127.4, **PRE_ANCHOR)
    a_off = sorted(r.meta.get("satin_angle_deg") for r in off)
    a_on = sorted(r.meta.get("satin_angle_deg") for r in on)
    assert a_off and a_off[0] is not None                        # the doubled-angle vote passes here
    assert a_on == a_off


def test_a_group_with_no_line_of_text_still_fails_open(refused_off):
    group = tc._lettering_groups(refused_off.regions)[0]
    # Two letters make no line by `_line_of_text_deg`'s own rule only when
    # they do not spread; a single member never does.
    assert tc._line_of_text_deg(group[:1]) is None
    assert tc._cluster_house_angle_deg(group[:1], fourfold=True, from_line=True) is None
