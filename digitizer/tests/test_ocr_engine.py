"""`digitizer_core.ocr`: one Tesseract for every read.

The contract the eight callers rely on is small and is pinned here: a
`{"text", "conf"}` dict with one entry per word, confidences 0..100 as
numbers, `("", 0.0)` from `words()` on a blank crop, the engine choice
readable (`engine()`, `version()`), and the `EMB_OCR_ENGINE` override. The
real-read tests skip without an engine, except on CI (`requires_tesseract`).
"""
from __future__ import annotations

import os
import shutil
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from digitizer_core import ocr

from .conftest import requires_tesseract


def _glyph(ch: str = "T", h: int = 120) -> np.ndarray:
    """Black letter on a white field, padded, the way `_ocr_raster` and
    `prepare_for_ocr` hand crops over."""
    img = np.full((h, h), 255, np.uint8)
    cv2.putText(img, ch, (int(h * 0.22), int(h * 0.8)), cv2.FONT_HERSHEY_SIMPLEX, h / 40.0, 0, max(2, h // 12),
                cv2.LINE_AA)
    return cv2.copyMakeBorder(img, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)


@pytest.fixture
def fresh_engine():
    ocr.reset()
    yield
    ocr.reset()


def test_engine_is_one_of_the_two_or_none(fresh_engine):
    assert ocr.engine() in ("tesserocr", "pytesseract", None)
    assert ocr.available() == (ocr.engine() is not None)
    v = ocr.version()
    if ocr.engine() is None:
        assert v is None
    else:
        assert v.startswith("tesseract") and ocr.engine() in v


def test_tesserocr_is_preferred_when_wheel_and_tessdata_are_present(fresh_engine):
    try:
        import tesserocr  # noqa: F401
    except Exception:
        pytest.skip("no tesserocr wheel in this venv")
    if ocr.tessdata_dir() is None:
        pytest.skip("no eng.traineddata found on this machine")
    assert ocr.engine() == "tesserocr"
    assert "in-process" in ocr.version()


def test_override_forces_the_subprocess_path(fresh_engine, monkeypatch):
    if shutil.which("tesseract") is None:
        pytest.skip("no tesseract binary to fall back to")
    monkeypatch.setenv(ocr.ENGINE_ENV, "pytesseract")
    ocr.reset()
    assert ocr.engine() == "pytesseract"
    assert "subprocess" in ocr.version()


def test_override_to_tesserocr_never_falls_back(fresh_engine, monkeypatch):
    """`EMB_OCR_ENGINE=tesserocr` on a box without the wheel means NO engine,
    not a quiet drop to the 50x slower path."""
    monkeypatch.setenv(ocr.ENGINE_ENV, "tesserocr")
    ocr.reset()
    with patch.object(ocr, "_tesserocr", lambda: None):
        ocr.engine.cache_clear()
        assert ocr.engine() is None
        assert not ocr.available()


def test_words_folds_the_dict_the_way_legibility_does(fresh_engine, monkeypatch):
    monkeypatch.setattr(ocr, "image_to_data",
                        lambda img, psm: {"text": ["", "HOTEL", " ", "FREMONT"], "conf": [-1, 96.9, -1, 90.2]})
    assert ocr.words(np.zeros((8, 8), np.uint8), 7) == ("HOTEL FREMONT", pytest.approx((96.9 + 90.2) / 2))
    monkeypatch.setattr(ocr, "image_to_data", lambda img, psm: {"text": ["", ""], "conf": [-1, -1]})
    assert ocr.words(np.zeros((8, 8), np.uint8), 7) == ("", 0.0)


def test_no_engine_raises_so_callers_fail_open_themselves(fresh_engine):
    with patch.object(ocr, "engine", lambda: None):
        with pytest.raises(RuntimeError, match="no OCR engine"):
            ocr.image_to_data(np.zeros((8, 8), np.uint8), 10)
        with pytest.raises(RuntimeError, match="no OCR engine"):
            ocr.image_to_string(np.zeros((8, 8), np.uint8), 7)


@requires_tesseract
def test_real_read_of_a_block_letter(fresh_engine):
    data = ocr.image_to_data(_glyph("T"), 10)
    assert set(data) >= {"text", "conf"} and len(data["text"]) == len(data["conf"])
    got = [(t, float(c)) for t, c in zip(data["text"], data["conf"]) if t and t.strip() and float(c) >= 0]
    assert got, "a 120 px block T reads as nothing"
    assert got[0][0].strip()[:1].upper() == "T"
    assert 0.0 <= got[0][1] <= 100.0
    assert ocr.image_to_string(_glyph("T"), 10).strip()[:1].upper() == "T"


@requires_tesseract
def test_blank_crop_reads_as_no_words_not_an_error(fresh_engine):
    blank = np.full((100, 100), 255, np.uint8)
    text, conf = ocr.words(blank, 7)
    assert text == "" and conf == 0.0


@requires_tesseract
def test_threads_each_get_their_own_api(fresh_engine):
    """One `PyTessBaseAPI` per thread (`threading.local`): four threads
    reading the same glyph at once agree with the serial read."""
    if ocr.engine() != "tesserocr":
        pytest.skip("the per-thread API is the in-process engine's")
    from concurrent.futures import ThreadPoolExecutor
    g = _glyph("T")
    serial = ocr.words(g, 10)
    with ThreadPoolExecutor(max_workers=4) as ex:
        got = list(ex.map(lambda _i: ocr.words(g, 10), range(8)))
    assert all(r == serial for r in got), got


@requires_tesseract
def test_both_engines_read_the_same_glyph_when_both_are_present(fresh_engine, monkeypatch):
    """The fallback and the in-process engine carry different Tesseract
    builds (5.4.0 / 5.3.4 vs the wheel's 5.5.3), so confidences may differ;
    the LETTER must not, on a clean 120 px block capital."""
    if ocr.engine() != "tesserocr" or shutil.which("tesseract") is None:
        pytest.skip("needs both engines on this machine")
    g = _glyph("E")
    fast = ocr.words(g, 10)[0].strip().upper()
    monkeypatch.setenv(ocr.ENGINE_ENV, "pytesseract")
    ocr.reset()
    slow = ocr.words(g, 10)[0].strip().upper()
    assert fast[:1] == slow[:1] == "E", (fast, slow)


def test_tessdata_dir_honours_the_env(fresh_engine, monkeypatch, tmp_path):
    (tmp_path / "eng.traineddata").write_bytes(b"x")
    monkeypatch.setenv("TESSDATA_PREFIX", str(tmp_path))
    ocr.tessdata_dir.cache_clear()
    assert ocr.tessdata_dir() == str(tmp_path)
    nested = tmp_path / "nest"
    (nested / "tessdata").mkdir(parents=True)
    (nested / "tessdata" / "eng.traineddata").write_bytes(b"x")
    monkeypatch.setenv("TESSDATA_PREFIX", str(nested))
    ocr.tessdata_dir.cache_clear()
    assert ocr.tessdata_dir() == os.path.join(str(nested), "tessdata")
