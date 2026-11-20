"""Stage 0's photo gate, scale half (`cfg.stage0_grain_needs_texture`, built OFF
2026-11-19). Doc: `docs/stage0-grain-needs-texture-2026-11-19.md`.

Fixture readings pinned here are instrument readings on real files, not
quality claims (ROADMAP gate 4); the in-line numbers check arithmetic only and
calibrate nothing (gate 2). No constant moves: the flag changes which routes
may decide, not where any gate sits.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from digitizer_core import stage0_classify as s0
from digitizer_core.config import PipelineConfig

from .conftest import ENGINE_2026_10_27

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
ON = PipelineConfig(stage0_grain_needs_texture=True)
OFF = PipelineConfig(stage0_grain_needs_texture=False)


def test_the_flag_defaults_on():
    """Kent's flip 2026-11-19."""
    assert PipelineConfig().stage0_grain_needs_texture is True


def test_the_frozen_snapshot_holds_the_off_value():
    assert ENGINE_2026_10_27["stage0_grain_needs_texture"] is False


@pytest.mark.parametrize("ucm,tex,two,cut,want", [
    # grain alone on an opaque file: held ON, photo OFF
    (0.30, 0.06, 0.85, False, (False, "grain_held")),
    # texture agrees: still photo, both routes named
    (0.30, 0.20, 0.50, False, (True, "grain+texture")),
    # texture alone: unchanged
    (0.10, 0.20, 0.50, False, (True, "texture")),
    # the veto still decides first
    (0.36, 0.00, 0.99, False, (False, "veto")),
    # neither fires: unchanged
    (0.10, 0.05, 0.50, False, (False, "none")),
    # a cut-out keeps the grain gate alone
    (0.30, 0.06, 0.85, True, (True, "legacy")),
])
def test_decide_photo_with_the_flag(ucm, tex, two, cut, want):
    is_photo, _conf, route = s0.decide_photo(ucm, tex, two, cut, True, True)
    assert (is_photo, route) == want


def test_the_flag_needs_the_texture_gate():
    """With the texture gate off the whole old tree runs, flag or not."""
    assert s0.decide_photo(0.30, 0.06, 0.85, False, False, True) == \
        s0.decide_photo(0.30, 0.06, 0.85, False, False, False)


def test_a_held_verdict_carries_the_texture_gate_confidence():
    _p, conf, _r = s0.decide_photo(0.30, 0.07, 0.85, False, True, True)
    assert conf == pytest.approx(s0._gate_confidence(0.07, s0.TEXTURE_PHOTO_MIN, s0.TEXTURE_MARGIN))


def test_off_is_the_old_decision_on_every_route():
    for args in [(0.30, 0.06, 0.85, False), (0.30, 0.20, 0.5, False),
                 (0.10, 0.20, 0.5, False), (0.36, 0.0, 0.99, False), (0.3, 0.06, 0.85, True)]:
        assert s0.decide_photo(*args, True, False) == s0.decide_photo(*args, True)


def test_the_lens_restates_the_flag():
    from tools import classify_lens as lens
    th = lens.Thresholds.nominal()
    for args in [(0.30, 0.06, 0.85, False), (0.30, 0.20, 0.5, False), (0.36, 0.0, 0.99, False)]:
        assert lens._photo_gate(*args, th, True, True) == s0.decide_photo(*args, True, True)


# --- real fixtures ------------------------------------------------------------

def test_mfab_hat_native_leaves_photo_territory_on():
    """The one real logo the shipped engine sends to the photo lane at native
    size, by grain alone (ucm ~0.30, texture ~0.06)."""
    path = str(TESTDATA / "art" / "logo_mfab_hat.png")
    off = s0.classify(path, OFF)
    on = s0.classify(path, ON)
    assert off.signals["photo_route"] == "grain" and off.class_ == "photo_scene"
    assert on.signals["photo_route"] == "grain_held"
    assert on.class_ not in ("photo_scene", "photo_subject")


def test_a_real_photograph_keeps_its_class_on():
    path = str(TESTDATA / "photo" / "owl_kent.jpg")
    assert s0.classify(path, ON).class_ == s0.classify(path, OFF).class_ == "photo_scene"


@pytest.mark.parametrize("rel", ["art/logo_toat_machine.png", "art/logo_mfab_lc.png"])
def test_a_small_real_logo_downscaled_stays_out_of_photo_territory_on(rel, tmp_path):
    im = Image.open(TESTDATA / rel).convert("RGB")
    w = 200
    out = tmp_path / f"{Path(rel).stem}_{w}.png"
    im.resize((w, max(1, round(im.height / im.width * w))), Image.LANCZOS).save(out)
    assert s0.classify(str(out), ON).class_ not in ("photo_scene", "photo_subject")
