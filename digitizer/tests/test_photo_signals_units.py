"""Unit-level pins for `digitizer_core/photo_signals.py` on tiny synthetic inputs.

`tests/test_photo_detection.py` covers the signals end to end (pipeline entry
points, the corpus logos, the face route). This file fills the gaps beneath
that: the `PhotoSignals` verdict/`signal`/`why` matrix, the EXIF reader's input
types, `detect`'s short-circuit and `faces_always` branches, `resolve`'s
gating, and the one monotonic property the module promises — more evidence can
only add to the verdict, never take it away. Pure functions, a stubbed face
detector, no corpus files.
"""
from __future__ import annotations

import io

import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import photo_signals as ps

DETECTOR = "digitizer_core.stage1_photo_prep.detect_faces_seam"
RGB = np.zeros((16, 16, 3), np.uint8)


def _jpeg_bytes(make="Canon", model="EOS R6", size=(16, 16)):
    from PIL import Image
    im = Image.fromarray(np.full((*size, 3), 90, np.uint8))
    exif = im.getexif()
    if make is not None:
        exif[0x010F] = make
    if model is not None:
        exif[0x0110] = model
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def _png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(np.full((8, 8, 3), 200, np.uint8)).save(buf, format="PNG")
    return buf.getvalue()


def _faces(monkeypatch, n):
    calls = []
    monkeypatch.setattr(DETECTOR, lambda rgb, cfg: calls.append(1) or ["f"] * n)
    return calls


# --- PhotoSignals: verdict, signal, why --------------------------------------

@pytest.mark.parametrize("sig, verdict, name", [
    (ps.PhotoSignals(), None, None),
    (ps.PhotoSignals(faces=0), None, None),            # looked, found none: still no opinion
    (ps.PhotoSignals(faces=None, face_reason="x"), None, None),
    (ps.PhotoSignals(exif_camera="Canon R6"), True, "exif"),
    (ps.PhotoSignals(faces=1), True, "face"),
    (ps.PhotoSignals(faces=7), True, "face"),
    (ps.PhotoSignals(exif_camera="Canon R6", faces=3), True, "exif"),  # exif outranks face
])
def test_verdict_is_true_or_none_never_false(sig, verdict, name):
    assert sig.is_photograph is verdict
    assert sig.signal == name


def test_why_names_the_signal_that_fired():
    assert "Canon R6" in ps.PhotoSignals(exif_camera="Canon R6").why
    assert "2 face(s)" in ps.PhotoSignals(faces=2).why
    assert "Canon R6" in ps.PhotoSignals(exif_camera="Canon R6", faces=2).why


def test_why_distinguishes_unavailable_from_none_found():
    assert "no face detected" in ps.PhotoSignals(faces=0).why
    unavailable = ps.PhotoSignals(faces=None, face_reason="model missing").why
    assert "model missing" in unavailable and "unavailable" in unavailable
    assert "no face detected" in ps.PhotoSignals().why      # not run, no reason


# --- exif_camera -------------------------------------------------------------

def test_exif_reads_from_bytes_and_bytearray():
    data = _jpeg_bytes()
    assert ps.exif_camera(data) == "Canon EOS R6"
    assert ps.exif_camera(bytearray(data)) == "Canon EOS R6"


def test_exif_strips_whitespace_and_drops_empty_halves():
    assert ps.exif_camera(_jpeg_bytes(make="  Nikon ", model=" Z6 ")) == "Nikon Z6"
    assert ps.exif_camera(_jpeg_bytes(make="Sony", model=None)) == "Sony"
    assert ps.exif_camera(_jpeg_bytes(make="  ", model="  ")) is None


def test_exif_is_none_for_headerless_and_unreadable_input():
    assert ps.exif_camera(_jpeg_bytes(make=None, model=None)) is None
    assert ps.exif_camera(_png_bytes()) is None
    assert ps.exif_camera(b"") is None
    assert ps.exif_camera(b"not an image at all") is None


# --- detect ------------------------------------------------------------------

def test_without_pixels_only_exif_is_read(monkeypatch):
    calls = _faces(monkeypatch, 1)
    out = ps.detect(_png_bytes())
    assert out == ps.PhotoSignals() and not calls
    assert ps.detect(_jpeg_bytes()).signal == "exif" and not calls


def test_faces_always_fills_both_fields_but_signal_stays_exif(monkeypatch):
    calls = _faces(monkeypatch, 2)
    out = ps.detect(_jpeg_bytes(), rgb=RGB, faces_always=True)
    assert calls and out.faces == 2 and out.exif_camera == "Canon EOS R6"
    assert out.signal == "exif"


def test_a_clean_image_with_no_faces_is_zero_faces_and_no_opinion(monkeypatch):
    _faces(monkeypatch, 0)
    out = ps.detect(_png_bytes(), rgb=RGB)
    assert out.faces == 0 and out.is_photograph is None


def test_more_evidence_never_flips_the_verdict_off(monkeypatch):
    """Monotonic: adding a camera header or one more face can only move the
    verdict None -> True. Walk the evidence up and assert it never steps down."""
    steps = []
    for n in (0, 1, 2, 5):
        _faces(monkeypatch, n)
        steps.append(ps.detect(_png_bytes(), rgb=RGB).is_photograph)
    assert steps == [None, True, True, True]
    _faces(monkeypatch, 0)
    with_cam = ps.detect(_jpeg_bytes(), rgb=RGB)
    assert with_cam.is_photograph is True
    rank = {None: 0, True: 1}
    assert rank[with_cam.is_photograph] >= rank[ps.detect(_png_bytes(), rgb=RGB).is_photograph]


# --- apply_detection / resolve ----------------------------------------------

@pytest.mark.parametrize("declared, detected, expect", [
    (None, True, True),
    (None, False, None),
    (False, True, False),      # the caller said no: outranks every signal
    (True, False, True),
    (True, True, True),
])
def test_apply_detection_truth_table(declared, detected, expect):
    cfg = PipelineConfig(is_photographic=declared)
    assert ps.apply_detection(cfg, detected).is_photographic is expect


def test_apply_detection_returns_the_same_object_when_nothing_changes():
    cfg = PipelineConfig()
    assert ps.apply_detection(cfg, False) is cfg
    declared = PipelineConfig(is_photographic=False)
    assert ps.apply_detection(declared, True) is declared


def test_resolve_is_inert_when_off_or_declared(monkeypatch):
    calls = _faces(monkeypatch, 1)
    off = PipelineConfig()
    assert ps.resolve(off, image=_jpeg_bytes(), rgb=RGB) == (off, None)
    declared = PipelineConfig(detect_photographic=True, is_photographic=False)
    assert ps.resolve(declared, image=_jpeg_bytes(), rgb=RGB) == (declared, None)
    assert not calls


def test_resolve_with_no_inputs_is_no_opinion():
    cfg = PipelineConfig(detect_photographic=True)
    out, signals = ps.resolve(cfg)
    assert out is cfg and signals == ps.PhotoSignals()


def test_resolve_folds_a_fired_signal_into_the_config(monkeypatch):
    cfg = PipelineConfig(detect_photographic=True)
    out, signals = ps.resolve(cfg, image=_jpeg_bytes())
    assert out.is_photographic is True and signals.signal == "exif"
    _faces(monkeypatch, 1)
    out, signals = ps.resolve(cfg, image=_png_bytes(), rgb=RGB)
    assert out.is_photographic is True and signals.signal == "face"
    _faces(monkeypatch, 0)
    out, signals = ps.resolve(cfg, image=_png_bytes(), rgb=RGB)
    assert out.is_photographic is None and signals.is_photograph is None


def test_resolve_passes_faces_route_flat_as_faces_always(monkeypatch):
    calls = _faces(monkeypatch, 1)
    ps.resolve(PipelineConfig(detect_photographic=True), image=_jpeg_bytes(), rgb=RGB)
    assert not calls
    ps.resolve(PipelineConfig(detect_photographic=True, faces_route_flat=True),
               image=_jpeg_bytes(), rgb=RGB)
    assert calls
