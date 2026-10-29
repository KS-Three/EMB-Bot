"""The subject cut-out's "no subject found" guard
(`cfg.photo_cutout_min_subject_frac`, built OFF 2026-10-28).

On the 18 Commons corpus photographs (2026-10-28, rembg `isnet-general-use`),
a SCENE gets no subject: alpha >= 128 covers 0.01-5.4% of the frame
(snow_highkey 0.0001, landscape_lake 0.0006, underwater_reef 0.003,
night_neon 0.005, night_skyline 0.014, stained_glass 0.054), where every row
with a real subject reads 0.27-0.76 (fireworks 0.27 ... architecture 0.76).
`remove_background_seam` thresholds at 128, its island cleanup only fills
back SMALL background specks, and `pipeline.run_stages` accepted any
non-None mask -- so the whole frame became background and the lane sewed
0-3,117 stitches of a 13,000-40,000-stitch photograph (census item 1,
docs/photo-style-census-2026-10-27.md).

The guard reads the cut-out's own SUBJECT share of the frame (not the
after-minus-before `cutout_removed_frac`, which a border-flood background
under-reads) and, below `cfg.photo_cutout_min_subject_frac`, refuses the
cut-out: stage 1's border-flood `bg_mask` stays, `subject_bg_mask` stays None
(no dishonest "background" class for the palette), and the job says so with
PHOTO_BACKGROUND_KEPT instead of PHOTO_BACKGROUND_REMOVED. None is OFF: the
tree as it was, byte for byte -- the first test here pins that arm.

Sited at 0.12, the geometric midpoint of the 0.054 -> 0.27 gap (2.2x clear
on both sides). The corpus images are not committed (public repo), so the
siting is recorded in the design doc and the real-photo half of this file
runs only where the isolated rembg venv is built.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import digitizer_core.pipeline as pipeline_module
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.warnings_codes import (
    PHOTO_BACKGROUND_KEPT,
    PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE,
    PHOTO_BACKGROUND_REMOVED,
    PHOTO_PREP_APPLIED,
)
from tests.conftest import own_thread_only
from tools import photo_corpus as pc

from .test_background_removal import (
    REMBG_AVAILABLE,
    SKIP_REASON,
    TESTDATA,
    _astronaut,
    _cfg,
    _plan_signature,
)
from .test_photo_corpus import _output

SITED = 0.12
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


# --- the flag and its OFF arm ----------------------------------------------------

def test_the_guard_ships_off():
    assert PipelineConfig().photo_cutout_min_subject_frac is None


def test_off_arm_accepts_an_all_background_cutout_exactly_as_before(monkeypatch):
    """None is today's tree: a mask that calls EVERY pixel background is
    accepted, PHOTO_BACKGROUND_REMOVED reports 100% background, and the
    whole frame is handed to stage 2 as background."""
    captured = _install_seam(monkeypatch, 0.0)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=None))
    codes = _codes(result)
    assert PHOTO_BACKGROUND_REMOVED in codes
    assert codes[PHOTO_BACKGROUND_REMOVED]["background_frac_after"] == 1.0
    assert PHOTO_BACKGROUND_KEPT not in codes
    assert captured["bg_mask"] is not None and bool(captured["bg_mask"].all())


# --- the ON arm --------------------------------------------------------------------

def test_a_cutout_with_no_subject_is_refused_and_the_frame_kept(monkeypatch):
    captured = _install_seam(monkeypatch, 0.0)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=SITED))
    codes = _codes(result)
    assert PHOTO_BACKGROUND_REMOVED not in codes, "a refused cut-out must not claim it removed anything"
    assert PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE not in codes, (
        "a refusal is a reading of the photo, not a machine that cannot run rembg")
    kept = codes[PHOTO_BACKGROUND_KEPT]
    assert kept["subject_frac"] == 0.0
    assert kept["min_subject_frac"] == SITED
    assert captured["bg_mask"] is None, "stage 2 must get NO subject/background claim"
    assert result.regions, "the whole frame is sewn, not an empty hoop"


def test_the_refusal_reads_the_cutout_s_own_subject_share(monkeypatch):
    """5% of the frame kept as subject, against 12%: refused, and the
    warning carries the share it read (rounded to 3 places like the
    before/after fractions PHOTO_BACKGROUND_REMOVED reports)."""
    _install_seam(monkeypatch, 0.05)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=SITED))
    kept = _codes(result)[PHOTO_BACKGROUND_KEPT]
    assert kept["subject_frac"] == pytest.approx(0.05, abs=0.005)
    assert kept["background_frac_would_be"] == pytest.approx(0.95, abs=0.005)


def test_a_cutout_with_a_real_subject_is_kept_exactly_as_before(monkeypatch):
    """40% of the frame as subject clears the gate: the ON arm is the OFF
    arm for every photo rembg reads a subject in."""
    captured = _install_seam(monkeypatch, 0.4)
    on = run_stages(BLOBS, _cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=SITED))
    codes = _codes(on)
    assert PHOTO_BACKGROUND_REMOVED in codes and PHOTO_BACKGROUND_KEPT not in codes
    assert captured["bg_mask"] is not None and not bool(captured["bg_mask"].all())
    sig_on = _plan_signature(_cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=SITED))
    sig_off = _plan_signature(_cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=None))
    assert sig_on == sig_off


def test_at_the_threshold_the_cutout_is_kept(monkeypatch):
    """`<`, not `<=`: a subject share equal to the floor passes."""
    _install_seam(monkeypatch, SITED)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=SITED))
    codes = _codes(result)
    assert PHOTO_BACKGROUND_REMOVED in codes and PHOTO_BACKGROUND_KEPT not in codes


def test_the_guard_never_runs_when_the_cutout_is_off(monkeypatch):
    """The flag rides the cut-out: with `photo_prep_background_removal` OFF
    the seam is never called, so there is nothing to refuse and no warning."""
    calls = []
    monkeypatch.setattr(
        pipeline_module, "remove_background_seam",
        own_thread_only(lambda rgb, px_per_mm, cfg: calls.append(1) or (None, "x"),
                        pipeline_module.remove_background_seam),
    )
    result = run_stages(BLOBS, _cfg(forced_class="photo_scene", photo_prep=True,
                                    photo_prep_background_removal=False,
                                    photo_cutout_min_subject_frac=SITED))
    assert calls == []
    assert PHOTO_BACKGROUND_KEPT not in _codes(result)


# --- the real seam ------------------------------------------------------------------

@pytest.mark.skipif(not REMBG_AVAILABLE, reason=SKIP_REASON)
def test_a_real_subject_photo_clears_the_sited_floor():
    """The astronaut (a real subject against a busy backdrop) must keep well
    more than 12% of the frame as subject through the real worker -- the
    gate is for frames with NO subject, and a portrait is the opposite case."""
    from digitizer_core.stage1_photo_prep import remove_background_seam
    mask, reason = remove_background_seam(_astronaut(), px_per_mm=4.0, cfg=_cfg())
    assert reason is None and mask is not None
    assert float((~mask).mean()) >= SITED


# --- the corpus instrument reads the refusal ----------------------------------------

def test_summarise_reads_a_refused_cutout():
    warnings = [{"code": "PHOTO_BACKGROUND_KEPT", "subject_frac": 0.004,
                 "min_subject_frac": 0.12, "background_frac_before": 0.0,
                 "background_frac_would_be": 0.996}]
    row = pc.summarise(_output(warnings=warnings), cap=6)
    assert row["cutout_removed_frac"] is None
    assert row["cutout_refused_subject_frac"] == pytest.approx(0.004)


def test_summarise_leaves_the_refusal_none_when_the_cutout_was_kept():
    warnings = [{"code": "PHOTO_BACKGROUND_REMOVED", "background_frac_before": 0.1,
                 "background_frac_after": 0.6}]
    row = pc.summarise(_output(warnings=warnings), cap=6)
    assert row["cutout_removed_frac"] == pytest.approx(0.5)
    assert row["cutout_refused_subject_frac"] is None


def test_the_sxs_page_shows_the_refusal():
    assert "cutout_refused_subject_frac" in {k for k, _, _ in pc.SXS_METRICS}


def test_capture_set_overrides_one_request_field():
    """`--set FIELD=JSON` is how an ON arm of a flag built OFF is captured
    without editing the tree; the value is JSON, a non-JSON value a string."""
    assert pc.parse_sets(["photo_cutout_min_subject_frac=0.12", "forced_class=photo_scene"]) == {
        "photo_cutout_min_subject_frac": 0.12, "forced_class": "photo_scene"}
    assert pc.parse_sets([]) == {}
    with pytest.raises(ValueError):
        pc.parse_sets(["no_equals_sign"])


# --- the shipped arm: a refused cut-out skips prep too ----------------------------

def test_a_refused_cutout_lands_on_the_classical_route(monkeypatch):
    """Arm B (Kent 2026-10-28, "measure A vs B, ship better": prep-skipped
    beat prep-kept on fidelity_cc on four of the six corpus scenes). A
    refused cut-out must land on the PLAIN classical route -- the same
    geometry as `photo_prep=False`, derived, not pinned."""
    _install_seam(monkeypatch, 0.0)
    refused = _plan_signature(_cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=SITED))
    classical = _plan_signature(_cfg(forced_class="photo_scene", photo_prep=False,
                                     photo_prep_background_removal=False))
    assert refused == classical


def test_a_refused_cutout_does_not_claim_prep_ran(monkeypatch):
    _install_seam(monkeypatch, 0.0)
    result = run_stages(BLOBS, _cfg(**CUTOUT_ON, photo_cutout_min_subject_frac=SITED))
    codes = _codes(result)
    assert PHOTO_BACKGROUND_KEPT in codes
    assert PHOTO_PREP_APPLIED not in codes
