"""`tools/color_diversity.py` — the 08-15 spec's candidate stage-0 signal.

The statistic is "distinct 3-bit-per-channel colours needed to cover 90% of
foreground pixels", and its whole claim is SCALE INVARIANCE: a fraction of
the pixels, never a count of them. These pin the definition, because an
instrument whose definition drifts silently re-sites a boundary nobody
re-measured.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

from color_diversity import (BITS, COVERAGE, CORPUS, MIN_TONAL,  # noqa: E402
                             diversity)


def _field(colours, counts, shape=None):
    """A raster of `counts[i]` pixels of `colours[i]`, and an all-true mask."""
    px = np.concatenate([np.tile(np.asarray(c, np.uint8), (n, 1))
                         for c, n in zip(colours, counts)])
    img = px.reshape(1, -1, 3)
    return img, np.ones(img.shape[:2], bool)


def test_one_colour_is_one():
    img, fg = _field([(200, 30, 30)], [1000])
    assert diversity(img, fg) == 1


def test_it_counts_only_as_far_as_the_coverage_fraction():
    """Nine tenths red, one tenth blue: the red alone reaches 90%, so the
    blue is not needed and is not counted. That IS the statistic."""
    img, fg = _field([(200, 30, 30), (30, 30, 200)], [900, 100])
    assert diversity(img, fg) == 1
    # Move one pixel across the line and the second colour becomes necessary.
    img, fg = _field([(200, 30, 30), (30, 30, 200)], [899, 101])
    assert diversity(img, fg) == 2


def test_it_is_invariant_to_the_pixel_COUNT_which_is_the_whole_claim():
    """The same mixture at 10x the pixels reads the same number. A count of
    colours would not; a count needed to cover a FRACTION does."""
    mix = [(200, 30, 30), (30, 200, 30), (30, 30, 200), (200, 200, 30)]
    small, fg_s = _field(mix, [40, 30, 20, 10])
    big, fg_b = _field(mix, [400, 300, 200, 100])
    assert diversity(small, fg_s) == diversity(big, fg_b)


def test_three_bits_swallow_anti_aliasing():
    """Two shades inside one 3-bit cell are one colour — the quantisation's
    reason for being. 8 levels per channel, so a cell is 32 wide."""
    img, fg = _field([(200, 30, 30), (207, 30, 30)], [500, 500])
    assert diversity(img, fg) == 1
    # And two shades either side of a cell boundary are two.
    img, fg = _field([(191, 30, 30), (200, 30, 30)], [500, 500])
    assert diversity(img, fg) == 2


def test_the_mask_is_what_is_counted():
    """Background pixels excluded by the mask cannot contribute — the
    `engine` foreground mode depends on this."""
    img, _fg = _field([(255, 255, 255), (10, 10, 10)], [900, 100])
    fg = np.zeros(img.shape[:2], bool)
    fg[:, 900:] = True                     # the ink only
    assert diversity(img, fg) == 1


def test_an_empty_foreground_is_zero_not_an_error():
    img, _ = _field([(10, 10, 10)], [100])
    assert diversity(img, np.zeros(img.shape[:2], bool)) == 0


def test_the_constants_are_the_specs():
    assert COVERAGE == 0.90
    assert BITS == 3
    assert MIN_TONAL == 4          # "four or five would make a boundary defensible"


def test_every_corpus_row_carries_a_label_and_a_provenance():
    """Gate 2 bars synthetic artwork from siting a boundary, so provenance is
    not optional metadata — it is what the margin filters on."""
    for name, (rel, label, prov) in CORPUS.items():
        assert label in ("flat", "tonal"), name
        assert prov in ("real", "synthetic"), name


@pytest.mark.parametrize("name", ["owl", "meadow", "grass", "sunset", "chrome",
                                  "repro_icon", "summit", "ramp_lin", "ramp_rad"])
def test_the_generated_fixtures_are_labelled_synthetic(name):
    """`tools/make_photo_fixtures.py` writes these, and the repro icon is a
    reproduction of Kent's artwork rather than the artwork. Enrolling any of
    them as a positive is the fixture bias the 08-15 spec was blocked on."""
    assert CORPUS[name][2] == "synthetic"


def test_the_customer_artwork_is_labelled_real():
    for name in ("becker", "tires", "bridge", "drone", "golden_tee"):
        assert CORPUS[name][2] == "real"
