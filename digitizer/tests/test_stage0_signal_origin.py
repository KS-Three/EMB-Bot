"""`tools/stage0_signal_origin.py`, and the defect it was written to explain.

Three kinds of test live here, and they have different lifetimes:

1. The tool's own definitions (zones cover the image exactly; the opened-up
   `unique_color_mass` equals the shipped one). These are permanent.
2. **A documentation test of the DEFECT** —
   `test_one_grey_level_of_invisible_noise_crosses_the_photo_gate`. It pins
   current, wrong behaviour on purpose, so the sensitivity has a number
   attached to it. When stage 0's colour signal is replaced it will fail:
   **delete it then, do not repair it.**
3. **A tripwire for the fix** — the real flat wordmark, xfail(strict=True) per
   the convention `tests/test_classifier_scale_invariance.py` established. It
   turns green the day the misroute is fixed, and strict mode reports that as
   a failure so the marker gets deleted rather than the property forgotten.

Nothing here moves a threshold: ROADMAP gate 2 refuses stage-0 recalibration
without real tonal artwork. See docs/stage0-tires-photo-scene-2026-09-11.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

from digitizer_core import stage0_classify as s0            # noqa: E402
from digitizer_core.config import PipelineConfig            # noqa: E402
from stage0_signal_origin import ucm_parts, zones           # noqa: E402

from .conftest import TESTDATA                              # noqa: E402

TIRES = "logo_script_tires.png"


def _wordmark(h=120, w=200, ground=253, ink=8):
    """A crude two-colour 'logo': one solid bar of ink on a solid ground."""
    img = np.full((h, w, 3), ground, np.uint8)
    img[40:80, 30:170] = ink
    return img


def _noisy_ground(img, rng, amplitude=1):
    """The same image with +/- `amplitude` grey levels on the GROUND only —
    invisible to an eye (see the dE00 reading the tool prints), and the whole
    of what this fixture changes."""
    out = img.astype(np.int16)
    ground = out[:, :, 0] > 127
    noise = rng.integers(-amplitude, amplitude + 1, size=out.shape[:2])
    out[ground] += noise[ground, None]
    return np.clip(out, 0, 255).astype(np.uint8)


def test_zones_are_disjoint_and_cover_the_image():
    z = zones(_wordmark())
    stack = np.stack(list(z.values()))
    assert stack.sum(0).min() == 1 and stack.sum(0).max() == 1
    assert z["ink_interior"].any() and z["bg_interior"].any()


def test_opened_up_ucm_equals_the_shipped_signal():
    """The tool must not drift into measuring a different statistic."""
    img = _noisy_ground(_wordmark(), np.random.default_rng(7))
    cfg = PipelineConfig()
    fg = s0._fg_mask(img, None)
    mine = ucm_parts(img, fg, cfg.seed)[0]
    # `classify` decodes BGR; the array is grey-ish either way, but convert so
    # the two see identical pixels rather than nearly identical ones.
    theirs = s0.classify(img[:, :, ::-1], cfg).signals["unique_color_mass"]
    assert mine == pytest.approx(theirs, abs=1e-9)


def test_a_clean_two_colour_wordmark_reads_flat():
    """The control. Same geometry, same colours, no grain — so anything the
    noisy sibling does is the grain, not the shape.

    Not exactly zero: a hard two-colour boundary still disagrees with its own
    3x3 mode along the one-pixel edge (1.7e-4 here). Three orders of magnitude
    below the gate, which is the point — the ink boundary is not what moves
    this statistic.
    """
    cfg = PipelineConfig()
    r = s0.classify(_wordmark()[:, :, ::-1], cfg)
    assert r.signals["unique_color_mass"] < s0.UCM_PHOTO_MIN / 100
    assert r.class_ == "flat"


def test_one_grey_level_of_invisible_noise_crosses_the_photo_gate():
    """DOCUMENTS A DEFECT (delete when the signal is replaced, do not repair).

    `unique_color_mass` has no perceptual floor: the throwaway k=16 quantize
    spends centres inside a flat area whose values differ by ~1 grey level,
    and then counts neighbours landing in different centres as evidence of
    photographic texture. +/-1 level is roughly 0.2-1.0 dE00 — the repo's own
    `preflight.DELTA_E_VISIBLE` is 5.0.
    """
    img = _noisy_ground(_wordmark(), np.random.default_rng(0))
    r = s0.classify(img[:, :, ::-1], PipelineConfig())
    assert r.signals["unique_color_mass"] >= s0.UCM_PHOTO_MIN
    assert r.class_ in ("photo_scene", "photo_subject")


@pytest.mark.xfail(strict=True, reason=(
    "known defect: logo_script_tires.png is flat two-colour art (Kent's own "
    "ground-truth label, 2026-08-15 spec §3) and stage 0 routes it to the "
    "photo lane on the background's invisible grain. Cause and evidence: "
    "docs/stage0-tires-photo-scene-2026-09-11.md"))
def test_a_flat_script_wordmark_classifies_flat_at_every_seed():
    """The property the fix has to deliver, on real artwork.

    Across seeds because the verdict is not stable in the first place: the
    same file reads UCM 0.196-0.361 over seeds 0-11 while `classify` prints
    confidence 1.000, which is the distance of ONE draw from the gate.
    """
    seen = set()
    for seed in range(3):
        cfg = PipelineConfig()
        cfg.seed = seed
        seen.add(s0.classify(str(TESTDATA / TIRES), cfg).class_)
    assert seen == {"flat"}, f"classes across seeds: {sorted(seen)}"
