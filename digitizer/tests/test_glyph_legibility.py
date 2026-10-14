"""`tools/glyph_legibility.py` -- the per-glyph legibility read, pinned.

Synthetic glyphs, drawn from polylines in millimetres, are sewn three ways
and read back: correctly, as a blob with its counter shut, and with an arm
missing. The instrument must rank them in that order for the reason it
claims, and must say so when it cannot read at all. Everything here runs in
a few seconds and needs no digitize; the real-logo measurements are in the
PR that introduced it.
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

from tools import glyph_legibility as gl  # noqa: E402

from .conftest import requires_tesseract  # noqa: E402

SRC_PPM = 30.0                 # synthetic artwork resolution, px per mm
W_MM, H_MM = 24.0, 12.0


def _ring(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
            for k in range(n + 1)]


# Glyph strokes as polylines (mm, y down) on a 24 x 12 mm sheet.
O_STROKE = 0.7                                   # a stroke well over the thread
O_CENTRE, O_R = (6.0, 6.0), 2.2                  # ring centreline radius: counter ~3.7 mm
E_STROKES = [[(14.0, 3.0), (14.0, 9.0)],         # stem
             [(14.0, 3.0), (18.0, 3.0)],         # top arm
             [(14.0, 6.0), (17.0, 6.0)],         # middle arm
             [(14.0, 9.0), (18.0, 9.0)]]         # foot


def _artwork(strokes_mm, width_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """White sheet, black strokes of `width_mm`: (rgb float32, alpha)."""
    h, w = int(H_MM * SRC_PPM), int(W_MM * SRC_PPM)
    img = np.full((h, w), 255, np.uint8)
    for pl in strokes_mm:
        pts = np.array([[x * SRC_PPM, y * SRC_PPM] for x, y in pl], np.float32)
        cv2.polylines(img, [np.round(pts).astype(np.int32)], False, 0,
                      max(1, int(round(width_mm * SRC_PPM))), cv2.LINE_AA)
    rgb = np.repeat(img[..., None], 3, axis=2).astype(np.float32)
    return rgb, np.full((h, w), 255, np.uint8)


def _design(paths_mm, colour=(0, 0, 0), step=0.5, ground_under=False) -> dict:
    """A Design dict (0.1 mm, y up) that runs along each polyline in order,
    one run each, in a single colour block."""
    recs, cols = [], []
    if ground_under:
        cols.append({"r": 255, "g": 255, "b": 255})
        recs.append({"x": 0.0, "y": 0.0, "type": "jump"})
        for yy in np.arange(0.5, H_MM, 0.4):
            recs += [{"x": 0.0, "y": -yy * 10, "type": "stitch"},
                     {"x": W_MM * 10, "y": -yy * 10, "type": "stitch"}]
        recs.append({"x": 0.0, "y": 0.0, "type": "color"})
    cols.append({"r": colour[0], "g": colour[1], "b": colour[2]})
    for pl in paths_mm:
        first = True
        for (x0, y0), (x1, y1) in zip(pl[:-1], pl[1:]):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
            for k in range(0 if first else 1, n + 1):
                t = k / n
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                if first and k == 0:      # a run starts with a jump, then a stitch at the same point
                    recs.append({"x": x * 10, "y": -y * 10, "type": "jump"})
                recs.append({"x": x * 10, "y": -y * 10, "type": "stitch"})
                first = False
    return {"stitches": recs, "colors": cols}


def _read(strokes, width, paths, box, **kw):
    rgb, alpha = _artwork(strokes, width)
    words, dbg, reg = gl.read_arrays(rgb, alpha, {"w": box}, _design(paths, **kw), use_ocr=False)
    return words[0], reg


O_BOX = (0.04, 0.10, 0.46, 0.90)
E_BOX = (0.52, 0.10, 0.82, 0.90)


def _o_paths(radii):
    return [_ring(*O_CENTRE, r) for r in radii]


def test_a_glyph_sewn_through_its_stroke_reads_as_itself():
    # three passes across a 0.7 mm stroke, 0.4 mm thread: covers it, counter open
    word, reg = _read([_ring(*O_CENTRE, O_R)], O_STROKE, _o_paths([O_R - 0.15, O_R, O_R + 0.15]), O_BOX)
    g = word.glyphs[0]
    assert len(word.glyphs) == 1
    assert g["legibility"] >= 0.8, g
    assert g["counters"] == 1.0 and g["euler_match"] and g["src_counters_openable"] == 1
    assert g["strokes"] >= 0.95 and g["clean"] >= 0.85


def test_counters_shut_is_caught_by_the_euler_read_and_nothing_else_bills_it_enough():
    """A filled disc has the ink around the counter and ten times the excess;
    the point is the counter column reads 0 and the glyph falls well below a
    correct sewing."""
    good, _ = _read([_ring(*O_CENTRE, O_R)], O_STROKE, _o_paths([O_R - 0.15, O_R, O_R + 0.15]), O_BOX)
    rows = [[(O_CENTRE[0] - O_R - 0.4, O_CENTRE[1] + dy), (O_CENTRE[0] + O_R + 0.4, O_CENTRE[1] + dy)]
            for dy in np.arange(-O_R - 0.4, O_R + 0.41, 0.3)]
    shut, _ = _read([_ring(*O_CENTRE, O_R)], O_STROKE, rows, O_BOX)
    g, s = good.glyphs[0], shut.glyphs[0]
    assert s["counters"] == 0.0
    assert s["sewn_counters"] == 0 and s["src_counters_openable"] == 1
    assert not s["euler_match"] and g["euler_match"]
    assert s["legibility"] < 0.5 * g["legibility"]
    assert s["strokes"] >= 0.9            # recall alone would have passed it


def test_a_missing_arm_has_the_same_euler_number_and_is_caught_by_strokes():
    """An E sewn as an L has Euler number 1 either way, and on a small letter
    its IoU is nearly unchanged -- the reason topology alone is not the read."""
    stem_arms = [[p for p in E_STROKES[0]], E_STROKES[1], E_STROKES[2], E_STROKES[3]]
    full, _ = _read(E_STROKES, 0.6, [[(14.0, 3.0), (18.0, 3.0)], [(14.0, 3.0), (14.0, 9.0)],
                                      [(14.0, 6.0), (17.0, 6.0)], [(14.0, 9.0), (18.0, 9.0)]], E_BOX)
    as_l, _ = _read(E_STROKES, 0.6, [[(14.0, 3.0), (14.0, 9.0), (18.0, 9.0)]], E_BOX)
    del stem_arms
    f, l = full.glyphs[0], as_l.glyphs[0]
    assert f["euler_match"] and l["euler_match"]
    assert f["strokes"] >= 0.9 and l["strokes"] < 0.7
    assert l["legibility"] < 0.8 * f["legibility"]
    assert l["shape"] < f["shape"]


def _e_paths():
    return [[(14.0, 3.0), (18.0, 3.0)], [(14.0, 3.0), (14.0, 9.0)],
            [(14.0, 6.0), (17.0, 6.0)], [(14.0, 9.0), (18.0, 9.0)]]


def test_thread_poured_into_the_bays_is_billed_as_lost_space():
    """An E whose arms are joined by solid thread has every stroke, no counter
    to lose and nothing missing: only the negative-space read sees it."""
    good, _ = _read(E_STROKES, 0.6, _e_paths(), E_BOX)
    rows = [[(14.0, y), (18.0, y)] for y in np.arange(3.0, 9.01, 0.3)]
    flooded, _ = _read(E_STROKES, 0.6, rows, E_BOX)
    g, f = good.glyphs[0], flooded.glyphs[0]
    assert g["space"] >= 0.9 and f["space"] < 0.3
    assert f["strokes"] >= 0.95 and f["counters"] == 1.0
    assert f["legibility_space"] < g["legibility_space"] - 0.5


def test_two_counters_run_into_one_are_billed_once():
    """An 8 sewn as one big loop (its waist never sewn) has ONE hole against
    the source's TWO. Matching is one-to-one, so one counter is lost."""
    eight = [_ring(6.0, 4.0, 1.6), _ring(6.0, 7.4, 2.0)]
    rgb, alpha = _artwork(eight, 0.5)
    box = (0.14, 0.05, 0.36, 0.95)
    right = [_ring(6.0, 4.0, r) for r in (1.55, 1.6, 1.65)] + [_ring(6.0, 7.4, r) for r in (1.95, 2.0, 2.05)]
    one_loop = [[(6.0 + 2.2 * math.cos(2 * math.pi * k / 72), 5.9 + 3.7 * math.sin(2 * math.pi * k / 72))
                 for k in range(73)]]
    good = gl.read_arrays(rgb, alpha, {"w": box}, _design(right), use_ocr=False)[0][0].glyphs[0]
    zero = gl.read_arrays(rgb, alpha, {"w": box}, _design(one_loop), use_ocr=False)[0][0].glyphs[0]
    assert good["src_counters_openable"] == 2 and good["counters"] == 1.0 and good["euler_match"]
    assert zero["sewn_counters"] == 1 and zero["counters"] == 0.5 and not zero["euler_match"]


def test_thread_off_the_letter_is_billed_as_not_clean():
    word, _ = _read(E_STROKES, 0.6, [[(14.0, 3.0), (18.0, 3.0)], [(14.0, 3.0), (14.0, 9.0)],
                                     [(14.0, 6.0), (17.0, 6.0)], [(14.0, 9.0), (18.0, 9.0)],
                                     [(15.0, 4.0), (17.0, 8.0)]],          # a stray diagonal across the counters
                    E_BOX)
    g = word.glyphs[0]
    assert g["clean"] < 0.9


def test_ground_coloured_thread_under_the_letters_is_not_ink():
    paths = _o_paths([O_R - 0.15, O_R, O_R + 0.15])
    plain, _ = _read([_ring(*O_CENTRE, O_R)], O_STROKE, paths, O_BOX)
    under, _ = _read([_ring(*O_CENTRE, O_R)], O_STROKE, paths, O_BOX, ground_under=True)
    assert under.glyphs[0]["legibility"] == pytest.approx(plain.glyphs[0]["legibility"], abs=0.05)


def test_a_design_shifted_off_the_artwork_is_registered_back():
    paths = _o_paths([O_R - 0.15, O_R, O_R + 0.15])
    rgb, alpha = _artwork([_ring(*O_CENTRE, O_R)], O_STROKE)
    ref = gl.read_arrays(rgb, alpha, {"w": O_BOX}, _design(paths), use_ocr=False)[0][0].glyphs[0]
    shifted = [[(x + 0.35, y - 0.30) for x, y in pl] for pl in paths]
    got = gl.read_arrays(rgb, alpha, {"w": O_BOX}, _design(shifted), use_ocr=False)[0][0].glyphs[0]
    assert got["legibility"] == pytest.approx(ref["legibility"], abs=0.08)


def test_a_word_box_with_no_ink_reports_no_glyphs_instead_of_a_score():
    rgb, alpha = _artwork([_ring(*O_CENTRE, O_R)], O_STROKE)
    words, _d, _r = gl.read_arrays(rgb, alpha, {"empty": (0.60, 0.10, 0.95, 0.90)},
                                   _design(_o_paths([O_R])), use_ocr=False)
    assert words[0].glyphs == []
    assert words[0].summary()["legibility"] is None


def test_the_ceiling_keeps_a_thin_stroke_from_reading_as_a_failure():
    """A 0.2 mm stroke sewn with 0.4 mm thread cannot reach IoU 1; its
    ceiling is the thread-width one, and `shape` divides by it."""
    word, _ = _read(E_STROKES, 0.2, [[(14.0, 3.0), (18.0, 3.0)], [(14.0, 3.0), (14.0, 9.0)],
                                     [(14.0, 6.0), (17.0, 6.0)], [(14.0, 9.0), (18.0, 9.0)]], E_BOX)
    g = word.glyphs[0]
    assert g["iou_ceiling"] < 0.7 and g["iou"] < 0.7
    assert g["shape"] >= 0.8


def test_without_tesseract_ocr_says_so_and_never_passes(monkeypatch):
    monkeypatch.setattr(gl.shutil, "which", lambda _n: None)
    rgb, alpha = _artwork([_ring(*O_CENTRE, O_R)], O_STROKE)
    words, _d, _r = gl.read_arrays(rgb, alpha, {"w": O_BOX}, _design(_o_paths([O_R])), use_ocr=True)
    assert words[0].ocr == "OCR UNAVAILABLE"
    assert "ocr_recovered" not in words[0].glyphs[0]
    assert gl.validate({"ours_fremont81": words})["ocr_cross_check"] == "OCR UNAVAILABLE"


@requires_tesseract
def test_ocr_reads_a_glyph_alone_and_reports_a_wilson_interval():
    rgb = np.full((int(H_MM * SRC_PPM), int(W_MM * SRC_PPM)), 255, np.uint8)
    cv2.putText(rgb, "E", (int(2 * SRC_PPM), int(10 * SRC_PPM)), cv2.FONT_HERSHEY_SIMPLEX,
                9.0, 0, 18, cv2.LINE_AA)
    mask = rgb < 128
    txt, conf = gl._ocr_char(np.pad(mask, 10), SRC_PPM)
    assert txt == "E" and conf > 0
    lo, hi = gl.wilson(3, 4)
    assert 0.3 < lo < 0.5 and 0.9 < hi < 1.0
    assert gl.wilson(0, 0) is None


def test_auc_and_its_cluster_bootstrap():
    assert gl.auc([0.9, 0.8], [0.2, 0.3]) == 1.0
    assert gl.auc([0.5], [0.5]) == 0.5
    assert gl.auc([], [0.1]) is None
    r = gl.cluster_auc_ci([[0.9, 0.8], [0.85], [0.7, 0.75]], [[0.2, 0.3], [0.4]], n_boot=200)
    assert r["auc"] == 1.0 and r["ci95"] == [1.0, 1.0] and (r["n_pos"], r["n_neg"]) == (3, 2)
    mixed = gl.cluster_auc_ci([[0.9], [0.3]], [[0.5], [0.2]], n_boot=200)
    assert mixed["ci95"][0] < mixed["auc"] < mixed["ci95"][1] + 1e-9


def test_fremont_word_boxes_find_the_glyphs_Kent_circled():
    """Source side only (no design): the labelled boxes must hold the letters
    and nothing else, or every number downstream is about the wrong thing."""
    rgb, alpha = gl.load_source(gl.ROOT / "testdata" / gl.CASES["fremont"]["source"])
    h, w = rgb.shape[:2]
    G = gl.ground_colour(rgb, alpha)
    soft, _thr = gl.soft_ink(rgb, alpha, G)
    expect = {"est": 3, "1895": 4, "the": 3, "hotel": 5, "fremont": 7}
    for name, n in expect.items():
        fx0, fy0, fx1, fy1 = gl.CASES["fremont"]["boxes"][name]
        box = (int(fx0 * w), int(fy0 * h), int(fx1 * w), int(fy1 * h))
        sub = np.zeros(soft.shape, bool)
        sub[box[1]:box[3], box[0]:box[2]] = soft[box[1]:box[3], box[0]:box[2]] >= 0.5
        sm = cv2.resize(sub.astype(np.uint8), None, fx=0.25, fy=0.25, interpolation=cv2.INTER_NEAREST) > 0
        _lab, found = gl._label_glyphs(sm, (box[0] // 4, box[1] // 4, box[2] // 4, box[3] // 4), 5.0)
        assert len(found) == n, (name, len(found))


# --- pull-aware reading --------------------------------------------------------
#
# A narrow-bayed E: arms 1.4 mm apart, drawn 0.5 mm thick, so each bay is 0.9 mm
# clear in the artwork. Sewn the way the engine sews a cap, every rail pushed out
# 0.4 mm (the structured cap's pull), each arm is 1.3 mm of thread and the bay
# is 0.1 mm: shut, as a render, though the cloth would draw it back open.

PULL_E = [[(14.0, 4.0), (14.0, 6.8)], [(14.0, 4.0), (17.0, 4.0)],
          [(14.0, 5.4), (16.0, 5.4)], [(14.0, 6.8), (17.0, 6.8)]]
PULL_E_BOX = (0.50, 0.20, 0.82, 0.70)


def _pushed_e(push: float, step: float = 0.15):
    """The E as parallel passes: each stroke gets passes every `step` mm out to
    `0.25 + push` either side of its centreline (less half a thread)."""
    reach = 0.25 + push - 0.2
    offs = np.arange(-reach, reach + 1e-9, step)
    paths = [[(14.0 + dx, 4.0 - reach), (14.0 + dx, 6.8 + reach)] for dx in offs]
    for y0, x1 in ((4.0, 17.0), (5.4, 16.0), (6.8, 17.0)):
        paths += [[(14.0, y0 + dy), (x1, y0 + dy)] for dy in offs]
    return paths


def _read_pull(push: float, pull, **kw):
    rgb, alpha = _artwork(PULL_E, 0.5)
    words, dbg, _reg = gl.read_arrays(rgb, alpha, {"w": PULL_E_BOX}, _design(_pushed_e(push)),
                                      use_ocr=False, pull_mm=pull, **kw)
    return words[0], dbg["w"]


def test_default_pull_is_zero_and_today_s_output_exactly():
    """`pull_mm` left out, 0 and 0.0 are one read, and it is the read the
    instrument made before the option existed (numbers measured on the commit
    before `--pull-mm` landed)."""
    o_paths = _o_paths([O_R - 0.15, O_R, O_R + 0.15])
    rgb, alpha = _artwork([_ring(*O_CENTRE, O_R)], O_STROKE)
    base = gl.read_arrays(rgb, alpha, {"w": O_BOX}, _design(o_paths), use_ocr=False)[0][0]
    zero = gl.read_arrays(rgb, alpha, {"w": O_BOX}, _design(o_paths), use_ocr=False, pull_mm=0.0)[0][0]
    assert base.glyphs == zero.glyphs and base.pull_mm == 0.0
    g = base.glyphs[0]
    assert (g["iou"], g["area_sewn_mm2"], g["stroke_w_sewn_mm"]) == (0.962, 10.915, 0.781)
    e, _ = _read(E_STROKES, 0.6, _e_paths(), E_BOX)
    ge = e.glyphs[0]
    assert (ge["iou"], ge["area_sewn_mm2"], ge["stroke_w_sewn_mm"]) == (0.681, 8.008, 0.5)
    mask = np.zeros((40, 40), bool)
    mask[10:30, 10:30] = True
    assert gl.pull_erode(mask, 0.0, 0.4) is mask


def test_pull_erode_takes_the_pull_off_each_side_but_never_a_stroke_under_one_thread():
    wide = np.zeros((200, 200), bool)
    wide[80:120, 20:180] = True                              # a 2.0 mm bar at 20 px/mm
    out = gl.pull_erode(wide, 0.4, 0.4)
    assert (out.sum(axis=0)[100], wide.sum(axis=0)[100]) == (24, 40)      # 0.4 mm gone each side
    thin = np.zeros((200, 200), bool)
    thin[96:104, 20:180] = True                              # 0.4 mm: one thread
    kept = gl.pull_erode(thin, 0.4, 0.4)
    assert kept.any() and kept.sum() >= 0.8 * thin.sum()     # it keeps its own line


def test_a_thin_line_survives_the_pull_only_where_it_lies_on_the_ink():
    thin = np.zeros((200, 200), bool)
    thin[96:104, 20:180] = True                              # 0.4 mm line
    ink = np.zeros_like(thin)
    ink[90:110, 20:100] = True                               # the artwork's ink under its left half
    got = gl.pull_erode(thin, 0.4, 0.4, ink=ink, lines="ink")
    assert got[:, 30:90].any() and not got[:, 110:170].any()
    assert gl.pull_erode(thin, 0.4, 0.4, ink=ink, lines="all")[:, 110:170].any()
    assert not gl.pull_erode(thin, 0.4, 0.4, ink=ink, lines="none").any()


def test_a_pinhole_in_a_column_is_not_grown_into_a_counter_by_the_pull():
    col = np.zeros((200, 200), bool)
    col[60:140, 40:160] = True
    col[100:102, 100:102] = False                            # 0.1 mm texture gap between rows
    assert gl.pull_erode(col, 0.3, 0.4)[100, 100]            # closed before the erosion, so it stays closed
    real = col.copy()
    real[85:115, 85:115] = False                             # 1.5 mm: a counter
    assert gl.ndi.binary_fill_holes(gl.pull_erode(real, 0.3, 0.4))[100, 100] and not gl.pull_erode(real, 0.3, 0.4)[100, 100]


def test_a_bay_the_pull_would_reopen_reads_closed_without_pull_and_open_with_it():
    shut, shut_dbg = _read_pull(0.4, 0.0)
    pulled, dbg = _read_pull(0.4, 0.4)
    gs, gp = shut.glyphs[0], pulled.glyphs[0]
    assert gs["space"] < 0.4 and gp["space"] >= 0.7, (gs["space"], gp["space"])
    assert gp["strokes"] >= 0.9 and gp["legibility_space"] > gs["legibility_space"] + 0.4
    assert pulled.pull_mm == 0.4 and shut.pull_mm == 0.0
    assert dbg["T"].sum() < shut_dbg["T"].sum()


def test_pull_does_not_rescue_a_bay_that_was_poured_full():
    """The pull takes back what the push put out. Solid thread across the bays
    is still solid thread after it."""
    rgb, alpha = _artwork(PULL_E, 0.5)
    rows = [[(14.0, y), (17.0, y)] for y in np.arange(3.6, 7.21, 0.2)]
    words, _d, _r = gl.read_arrays(rgb, alpha, {"w": PULL_E_BOX}, _design(rows), use_ocr=False, pull_mm=0.4)
    kept_open = _read_pull(0.4, 0.4)[0].glyphs[0]["space"]
    assert words[0].glyphs[0]["space"] < kept_open - 0.2, (words[0].glyphs[0]["space"], kept_open)


def test_a_design_that_declares_its_pull_is_believed_and_one_that_does_not_is_estimated():
    d = _design(_pushed_e(0.4))
    assert gl.declared_pull_mm(d) is None
    assert gl.declared_pull_mm({**d, "pull_comp_mm": 0.35}) == 0.35
    assert gl.declared_pull_mm({**d, "fabric": {"pull_comp_mm": 0.5}}) == 0.5
    rgb, alpha = _artwork(PULL_E, 0.5)
    box = {"w": PULL_E_BOX}
    declared = gl.read_arrays(rgb, alpha, box, {**d, "pull_comp_mm": 0.4}, use_ocr=False, pull_mm="auto")[0][0]
    explicit = gl.read_arrays(rgb, alpha, box, d, use_ocr=False, pull_mm=0.4)[0][0]
    assert declared.pull_mm == 0.4 and declared.glyphs == explicit.glyphs
    est = gl.read_arrays(rgb, alpha, box, d, use_ocr=False, pull_mm="auto")[0][0]
    assert 0.2 <= est.pull_mm <= gl.PULL_AUTO_MAX_MM            # the push is 0.4 a side; stroke width reads it back
    assert est.glyphs[0]["space"] >= 0.6                       # and the estimate opens the bay
    plain = gl.read_arrays(rgb, alpha, box, _design(PULL_E, step=0.2), use_ocr=False, pull_mm="auto")[0][0]
    assert plain.pull_mm <= 0.12                                # a design with no push is not eroded
    with pytest.raises(ValueError):
        gl.read_arrays(rgb, alpha, box, d, use_ocr=False, pull_mm="sometimes")


def test_the_cli_takes_a_number_or_auto_and_nothing_else(capsys):
    for bad in ("sometimes", "-0.1", "9"):
        with pytest.raises(SystemExit) as e:
            gl.main(["--list", "--pull-mm", bad])
        assert e.value.code == 2
    capsys.readouterr()
