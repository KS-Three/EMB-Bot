"""`tools.letter_fault_reader` pure helpers and the letter pin rule. No engine.

Synthetic masks at the reader's own 12 px/mm: an "O" whose counter the
thread fills, two bars the thread bridges, a "C" whose mouth the thread
closes, and the controls that must stay silent (a faithful copy, a lone
running-stitch filament between two shapes, a fringe the thread never sews).
"""
import json
from pathlib import Path

import numpy as np
import pytest

from tools import fault_reader_harness as h
from tools import letter_fault_reader as lfr

DOCS = Path(__file__).resolve().parents[2] / "docs" / "defect-marks-2026-11-10"
PX = lfr.PXMM


def _pin(note="", what=None):
    return {"x_mm": 0.0, "y_mm": 0.0, "what": what, "severity": "noticeable", "note": note}


# --------------------------------------------------------------- selection ----

@pytest.mark.parametrize("note,what,expect", [
    ("The B is missing the two center holes.", "letter_shape", "closure word"),
    ("The N and the T are mergerd together", "letter_shape", "closure word"),
    ("I cannot read the e", "letter_shape", "read word on a letter"),
    ("I can't tell this is an & symbol", "letter_shape", "read word on a letter"),
    ("I cannot tell this is a drone", "missing", None),               # read word, not a letter
    ("Hard to tell what the stitches are doing here.", "mushed", None),
    ("The \"T\" intersects the border", "other", "closure word"),
    ("The white spacing is not very apparent, and the edges are very jagged.", "mushed",
     "closure word, also edge"),                                       # rule 3: shared, says why
    ("The \"M\" is jagged and n", "letter_shape", None),              # edge's, no closure named
    ("The thread is too thick", "other", None),                       # "thread" is not "read"
    ("All of the wheel handles look different from eachother", "letter_shape", None),
])
def test_letter_reason(note, what, expect):
    assert h.letter_reason(_pin(note, what)) == expect


def test_committed_letter_pin_list_is_what_the_rule_selects():
    marks = json.loads((DOCS / "marks.json").read_text(encoding="utf-8"))
    committed = json.loads((DOCS / "letter-reader-pins.json").read_text(encoding="utf-8"))
    assert committed["rule"] == h.FAULTS["letters"][1]
    assert h.select_letter_pins(marks) == committed["pins"]
    assert len(committed["pins"]) == 14 and len({p["item"] for p in committed["pins"]}) == 6
    edge = {(p["item"], p["pin"]) for p in h.select_edge_pins(marks)}
    shared = [(p["item"], p["pin"]) for p in committed["pins"] if (p["item"], p["pin"]) in edge]
    assert shared == [("L_gaulke_roofing_hat", 3)]          # the one pin rule 3 shares, by name


def test_edge_selection_is_untouched_by_the_generalisation():
    marks = json.loads((DOCS / "marks.json").read_text(encoding="utf-8"))
    assert h.select_pins(marks, h.edge_reason) == h.select_edge_pins(marks)


# ----------------------------------------------------------------- helpers ----

def _canvas(w_mm=20, h_mm=12):
    return np.zeros((int(h_mm * PX), int(w_mm * PX)), bool)


def _ring(m, cx, cy, r_out, r_in):
    yy, xx = np.mgrid[: m.shape[0], : m.shape[1]]
    d = np.hypot((xx - cx * PX), (yy - cy * PX))
    m |= (d <= r_out * PX) & (d >= r_in * PX)
    return m


def _rect(m, x0, y0, x1, y1):
    m[int(y0 * PX): int(y1 * PX), int(x0 * PX): int(x1 * PX)] = True
    return m


def test_colour_classes_merge_near_spools():
    cols = [{"r": 0, "g": 0, "b": 0}, {"r": 255, "g": 255, "b": 255}, {"r": 5, "g": 5, "b": 5}]
    assert lfr.colour_classes(cols) == [(0, 0, 0), (255, 255, 255)]


def test_to_mm_is_the_pins_frame():
    assert lfr.to_mm((24.0, 36.0)) == (0.0, 1.0)


def test_faithful_copy_is_silent():
    art = _ring(_canvas(), 6, 6, 3, 1.5)
    assert lfr.read_class(art, art.copy()) == []


def test_filled_counter_is_flagged_at_its_centre():
    art = _ring(_canvas(), 6, 6, 3, 1.5)
    thr = _ring(_canvas(), 6, 6, 3, 0.0)                 # the O sewn solid
    ev = [e for e in lfr.read_class(art, thr) if e["kind"] == "counter_lost"]
    assert len(ev) == 1
    x, y = ev[0]["px"]
    assert abs(x / PX - 6) < 0.2 and abs(y / PX - 6) < 0.2
    assert ev[0]["strength"] == pytest.approx(3.0, abs=0.2)  # the 3 mm counter, all lost


def test_shrunk_counter_past_half_is_lost_and_under_half_shrink_is_kept():
    art = _ring(_canvas(), 6, 6, 3, 1.5)
    small = _ring(_canvas(), 6, 6, 3, 0.6)               # 1.2 mm of 3: under half
    fine = _ring(_canvas(), 6, 6, 3, 1.0)                # 2.0 mm of 3: kept
    assert [e["kind"] for e in lfr.read_class(art, small)] == ["counter_lost"]
    assert lfr.read_class(art, fine) == []


def test_bridged_bars_are_a_join_and_a_lone_filament_is_not():
    art = _rect(_rect(_canvas(), 2, 2, 5, 10), 7, 2, 10, 10)   # two bars, 2 mm apart
    fat = _rect(art.copy(), 5, 5, 7, 7)                         # a 2 mm satin across the gap
    thin = art.copy()
    thin[int(6 * PX): int(6 * PX) + 4, int(5 * PX): int(7 * PX)] = True   # 0.33 mm: one filament
    ev = lfr.read_class(art, fat)
    joins = [e for e in ev if e["kind"] == "join"]
    assert len(joins) == 1 and joins[0]["strength"] == pytest.approx(2.0, abs=0.2)
    assert abs(joins[0]["px"][0] / PX - 6) < 0.3
    assert [e for e in lfr.read_class(art, thin) if e["kind"] == "join"] == []


def test_closed_mouth_is_a_bay_but_a_gap_over_ink_is_not():
    c = _ring(_canvas(), 6, 6, 3, 1.5)
    c[int(5 * PX): int(7 * PX), int(7.5 * PX):] = False         # the C's mouth
    shut = _ring(_canvas(), 6, 6, 3, 1.5)                       # thread closes it: an O
    ev = lfr.read_class(c, shut)
    assert [e["kind"] for e in ev] == ["bay_closed"]
    solid = _rect(_canvas(), 2, 2, 12, 10)
    holed = solid.copy()
    holed[int(5 * PX): int(7 * PX), int(5 * PX): int(7 * PX)] = False   # thread missing over ink
    assert lfr.read_class(solid, holed) == []


def test_a_field_sewn_where_the_art_has_none_of_its_colour_closes_no_bay():
    """Becker: white thread fills the letters' interiors; the art has no white,
    so the white field's holes (the dark letters on top) are not bays."""
    art = np.full(_canvas().shape, lfr.UNSEWN, np.int16)
    letter = _rect(_canvas(), 6, 4, 9, 8)
    art[letter] = 1
    thr = art.copy()
    field = _rect(_canvas(), 2, 2, 14, 10) & ~letter
    thr[field] = 0
    assert lfr.read_faults(art, thr) == []


def test_unsewn_shape_is_not_judged():
    art = _ring(_canvas(), 6, 6, 3, 1.5)
    thr = _rect(_canvas(), 2.5, 5.5, 9.5, 6.5)                  # thread over < half of it
    assert [e for e in lfr.read_class(art, thr) if e["kind"] == "counter_lost"] == []


def test_read_faults_puts_flags_in_the_pins_frame_strongest_first():
    art = np.full(_canvas().shape, lfr.UNSEWN, np.int16)
    thr = art.copy()
    a = _ring(_canvas(), 6, 6, 3, 1.5)
    t = _ring(_canvas(), 6, 6, 3, 0.0)
    art[a] = 0
    thr[t] = 0
    big = _ring(_canvas(), 15, 6, 2, 0.5)
    art[big] = 1
    thr[_ring(_canvas(), 15, 6, 2, 0.0)] = 1
    fl = lfr.read_faults(art, thr)
    assert [f["class"] for f in fl] == [0, 1]
    assert fl[0]["x_mm"] == pytest.approx(6 - lfr.PAD_MM, abs=0.2)
    assert fl[0]["strength"] >= fl[1]["strength"]
