"""rembg background removal (photo plan §2 row 1, build step 3's isolated-venv
slice) — `stage1_photo_prep.remove_background_seam`. What this file pins:

1. REAL cutout on a real photo, through the actual isolated-venv subprocess,
   when that venv is built in this environment (`digitizer/rembg_isolated/`,
   see its README.md — NOT committed, so this half of the file SKIPS rather
   than fails when the venv isn't there). The fixture is
   `skimage.data.astronaut()`, the same rights-safe real photo
   `tests/test_face_priors.py` already uses — no network, no new committed
   image, a real subject/background split rembg actually resolves.
2. The graceful fallback, in both of its environment-level forms: worker
   script missing and isolated venv missing each degrade to `(None, reason)`
   deterministically, with an honest reason — never an exception.
3. Runtime subprocess failures (nonzero exit, timeout) ALSO degrade to
   `(None, reason)` rather than raising — this half needs no isolated venv
   at all, since it mocks `subprocess.run` directly, so it always runs.
4. The wiring: `pipeline.run_stages` says PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE
   when the seam can't run, and the job still completes; a successful cutout
   grows `bg_mask` and reports PHOTO_BACKGROUND_REMOVED with before/after
   background fraction.
5. The gate: `photo_prep_background_removal` is a THIRD gate on top of
   `photo_prep` + photo classification — flag off never calls the seam even
   when photo_prep is on, and the flat lane stays byte-identical regardless
   of this flag (it never reaches the double-gated block at all).
6. `_clean_background_mask`'s own contract: morphology at the texture-kill
   scale plus small-island dropping, measured on a synthetic mask.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

import digitizer_core.pipeline as pipeline_module
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.stage1_photo_prep import (
    REMBG_ALPHA_THRESHOLD,
    _clean_background_mask,
    background_removal_unavailable_reason,
    remove_background_seam,
)
from digitizer_core.warnings_codes import (
    PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE,
    PHOTO_BACKGROUND_REMOVED,
)

from .test_flat_lane_byte_identical import GOLDEN
from .test_flat_lane_byte_identical import _snapshot as _golden_snapshot

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


def _astronaut(size: int = 256) -> np.ndarray:
    """The same rights-safe real-photo fixture test_face_priors.py uses
    (skimage.data.astronaut, bundled in the scikit-image wheel this venv
    already pins — no network, no committed photograph). A real person
    against a real (if busy) background: flag, backdrop, a shuttle model —
    exactly the kind of scene rembg's isnet-general-use tier is built for,
    not a synthetic cutout an easier fixture would flatter."""
    import cv2 as _cv2
    from skimage import data

    return _cv2.resize(data.astronaut(), (size, size), interpolation=_cv2.INTER_AREA)


REMBG_AVAILABLE = background_removal_unavailable_reason() is None
SKIP_REASON = "isolated rembg venv not built in this environment — see digitizer/rembg_isolated/README.md"


# --- 1. Real cutout, through the actual isolated venv ---------------------------


@pytest.mark.skipif(not REMBG_AVAILABLE, reason=SKIP_REASON)
def test_real_background_removal_on_a_real_photo():
    rgb = _astronaut()
    mask, reason = remove_background_seam(rgb, px_per_mm=4.0, cfg=_cfg())
    assert reason is None
    assert mask is not None
    assert mask.shape == rgb.shape[:2] and mask.dtype == bool

    frac = float(mask.mean())
    # A real photo with a real subject: neither "everything is background"
    # nor "nothing is" would mean the cutout did its job.
    assert 0.05 < frac < 0.85, f"implausible background fraction {frac:.3f}"

    # The astronaut's face sits in the upper-middle of the frame at this
    # crop — that patch must survive as foreground, not get swept into
    # background by a degenerate mask.
    h, w = rgb.shape[:2]
    face_patch = mask[int(h * 0.15):int(h * 0.35), int(w * 0.35):int(w * 0.65)]
    assert face_patch.mean() < 0.5, "the astronaut's own face was marked background"

    # Determinism: same raster, same worker, same mask.
    again, reason2 = remove_background_seam(rgb, px_per_mm=4.0, cfg=_cfg())
    assert reason2 is None
    assert np.array_equal(mask, again)


@pytest.mark.skipif(not REMBG_AVAILABLE, reason=SKIP_REASON)
def test_pipeline_grows_bg_mask_and_reports_background_removed():
    rgb = _astronaut()
    cfg = _cfg(
        forced_class="photo_subject",
        photo_prep=True,
        photo_prep_background_removal=True,
    )
    result = run_stages(rgb, cfg)
    hits = [w for w in result.warnings if w["code"] == PHOTO_BACKGROUND_REMOVED]
    assert len(hits) == 1
    w = hits[0]
    assert w["background_frac_after"] >= w["background_frac_before"]
    assert not any(
        x["code"] == PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE for x in result.warnings
    )
    assert result.regions, "the job itself must still complete"


# --- 2. Graceful fallback: environment-level -------------------------------------


def test_missing_worker_script_degrades_to_none_with_a_reason(monkeypatch, tmp_path):
    import digitizer_core.stage1_photo_prep as spp

    monkeypatch.setattr(spp, "REMBG_WORKER_PATH", tmp_path / "not_there.py")
    reason = spp.background_removal_unavailable_reason()
    assert reason is not None and "worker script missing" in reason

    mask, got_reason = spp.remove_background_seam(_astronaut(64), 4.0, _cfg())
    assert mask is None
    assert got_reason == reason


def test_missing_isolated_venv_degrades_to_none_with_a_reason(monkeypatch, tmp_path):
    import digitizer_core.stage1_photo_prep as spp

    monkeypatch.setattr(spp, "REMBG_VENV_PYTHON", tmp_path / "venv" / "bin" / "python")
    reason = spp.background_removal_unavailable_reason()
    assert reason is not None and "isolated rembg venv not found" in reason

    mask, got_reason = spp.remove_background_seam(_astronaut(64), 4.0, _cfg())
    assert mask is None
    assert got_reason == reason


def test_pipeline_says_so_when_background_removal_is_unavailable(monkeypatch):
    """The documented no-op fallback, observed at the pipeline boundary: the
    job completes and carries PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE instead
    of silently skipping the cutout — mirrors
    test_pipeline_says_so_when_the_detector_is_unavailable in
    tests/test_face_priors.py."""
    monkeypatch.setattr(
        pipeline_module,
        "remove_background_seam",
        lambda rgb, px_per_mm, cfg: (None, "isolated rembg venv not found (test)"),
    )
    result = run_stages(
        TESTDATA / "photo" / "region_blobs.png",
        _cfg(
            forced_class="photo_scene",
            photo_prep=True,
            photo_prep_background_removal=True,
        ),
    )
    hits = [
        w for w in result.warnings
        if w["code"] == PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE
    ]
    assert len(hits) == 1
    assert hits[0]["reason"]
    assert result.regions, "the job itself must still complete"


# --- 3. Graceful fallback: runtime subprocess failures ---------------------------
# These need no isolated venv at all — subprocess.run itself is mocked, so
# they always run regardless of whether digitizer/rembg_isolated/ is built.


def test_subprocess_timeout_degrades_to_none_with_a_reason(monkeypatch):
    import digitizer_core.stage1_photo_prep as spp

    monkeypatch.setattr(spp, "background_removal_unavailable_reason", lambda: None)
    monkeypatch.setattr(spp, "REMBG_VENV_PYTHON", Path("/fake/python"))
    monkeypatch.setattr(spp, "REMBG_WORKER_PATH", Path("/fake/worker.py"))

    def _raise_timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="rembg_worker.py", timeout=1.0)

    monkeypatch.setattr(spp.subprocess, "run", _raise_timeout)
    mask, reason = spp.remove_background_seam(
        _astronaut(64), 4.0, _cfg(photo_prep_background_removal_timeout_s=1.0)
    )
    assert mask is None
    assert reason is not None and "timed out" in reason


def test_subprocess_nonzero_exit_degrades_to_none_with_a_reason(monkeypatch):
    import digitizer_core.stage1_photo_prep as spp

    monkeypatch.setattr(spp, "background_removal_unavailable_reason", lambda: None)
    monkeypatch.setattr(spp, "REMBG_VENV_PYTHON", Path("/fake/python"))
    monkeypatch.setattr(spp, "REMBG_WORKER_PATH", Path("/fake/worker.py"))

    class _Proc:
        returncode = 4
        stdout = ""
        stderr = "rembg_worker: background removal failed: boom\n"

    monkeypatch.setattr(spp.subprocess, "run", lambda *a, **kw: _Proc())
    mask, reason = spp.remove_background_seam(_astronaut(64), 4.0, _cfg())
    assert mask is None
    assert reason is not None and "exited 4" in reason and "boom" in reason


def test_launch_failure_degrades_to_none_with_a_reason(monkeypatch):
    import digitizer_core.stage1_photo_prep as spp

    monkeypatch.setattr(spp, "background_removal_unavailable_reason", lambda: None)
    monkeypatch.setattr(spp, "REMBG_VENV_PYTHON", Path("/fake/python"))
    monkeypatch.setattr(spp, "REMBG_WORKER_PATH", Path("/fake/worker.py"))

    def _raise_oserror(*a, **kw):
        raise OSError("no such file")

    monkeypatch.setattr(spp.subprocess, "run", _raise_oserror)
    mask, reason = spp.remove_background_seam(_astronaut(64), 4.0, _cfg())
    assert mask is None
    assert reason is not None and "failed to launch" in reason


# --- 4. The gate ------------------------------------------------------------------


def test_flag_off_never_calls_the_seam_even_with_photo_prep_on(monkeypatch):
    called = []
    monkeypatch.setattr(
        pipeline_module,
        "remove_background_seam",
        lambda rgb, px_per_mm, cfg: called.append(1) or (None, "should not be called"),
    )
    result = run_stages(
        TESTDATA / "photo" / "region_blobs.png",
        _cfg(forced_class="photo_scene", photo_prep=True,
             photo_prep_background_removal=False),
    )
    assert called == []
    codes = {w["code"] for w in result.warnings}
    assert PHOTO_BACKGROUND_REMOVED not in codes
    assert PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE not in codes


def test_flag_on_but_photo_prep_off_never_calls_the_seam(monkeypatch):
    """photo_prep itself is the outer gate — background removal cannot run
    on its own even when explicitly requested."""
    called = []
    monkeypatch.setattr(
        pipeline_module,
        "remove_background_seam",
        lambda rgb, px_per_mm, cfg: called.append(1) or (None, "should not be called"),
    )
    run_stages(
        TESTDATA / "photo" / "region_blobs.png",
        _cfg(forced_class="photo_scene", photo_prep=False,
             photo_prep_background_removal=True),
    )
    assert called == []


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flat_lane_is_byte_identical_with_the_flag_on(fixture):
    """The classification half of the gate: turning
    photo_prep_background_removal (and photo_prep) on must not move one
    byte for a flat-classified design — mirrors
    test_photo_prep.py::test_flag_on_is_byte_identical_for_flat_classified_designs."""
    from digitizer_core.pipeline import digitize

    result, plan = digitize(
        TESTDATA / fixture,
        PipelineConfig(
            target_width_mm=80.0,
            photo_prep=True,
            photo_prep_background_removal=True,
        ),
    )
    snap = {
        "shape_ids": sorted(r.shape_id for r in result.regions),
        "areas_mm2": sorted(round(r.area_mm2, 4) for r in result.regions),
        "warnings": sorted(
            f"{w['code']}:{w.get('count', '')}" for w in result.warnings
        ),
        "stitch_count": sum(len(r.points) for _, r in plan.iter_runs()),
        "stitch_coords": [
            [round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
            for _, r in plan.iter_runs()
            for x, y in r.points
        ],
    }
    assert snap == _golden_snapshot(fixture)


# --- 6. The class-weight wiring: bg_mask reaches _region_classes ------------------
# The literal downstream gap this module used to leave open: `remove_
# background_seam`'s own mask reaching `stage2_photo_segment._region_classes`
# one hop further than `p.bg_mask` did (previously only OR'd into it for
# stage-1-style consumers). See `stage2_photo_segment._region_classes` and
# `palette.py`'s module docstring for the class-weight math; this section
# proves the WIRING — that `pipeline.run_stages` passes a real mask through
# to `photo_segment`, and ONLY a real one.


def test_bg_mask_reaches_photo_segment_when_rembg_succeeds(monkeypatch):
    captured = {}
    real_segment = pipeline_module.photo_segment

    def _spy(p, cfg, face_regions=None, bg_mask=None):
        captured["bg_mask"] = bg_mask
        return real_segment(p, cfg, face_regions=face_regions, bg_mask=bg_mask)

    monkeypatch.setattr(pipeline_module, "photo_segment", _spy)
    monkeypatch.setattr(
        pipeline_module,
        "remove_background_seam",
        lambda rgb, px_per_mm, cfg: (np.zeros(rgb.shape[:2], bool), None),
    )
    result = run_stages(
        TESTDATA / "photo" / "region_blobs.png",
        _cfg(forced_class="photo_scene", photo_prep=True,
             photo_prep_background_removal=True),
    )
    assert "bg_mask" in captured, "photo_segment was never called"
    assert captured["bg_mask"] is not None
    assert captured["bg_mask"].dtype == bool
    assert result.regions, "the job itself must still complete"


def test_bg_mask_stays_none_when_rembg_is_unavailable(monkeypatch):
    """The honesty guard this seam depends on: a failed/unavailable rembg
    pass must NOT let `p.bg_mask`'s border-flood default masquerade as a
    real subject/background mask downstream — see `_region_classes`'
    docstring for why that would misrepresent what the mask actually
    knows."""
    captured = {}
    real_segment = pipeline_module.photo_segment

    def _spy(p, cfg, face_regions=None, bg_mask=None):
        captured["bg_mask"] = bg_mask
        return real_segment(p, cfg, face_regions=face_regions, bg_mask=bg_mask)

    monkeypatch.setattr(pipeline_module, "photo_segment", _spy)
    monkeypatch.setattr(
        pipeline_module,
        "remove_background_seam",
        lambda rgb, px_per_mm, cfg: (None, "unavailable (test)"),
    )
    run_stages(
        TESTDATA / "photo" / "region_blobs.png",
        _cfg(forced_class="photo_scene", photo_prep=True,
             photo_prep_background_removal=True),
    )
    assert "bg_mask" in captured, "photo_segment was never called"
    assert captured["bg_mask"] is None


def test_bg_mask_stays_none_when_the_flag_is_off(monkeypatch):
    captured = {}
    real_segment = pipeline_module.photo_segment

    def _spy(p, cfg, face_regions=None, bg_mask=None):
        captured["bg_mask"] = bg_mask
        return real_segment(p, cfg, face_regions=face_regions, bg_mask=bg_mask)

    monkeypatch.setattr(pipeline_module, "photo_segment", _spy)
    run_stages(
        TESTDATA / "photo" / "region_blobs.png",
        _cfg(forced_class="photo_scene", photo_prep=True,
             photo_prep_background_removal=False),
    )
    assert "bg_mask" in captured, "photo_segment was never called"
    assert captured["bg_mask"] is None


# --- 7. _clean_background_mask's own contract -------------------------------------


def test_clean_background_mask_drops_small_islands_and_smooths_speckle():
    h, w = 100, 100
    bg = np.zeros((h, w), bool)
    bg[:, :] = True          # start all-background
    bg[20:80, 20:80] = False  # a real 60x60 foreground block survives

    # A single-pixel background speck INSIDE the foreground block — noise,
    # not a real gap; must be filled back to foreground (i.e. absent from
    # the cleaned background mask).
    bg[50, 50] = True
    # A larger, real background island well outside the foreground block —
    # must survive (it is genuinely background, and big enough to matter).
    bg[5:15, 5:15] = True

    cleaned = _clean_background_mask(bg, kill_px=3, min_island_px=9.0)

    assert cleaned[50, 50] == False, "a single-pixel speck was not cleaned up"
    assert cleaned[10, 10] == True, "a real background island was dropped"
    # The foreground block's interior is still foreground (not swallowed by
    # the morphology closing the background around it).
    assert cleaned[50, 20:80].sum() < 60, "morphology ate real foreground"


def test_clean_background_mask_is_a_noop_on_a_clean_mask():
    h, w = 60, 60
    bg = np.zeros((h, w), bool)
    bg[:20, :] = True
    cleaned = _clean_background_mask(bg, kill_px=2, min_island_px=4.0)
    # A big, already-clean rectangular island survives essentially intact —
    # morphology at a small kill scale should not meaningfully erode a
    # region much larger than the kernel. The close step can bleed the edge
    # by about a kernel width (measured: 2 rows at kill_px=2), so the "stays
    # clean" check starts a kernel width past the boundary, not right at it.
    assert cleaned[:20, :].mean() > 0.9
    assert cleaned[20 + 4:, :].mean() == 0.0


def test_alpha_threshold_is_the_documented_midpoint():
    assert REMBG_ALPHA_THRESHOLD == 128
