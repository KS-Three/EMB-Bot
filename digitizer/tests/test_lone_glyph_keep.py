"""`cfg.extra["lone_glyph_keep"]` (built OFF 2026-11-14): a tittle over a
joined (cursive) word is admitted by the dot rung as a printed i's dot is.

The eye sweep's "Seriously" read "Senaudy" at 70.9 and 80.2 mm: its i-dot
(0.74 x 0.96 mm) fails the run tier's loop proxy (2 x 0.96 < 2.2 mm) and the
dot rung's lettering scope finds no stem under it, because a cursive i's
stroke is one region with its whole word. ON, a dot inside its own colour's
word, with that word's ink in the dot's columns under it, is kept; a speck
is not, nor a dot over another colour, nor anything on the photo lane.
Absent or false: the engine as it was.
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions
from digitizer_core.threads import rgb_to_lab

PX = 30.0
FRAME = (200, 260)
RGB = np.array([(255, 255, 255), (0, 0, 0), (200, 0, 0)], float)


def _disc(cy, cx, r=9):
    yy, xx = np.mgrid[:FRAME[0], :FRAME[1]]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r


def _rect(y0, x0, y1, x1):
    m = np.zeros(FRAME, bool)
    m[y0:y1, x0:x1] = True
    return m


def _scene(word_layer=1, body_top=120):
    """A white panel; a black joined word: an ascender at its left reaching
    ABOVE the dot and a body under it, one region; the dot (19 px, 0.63 mm)
    inside the word's box, its body `body_top - 40` px under the dot; and a
    black speck of the dot's size alone at the far right."""
    dot = _disc(30, 60)
    word = _rect(10, 20, 170, 38) | _rect(body_top, 20, 170, 120)
    speck = _disc(30, 220)
    ground = _rect(5, 5, 195, 255) & ~dot & ~word & ~speck
    return [RegionMask.from_full(ground, 0), RegionMask.from_full(dot, 1),
            RegionMask.from_full(word, word_layer), RegionMask.from_full(speck, 1)]


def _kept(regions, *, on, chain_rescue=True):
    cfg = PipelineConfig(extra={"lone_glyph_keep": True} if on else {})
    kept, _w = resolve_small_regions(regions, cfg, PX, layer_lab=rgb_to_lab(RGB),
                                     chain_rescue=chain_rescue)
    return [any(k is r for k in kept) for r in regions]


def test_off_the_tittle_of_a_joined_word_is_dropped_as_today():
    _g, dot, word, speck = _kept(_scene(), on=False)
    assert word and not dot and not speck
    assert _kept(_scene(), on=False) == _kept(_scene(), on=None)


def test_on_the_tittle_is_kept_and_the_speck_is_not():
    _g, dot, word, speck = _kept(_scene(), on=True)
    assert dot and word and not speck


def test_a_word_of_another_colour_holds_no_tittle():
    _g, dot, _word, _speck = _kept(_scene(word_layer=2), on=True)
    assert not dot


def test_ink_too_far_under_the_dot_holds_no_tittle():
    # the body 125 px under the dot's foot: 6.6 dot heights, past the 6
    # allowed; the word still spans the dot, so only the gap refuses it
    regions = _scene(body_top=165)
    assert regions[2].bbox[1] <= regions[1].bbox[1] and regions[2].bbox[3] >= regions[1].bbox[3]
    _g, dot, _word, _speck = _kept(regions, on=True)
    assert not dot


def test_the_photo_lane_is_untouched():
    assert _kept(_scene(), on=True, chain_rescue=False) == _kept(_scene(), on=False, chain_rescue=False)


def _star_scene():
    """Hotel Fremont's Wisconsin star (2026-11-15, the flip's STOP): a white
    speck inside a black shape inside a big white field. The field spans the
    speck's box and has ink under it, but the speck sits on the black shape,
    not on the field's ground: it is an enclosed mark, not a tittle."""
    field = _rect(5, 5, 195, 255)
    blob = _rect(20, 30, 120, 110)
    star = _disc(50, 70)
    return [RegionMask.from_full(field & ~blob, 0), RegionMask.from_full(blob & ~star, 1),
            RegionMask.from_full(star, 0)]


def _tagged(regions, *, on):
    cfg = PipelineConfig(extra={"lone_glyph_keep": True} if on else {})
    kept, _w = resolve_small_regions(regions, cfg, PX, layer_lab=rgb_to_lab(RGB))
    return [(any(k is r for k in kept), bool(getattr(r, "dot_rung", False))) for r in regions]


def test_an_enclosed_mark_in_another_colour_is_not_a_tittle():
    assert _tagged(_star_scene(), on=True) == _tagged(_star_scene(), on=False)
    assert not _tagged(_star_scene(), on=True)[2][1]          # never sewn as the rung's tack
