"""The cut-out guard on a SCENE (`cfg.photo_cutout_min_kept`, #1179) -- what
the six-scene measurement of 2026-10-28/29 adds to `test_background_removal.py`.

On the 18 Commons corpus photographs rembg (`isnet-general-use`) answers a
scene with low alpha everywhere: alpha >= 128 covers 0.01-5.4% of the frame
(snow_highkey 0.0001, landscape_lake 0.0006, underwater_reef 0.003,
night_neon 0.005, night_skyline 0.014, stained_glass 0.054) where every row
with a real subject reads 0.27-0.76. Before the guard the pipeline accepted
any non-None mask, the whole frame became background and the lane sewed
0-3,117 stitches of a 13,000-40,000-stitch photograph. #1179's guard refuses
such a cut-out; this file pins the parts of the refusal the six-scene
measurement leaned on, and the corpus instrument's reading of it:

* stage 2 receives NO subject/background mask for a refused cut-out (the
  palette must not weight by a "background" class the cut-out did not earn);
* a refused cut-out lands on the PLAIN classical route -- full stitch
  geometry identical to `photo_prep=False`, derived, not pinned -- and never
  claims prep ran (Kent 2026-10-28: "measure A vs B, ship better"; B, prep
  skipped, beat A on fidelity_cc on four of the six scenes);
* `tools.photo_corpus` shows the refused share on the sxs page and captures
  the other arm of a flag with `--set FIELD=JSON`.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import digitizer_core.pipeline as pipeline_module
from digitizer_core.pipeline import run_stages
from digitizer_core.warnings_codes import (
    PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE,
    PHOTO_BACKGROUND_REMOVED,
    PHOTO_CUTOUT_REFUSED,
    PHOTO_PREP_APPLIED,
)
from tests.conftest import own_thread_only
from tools import photo_corpus as pc

from .test_background_removal import TESTDATA, _cfg, _plan_signature
from .test_photo_corpus import _output

BLOBS = TESTDATA / "photo" / "region_blobs.png"
CUTOUT_ON = dict(forced_class="photo_scene", photo_prep=True,
                 photo_prep_background_removal=True)


def _seam_keeping(subject_frac: float):
    """A fake seam whose mask keeps a centred block covering `subject_frac`
    of the frame as subject (False) and calls the rest background (True)."""
    def fake(rgb, px_per_mm, cfg):
        h, w = rgb.shape[:2]
        bg = np.ones((h, w), bool)
        if subject_frac > 0:
            side = math.sqrt(subject_frac)
            hh, ww = max(1, int(round(h * side))), max(1, int(round(w * side)))
            y0, x0 = (h - hh) // 2, (w - ww) // 2
            bg[y0:y0 + hh, x0:x0 + ww] = False
        return bg, None
    return fake


def _install_seam(monkeypatch, subject_frac: float) -> dict:
    """Patch the seam (this thread only) and spy on what `photo_segment`
    receives as `bg_mask`; returns the capture dict."""
    captured: dict = {}
    real_segment = pipeline_module.photo_segment

    def _spy(p, cfg, face_regions=None, bg_mask=None, split_tonal=False,
             shade_demand=False, design_ramp=None, **kwargs):
        captured["bg_mask"] = bg_mask
        return real_segment(p, cfg, face_regions=face_regions, bg_mask=bg_mask,
                            split_tonal=split_tonal, shade_demand=shade_demand,
                            design_ramp=design_ramp, **kwargs)

    monkeypatch.setattr(pipeline_module, "photo_segment", own_thread_only(_spy, real_segment))
    monkeypatch.setattr(
        pipeline_module, "remove_background_seam",
        own_thread_only(_seam_keeping(subject_frac), pipeline_module.remove_background_seam),
    )
    return captured


def _codes(result) -> dict:
    return {w["code"]: w for w in result.warnings}


def test_a_refused_cutout_hands_stage_2_no_subject_mask(monkeypatch):
    """A scene's cut-out (nothing kept) is refused, and `photo_segment` gets
    `bg_mask=None`: no region may be classed "background" on a mask the
    engine just declined to believe."""
    captured = _install_seam(monkeypatch, 0.0)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON))
    codes = _codes(result)
    assert PHOTO_CUTOUT_REFUSED in codes
    assert PHOTO_BACKGROUND_REMOVED not in codes
    assert PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE not in codes, (
        "a refusal is a reading of the photo, not a machine that cannot run rembg")
    assert captured["bg_mask"] is None
    assert result.regions, "the whole frame is sewn, not an empty hoop"


def test_a_kept_cutout_still_reaches_stage_2(monkeypatch):
    """40% of the frame as subject clears the floor and the mask goes through
    exactly as before the guard existed."""
    captured = _install_seam(monkeypatch, 0.4)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON))
    codes = _codes(result)
    assert PHOTO_BACKGROUND_REMOVED in codes and PHOTO_CUTOUT_REFUSED not in codes
    assert captured["bg_mask"] is not None and not bool(captured["bg_mask"].all())


def test_a_refused_cutout_lands_on_the_classical_route(monkeypatch):
    """Arm B: the refused frame takes the plain classical route -- the same
    stitch geometry as `photo_prep=False`, not merely the same region count
    (`test_background_removal` compares regions; this compares every stitch)."""
    _install_seam(monkeypatch, 0.0)
    refused = _plan_signature(_cfg(**CUTOUT_ON))
    classical = _plan_signature(_cfg(forced_class="photo_scene", photo_prep=False,
                                     photo_prep_background_removal=False))
    assert refused == classical


def test_a_refused_cutout_does_not_claim_prep_ran(monkeypatch):
    _install_seam(monkeypatch, 0.0)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON))
    codes = _codes(result)
    assert PHOTO_CUTOUT_REFUSED in codes
    assert PHOTO_PREP_APPLIED not in codes


# --- the corpus instrument reads the refusal ----------------------------------------

def test_summarise_reads_a_refused_cutout():
    warnings = [{"code": "PHOTO_CUTOUT_REFUSED", "kept_frac": 0.013, "min_kept": 0.2}]
    row = pc.summarise(_output(warnings=warnings), cap=6)
    assert row["cutout_removed_frac"] is None
    assert row["cutout_refused_kept_frac"] == pytest.approx(0.013)


def test_summarise_leaves_the_refusal_none_when_the_cutout_was_kept():
    warnings = [{"code": "PHOTO_BACKGROUND_REMOVED", "background_frac_before": 0.1,
                 "background_frac_after": 0.6}]
    row = pc.summarise(_output(warnings=warnings), cap=6)
    assert row["cutout_removed_frac"] == pytest.approx(0.5)
    assert row["cutout_refused_kept_frac"] is None


def test_the_sxs_page_shows_the_refusal():
    assert "cutout_refused_kept_frac" in {k for k, _, _ in pc.SXS_METRICS}


def test_capture_set_overrides_one_request_field():
    """`--set FIELD=JSON` is how the other arm of a flag is captured without
    editing the tree; the value is JSON, a non-JSON value a string."""
    assert pc.parse_sets(["photo_cutout_min_kept=0.0", "forced_class=photo_scene"]) == {
        "photo_cutout_min_kept": 0.0, "forced_class": "photo_scene"}
    assert pc.parse_sets([]) == {}
    with pytest.raises(ValueError):
        pc.parse_sets(["no_equals_sign"])
