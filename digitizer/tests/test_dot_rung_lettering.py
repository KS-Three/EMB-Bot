"""`cfg.small_dot_rung_lettering` (built OFF 2026-10-15): the dot rung
(`cfg.small_dot_rung`, itself OFF) scoped to lettering. PR #939's catch was
that stage 3 cannot tell an i dot from a photo speck; with no tagger at
stage 3, the scope is geometric -- a part is admitted through the rung only
over a SAME-COLOUR stem (`stage3_segment.has_stem_below`). The rung's numbers
and `machine.RUN_MIN_LOOP_MM` are untouched (ROADMAP gate 1);
`tools/small_dot_rung.py` carries the measurements.

Pinned here: stage 3 keeps a dot over its stem and drops a speck (no stem, a
stem of another colour, a block too wide to be a stem, no colour known); the
scope is inert without the rung; the synthetic i/j words' dots all sew with
the scope at 60 and 80 mm, byte-identical to the rung alone; and the OFF and
rung-ON-without-scope paths are byte-identical (md5).
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from digitizer_core import PipelineConfig, digitize, machine
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions
from digitizer_core.threads import rgb_to_lab

from .conftest import TESTDATA


def test_flag_defaults_off_and_the_rung_is_untouched():
    cfg = PipelineConfig()
    assert cfg.small_dot_rung_lettering is False and cfg.small_dot_rung is False
    assert machine.RUN_MIN_LOOP_MM == 2.2
    assert machine.DOT_RUNG_STITCH_MM == 0.45 and machine.DOT_RUNG_PASSES == 3
    assert machine.DOT_RUNG_MIN_LOOP_MM == pytest.approx(1.35)


# --- stage 3: a dot over its stem, not a speck -------------------------------------

PX = 30.0
FRAME = (200, 260)
# Layers: 0 white ground, 1 black ink, 2 red ink.
RGB = np.array([(255, 255, 255), (0, 0, 0), (200, 0, 0)], float)


def _disc(cy: int, cx: int, r: int = 9) -> np.ndarray:
    yy, xx = np.mgrid[:FRAME[0], :FRAME[1]]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r


def _rect(y0, x0, y1, x1) -> np.ndarray:
    m = np.zeros(FRAME, bool)
    m[y0:y1, x0:x1] = True
    return m


def _scene(stem_layer: int = 1, stem_width: int = 18, panel: bool = True):
    """A white panel (or none: the photo lane's removed background); a black 19 px dot (0.63 mm, isoperimetric ring 2.0 mm,
    in the rung's band) with a column 120 px tall standing 10 px under it,
    and a black speck of the same size alone at the far right."""
    dot = _disc(30, 60)
    stem = _rect(50, 60 - stem_width // 2, 170, 60 - stem_width // 2 + stem_width)
    speck = _disc(30, 200)
    ground = _rect(5, 5, 195, 255) & ~dot & ~stem & ~speck
    if not panel:
        ground[:] = False
        ground[0, 0] = True                                  # a 1 px stand-in, far off
    return [RegionMask.from_full(ground, 0), RegionMask.from_full(dot, 1),
            RegionMask.from_full(stem, stem_layer), RegionMask.from_full(speck, 1)]


def _kept(regions, *, rung=True, scope=True, colours=True, lab_img=None):
    cfg = PipelineConfig(small_dot_rung=rung, small_dot_rung_lettering=scope)
    kept, _w = resolve_small_regions(regions, cfg, PX,
                                     layer_lab=rgb_to_lab(RGB) if colours else None,
                                     lab_img=lab_img)
    return [any(k is r for k in kept) for r in regions]


def test_the_scene_is_in_the_rungs_band():
    regions = _scene()
    dot = regions[1]
    h, w = dot.crop.shape
    assert 2 * max(h, w) < machine.DOT_RUNG_MIN_LOOP_MM * PX       # the plain proxy misses it
    assert 2 * np.sqrt(np.pi * dot.area) >= machine.DOT_RUNG_MIN_LOOP_MM * PX
    assert dot.area < (PipelineConfig().min_detail_mm * PX) ** 2
    assert regions[2].area >= (PipelineConfig().min_detail_mm * PX) ** 2   # the stem is full size


def test_rung_on_without_scope_keeps_dot_and_speck_alike():
    """The rung as #939 built it: unchanged by this flag."""
    _panel, dot, _stem, speck = _kept(_scene(), scope=False)
    assert dot and speck


def test_scope_keeps_the_dot_and_drops_the_speck():
    _panel, dot, stem, speck = _kept(_scene())
    assert dot and stem and not speck


def test_scope_is_inert_without_the_rung():
    for scope in (False, True):
        _panel, dot, _stem, speck = _kept(_scene(), rung=False, scope=scope)
        assert not dot and not speck


def test_a_stem_of_another_colour_is_no_stem():
    _panel, dot, _stem, speck = _kept(_scene(stem_layer=2))
    assert not dot and not speck


def test_a_block_too_wide_is_no_stem():
    """A ground or a bar under a speck: its top spans more than 2.5 dots."""
    _panel, dot, _stem, _speck = _kept(_scene(stem_width=60))
    assert not dot


def test_no_colour_known_admits_nothing():
    """On no ground (so the dot is not absorbed either way), with no colour."""
    _g, dot, _stem, speck = _kept(_scene(panel=False), scope=False, colours=False)
    assert dot and speck                                     # the rung alone keeps both
    _g, dot, _stem, speck = _kept(_scene(panel=False), colours=False)
    assert not dot and not speck


def test_the_raster_colour_serves_where_every_region_is_one_layer():
    """The photo lane: every region is layer 0, so the colour is the raster's
    mean under it (`lab_img`, handed over when the scope is on)."""
    regions = _scene(panel=False)
    img = np.full(FRAME + (3,), 255.0)
    for r in regions[1:]:
        img[r.full_mask()] = 0.0
    lab = rgb_to_lab(img.reshape(-1, 3)).reshape(FRAME + (3,))
    for r in regions:
        r.layer = 0
    _panel, dot, _stem, speck = _kept(regions, colours=False, lab_img=lab)
    assert dot and not speck


# --- the whole pipeline: the synthetic i/j words at 60 and 80 mm --------------------

def _word_cases(tmp_path):
    from tools.small_dot_rung import WORD, dot_cases
    return [c for c in dot_cases(tmp_path) if c[0].split()[-1] == WORD]


def test_the_word_dots_all_sew_with_the_scope_as_with_the_rung(tmp_path):
    import tools.small_dot_rung as sdr
    cases = _word_cases(tmp_path)
    assert len(cases) == 2                                     # 80 and 60 mm
    real = sdr.dot_cases
    sdr.dot_cases = lambda _tmp: cases
    try:
        on, scope = sdr.dots("on", tmp_path), sdr.dots("scope", tmp_path)
    finally:
        sdr.dot_cases = real
    for a, b in zip(on, scope):
        assert a["dots_in_art"] == b["dots_in_art"] == 4
        assert b["dots_sewn"] == 4 and b["dropped_small_shapes"] == 0
        assert b["md5"] == a["md5"]


# --- OFF, and the rung without the scope, are byte-identical --------------------------

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("rung,scope", [(False, True), (True, False), (True, True)])
def test_goldens_are_byte_identical_in_every_arm(fixture, rung, scope):
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            small_dot_rung=rung, small_dot_rung_lettering=scope))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
