"""`tools/word_legibility.py` -- the per-word, ours-vs-pro legibility number, pinned.

The scoring (a chance-corrected character similarity) and the geometry (the
window cut out of a design, the per-word search in a file's own frame) run
with no tesseract. The tests that need the real reader draw a word, sew it as
a fill of stitches and read it back; they skip where `tesseract` is not on
PATH (Kent's Windows box) and run in CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import word_legibility as wl  # noqa: E402

from .conftest import requires_tesseract  # noqa: E402

PPM = 10.0      # synthetic artwork, px per mm


# --- the number --------------------------------------------------------------

def test_exact_reading_is_one_and_empty_is_zero():
    full = wl.chance_corrected("HOTEL", "hotel")
    assert full["raw"] == 1.0 and full["cc"] == 1.0
    empty = wl.chance_corrected("", "HOTEL")
    assert empty["raw"] == 0.0 and empty["cc"] == 0.0


def test_right_letters_in_the_wrong_order_earn_about_nothing():
    """The point of the baseline: a raw 0.6 would read as 'mostly legible',
    and it is what a shuffle of the right letters earns."""
    r = wl.chance_corrected("HETOL", "HOTEL")
    assert r["raw"] >= 0.6         # raw flatters it: a 60% "match"
    assert r["cc"] < 0.35          # chance-corrected does not
    assert wl.chance_corrected("LETOH", "HOTEL")["cc"] < 0   # worse than a shuffle is below zero
    # and a real partial read lands above it
    part = wl.chance_corrected("HOTL", "HOTEL")
    assert part["cc"] > r["cc"] + 0.4
    assert part["cc"] < part["raw"]


def test_baseline_is_deterministic_and_undefined_when_every_shuffle_is_the_word():
    assert wl.shuffle_baseline("MARINE", "MARINE") == wl.shuffle_baseline("MARINE", "MARINE")
    assert wl.chance_corrected("A", "A")["cc"] is None
    assert wl.chance_corrected("AAA", "AAA")["cc"] is None


def test_norm_keeps_letters_and_digits():
    assert wl.norm("est. 1895 -") == "EST1895"


def test_job_figure_weights_by_letters_and_skips_undefined():
    rows = [{"text": "AB", "cc": 1.0, "raw": 1.0}, {"text": "ABCDEF", "cc": 0.0, "raw": 0.5},
            {"text": "X", "cc": None, "raw": 1.0}]
    f = wl.job_figure(rows)
    assert f["words"] == 2
    assert f["cc"] == pytest.approx(0.25)          # (2*1 + 6*0) / 8
    assert f["raw"] == pytest.approx(0.625)
    assert wl.job_figure([])["cc"] is None


# --- geometry ----------------------------------------------------------------

def _design(records, colors=None):
    return {"stitches": records, "colors": colors or [{"r": 0, "g": 0, "b": 0}]}


def test_window_keeps_inside_scales_about_centre_and_never_bridges_the_edge():
    # a thread that runs (0,0) -> (10,0) mm -> (100,0) mm -> back to (12,0) mm, 0.1 mm units
    recs = [{"x": 0, "y": 0, "type": "stitch"}, {"x": 100, "y": 0, "type": "stitch"},
            {"x": 1000, "y": 0, "type": "stitch"}, {"x": 120, "y": 0, "type": "stitch"},
            {"x": 130, "y": 0, "type": "color"}, {"x": 140, "y": 0, "type": "stitch"}]
    sub = wl.window_scaled(_design(recs), (0.0, -1.0, 14.0, 1.0), 2.0, 1.0)
    xs = [r["x"] for r in sub["stitches"] if r["type"] != "color"]
    assert max(xs) < 400 and min(xs) < 0          # the far stitch is gone; scaling about x=7 mm pushes 0 to -7 mm
    types = [r["type"] for r in sub["stitches"]]
    # the stitch that came back in after leaving starts a fresh thread: a jump first
    assert types.count("jump") == 3 and "color" in types
    assert sub["colors"] == _design(recs)["colors"]


def test_render_word_is_taller_by_the_scale_and_none_off_the_thread():
    recs = [{"x": 0, "y": 0, "type": "jump"}, {"x": 0, "y": 0, "type": "stitch"}, {"x": 0, "y": 60, "type": "stitch"},
            {"x": 80, "y": 60, "type": "stitch"}, {"x": 80, "y": 0, "type": "stitch"}]
    d = _design(recs)
    box = (0.0, 0.0, 8.0, 6.0)
    one = wl.render_word(d, box, 1.0, (255, 255, 255))
    two = wl.render_word(d, box, 2.0, (255, 255, 255))
    assert one is not None and two is not None
    assert two.shape[0] / one.shape[0] == pytest.approx(2.0, rel=0.1)
    assert wl.render_word(_design([]), box, 1.0, (255, 255, 255)) is None


def test_find_word_takes_the_words_own_thread_not_the_neighbours_or_the_seed_box():
    """Two orange words and a black bar between them, as EAT | STAY; the seed
    box is the art's (too small for the bolder word). The found box is the
    word's own: wider than the seed, and clear of the bar and of the other word."""
    m_orange = np.zeros((200, 600), bool)
    m_black = np.zeros((200, 600), bool)
    for x0 in (60, 100, 140):                     # EAT: three letters, 40 px wide, 12 px gaps
        m_orange[60:120, x0:x0 + 28] = True
    m_black[40:140, 215:221] = True               # the bar
    for x0 in (260, 300, 340, 380):               # STAY
        m_orange[60:120, x0:x0 + 28] = True
    seed = (80, 60, 150, 120)                     # the art's EAT: narrower than the pro's three letters
    box, note, cost = wl.find_word([m_black, m_orange], seed, 20.0)
    assert box is not None, note
    assert box[0] <= 62 and box[2] >= 166         # the whole word, past the seed
    assert box[2] < 215                           # not the bar, not STAY
    assert wl.find_word([np.zeros((50, 50), bool)], (5, 5, 20, 20), 20.0)[0] is None
    assert wl.find_word([], (5, 5, 20, 20), 20.0)[0] is None


# --- a whole job on a drawn word ---------------------------------------------------

def _word_art(text="HOTEL", scale=7.0, thickness=14):
    """-> (rgb float32, alpha, mask bool): black `text` on white, PPM px/mm,
    about 16 mm tall and 70 mm wide."""
    img = np.full((int(24 * PPM), int(84 * PPM), 3), 255, np.uint8)
    cv2.putText(img, text, (int(3 * PPM), int(20 * PPM)), cv2.FONT_HERSHEY_DUPLEX, scale, (0, 0, 0), thickness,
                cv2.LINE_AA)
    mask = img[..., 0] < 128
    return img[..., ::-1].astype(np.float32), np.full(mask.shape, 255, np.uint8), mask


def _fill_design(mask, offset_mm=(0.0, 0.0), pitch_mm=0.3):
    """The mask sewn as horizontal runs, 0.1 mm units, y up (`design_from_pes`'s frame)."""
    recs, step = [], max(1, int(round(pitch_mm * PPM)))
    for row in range(0, mask.shape[0], step):
        cols = np.flatnonzero(np.diff(np.r_[0, mask[row].astype(np.int8), 0]))
        for a, b in zip(cols[::2], cols[1::2]):
            y = -(row / PPM + offset_mm[1]) * 10.0
            xa, xb = (a / PPM + offset_mm[0]) * 10.0, (b / PPM + offset_mm[0]) * 10.0
            recs += [{"x": xa, "y": y, "type": "jump"}, {"x": xa, "y": y, "type": "stitch"},
                     {"x": xb, "y": y, "type": "stitch"}]
    return _design(recs)


def test_read_job_finds_the_word_in_each_files_own_frame_without_ocr():
    rgb, alpha, mask = _word_art()
    ours = _fill_design(mask)
    pro = _fill_design(mask, offset_mm=(31.0, -7.5))      # the pro's file sits elsewhere in its own frame
    words = [{"text": "HOTEL", "box": [0.0, 0.0, 1.0, 1.0]}]
    res = wl.read_job("synthetic", ours, pro, words, rgb, alpha, use_ocr=False)
    assert res["ocr"] == "OCR UNAVAILABLE"
    ys, xs = np.where(mask)
    want_h = (ys.max() - ys.min() + 1) / PPM
    for f in ("ours", "pro"):
        row = next(r for r in res["rows"] if r["file"] == f and r.get("size") == "native")
        assert row["located"]
        assert row["height_mm"] == pytest.approx(want_h, rel=0.1)
    assert {r["size"] for r in res["rows"] if r.get("size")} == {"native", "4mm", "7mm", "12mm"}


@requires_tesseract
def test_read_crop_reads_a_drawn_word():
    rgb, _a, _m = _word_art()
    txt, conf = wl.read_crop(cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR), PPM)
    assert wl.norm(txt) == "HOTEL" and conf > 50


@requires_tesseract
def test_read_job_scores_a_sewn_word_above_chance_at_a_readable_size():
    rgb, alpha, mask = _word_art()
    d = _fill_design(mask)
    words = [{"text": "HOTEL", "box": [0.0, 0.0, 1.0, 1.0]}]
    res = wl.read_job("synthetic", d, d, words, rgb, alpha, use_ocr=True, heights=(7.0, 40.0))
    assert res["ocr"] == "ok"
    seven = res["figures"]["ours/7mm"]
    assert seven["cc"] is not None and seven["cc"] > 0.5
    assert res["figures"]["pro/native"]["cc"] > 0.5
    assert res["art_ceiling"]["HOTEL"]["cc"] > 0.5
    # a word is not read at a height above its own: the layout would open gaps
    big = next(r for r in res["rows"] if r["file"] == "ours" and r.get("size") == "40mm")
    assert big["read"] is None and big["note"].startswith("skipped")
    assert res["figures"]["ours/40mm"]["cc"] is None
