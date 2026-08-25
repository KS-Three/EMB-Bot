"""YuNet face priors (photo plan §2 row 2, build step 3) — wired for real.

What this file pins:

1. The committed model is the exact artifact the probe verified: bytes on
   disk hash to the recorded sha256 (docs/photo-prep-deps-probe-2026-08-04.md
   §3), so a bad merge/LFS-pointer checkout fails loudly here rather than as
   silent zero detections.
2. TRUE-POSITIVE detection on a real face. The fixture is
   `skimage.data.astronaut()` — NASA's public-domain photograph of Eileen
   Collins, shipped INSIDE the scikit-image wheel this venv already pins:
   rights-safe, no network, no committed photograph, and a real face YuNet
   actually detects (synthetic face-like drawings do not reliably trigger
   it; measured while wiring this — detection holds down to a 160 px
   resize and drops out at 128).
3. Zero detections on a no-face image are `[]`, never `None` — the contract
   separates "ran, found nothing" from "cannot run".
4. The graceful fallback: model missing or corrupt -> `None` + an honest
   reason, and the pipeline says so in PHOTO_FACE_PRIORS_UNAVAILABLE while
   completing the job exactly as if no faces existed.
5. The wiring: PHOTO_FACES_DETECTED rides the photo_prep double gate (flag
   OFF = no face machinery, same as every other photo-prep behaviour); the
   face-local merge-threshold drop measurably splits shades inside a face
   that merge outside one; `_region_classes` maps eye/skin regions and
   nothing else.
6. The preflight face-size guard (photo plan §2 row 15): a detected face in
   a design that fits a 4x4" hoop blocks with a size-up suggestion; a
   design past that scale, or a plan with no face warning, stays silent.

Flat-lane byte-identity is NOT re-pinned here — the double gate's two
halves are already pinned by tests/test_photo_prep.py (flag ON + flat class,
flag OFF + photo class), and face detection sits strictly inside that gate.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

import digitizer_core.pipeline as pipeline_module
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.preflight import (
    FACE_BLOCK_HOOP_MM,
    FACE_TOO_SMALL,
    run_preflight,
)
from digitizer_core.stage1_photo_prep import (
    FaceRegion,
    YUNET_MODEL_PATH,
    YUNET_MODEL_SHA256,
    detect_faces_seam,
    face_detector_unavailable_reason,
)
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import _region_classes, segment
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.stitches import StitchPlan
from digitizer_core.warnings_codes import (
    PHOTO_FACE_PRIORS_UNAVAILABLE,
    PHOTO_FACES_DETECTED,
    PHOTO_SEGMENT_REGION_COUNT,
)

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
NO_FACE_FIXTURE = TESTDATA / "photo" / "region_blobs.png"


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


def _astronaut(size: int = 256) -> np.ndarray:
    """The rights-safe real-face fixture (see the module docstring), resized
    small enough to keep the pipeline-level tests fast while staying above
    the measured 160 px detection floor."""
    import cv2
    from skimage import data

    return cv2.resize(data.astronaut(), (size, size), interpolation=cv2.INTER_AREA)


# --- 1. The committed model is the verified artifact ---------------------------


def test_committed_model_matches_the_probe_recorded_sha256():
    assert YUNET_MODEL_PATH.is_file(), f"model not committed at {YUNET_MODEL_PATH}"
    blob = YUNET_MODEL_PATH.read_bytes()
    assert len(blob) == 232_589          # the probe doc's recorded size
    assert hashlib.sha256(blob).hexdigest() == YUNET_MODEL_SHA256
    assert face_detector_unavailable_reason() is None


# --- 2. True-positive detection on a real face ---------------------------------


def test_detects_the_real_face_with_five_landmarks_deterministically():
    rgb = _astronaut()
    faces = detect_faces_seam(rgb, _cfg())
    assert isinstance(faces, list) and len(faces) == 1
    f = faces[0]
    x, y, w, h = f.box_px
    assert w > 20 and h > 20                      # a real face span, not a speck
    assert 0 <= x and 0 <= y
    assert x + w <= rgb.shape[1] and y + h <= rgb.shape[0]
    assert f.score >= 0.9
    assert len(f.landmarks_px) == 5
    # The eye landmarks (YuNet order: right eye, left eye) sit inside the
    # upper half of the box — a sanity check that the 15-float row was
    # unpacked in the right order, not just that 5 pairs exist.
    for lx, ly in f.landmarks_px[:2]:
        assert x <= lx <= x + w
        assert y <= ly <= y + h / 2 + 1.0
    # Determinism: same raster, same detections.
    again = detect_faces_seam(rgb, _cfg())
    assert again == faces


# --- 3. No face -> [], never None ----------------------------------------------


def test_no_face_image_detects_zero_faces_not_unavailable():
    p = prep(NO_FACE_FIXTURE, _cfg())
    faces = detect_faces_seam(p.rgb, _cfg())
    assert faces == []


# --- 4. Graceful fallback ------------------------------------------------------


def test_missing_model_degrades_to_none_with_a_reason(monkeypatch, tmp_path):
    import digitizer_core.stage1_photo_prep as spp

    monkeypatch.setattr(spp, "YUNET_MODEL_PATH", tmp_path / "not_there.onnx")
    reason = spp.face_detector_unavailable_reason()
    assert reason is not None and "missing" in reason
    assert spp.detect_faces_seam(_astronaut(), _cfg()) is None


def test_corrupt_model_fails_integrity_and_degrades_to_none(monkeypatch, tmp_path):
    import digitizer_core.stage1_photo_prep as spp

    bad = tmp_path / "face_detection_yunet_2023mar.onnx"
    bad.write_bytes(b"not an onnx model" * 100)
    monkeypatch.setattr(spp, "YUNET_MODEL_PATH", bad)
    reason = spp.face_detector_unavailable_reason()
    assert reason is not None and "sha256" in reason
    assert spp.detect_faces_seam(_astronaut(), _cfg()) is None


# `photo_prep_background_removal=False` is PINNED in the prep-gate tests
# below as of 2026-08-24. Kent flipped that default ON that day, and a
# requested-but-unavailable cutout now skips the entire prep block
# (see pipeline.build_generation) — so without the pin these would stop
# exercising the gate they are named for and quietly start exercising
# the fallback. Exactly why every forced-class acceptance arm pins
# `shade_palette_bind` after its own default moved.
def test_pipeline_says_so_when_the_detector_is_unavailable(monkeypatch):
    """The documented no-op fallback, observed at the pipeline boundary: the
    job completes and carries PHOTO_FACE_PRIORS_UNAVAILABLE instead of
    silently skipping faces."""
    monkeypatch.setattr(
        pipeline_module, "detect_faces_seam", lambda rgb, cfg: None
    )
    result = run_stages(
        NO_FACE_FIXTURE, _cfg(forced_class="photo_scene", photo_prep=True,
                              photo_prep_background_removal=False)
    )
    hits = [w for w in result.warnings
            if w["code"] == PHOTO_FACE_PRIORS_UNAVAILABLE]
    assert len(hits) == 1
    assert hits[0]["reason"]
    assert result.regions, "the job itself must still complete"


# --- 5. The wiring -------------------------------------------------------------


def test_pipeline_emits_faces_detected_behind_the_photo_prep_gate():
    rgb = _astronaut()

    on = run_stages(rgb, _cfg(forced_class="photo_subject", photo_prep=True,
                              photo_prep_background_removal=False))
    hits = [w for w in on.warnings if w["code"] == PHOTO_FACES_DETECTED]
    assert len(hits) == 1
    w = hits[0]
    assert w["count"] == 1
    span = w["faces"][0]["span_mm"]
    # 256 px / 80 mm target: the astronaut face box (~45 px at this size)
    # spans roughly 12-20 mm — assert scale-sanity, not an exact geometry.
    assert 5.0 < span[0] < 40.0 and 5.0 < span[1] < 40.0
    assert w["faces"][0]["score"] >= 0.9

    off = run_stages(rgb, _cfg(forced_class="photo_subject", photo_prep=False))
    codes = {x["code"] for x in off.warnings}
    assert PHOTO_FACES_DETECTED not in codes
    assert PHOTO_FACE_PRIORS_UNAVAILABLE not in codes


def test_no_face_photo_run_emits_neither_face_warning():
    result = run_stages(
        NO_FACE_FIXTURE, _cfg(forced_class="photo_scene", photo_prep=True,
                              photo_prep_background_removal=False)
    )
    codes = {w["code"] for w in result.warnings}
    assert PHOTO_FACES_DETECTED not in codes
    assert PHOTO_FACE_PRIORS_UNAVAILABLE not in codes


def _two_tone_blob(a: int = 118, b: int = 138) -> np.ndarray:
    """Two gray shades ~7 L* apart on a white canvas: under the global
    merge threshold (10) they fuse into one region; under the face-local
    drop (x0.5 -> 5) they survive separately. Chosen against the module's
    own constants, same spirit as MERGE_DELTAE00_THRESH's measured elbow."""
    img = np.full((200, 200, 3), 255, np.uint8)
    img[50:150, 50:100] = a
    img[50:150, 100:150] = b
    return img


def _whole_raster_face(h: int, w: int) -> FaceRegion:
    return FaceRegion(
        box_px=(0.0, 0.0, float(w), float(h)),
        landmarks_px=(
            (w * 0.4, h * 0.45), (w * 0.6, h * 0.45), (w * 0.5, h * 0.55),
            (w * 0.42, h * 0.65), (w * 0.58, h * 0.65),
        ),
        score=0.95,
    )


def _merged_regions(q) -> int:
    w = [x for x in q.warnings if x["code"] == PHOTO_SEGMENT_REGION_COUNT][0]
    return w["merged_regions"]


def test_face_local_threshold_splits_shades_that_merge_outside_a_face():
    cfg = _cfg()
    p = prep(_two_tone_blob(), cfg)
    h, w = p.rgb.shape[:2]

    without = _merged_regions(segment(p, cfg, face_regions=None))
    with_face = _merged_regions(
        segment(p, cfg, face_regions=[_whole_raster_face(h, w)])
    )
    assert without == 1, "fixture drifted: shades must merge under the global threshold"
    assert with_face == 2, "the face-local threshold drop failed to protect the split"


def test_region_classes_maps_eyes_then_skin_then_none():
    shape = (200, 200)
    face = FaceRegion(
        box_px=(40.0, 40.0, 80.0, 100.0),
        landmarks_px=(
            (60.0, 75.0), (100.0, 75.0), (80.0, 95.0),
            (65.0, 115.0), (95.0, 115.0),
        ),
        score=0.9,
    )

    def region(y0, y1, x0, x1):
        m = np.zeros(shape, bool)
        m[y0:y1, x0:x1] = True
        return RegionMask.from_full(m, layer=0, source="photo")

    eye = region(70, 80, 55, 65)        # small patch on the right-eye disk
    skin = region(80, 110, 60, 100)     # mid-face patch inside the ellipse
    elsewhere = region(160, 190, 160, 190)   # far corner, no prior covers it

    classes = _region_classes([eye, skin, elsewhere], [face])
    assert classes == ["eyes", "skin", None]
    # And the no-face degradation stays the documented all-None contract.
    assert _region_classes([eye, skin, elsewhere], None) == [None, None, None]
    assert _region_classes([eye, skin, elsewhere], []) == [None, None, None]


def test_region_classes_maps_subject_and_background_from_a_bg_mask():
    """The subject/background half of `_region_classes` (wired 2026-08-05,
    consuming `stage1_photo_prep.remove_background_seam`'s output one hop
    downstream, via `pipeline.run_stages`'s `subject_bg_mask`). Same
    majority-of-pixels pattern as eyes/skin, and eyes/skin still win when
    both a face and a bg_mask are present — a region cannot be BOTH an eye
    and background."""
    shape = (200, 200)

    def region(y0, y1, x0, x1):
        m = np.zeros(shape, bool)
        m[y0:y1, x0:x1] = True
        return RegionMask.from_full(m, layer=0, source="photo")

    bg_mask = np.zeros(shape, bool)
    bg_mask[:, 100:] = True  # right half of the frame is background

    bg_region = region(20, 180, 120, 180)     # entirely inside bg_mask
    subj_region = region(20, 180, 10, 80)     # entirely outside bg_mask

    assert _region_classes([bg_region, subj_region], None, bg_mask) == [
        "background", "subject",
    ]
    # No bg_mask at all -> the documented pre-rembg degradation, unchanged:
    # every non-face region stays None, exactly like the no-face case above.
    assert _region_classes([bg_region, subj_region], None, None) == [None, None]

    # eyes/skin still take priority over bg_mask when a face is ALSO present.
    face = FaceRegion(
        box_px=(40.0, 40.0, 80.0, 100.0),
        landmarks_px=(
            (60.0, 75.0), (100.0, 75.0), (80.0, 95.0),
            (65.0, 115.0), (95.0, 115.0),
        ),
        score=0.9,
    )
    eye = region(70, 80, 55, 65)  # x 55-65: outside bg_mask (x >= 100)
    # Without face priors this patch would class "subject" (it sits outside
    # bg_mask); with a face present it must still class "eyes" first.
    assert _region_classes([eye], [face], bg_mask) == ["eyes"]


# --- 6. The preflight face-size guard ------------------------------------------


def _plan_with(warnings: list[dict], size_mm: tuple[float, float]) -> StitchPlan:
    return StitchPlan(blocks=[], palette=[], warnings=warnings,
                      design_size_mm=size_mm)


def _faces_warning(count: int = 1) -> dict:
    return {"code": PHOTO_FACES_DETECTED, "message": "faces", "count": count,
            "faces": [{"span_mm": [15.0, 18.0], "score": 0.9}] * count}


def test_face_in_a_4x4_hoop_design_blocks_with_a_size_up_suggestion():
    plan = _plan_with([_faces_warning()], (80.0, 96.0))
    report = run_preflight(None, plan, _cfg())
    hits = [f for f in report["findings"] if f["code"] == FACE_TOO_SMALL]
    assert len(hits) == 1
    f = hits[0]
    assert f["severity"] == "block"
    assert "5x7" in f["message"]
    assert f["extra"]["count"] == 1
    assert f["extra"]["design_mm"] == [80.0, 96.0]
    assert f["extra"]["fits_hoop_mm"] == FACE_BLOCK_HOOP_MM
    assert report["metrics"]["faces_detected"] == 1


def test_face_guard_is_silent_past_the_4x4_scale_and_without_faces():
    # Needs a bigger hoop than 4x4 already — the stated 5x7 minimum is met.
    big = run_preflight(None, _plan_with([_faces_warning(2)], (150.0, 96.0)), _cfg())
    assert FACE_TOO_SMALL not in {f["code"] for f in big["findings"]}
    assert big["metrics"]["faces_detected"] == 2

    # No face warning at all (every non-photo lane): silent, metric says 0.
    none = run_preflight(None, _plan_with([], (80.0, 96.0)), _cfg())
    assert FACE_TOO_SMALL not in {f["code"] for f in none["findings"]}
    assert none["metrics"]["faces_detected"] == 0


def test_face_block_hoop_boundary_matches_the_literal_4in_conversion():
    # FACE_BLOCK_HOOP_MM must be 4 * 25.4 = 101.6mm (the app's own hoop-size
    # convention, src/units.js inToMm), matching FACE_MIN_HOOP_MM's 5x7
    # derivation (127.0, 178.0) — not the rounded-to-100 nominal figure. A
    # design that still needs a real 4x4in hoop (e.g. 101mm) must still warn.
    assert FACE_BLOCK_HOOP_MM == 101.6
    still_needs_4x4 = run_preflight(
        None, _plan_with([_faces_warning()], (101.0, 96.0)), _cfg()
    )
    assert FACE_TOO_SMALL in {f["code"] for f in still_needs_4x4["findings"]}
