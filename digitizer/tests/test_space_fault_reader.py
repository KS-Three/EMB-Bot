"""`tools.space_fault_reader` pure helpers and its pin list. No engine.

Synthetic class images at the reader's own 12 px/mm: a "C" whose bay the
thread fills solid (the S case: no hole appears or vanishes, so the letter
reader's topology cannot see it), two bars whose gap the thread fills, and
the controls that must stay silent (a faithful copy, one running-stitch
filament across the gap, thread on the two bars' Voronoi line OUTSIDE the
pair's hull, a shape its thread never sews).
"""
import json
from pathlib import Path

import numpy as np

from tools import fault_reader_harness as h
from tools import letter_fault_reader as lfr
from tools import space_fault_reader as sfr

DOCS = Path(__file__).resolve().parents[2] / "docs"
PX = sfr.PXMM


def _disc(shape, cx, cy, r):
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def _c_letter(shape=(120, 120)):
    ring = _disc(shape, 60, 60, 30) & ~_disc(shape, 60, 60, 18)
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    return ring & ~((xx > 60) & (abs(yy - 60) < 10))


def _labels(art: np.ndarray, thr: np.ndarray):
    a = np.where(art, 0, sfr.UNSEWN).astype(np.int16)
    t = np.where(thr, 0, sfr.UNSEWN).astype(np.int16)
    return a, t


def _bars(shape=(120, 100)):
    art = np.zeros(shape, bool)
    art[20:100, 20:40] = True
    art[20:100, 50:70] = True               # gap 10 px = 0.83 mm
    return art


def test_constants_are_the_documented_ones():
    from digitizer_core import glyph_read, stitchviz
    from tools import edge_fault_reader as efr
    assert sfr.SPACE_MIN_HALF_MM == glyph_read.SPACE_MIN_HALF_MM
    assert sfr.SPACE_KEEP_HALF_MM == glyph_read.SPACE_KEEP_HALF_MM
    assert sfr.MIN_SHAPE_MM2 == glyph_read.MIN_GLYPH_MM2 == lfr.MIN_SHAPE_MM2
    assert sfr.SEWN_FRAC == lfr.SEWN_FRAC and sfr.BRIDGE_MIN_MM == lfr.BRIDGE_MIN_MM
    assert sfr.SPACING_MM == efr.MERGE_MM
    assert sfr.THREAD_MM == stitchviz.THREAD_MM and sfr.PXMM == lfr.PXMM and sfr.PAD_MM == lfr.PAD_MM


def test_faithful_c_is_silent_and_has_candidates():
    art = _c_letter()
    flags, cands, cand = sfr.read_spaces(*_labels(art, art))
    assert flags == []
    assert cands and cand.any() and all(c["kind"] == "bay" for c in cands)


def test_c_with_its_bay_filled_solid_is_flagged_but_topology_is_unchanged():
    art = _c_letter()
    thr = _disc(art.shape, 60, 60, 30)                    # thread pours into the bay
    flags, _c, _m = sfr.read_spaces(*_labels(art, thr))
    assert flags and {f["kind"] for f in flags} == {"bay"}
    assert all(f["strength"] > sfr.BRIDGE_MIN_MM for f in flags)
    # the letter reader's three rules see nothing: no counter in the art, no hole in the thread
    assert lfr.read_faults(*_labels(art, thr)) == []
    # the flag sits in the bay (pins' frame: px / 12 - 2)
    x, y = flags[0]["x_mm"], flags[0]["y_mm"]
    assert abs((x + 2) * PX - 60) <= 30 and abs((y + 2) * PX - 60) <= 30


def test_gap_filled_between_two_bars_is_a_gap_flag():
    art = _bars()
    thr = art.copy()
    thr[20:100, 40:50] = True
    flags, cands, _m = sfr.read_spaces(*_labels(art, thr))
    assert flags and {f["kind"] for f in flags} == {"gap"}
    xs = {round((f["x_mm"] + 2) * PX) for f in flags}
    assert xs <= {44, 45}                                  # the Voronoi line, mid-gap
    # spread along the 80 px run, no two flags within SPACING_MM
    pts = np.array([(f["x_mm"], f["y_mm"]) for f in flags])
    d = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1)) + np.eye(len(pts)) * 99
    assert d.min() >= sfr.SPACING_MM - 1e-6 and len(flags) >= 3
    assert {c["kind"] for c in cands} == {"gap"}


def test_one_filament_across_the_gap_is_travel_not_a_fault():
    art = _bars()
    thr = art.copy()
    thr[58:63, 40:50] = True                               # 5 px = one 0.4 mm filament
    assert sfr.read_spaces(*_labels(art, thr))[0] == []


def test_thread_on_the_voronoi_line_outside_the_pair_hull_is_not_a_gap():
    art = _bars()
    thr = art.copy()
    thr[0:16, 38:52] = True                                # above both bars, on x = 45
    assert sfr.read_spaces(*_labels(art, thr))[0] == []


def test_thread_spill_into_a_shallow_outline_dent_is_not_a_space():
    art = np.zeros((120, 160), bool)
    art[30:100, 20:140] = True
    art[30:36, 50:110] = False                             # a 0.5 mm dent along the top edge
    thr = np.zeros_like(art)
    thr[27:103, 17:143] = True                             # the render's outline: 3 px of spill
    thr[33:36, 53:107] = False                             # the dent still shows, narrower
    flags, cands, _m = sfr.read_spaces(*_labels(art, thr))
    assert flags == [] and cands == []


def test_hull_depth():
    sq = np.array([[0, 0], [10, 0], [10, 10], [0, 10]])
    d = sfr.hull_depth(np.array([5, 1, 12, 10]), np.array([5, 5, 5, 3]), sq)
    assert d.tolist() == [5.0, 1.0, -1.0, 0.0]
    assert sfr.hull_depth(np.array([5]), np.array([5]), sq[::-1]).tolist() == [5.0]


def test_unsewn_shape_is_not_judged():
    art = _c_letter()
    thr = np.zeros_like(art)
    thr[40:80, 70:100] = True                              # thread only in the mouth, C itself unsewn
    flags, cands, _m = sfr.read_spaces(*_labels(art, thr))
    assert flags == [] and cands == []


def test_other_colour_in_the_space_is_not_closure():
    art = _c_letter()
    a = np.where(art, 0, sfr.UNSEWN).astype(np.int16)
    t = np.where(art, 0, 1).astype(np.int16)               # the bay sewn in a second colour: correct
    t[~_disc(art.shape, 60, 60, 30)] = sfr.UNSEWN
    assert sfr.read_spaces(a, t)[0] == []


def test_spread_keeps_order_and_spacing():
    ys = np.array([0, 0, 0, 0], float)
    xs = np.array([0, 5, 10, 30], float)
    assert sfr.spread(ys, xs, np.array([1, 0, 2, 3]), 8.0) == [1, 3]


def test_space_pins_are_the_letter_pins_with_their_note():
    out = {}
    for sit, prefix in (("defect-marks-2026-11-10", "L_"), ("defect-marks-2026-11-11", "C_")):
        marks = json.loads((DOCS / sit / "marks.json").read_text(encoding="utf-8"))
        sp = h.select_space_pins(marks, prefix)
        assert [{k: v for k, v in p.items() if k != "note_pin"} for p in sp] == h.select_letter_pins(marks, prefix)
        out[sit] = sp
    committed = json.loads((DOCS / "space-fault-reader-2026-11-12" / "pins.json").read_text(encoding="utf-8"))
    assert committed["rule"] == h.FAULTS["space"][1]
    assert committed["pins"] == out["defect-marks-2026-11-10"] + out["defect-marks-2026-11-11"]
    pins = committed["pins"]
    assert len(pins) == 44 and len({p["item"] for p in pins}) == 7
    assert len({(p["item"], p["note_pin"]) for p in pins}) == 15
    assert {p["note_pin"] for p in pins if p["item"] == "C_silhouette_logo"} == {3}


def test_harness_scores_a_space_dir(tmp_path):
    art = _c_letter()
    thr = _disc(art.shape, 60, 60, 30)
    flags, cands, cand = sfr.read_spaces(*_labels(art, thr))
    (tmp_path / "L_x.flags.json").write_text(json.dumps(
        {"flags": flags, "candidates": cands, "px_per_mm": PX, "pad_mm": sfr.PAD_MM}), encoding="utf-8")
    np.savez_compressed(tmp_path / "L_x.mask.npz", mask=thr, cand=cand)
    f = flags[0]
    marks = {"items": {"L_x": {"pins": [{"x_mm": f["x_mm"], "y_mm": f["y_mm"], "what": "letter_shape",
                                         "note": "The S doesn't have spacing between the curves"}]}}}
    res = h.score_many([(marks, tmp_path, "L_")], "space")
    b = res["items"]["L_x"]["by_radius"]["3.0"]
    assert b["hit"] == 1 and "chance_pick" in b and res["pooled_notes"]["3.0"]["chance_pick"]["notes"] == 1
