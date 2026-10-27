"""`cfg.bean_ink_outlined_letters` (W5-05, 2026-10-27, built OFF): a bean ink
read whose skeleton runs mostly outside the traced letter read the letter's
OUTLINE, not its stroke, and is no read (`beanletters.INK_INSIDE_MIN_SHARE`).

MFab's AND / WELDING / LLC are black letters on a black body, each ringed by
a thin white keyline. `ink_path.read_cluster_ink` takes its ground from the
pixels far from the letters -- the black body -- so the most different
colour near the letter is the WHITE keyline, and that is what it reads: on
the LC, AND's A and N at 0.42-0.44 mm with 0.4-1.7% of their spines inside
the letter. They pass `INK_SHAPE_MAX_RATIO` and go bean, and the A sews as a
white letter instead of a black one (`docs/outlined-bean-ink-2026-10-27.md`).

The raster cases draw that construction (and its control, the same letters
on a white page) and read them with the real ink reader; the stub cases pin
the decision; bridge, the real art the bean rule was built on, keeps its
eight bean letters; the goldens pin that OFF is the engine as it was and
that ON moves nothing on art with no outlined letters.
"""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, beanletters, digitize
from digitizer_core.beanletters import (BEAN_LETTER_KEY, INK_INSIDE_MIN_SHARE, ink_inside_shape,
                                        spines_inside, tag_bean_letters)
from digitizer_core.ink_path import MemberInk
from digitizer_core.pipeline import build_generation, finish_generation
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import prep

from .conftest import TESTDATA, own_thread_only

# --- the share of the spine inside the letter -----------------------------------

BAR = box(0.0, 0.0, 0.8, 3.0)
CENTRE = [(0.4, 0.2), (0.4, 2.8)]
OUTLINE = list(box(-0.14, -0.14, 0.94, 3.14).exterior.coords)     # 0.14 mm outside, MFab's median
OUTLINE_LEN = 2 * (1.08 + 3.28)


def test_the_threshold_sits_between_the_measured_populations():
    # AND's outline reads 0.4-1.7% inside on the LC. A letter's own ink:
    # bridge's bean letters 98.4-100%, the same MFab words on the hat 67.7-100%.
    assert 0.017 < INK_INSIDE_MIN_SHARE < 0.677


def test_spines_inside_is_the_share_of_spine_length_in_the_polygon():
    assert spines_inside(BAR, [CENTRE]) == pytest.approx(1.0)
    assert spines_inside(BAR, [OUTLINE]) == pytest.approx(0.0)
    half_out = [(0.4, 1.5), (0.4, 4.5)]                              # 1.5 of 3.0 mm inside
    assert spines_inside(BAR, [half_out]) == pytest.approx(0.5)
    assert spines_inside(BAR, [CENTRE, OUTLINE]) == pytest.approx(2.6 / (2.6 + OUTLINE_LEN))


def test_a_counter_is_not_inside():
    ring = Polygon(BAR.exterior.coords, [list(box(0.3, 1.0, 0.5, 2.0).exterior.coords)])
    assert spines_inside(ring, [[(0.4, 1.2), (0.4, 1.8)]]) == pytest.approx(0.0)


def test_nothing_to_measure_is_nothing_to_disagree_with():
    assert spines_inside(None, [CENTRE]) is None
    assert spines_inside(Polygon(), [CENTRE]) is None
    assert spines_inside(BAR, []) is None
    assert spines_inside(BAR, [[(0.4, 0.4)]]) is None                # a single point has no length
    assert ink_inside_shape(None, [OUTLINE])
    assert ink_inside_shape(BAR, [])
    assert ink_inside_shape(BAR, [CENTRE])
    assert not ink_inside_shape(BAR, [OUTLINE])


# --- the real ink reader on the construction -------------------------------------

PX_PER_MM = 10.0
SS = 8
PAGE_MM = (30.0, 12.0)
BODY_MM = (2.0, 2.0, 28.0, 10.0)
LETTERS_MM = [(8.0 + 2.0 * i, 4.5, 8.8 + 2.0 * i, 7.5) for i in range(3)]     # 0.8 x 3 mm stems
THIN_MM = [(8.0 + 2.0 * i, 4.5, 8.3 + 2.0 * i, 7.5) for i in range(3)]        # 0.3 x 3 mm stems


def _page(letters, *, body: bool, keyline_mm: float = 0.0):
    """Black letters (x0, y0, x1, y1 mm) -- on a black body, each ringed by a
    white keyline, or on a bare white page between two corner marks that keep
    the artwork the body's size -- drawn supersampled and reduced by area, so
    every edge is an anti-alias ramp. -> (rgb image, art width mm, art centre
    mm)."""
    s = PX_PER_MM * SS
    w, h = int(PAGE_MM[0] * s), int(PAGE_MM[1] * s)
    img = np.full((h, w), 255, np.uint8)

    def rect(r, v, grow=0.0):
        cv2.rectangle(img, (int((r[0] - grow) * s), int((r[1] - grow) * s)),
                      (int((r[2] + grow) * s) - 1, int((r[3] + grow) * s) - 1), v, -1)

    if body:
        rect(BODY_MM, 20)
    else:
        x0, y0, x1, y1 = BODY_MM
        rect((x0, y0, x0 + 1.0, y0 + 1.0), 20)
        rect((x1 - 1.0, y1 - 1.0, x1, y1), 20)
    for r in letters:
        if keyline_mm:
            rect(r, 255, keyline_mm)
        rect(r, 20)
    small = cv2.resize(img, (w // SS, h // SS), interpolation=cv2.INTER_AREA)
    x0, y0, x1, y1 = BODY_MM
    return np.dstack([small] * 3), x1 - x0, ((x0 + x1) / 2, (y0 + y1) / 2)


def _tag(letters, *, on: bool, **page):
    img, width, (cx, cy) = _page(letters, **page)
    p = prep(img, PipelineConfig(target_width_mm=width, garment_id="left_chest"))
    assert p.input_px_per_mm == pytest.approx(PX_PER_MM, rel=0.02)
    members = [Region(shape_id=f"S{i}", polygon=box(x0 - cx, y0 - cy, x1 - cx, y1 - cy), thread_index=0,
                      thread_number="0020", area_mm2=(x1 - x0) * (y1 - y0), meta={"text_cluster_id": "c"})
               for i, (x0, y0, x1, y1) in enumerate(letters)]
    cfg = PipelineConfig(target_width_mm=width, bean_letter_max_stroke_mm=0.5, small_text_true_size=False,
                         bean_ink_outlined_letters=on)
    return tag_bean_letters(members, p, cfg), members


@pytest.mark.parametrize("keyline_mm", [0.2, 0.3])
def test_off_a_keylined_letter_reads_its_outline_and_goes_bean(keyline_mm):
    n, members = _tag(LETTERS_MM, on=False, body=True, keyline_mm=keyline_mm)
    assert n == 3                                                       # the A of AND, as it is
    for r in members:
        assert spines_inside(r.polygon, r.meta[BEAN_LETTER_KEY]) < 0.05     # the keyline round it
        assert r.meta["ink_stroke_mm"] < 0.5                            # a 0.8 mm stem read thin


@pytest.mark.parametrize("keyline_mm", [0.2, 0.3])
def test_on_the_outline_read_is_no_read(keyline_mm):
    n, members = _tag(LETTERS_MM, on=True, body=True, keyline_mm=keyline_mm)
    assert n == 0
    assert not any(BEAN_LETTER_KEY in r.meta for r in members)
    assert all(r.meta["ink_stroke_mm"] < 0.5 for r in members)       # the read is still recorded


def test_on_thin_letters_on_a_page_still_go():
    off, _ = _tag(THIN_MM, on=False, body=False)
    on, members = _tag(THIN_MM, on=True, body=False)
    assert off == on == 3
    assert all(spines_inside(r.polygon, r.meta[BEAN_LETTER_KEY]) > 0.95 for r in members)


# --- the decision ------------------------------------------------------------------

def _region(polygon):
    return SimpleNamespace(meta={"text_cluster_id": "c1"}, polygon=polygon)


def _stub_ink(monkeypatch, inks):
    def fake(p, members):
        return [inks[id(r)] for r in members]

    monkeypatch.setattr(beanletters, "read_cluster_ink",
                        own_thread_only(fake, beanletters.read_cluster_ink))


def _cfg(**kw):
    return PipelineConfig(bean_letter_max_stroke_mm=0.5, small_text_true_size=False, **kw)


def test_an_outline_read_is_left_out_and_the_rest_decide(monkeypatch):
    thin = [_region(box(0.0, 0.0, 0.4, 3.0)) for _ in range(3)]
    outlined = _region(BAR)
    _stub_ink(monkeypatch, {**{id(r): MemberInk(stroke_mm=0.35, spines=[[(0.2, 0.2), (0.2, 2.8)]]) for r in thin},
                            id(outlined): MemberInk(stroke_mm=0.45, spines=[OUTLINE])})
    regions = thin + [outlined]
    assert tag_bean_letters(regions, object(), _cfg()) == 4              # OFF: the outline goes too
    for r in regions:
        r.meta.pop(BEAN_LETTER_KEY, None)
    assert tag_bean_letters(regions, object(), _cfg(bean_ink_outlined_letters=True)) == 3
    assert BEAN_LETTER_KEY not in outlined.meta
    assert outlined.meta["ink_stroke_mm"] == 0.45


def test_the_gate_holds_under_word_tiers_too(monkeypatch):
    a = _region(BAR)
    _stub_ink(monkeypatch, {id(a): MemberInk(stroke_mm=0.45, spines=[OUTLINE])})
    assert tag_bean_letters([a], object(), _cfg(lettering_word_tiers=True)) == 1
    a.meta.pop(BEAN_LETTER_KEY)
    assert tag_bean_letters([a], object(), _cfg(lettering_word_tiers=True, bean_ink_outlined_letters=True)) == 0


# --- real art: bridge's bean letters read their own stroke, and stay ---------------

BRIDGE = TESTDATA / "photo" / "logo_bridge_bar.jpg"


def _bridge_cfg(on: bool) -> PipelineConfig:
    # `test_bean_letters_pipeline`'s engine: the line alone, at 1.0 mm.
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=6,
                          small_text_true_size=False, bean_letter_max_stroke_mm=1.0,
                          bean_ink_outlined_letters=on)


def test_on_bridge_keeps_its_eight_bean_letters():
    gen = build_generation(str(BRIDGE), _bridge_cfg(False))
    tags = []
    for on in (False, True):
        result = finish_generation(gen.fork(), _bridge_cfg(on))
        tags.append({r.shape_id: r.meta[BEAN_LETTER_KEY] for r in result.regions if BEAN_LETTER_KEY in r.meta})
    assert len(tags[0]) == 8
    assert tags[1] == tags[0]
    by_id = {r.shape_id: r for r in result.regions}
    assert all(spines_inside(by_id[sid].polygon, sp) > 0.98 for sid, sp in tags[1].items())


# --- OFF is the engine as it was; ON moves nothing without outlined letters ------

GOLDEN_MD5 = {
    "logo_alpha.png": "554e898c04a65643c086b43be64b9e2c",
    "logo_whitebg.png": "d53de4bbf6881dc8465caec31e93e7c9",
    "ribbon_curve.png": "98bf128674db0f829a210f32264318e6",
}


def _md5(fixture: str, **kw) -> str:
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none", sew_enclosed_white=False, **kw))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def test_the_default_is_off():
    assert PipelineConfig().bean_ink_outlined_letters is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_off_is_byte_identical(fixture):
    assert _md5(fixture) == GOLDEN_MD5[fixture]


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_on_moves_nothing_on_the_goldens(fixture):
    assert _md5(fixture, bean_ink_outlined_letters=True) == GOLDEN_MD5[fixture]
