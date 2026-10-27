"""`legibility.read_side` reads its crops side by side (`_ocr_all`) and must
pick exactly what the serial loop picked: the same reading, the same psm, a
tie going to the earlier read. And every tesseract child must still run on one
OpenMP thread, with the variable restored afterwards.

No tesseract needed: `legibility.ocr` is replaced by a deterministic fake that
sleeps so the workers finish out of order."""
import os
import random
import time

import numpy as np
import pytest

from digitizer_core import legibility as L


def _serial(imgs, px_per_mm, psms, ocr):
    """The loop as it was before 2026-10-26, verbatim but for `ocr`."""
    best = ("", -1.0, psms[0])
    for img in imgs:
        if img is None or img.size == 0:
            continue
        for psm in psms:
            for blur_mm, thin_mm in L.VARIANTS_MM:
                txt, conf = ocr(img, psm, blur_mm * px_per_mm, thin_mm * px_per_mm)
                key = (conf if L.normalise(txt) else -1.0, len(L.normalise(txt)))
                if key > (best[1], len(L.normalise(best[0]))):
                    best = (txt, conf, psm)
    return best


def _fake(seed, seen):
    rng = random.Random(seed)
    table = {}

    def ocr(img, psm, blur, thin):
        seen.append(os.environ.get("OMP_THREAD_LIMIT"))
        key = (img.shape, psm, round(blur, 6), round(thin, 6))
        if key not in table:
            # few distinct readings and confidences, so ties are common
            table[key] = (rng.choice(["", "THE", "TH E", "THC", "HOTEL", "x"]),
                          float(rng.choice([0, 40, 80, 80, 95])))
        time.sleep(rng.random() * 0.004)
        return table[key]
    return ocr


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("psms", [L.OCR_MODES, (7,)])
def test_read_side_picks_what_the_serial_loop_picked(monkeypatch, seed, psms):
    imgs = [np.zeros((10 + seed, 20), np.uint8), None, np.zeros((0, 4), np.uint8),
            np.zeros((30, 20 + seed), np.uint8)]
    seen = []
    ocr = _fake(seed, seen)
    want = _serial(imgs, 8.0, psms, ocr)       # fills the table: both sides read the same
    monkeypatch.setattr(L, "ocr", ocr)
    for workers in (1, 4):
        monkeypatch.setattr(L, "OCR_WORKERS", workers)
        assert L.read_side(imgs, 8.0, psms) == want


@pytest.mark.parametrize("prev", [None, "3"])
def test_every_read_runs_on_one_thread_and_the_limit_is_restored(monkeypatch, prev):
    if prev is None:
        monkeypatch.delenv("OMP_THREAD_LIMIT", raising=False)
    else:
        monkeypatch.setenv("OMP_THREAD_LIMIT", prev)
    seen = []
    monkeypatch.setattr(L, "ocr", _fake(0, seen))
    monkeypatch.setattr(L, "OCR_WORKERS", 4)
    L.read_side([np.zeros((12, 12), np.uint8), np.zeros((14, 14), np.uint8)], 8.0, L.OCR_MODES)
    assert len(seen) == 2 * len(L.OCR_MODES) * len(L.VARIANTS_MM)
    # the fake reads the variable from inside each call, while the others run
    assert set(seen) == {"1"}
    assert os.environ.get("OMP_THREAD_LIMIT") == prev


def test_a_failing_read_raises_as_the_serial_loop_did(monkeypatch):
    def ocr(img, psm, blur, thin):
        raise RuntimeError("tesseract is not installed")
    monkeypatch.setattr(L, "ocr", ocr)
    monkeypatch.setattr(L, "OCR_WORKERS", 4)
    with pytest.raises(RuntimeError, match="not installed"):
        L.read_side([np.zeros((12, 12), np.uint8)], 8.0, L.OCR_MODES)
