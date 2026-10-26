"""`tools/word_legibility.py` -- the per-word, ours-vs-pro legibility number, pinned.

The scoring (a chance-corrected character similarity) and the geometry (the
window cut out of a design, the per-word search in a file's own frame) run
with no tesseract. The tests that need the real reader draw a word, sew it as
a fill of stitches and read it back; they skip where `tesseract` is not on
PATH (Kent's Windows box) and run in CI.
"""
from __future__ import annotations

import math
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
            recs += [{"x": xa, "y": y, "type": "jump"}]
            n = max(1, int(math.ceil((xb - xa) / 25.0)))        # stitches of at most 2.5 mm: a longer one is travel
            recs += [{"x": xa + (xb - xa) * i / n, "y": y, "type": "stitch"} for i in range(n + 1)]
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


def test_drop_travel_makes_only_the_long_stitches_jumps():
    recs = [{"x": 0, "y": 0, "type": "stitch"}, {"x": 30, "y": 0, "type": "stitch"},       # 3 mm: thread
            {"x": 330, "y": 0, "type": "stitch"}, {"x": 340, "y": 0, "type": "stitch"}]   # 30 mm: travel
    out = wl.drop_travel(_design(recs))["stitches"]
    assert [r["type"] for r in out] == ["stitch", "stitch", "jump", "stitch"]


# --- the batched reader ----------------------------------------------------------------

def test_tsv_reads_takes_the_words_of_each_page_and_whole_number_confidences():
    tsv = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
           "1\t1\t0\t0\t0\t0\t0\t0\t90\t30\t-1\t\n"
           "5\t1\t1\t1\t1\t1\t5\t5\t40\t20\t96.9\tHOTEL\n"
           "5\t1\t1\t1\t1\t2\t50\t5\t30\t20\t90.2\tFREMONT\n"
           "1\t2\t0\t0\t0\t0\t0\t0\t90\t30\t-1\t\n"
           "5\t3\t1\t1\t1\t1\t5\t5\t40\t20\t11.5\tEST\n")
    got = wl._tsv_reads(tsv, 3)
    assert got[0] == ("HOTEL FREMONT", pytest.approx((96 + 90) / 2))     # pytesseract's ints, as `legibility.ocr` meant
    assert got[1] == ("", 0.0)                                          # a page with no word is an empty reading
    assert got[2] == ("EST", 11.0)
    skipped = "\n".join(ln for i, ln in enumerate(tsv.splitlines()) if i == 0 or ln.split("\t")[1] != "2")
    with pytest.raises(ValueError, match="2 pages for 3"):               # an image tesseract skipped: no reading for a wrong crop
        wl._tsv_reads(skipped, 3)


@requires_tesseract
def test_read_crops_reads_what_read_crop_reads_and_in_the_same_order():
    imgs = []
    for text in ("HOTEL", "EST", "MARINE"):
        img = np.full((int(24 * PPM), int(84 * PPM), 3), 255, np.uint8)
        cv2.putText(img, text, (int(3 * PPM), int(20 * PPM)), cv2.FONT_HERSHEY_DUPLEX, 5.5, (0, 0, 0), 12, cv2.LINE_AA)
        imgs.append((img, PPM))
    one = [wl.read_crop(i, p) for i, p in imgs]
    many = wl.read_crops(imgs, workers=2)
    assert [wl.norm(t) for t, _c in many] == [wl.norm(t) for t, _c in one] == ["HOTEL", "EST", "MARINE"]
    assert [c for _t, c in many] == [c for _t, c in one]
    assert wl.read_crops([]) == []


# --- the finer number ------------------------------------------------------------------

def test_ladder_halves_the_word_every_other_rung_and_ends_on_the_floor():
    lv = wl.ladder_heights(100.0)
    assert lv[0] == pytest.approx(100 * wl.LADDER_STEP, abs=0.01) and lv[-1] == wl.LADDER_FLOOR_PX
    assert lv[1] == pytest.approx(50.0, abs=0.05)            # two rungs to the octave
    assert all(a > b for a, b in zip(lv, lv[1:]))
    assert wl.ladder_heights(3.0) == []                      # nothing to shrink a word that is already a smear


def test_reach_is_the_octaves_a_word_survives_and_zero_when_it_is_not_read_at_all():
    perfect = [(80.0, 1.0), (40.0, 1.0), (20.0, 1.0), (10.0, 1.0), (5.0, 1.0)]
    assert wl.reach_octaves(perfect) == pytest.approx(4.0)                    # log2(80 / 5)
    stops_at_half = [(80.0, 1.0), (40.0, 1.0), (20.0, 0.0), (10.0, 0.0), (5.0, 0.0)]
    assert wl.reach_octaves(stops_at_half) == pytest.approx(1.5)              # a ramp from 1 to 0 across the next octave
    assert wl.reach_octaves([(80.0, 0.0), (40.0, 1.0), (20.0, 1.0)]) < wl.reach_octaves([(80.0, 1.0), (40.0, 1.0), (20.0, 1.0)])
    assert wl.reach_octaves([(80.0, 0.0), (40.0, 0.0), (20.0, 0.0)]) == 0.0
    assert wl.reach_octaves([(80.0, -0.4), (40.0, 0.0)]) == 0.0              # worse than chance counts nothing, not minus
    assert wl.reach_octaves([(80.0, 1.0), (40.0, None)]) is None             # a one-letter word has no cc to integrate


def test_reach_moves_where_cc_cannot_two_words_that_both_read_perfectly_at_native():
    """The point of the number: cc is 1.00 for both words, and one survives two
    more octaves of distance."""
    a = [(80.0, 1.0), (40.0, 1.0), (20.0, 0.2), (10.0, 0.0), (5.0, 0.0)]
    b = [(80.0, 1.0), (40.0, 1.0), (20.0, 1.0), (10.0, 1.0), (5.0, 0.3)]
    assert a[0][1] == b[0][1] == 1.0
    assert wl.reach_octaves(b) - wl.reach_octaves(a) > 1.5
    assert 25.0 < wl.floor_px(a) < 40.0 and wl.floor_px(b) < 10.0
    assert wl.floor_px([(80.0, 0.3), (40.0, 1.0)]) is None                   # not read at native: no floor to name


def test_job_figure_carries_reach_weighted_by_letters_over_the_words_that_have_one():
    rows = [{"text": "AB", "cc": 1.0, "raw": 1.0, "reach": 4.0}, {"text": "ABCDEF", "cc": 1.0, "raw": 1.0, "reach": 2.0},
            {"text": "XYZ", "cc": 0.5, "raw": 0.6}]
    f = wl.job_figure(rows)
    assert f["reach"] == pytest.approx((2 * 4.0 + 6 * 2.0) / 8)
    assert wl.job_figure([{"text": "AB", "cc": 1.0, "raw": 1.0}])["reach"] is None


# --- words the first locator could not find ------------------------------------------------

def test_a_word_sewn_to_a_rope_by_a_thin_run_of_thread_is_cut_loose_and_found():
    """Fremont's pro: STAY and PLAY sit on a run of thread that ties them to the
    rope, one piece 10x the word, which the locator threw away whole. The
    peeled pieces make the word; with `runs=False` there is nothing to find."""
    m = np.zeros((300, 900), bool)
    m[10:290, 20:40] = True                              # the rope, tall as the border it is
    for x0 in (200, 250, 300, 350):                      # four letters, 40 px wide, 10 px apart
        m[100:160, x0:x0 + 40] = True
    m[158:166, 40:390] = True                            # the run: 8 px thick, from the rope under every letter
    seed = (190, 95, 390, 165)
    art = np.zeros((60, 200), bool)
    for x0 in range(0, 160, 50):
        art[:, x0:x0 + 40] = True
    box, note, cost = wl.find_word([m], seed, 20.0, art, runs=False)
    assert box is None, "the old locator found it: the fixture is not the case it was written for"
    box, note, cost = wl.find_word([m], seed, 20.0, art)
    assert box is not None, note
    assert box[0] >= 190 and box[2] <= 395 and cost < wl.LOC_MAX_COST       # the word, not the rope


def test_a_run_of_letters_ends_where_the_word_does_not_where_a_mark_beside_it_does():
    """ProSeal's SPRAY FOAM + COATINGS: the + is as far from FOAM as FOAM's own
    word space, so no dilation welds the words and leaves the mark."""
    m = np.zeros((100, 1000), bool)
    for x0 in list(range(100, 240, 28)) + list(range(282, 394, 28)):       # SPRAY, a word space, FOAM
        m[30:70, x0:x0 + 20] = True
    m[40:60, 436:456] = True                                               # the mark, one more word space on
    art = np.zeros((40, 286), bool)
    for x0 in list(range(0, 140, 28)) + list(range(182, 294, 28)):
        art[:, x0:x0 + 20] = True
    seed = (100, 30, 386, 70)
    box, note, cost = wl.find_word([m], seed, 20.0, art)
    assert box is not None, note
    assert box[2] <= 400, "the box reaches the mark"
    assert box[0] <= 105 and box[2] >= 380


def test_white_thread_sewn_over_a_black_bed_is_seen_and_white_on_bare_cloth_is_not():
    """MFab's pro sews white letters over a black bed on white art: the old
    filter dropped every white stitch as 'ground', the letters with them."""
    bed = [{"x": 0, "y": 0, "type": "jump"}] + [{"x": x, "y": y, "type": "stitch"}
                                               for y in range(0, 100, 4) for x in (0, 400)]
    over_bed = [{"x": 100, "y": 40, "type": "jump"}, {"x": 300, "y": 40, "type": "stitch"}]
    on_cloth = [{"x": 100, "y": 900, "type": "jump"}, {"x": 300, "y": 900, "type": "stitch"}]
    design = _design(bed + [{"x": 0, "y": 0, "type": "color"}] + over_bed + on_cloth,
                     colors=[{"r": 0, "g": 0, "b": 0}, {"r": 240, "g": 240, "b": 240}])
    G = np.array([254.0, 254.0, 254.0])
    old = wl.drop_ground_blocks(design, G)
    assert all(r["type"] != "stitch" for r in old["stitches"][len(bed) + 1:])       # old: every white stitch gone
    new, keep = wl.keep_visible_ground(design, G, 20.0)
    white = new["stitches"][len(bed) + 1:]
    assert [r["type"] for r in white] == ["jump", "stitch", "jump", "jump"]         # the one over the bed stays
    assert keep == [True, True]                                                     # the white block shows
    only_cloth = _design(bed + [{"x": 0, "y": 0, "type": "color"}] + on_cloth,
                         colors=[{"r": 0, "g": 0, "b": 0}, {"r": 240, "g": 240, "b": 240}])
    assert wl.keep_visible_ground(only_cloth, G, 20.0)[1] == [True, False]          # a white block on bare cloth does not


def _white_on_black(text="STAY", height_mm=3.5):
    """-> (rgb, alpha, mask of the word, mask of the bed, the word's box as
    fractions of the bed's): `text` knocked out of a black bed on white art,
    PPM px/mm."""
    img = np.full((int(18 * PPM), int(50 * PPM), 3), 255, np.uint8)
    b0, b1 = (int(2 * PPM), int(2 * PPM)), (int(48 * PPM), int(16 * PPM))
    img[b0[1]:b1[1], b0[0]:b1[0]] = 0
    scale = height_mm * PPM / 21.0                      # HERSHEY_DUPLEX capitals are ~21 px at scale 1
    word = np.zeros(img.shape[:2], np.uint8)
    cv2.putText(word, text, (int(8 * PPM), int(10.5 * PPM)), cv2.FONT_HERSHEY_DUPLEX, scale, 255,
                max(2, int(round(0.7 * PPM / 3))), cv2.LINE_AA)
    img[word > 127] = 255
    bed = np.zeros(img.shape[:2], bool)
    bed[b0[1]:b1[1], b0[0]:b1[0]] = True
    ys, xs = np.where(word > 127)
    m = 0.6 * PPM
    box = [(xs.min() - m - b0[0]) / (b1[0] - b0[0]), (ys.min() - m - b0[1]) / (b1[1] - b0[1]),
           (xs.max() + m - b0[0]) / (b1[0] - b0[0]), (ys.max() + m - b0[1]) / (b1[1] - b0[1])]
    return img[..., ::-1].astype(np.float32), np.full(bed.shape, 255, np.uint8), word > 127, bed, box


def _bed_and_white_word(word, bed):
    sewn, over = _fill_design(bed, pitch_mm=0.3), _fill_design(word, pitch_mm=0.2)
    return {"stitches": sewn["stitches"] + [{"x": 0, "y": 0, "type": "color"}] + over["stitches"],
            "colors": [{"r": 0, "g": 0, "b": 0}, {"r": 240, "g": 240, "b": 240}]}, len(sewn["stitches"]) + 1


def test_a_small_white_word_on_a_black_bed_used_to_be_not_located_and_is_now():
    rgb, alpha, word, bed, box = _white_on_black()
    design, n_bed = _bed_and_white_word(word, bed)
    words = [{"text": "STAY", "box": box}]
    ys, xs = np.where(word)
    res = wl.read_job("synthetic", design, design, words, rgb, alpha, use_ocr=False, heights=(), ladder=False)
    for f in ("ours", "pro"):
        row = next(r for r in res["rows"] if r["file"] == f and r.get("size") == "native")
        assert row["located"], (f, row)
        assert row["height_mm"] == pytest.approx((ys.max() - ys.min() + 1) / PPM, rel=0.6)       # the word and its margin
        assert row["width_mm"] > 8.0
    # and the old filter, run over the same file, leaves nothing white to find
    G = np.array([255.0, 255.0, 255.0])
    assert all(r["type"] != "stitch" for r in wl.drop_ground_blocks(design, G)["stitches"][n_bed:])


@requires_tesseract
def test_a_small_white_word_on_a_black_bed_is_read_and_has_a_reach():
    rgb, alpha, word, bed, box = _white_on_black()
    design, _n = _bed_and_white_word(word, bed)
    words = [{"text": "STAY", "box": box}]
    res = wl.read_job("synthetic", design, design, words, rgb, alpha, use_ocr=True, heights=())
    row = next(r for r in res["rows"] if r["file"] == "pro" and r.get("size") == "native")
    assert row["cc"] is not None and row["cc"] > 0.5, row
    assert row["view"] in ("wide", "tight")                        # which of the two crops read it
    assert row["reach"] is not None and row["reach"] > 0.0
    assert row["ladder"][0][0] == pytest.approx(row["height_mm"] * wl.RENDER_PPM, rel=0.01)
    assert res["figures"]["pro/native"]["reach"] == pytest.approx(row["reach"])
    assert res["art_ceiling"]["STAY"]["reach"] is not None


def test_a_word_nobody_reads_is_blind_and_a_word_only_the_pro_reads_is_not():
    """MFab's outlined AND: the art, ours and the pro's thread all read under
    0.2, so 0.00 against 0.06 is two guesses. BECKER reads 0.00 off the art
    and 1.00 off the pro's thread: that is a reading."""
    rows = [{"file": f, "text": t, "size": "native", "cc": cc}
            for t, o, p in (("AND", 0.0, 0.06), ("BECKER", 0.42, 1.0), ("EST", 1.0, 0.0))
            for f, cc in (("ours", o), ("pro", p))]
    ceilings = {"AND": {"cc": 0.0}, "BECKER": {"cc": 0.0}, "EST": {"cc": 1.0}}
    got = wl.blind_words(rows, ceilings)
    assert list(got) == ["AND"] and "neither the art nor either file" in got["AND"]
    assert wl.blind_words(rows, {"AND": {"cc": 0.9}}) == {}          # a word the art reads is one the reader CAN read
