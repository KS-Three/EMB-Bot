"""`tools.infill_fault_reader` pure helpers, the in-fill pin rule, the
harness's candidate nulls and the shared job helper. No engine.

Synthetic rasters at the reader's own 12 px/mm: a red ring with four counters
on a bare page, one counter sewn white (the kanji pattern), one closed up in
the ring's own red (the letter reader's fault, not this one), and four
enclosed spaces of which one is outlined by a running stitch.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from tools import fault_reader_harness as h
from tools import fault_reader_jobs as jobs
from tools import infill_fault_reader as ifr

DOCS = Path(__file__).resolve().parents[2] / "docs"
PX = ifr.PXMM
BARE, RED, WHITE = -1, 0, 1
FILL, RUN = ifr.KINDS.index("fill"), ifr.KINDS.index("run")


def _pin(note="", what=None, x=0.0, y=0.0):
    return {"x_mm": x, "y_mm": y, "what": what, "severity": "noticeable", "note": note}


# --------------------------------------------------------------- selection ----

@pytest.mark.parametrize("note,what,expect", [
    ("#1-#28 extra in-fill, some empty spaces have it while others don't", "extra", "in-fill word"),
    ("This is the only lettering in-fill, it doesn't match the rest", "extra", "in-fill word"),
    ("right leg infill doesn't match left leg", "direction", "in-fill word"),
    ("The interior gaps are inconsistant, some have bean stitching around the openings, while the other doesn't",
     "stitch_type", "contrast between places"),
    ("This extra bean stitch is inconsistant from the right nostrel.", "extra", "contrast between places"),
    ("All of the wheel handles look different from eachother", "letter_shape", "contrast between places"),
    ("This is the only letter that is thinly stitched", None, "contrast between places"),
    ("#2-#3 feet are differnt colors, they should be the same", "colour", None),     # rule 3: colour
    ("This random stitch in the middle doesnt match the pros", "mushed", None),     # against the pro
    ("Random Black Spot", "extra", None),                                           # kind alone: no
    ("The stitching directions and angles are very inconsistent here.", "blob", None),  # no other place named
    ("", "extra", None),
])
def test_infill_reason(note, what, expect):
    assert h.infill_reason(_pin(note, what)) == expect


@pytest.mark.parametrize("note,n,expect", [
    ("#1-#28 extra in-fill", 28, list(range(1, 29))),
    ("in-fill only in select spots (#5-#6)", 8, [5, 6]),
    ("for 7-8", 8, [7, 8]),
    ("all of the extra green stitches (#3 - #32) are the same issue", 32, list(range(3, 33))),
    ("marks 1-4", 2, [1, 2]),                                  # clipped to the item's pins
    ("95% of the way there", 5, []),
])
def test_note_ranges(note, n, expect):
    assert h.note_ranges(note, n) == expect


def test_ranges_cover_only_bare_pins_and_claimed_pins_stay_with_their_reader():
    marks = {"items": {"C_a": {"pins": [
        _pin("#1-#4 extra in-fill, some have it while others don't", "extra"),
        _pin(), _pin(what="pen_flow"),
        _pin("The circle edges should be smooth"),                  # own note: judged by it (edge's)
        _pin("I can't read the \"e\"", "letter_shape")]}}}          # letter rule's
    got = [(p["pin"], p["note_pin"], p["rule"]) for p in h.select_infill_pins(marks, "C_")]
    assert got == [(1, 1, "in-fill word"), (2, 1, "named by pin 1"), (3, 1, "named by pin 1")]


@pytest.mark.parametrize("sitting,prefix,n_pins,n_items,n_notes", [
    ("pins-sitting-1.json", "L_", 2, 1, 2),
    ("pins-sitting-2.json", "C_", 34, 5, 6),
])
def test_committed_infill_pin_lists_are_what_the_rule_selects(sitting, prefix, n_pins, n_items, n_notes):
    marks_dir = "defect-marks-2026-11-10" if prefix == "L_" else "defect-marks-2026-11-11"
    marks = json.loads((DOCS / marks_dir / "marks.json").read_text(encoding="utf-8"))
    committed = json.loads((DOCS / "infill-fault-reader-2026-11-11" / sitting).read_text(encoding="utf-8"))
    assert committed["rule"] == h.FAULTS["infill"][1]
    assert h.select_infill_pins(marks, prefix) == committed["pins"]
    pins = committed["pins"]
    assert (len(pins), len({p["item"] for p in pins}), len({(p["item"], p["note_pin"]) for p in pins})) == \
        (n_pins, n_items, n_notes)
    other = {(p["item"], p["pin"]) for p in h.select_edge_pins(marks, prefix) + h.select_letter_pins(marks, prefix)}
    assert not other & {(p["item"], p["pin"]) for p in pins}


def test_the_older_rules_are_untouched():
    for d, f in (("defect-marks-2026-11-10", "edge-reader-pins.json"),):
        marks = json.loads((DOCS / d / "marks.json").read_text(encoding="utf-8"))
        assert h.select_edge_pins(marks) == json.loads((DOCS / d / f).read_text(encoding="utf-8"))["pins"]


# ----------------------------------------------------------- harness nulls ----

def test_edge_band_null_is_zero_for_flags_inside_a_field():
    """Why `chance_edge` read 0.00 on Bridge and the silhouette logo: the band
    is thread beside FABRIC, so a field's only band is its outer rim, and a
    flag deeper than the radius inside the field is unreachable from it."""
    m = np.zeros((600, 600), bool)
    m[60:540, 60:540] = True                                      # a 40 x 40 mm sewn field
    flags = [{"x_mm": 23.0, "y_mm": 23.0, "strength": 1.0}]      # its middle: 20 mm from fabric
    assert h.chance_rate(flags, h.edge_band(m, PX), 5, PX, 2.0, 3.0, draws=500) == 0.0
    assert h.chance_rate(flags, m, 5, PX, 2.0, 3.0, draws=500) > 0.0


def test_pick_rate_is_the_share_of_candidates_near_a_flag():
    cands = [{"x_mm": 0, "y_mm": 0}, {"x_mm": 10, "y_mm": 0}, {"x_mm": 20, "y_mm": 0}, {"x_mm": 30, "y_mm": 0}]
    assert h.pick_rate([{"x_mm": 1, "y_mm": 0}], cands, 3.0) == 0.25
    assert np.isnan(h.pick_rate([{"x_mm": 1, "y_mm": 0}], [], 3.0))


def test_item_score_candidate_nulls_precision_and_notes():
    m = np.ones((600, 600), bool)
    cand = np.zeros_like(m)
    cand[100:140, 100:140] = True
    cands = [{"x_mm": 8, "y_mm": 8}, {"x_mm": 30, "y_mm": 30}, {"x_mm": 40, "y_mm": 8}, {"x_mm": 8, "y_mm": 40}]
    flags = [{"x_mm": 8, "y_mm": 8, "strength": 2.0}, {"x_mm": 30, "y_mm": 30, "strength": 1.0}]
    pins = [dict(_pin(x=8.5, y=8), note_pin=1), dict(_pin(x=9, y=9), note_pin=1), dict(_pin(x=40, y=40), note_pin=3)]
    row = h.item_score(pins, flags, m, PX, 2.0, draws=300, cand_mask=cand, cand_points=cands)
    b = row["by_radius"]["3.0"]
    assert b["hit"] == 2 and b["chance_pick"] == 0.5
    assert b["flags_near_pin"] == 1 and b["precision"] == 0.5 and b["precision_pick"] == 0.25
    assert row["notes"] == {"1": {"pins": 2, "hit": {"3.0": 2, "2.0": 2, "5.0": 2}},
                            "3": {"pins": 1, "hit": {"3.0": 0, "2.0": 0, "5.0": 0}}}
    pn = h.pool_notes({"a": row}, 3.0, "chance_pick", boots=50)
    assert pn["notes"] == 2 and pn["hit_rate"] == 0.5 and pn["chance"] == 0.5 and pn["ci95"] is None
    pp = h.pool_precision({"a": row}, 3.0, boots=50)
    assert pp["precision"] == 0.5 and pp["chance"] == 0.25


def test_pool_notes_weighs_a_note_once_however_many_pins():
    def row(notes, null):
        return {"pins": sum(p for p, _ in notes), "by_radius": {"3.0": {"chance_pick": null}},
                "notes": {str(i): {"pins": p, "hit": {"3.0": k}} for i, (p, k) in enumerate(notes)}}
    rows = {"a": row([(28, 28)], 0.5), "b": row([(1, 0), (1, 0)], 0.2)}
    pn = h.pool_notes(rows, 3.0, "chance_pick", boots=200)
    # per pin this would read 28 / 30 = 0.93; per note it is 1 of 3
    assert pn["notes"] == 3 and pn["hit_rate"] == pytest.approx(1 / 3, abs=1e-4) and pn["notes_above_null"] == 1
    assert pn["chance"] == pytest.approx(0.3) and pn["ci95"] is not None


# ------------------------------------------------------------- the reader ----

def test_empty_from_art_alpha_then_frame_colour():
    rgb = np.full((20, 20, 3), 200, np.uint8)
    a = np.full((20, 20), 255, np.uint8)
    a[5:10, 5:10] = 0
    assert ifr.empty_from_art(rgb, a).sum() == 25
    assert ifr.empty_from_art(rgb, np.full((20, 20), 255, np.uint8)).all()   # opaque: frame colour
    rgb[8:12, 8:12] = (200, 0, 0)
    e = ifr.empty_from_art(rgb, None)
    assert not e[8:12, 8:12].any() and e.sum() == 400 - 16


def _ring_scene():
    """A 40 x 40 mm page; a red block 6..34 mm with four 6 x 6 mm counters.
    Counter A sewn white, B closed in red, C and D bare."""
    S = int(40 * PX)
    empty = np.ones((S, S), bool)
    thr = np.full((S, S), BARE, np.int16)
    kind = np.full((S, S), ifr.NO_KIND, np.uint8)
    b0, b1 = int(6 * PX), int(34 * PX)
    empty[b0:b1, b0:b1] = False
    thr[b0:b1, b0:b1] = RED
    kind[b0:b1, b0:b1] = FILL
    boxes = {}
    for name, (x, y) in {"A": (9, 9), "B": (25, 9), "C": (9, 25), "D": (25, 25)}.items():
        sl = (slice(int(y * PX), int((y + 6) * PX)), slice(int(x * PX), int((x + 6) * PX)))
        empty[sl] = True
        thr[sl] = BARE
        kind[sl] = ifr.NO_KIND
        boxes[name] = sl
    return empty, thr, kind, boxes


def test_cover_flags_the_sewn_counter_not_the_closed_or_bare_ones():
    empty, thr, kind, boxes = _ring_scene()
    thr[boxes["A"]] = WHITE
    kind[boxes["A"]] = FILL
    thr[boxes["B"]] = RED                       # closed up in the ring's own colour
    kind[boxes["B"]] = FILL
    flags, cands, cand, mem = ifr.read_spaces(empty, thr, kind)
    assert [(f["kind"], f["treatment"], f["group"]) for f in flags] == [("cover", "infill", "bare")]
    x, y = flags[0]["x_mm"], flags[0]["y_mm"]
    assert 9 - 2 <= x <= 15 - 2 and 9 - 2 <= y <= 15 - 2           # inside A, pins' frame (pad 2)
    assert flags[0]["strength"] == pytest.approx(31.4, abs=1.0)    # ~ (6 - 2 x 0.2)^2 mm2
    assert sorted(m["cover"] for m in mem) == ["bare", "bare", "bare", "closed", "infill"]
    # candidates: every judged space but the largest (the page); B, closed, is not one
    assert len(cands) == 3 and not cand[0, 0] and cand[boxes["A"]].any() and not cand[boxes["B"]].any()


def test_a_space_sewn_in_the_arts_own_empty_colour_is_matched_not_infill():
    """A white field on a white page (`C_outline_lineart_logo`, a dev item):
    the thread draws what the art shows. Alpha art has no empty colour."""
    empty, thr, kind, boxes = _ring_scene()
    thr[boxes["A"]] = WHITE
    rgb = [(204, 0, 0), (255, 255, 255)]
    flags, *_rest, mem = ifr.read_spaces(empty, thr, kind, class_rgb=rgb, empty_rgb=[250.0, 250.0, 250.0])
    assert flags == [] and "matched" in [m["cover"] for m in mem]
    flags, *_ = ifr.read_spaces(empty, thr, kind, class_rgb=rgb, empty_rgb=None)
    assert [f["treatment"] for f in flags] == ["infill"]
    flags, *_ = ifr.read_spaces(empty, thr, kind, class_rgb=rgb, empty_rgb=[235.0, 232.0, 223.0])
    assert [f["treatment"] for f in flags] == ["infill"]          # cream page, white thread: 44 apart


def test_a_design_with_every_space_bare_is_silent():
    empty, thr, kind, _ = _ring_scene()
    flags, cands, _cand, _mem = ifr.read_spaces(empty, thr, kind)
    assert flags == [] and len(cands) == 4


def test_rim_flags_the_one_outlined_counter():
    empty, thr, kind, boxes = _ring_scene()
    ys, xs = boxes["D"]
    w = int(ifr.THREAD_MM * PX)
    for sl in ((slice(ys.start - w // 2, ys.start + w // 2), xs), (slice(ys.stop - w // 2, ys.stop + w // 2), xs),
               (ys, slice(xs.start - w // 2, xs.start + w // 2)), (ys, slice(xs.stop - w // 2, xs.stop + w // 2))):
        kind[sl] = RUN
        thr[sl] = RED
    flags, *_ = ifr.read_spaces(empty, thr, kind)
    assert [(f["kind"], f["treatment"], f["group"]) for f in flags] == [("rim", "outlined", "plain")]
    assert 25 - 2 <= flags[0]["x_mm"] <= 31 - 2 and 25 - 2 <= flags[0]["y_mm"] <= 31 - 2
    # a filled counter is not an opening: its outline is not read
    thr[boxes["D"]] = WHITE
    flags, *_ = ifr.read_spaces(empty, thr, kind)
    assert [f["kind"] for f in flags] == ["cover"]


def test_specks_under_the_floor_are_not_spaces():
    empty, thr, kind, _ = _ring_scene()
    empty[int(20 * PX):int(20 * PX) + 4, int(20 * PX):int(20 * PX) + 4] = True     # 0.33 mm square
    _f, _c, _m, mem = ifr.read_spaces(empty, thr, kind)
    assert len(mem) == 5


# --------------------------------------------------------------- job helper ----

def test_split_item_and_job_paths():
    assert jobs.split_item("L_bridge_hat") == ("L", "bridge_hat")
    assert jobs.split_item("C_kanji_seal") == ("C", "kanji_seal")
    for bad in ("P_architecture", "kanji", "C_"):
        with pytest.raises(ValueError):
            jobs.split_item(bad)
    assert jobs.job_paths("L_bridge_hat", Path("run"), None, None) == (Path("run") / "bridge_hat.json", None)
    with pytest.raises(ValueError):
        jobs.job_paths("C_kanji_seal", None, Path("c"), None)


def test_worker_reads_the_same_constants_as_the_pure_helper():
    """The worker cannot import this lane, so it repeats `empty_from_art`:
    the constants it is handed and the logic it runs must stay the pure
    helper's."""
    assert "alpha < ALPHA_EMPTY" in ifr.WORKER and "<= BG_TOL" in ifr.WORKER
    assert "f[:2].reshape(-1, 3), f[-2:].reshape(-1, 3), f[:, :2].reshape(-1, 3), f[:, -2:].reshape(-1, 3)" \
        in ifr.WORKER
