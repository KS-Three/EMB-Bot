"""Stage 1.25: detecting a photograph from EXIF and the shipped face detector.

Quality review 2026-09-08 item 13. `config.is_photographic` decides whether
the photographic machinery applies, and it was DECLARED-only because stage 0's
colour statistics cannot answer it — a real photograph reads LESS photographic
than two gradient logos on stage 0's own primary gate (the measurement is in
that function's docstring).

Two signals that are not colour statistics do separate them, and the repo
already owned both: EXIF camera Make/Model and the YuNet detector at
`stage1_photo_prep.detect_faces_seam` — 4/4 photos and 4/4 portraits against
0/9 logos when they were measured 2026-08-25 (DOCTRINE; PR #245).

WHAT THIS FILE CAN AND CANNOT MEASURE. No committed fixture carries EXIF at
all — every photo here was either re-saved (owl_kent) or written by this
repo's own generator — so the EXIF TRUE positive is tested against a header
this file writes, which tests the READER and claims nothing about artwork.
The face true positive goes through a monkeypatched seam for the same reason:
the only real portraits are Kent's, in the gitignored acceptance directory.
What IS measured on real committed artwork is the half that carries the risk:
**no logo trips either signal**, and the owl trips neither — the blind spot
that keeps the declaration alive rather than making it vestigial.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import photo_signals as ps
from digitizer_core.config import is_photographic
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from tests.conftest import TESTDATA

OWL = TESTDATA / "photo" / "owl_kent.jpg"
LOGO = TESTDATA / "photo" / "logo_hotel_fremont.webp"

# Every committed artwork labelled `logo` in tools/photo_signals.py's corpus —
# the false-positive population. A logo that trips either signal would gain
# the palette bind, the shade bind and the photo yardstick it must not have.
LOGOS = [
    "becker_marine_logo.png", "logo_script_tires.png", "logo_whitebg.png",
    "logo_alpha.png", "ribbon_curve.png", "bg_uncertain.png",
    "photo/enthusiast_logo.png", "photo/logo_hotel_fremont.webp",
    "photo/logo_bridge_bar.jpg", "photo/logo_gaulke_roofing.png",
    "photo/logo_golden_tee.jpg", "photo/screenshot_phone_ui_golke.jpg",
    "photo/drone_render.png", "photo/summit_badge.png",
]


def _jpeg_with_camera(path, make="Canon", model="Canon EOS R6"):
    """A 64x64 JPEG carrying the two TIFF tags a camera writes."""
    from PIL import Image
    im = Image.fromarray(np.full((64, 64, 3), 120, np.uint8))
    exif = im.getexif()
    exif[0x010F] = make
    exif[0x0110] = model
    im.save(path, exif=exif)
    return path


# --- the contract -----------------------------------------------------------

def test_off_by_default_and_free_when_off(tmp_path):
    """OFF must not read a byte — that is what makes every existing lane
    byte-identical without a single golden moving."""
    cfg = PipelineConfig()
    assert cfg.detect_photographic is False
    art = _jpeg_with_camera(tmp_path / "shot.jpg")
    out, signals = ps.resolve(cfg, image=art, rgb=None)
    assert out is cfg, "OFF must hand back the same config object, untouched"
    assert signals is None


def test_silence_is_never_a_denial():
    """`is_photograph` returns True or None. NEVER False.

    The corpus holds a real photograph neither signal catches (owl_kent:
    re-saved, so no EXIF, and an owl, so no face). False there would be a
    claim the evidence does not support AND would suppress the machinery on
    exactly the designs that need it, so detection can only ever ADD.
    """
    assert ps.PhotoSignals().is_photograph is None
    assert ps.PhotoSignals(faces=0).is_photograph is None
    assert ps.PhotoSignals(faces=None, face_reason="no cv2").is_photograph is None
    assert ps.PhotoSignals(faces=2).is_photograph is True
    assert ps.PhotoSignals(exif_camera="Canon EOS R6").is_photograph is True


def test_a_declaration_outranks_both_signals_in_both_directions(tmp_path):
    """The caller said no beats any detector; the caller said yes needs none.

    Both skip the work entirely — a verdict nothing may act on is not worth
    130 ms of neural net.
    """
    art = _jpeg_with_camera(tmp_path / "shot.jpg")
    for declared in (True, False):
        cfg = PipelineConfig(detect_photographic=True, is_photographic=declared)
        out, signals = ps.resolve(cfg, image=art)
        assert out is cfg and signals is None
        assert is_photographic(out, "flat") is declared


def test_apply_detection_only_ever_writes_true():
    base = PipelineConfig()
    assert ps.apply_detection(base, False) is base
    assert ps.apply_detection(base, True).is_photographic is True
    declared_off = PipelineConfig(is_photographic=False)
    assert ps.apply_detection(declared_off, True) is declared_off


# --- the EXIF reader --------------------------------------------------------

def test_exif_camera_reads_make_and_model(tmp_path):
    assert ps.exif_camera(_jpeg_with_camera(tmp_path / "a.jpg")) == "Canon Canon EOS R6"
    only_model = _jpeg_with_camera(tmp_path / "b.jpg", make="", model="iPhone 12")
    assert ps.exif_camera(only_model) == "iPhone 12"


@pytest.mark.parametrize("bad", ["missing.jpg", "corrupt"])
def test_the_exif_reader_never_raises(tmp_path, bad):
    """A detection signal that can take the pipeline down is worse than one
    that stays quiet, so every failure reads as "no camera"."""
    if bad == "corrupt":
        p = tmp_path / "corrupt.jpg"
        p.write_bytes(b"\xff\xd8\xff\xe0 not actually a jpeg")
    else:
        p = tmp_path / bad
    assert ps.exif_camera(p) is None


def test_a_decoded_array_has_no_header_left():
    """Which is exactly why the service passes its upload bytes down past its
    own decode (`build_generation(..., exif_source=data)`)."""
    assert ps.exif_camera(np.zeros((8, 8, 3), np.uint8)) is None


def test_exif_short_circuits_the_detector(tmp_path, monkeypatch):
    """Once EXIF says photograph, YuNet cannot change the answer — running it
    is pure cost on the one lane where the answer is already in."""
    called = []
    monkeypatch.setattr("digitizer_core.stage1_photo_prep.detect_faces_seam",
                        lambda *a, **k: called.append(1) or [])
    signals = ps.detect(_jpeg_with_camera(tmp_path / "a.jpg"),
                        rgb=np.zeros((32, 32, 3), np.uint8))
    assert signals.signal == "exif" and not called


# --- the face half ----------------------------------------------------------

def test_the_face_pass_runs_when_exif_is_silent(monkeypatch):
    monkeypatch.setattr("digitizer_core.stage1_photo_prep.detect_faces_seam",
                        lambda rgb, cfg: ["a face"])
    signals = ps.detect(np.zeros((32, 32, 3), np.uint8),
                        rgb=np.zeros((32, 32, 3), np.uint8))
    assert signals.is_photograph is True
    assert signals.signal == "face"
    assert "1 face" in signals.why


def test_an_unavailable_detector_is_no_opinion_not_no_faces(monkeypatch):
    """`detect_faces_seam` returns None when this machine cannot run it. That
    must not read as "no faces found" — it is the absence of an answer, and
    `why` has to say which."""
    monkeypatch.setattr("digitizer_core.stage1_photo_prep.detect_faces_seam",
                        lambda rgb, cfg: None)
    monkeypatch.setattr(
        "digitizer_core.stage1_photo_prep.face_detector_unavailable_reason",
        lambda: "cv2.FaceDetectorYN absent")
    signals = ps.detect(np.zeros((32, 32, 3), np.uint8),
                        rgb=np.zeros((32, 32, 3), np.uint8))
    assert signals.is_photograph is None
    assert signals.faces is None
    assert "cv2.FaceDetectorYN absent" in signals.why


# --- wired into the pipeline ------------------------------------------------

def _fake_face(monkeypatch):
    monkeypatch.setattr("digitizer_core.stage1_photo_prep.detect_faces_seam",
                        lambda rgb, cfg: ["a face"])


def test_a_detected_photograph_reaches_all_three_entry_points(monkeypatch):
    """The verdict has to survive two hops it did not used to make.

    `build_generation` rewrites its own local config, but `finish_generation`,
    `plan_stitches` and `run_preflight` are separate entry points holding the
    CALLER's config — the service re-finishes from a cached generation on
    every review edit. So the fact rides the Generation and the
    PipelineResult, the way stage 0's class and stage 1.5's faces_present
    already do, and each entry point folds it back in.
    """
    _fake_face(monkeypatch)
    cfg = PipelineConfig(detect_photographic=True, target_width_mm=60.0)
    gen = build_generation(str(LOGO), cfg)
    assert gen.detected_photographic is True

    result = finish_generation(gen.fork(), cfg)
    assert result.detected_photographic is True
    hit = [w for w in result.warnings if w.get("code") == "PHOTO_DETECTED"]
    assert len(hit) == 1 and hit[0]["signal"] == "face"

    plan = plan_stitches(result, cfg)
    assert any(w.get("code") == "PHOTO_DETECTED" for w in plan.warnings)
    # Preflight re-reads the warning rather than re-detecting, the same way it
    # re-reads the classifier's verdict.
    from digitizer_core.preflight import _is_photo_class
    assert _is_photo_class(plan, cfg) is True


def test_a_declared_non_photograph_stays_one_end_to_end(monkeypatch):
    """The suppression a caller can always reach for, with the detector
    firing on every raster."""
    _fake_face(monkeypatch)
    cfg = PipelineConfig(detect_photographic=True, is_photographic=False,
                         target_width_mm=60.0)
    gen = build_generation(str(LOGO), cfg)
    assert gen.detected_photographic is False
    result = finish_generation(gen.fork(), cfg)
    assert not [w for w in result.warnings if w.get("code") == "PHOTO_DETECTED"]


def test_the_owl_is_the_blind_spot_and_changes_nothing():
    """A REAL photograph both signals miss — and the reason the declaration
    stays the fallback rather than becoming a vestige.

    Detection ON must leave it identical to detection OFF: same class, same
    shape ids, same warnings, no PHOTO_DETECTED. If this ever starts failing
    because the owl gained a signal, that is good news — but it is still a
    deliberate change, not a silent one.
    """
    off = PipelineConfig(target_width_mm=60.0)
    on = PipelineConfig(target_width_mm=60.0, detect_photographic=True)
    a = finish_generation(build_generation(str(OWL), off).fork(), off)
    b = finish_generation(build_generation(str(OWL), on).fork(), on)
    assert b.detected_photographic is False
    assert a.design_class == b.design_class
    assert a.shape_ids == b.shape_ids
    assert [w.get("code") for w in a.warnings] == [w.get("code") for w in b.warnings]


# --- the risk, measured on real artwork -------------------------------------

@pytest.mark.parametrize("rel", LOGOS)
def test_no_logo_trips_either_signal(rel):
    """0 false positives across all 14 committed logos, re-measured 2026-09-11.

    This is the half that carries the risk: detection can only ever ADD the
    photographic machinery, so a wrong True is the only wrong answer it can
    give — and it would apply the palette bind, the shade bind and the photo
    yardstick to a logo that wants none of them.

    Run on the DECODED raster rather than through the pipeline: the detector
    is a pure function of pixels, and prep costs 0.04-1.10 s a fixture here
    against detection's 0.03-0.14 s.
    """
    import cv2
    path = TESTDATA / rel
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert bgr is not None, f"could not decode {rel}"
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    signals = ps.detect(path, rgb=rgb, cfg=PipelineConfig())
    assert signals.is_photograph is not True, (
        f"{rel} is a logo and trips {signals.signal}: {signals.why}")


# --- a face sews FLAT (Kent's ruling 2026-09-30) ----------------------------
#
# `cfg.faces_route_flat`: a detected face takes the flat lane, exactly as
# `forced_class="flat"` would, and FACE_ROUTED_FLAT replaces PHOTO_DETECTED.
# Measured on two stand-in portraits at 80 mm: the automatic lane read both
# as `gradient` and merged the subject into the background; forced flat gave
# a recognisable person on both, and is the run Kent called awesome on his
# own portrait. The route is pinned here as byte-identity with the forced
# run, not as a quality claim.

def _codes(result):
    return [w.get("code") for w in result.warnings]


def test_faces_route_flat_is_off_by_default_and_changes_nothing_off(monkeypatch):
    assert PipelineConfig().faces_route_flat is False
    _fake_face(monkeypatch)
    cfg = PipelineConfig(detect_photographic=True, target_width_mm=60.0)
    result = finish_generation(build_generation(str(LOGO), cfg).fork(), cfg)
    assert "PHOTO_DETECTED" in _codes(result)
    assert "FACE_ROUTED_FLAT" not in _codes(result)


def test_a_face_routes_flat_byte_identical_to_the_forced_run(monkeypatch):
    """The whole ruling in one assertion: routed == forced_class="flat",
    on class, shape ids and every warning but the one that says why."""
    _fake_face(monkeypatch)
    routed_cfg = PipelineConfig(detect_photographic=True, faces_route_flat=True,
                                target_width_mm=60.0)
    forced_cfg = PipelineConfig(forced_class="flat", target_width_mm=60.0)
    routed = finish_generation(build_generation(str(LOGO), routed_cfg).fork(), routed_cfg)
    forced = finish_generation(build_generation(str(LOGO), forced_cfg).fork(), forced_cfg)

    assert routed.design_class == "flat"
    assert routed.detected_photographic is False, \
        "the photographic machinery must stay OFF — that is the forced run Kent liked"
    assert "PHOTO_DETECTED" not in _codes(routed)
    hit = [w for w in routed.warnings if w.get("code") == "FACE_ROUTED_FLAT"]
    assert len(hit) == 1 and hit[0]["faces"] == 1
    assert routed.shape_ids == forced.shape_ids
    assert [c for c in _codes(routed) if c != "FACE_ROUTED_FLAT"] == _codes(forced)
    # And downstream reads it as flat too: preflight grades on the flat
    # yardstick, not the photo one.
    plan = plan_stitches(routed, routed_cfg)
    from digitizer_core.preflight import _is_photo_class
    assert _is_photo_class(plan, routed_cfg) is False


def test_a_camera_fresh_portrait_still_routes_flat(tmp_path, monkeypatch):
    """EXIF short-circuits plain detection; the ROUTE needs the face itself,
    so the face pass runs anyway when the flag is on."""
    _fake_face(monkeypatch)
    art = _jpeg_with_camera(tmp_path / "portrait.jpg")
    cfg = PipelineConfig(detect_photographic=True, faces_route_flat=True,
                         target_width_mm=60.0)
    out, signals = ps.resolve(cfg, image=art, rgb=np.zeros((64, 64, 3), np.uint8))
    assert signals.exif_camera and signals.faces == 1
    assert signals.signal == "exif", "the verdict's own name is unchanged"
    # ...and without the flag, EXIF still short-circuits the detector.
    plain = PipelineConfig(detect_photographic=True)
    _, quiet = ps.resolve(plain, image=art, rgb=np.zeros((64, 64, 3), np.uint8))
    assert quiet.exif_camera and quiet.faces is None


def test_an_explicit_class_or_declaration_outranks_the_face_route(monkeypatch):
    _fake_face(monkeypatch)
    forced = PipelineConfig(detect_photographic=True, faces_route_flat=True,
                            forced_class="gradient", target_width_mm=60.0)
    r = finish_generation(build_generation(str(LOGO), forced).fork(), forced)
    assert r.design_class == "gradient"
    assert "FACE_ROUTED_FLAT" not in _codes(r)

    declared = PipelineConfig(detect_photographic=True, faces_route_flat=True,
                              is_photographic=False, target_width_mm=60.0)
    r = finish_generation(build_generation(str(LOGO), declared).fork(), declared)
    assert "FACE_ROUTED_FLAT" not in _codes(r)
    assert "PHOTO_DETECTED" not in _codes(r)


def test_no_face_means_the_flag_is_a_no_op():
    """On the owl (no EXIF, no face) the flag must leave everything alone."""
    off = PipelineConfig(target_width_mm=60.0, detect_photographic=True)
    on = PipelineConfig(target_width_mm=60.0, detect_photographic=True, faces_route_flat=True)
    a = finish_generation(build_generation(str(OWL), off).fork(), off)
    b = finish_generation(build_generation(str(OWL), on).fork(), on)
    assert a.design_class == b.design_class
    assert a.shape_ids == b.shape_ids
    assert _codes(a) == _codes(b)
