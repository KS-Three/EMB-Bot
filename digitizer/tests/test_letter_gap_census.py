"""`tools/letter_gap_census.py` and the letter reader it adds to
`tools/small_text_columns.py` (W3-07, 2026-10-25).

Synthetic glyphs are satin columns drawn as needle points straight into the
reader's own frame (mm, y down): two apart, two whose thread overlaps along
their height (FUSED), two that meet only at a corner (a TIP touch). The
attribution is checked on the same columns with a traced polygon each: a
trace too close, rails compensated into each other, and an end cross run
past the outline. One committed pro file (Becker's small hat, MARINE) is read
end to end so the real path is covered without a digitize.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import letter_gap_census as lgc  # noqa: E402
from tools import small_text_columns as stc  # noqa: E402

DIGITIZER = HERE.parent
BECKER_SMALL = DIGITIZER / "testdata" / "reference" / "becker_hat_small_beckers_logo_hat_2_a.dst"


def satin(x0, x1, y0, y1, pitch=0.4, ends=None):
    """A vertical satin column's needle points: crosses between rails x0 and
    x1 from y0 to y1. `ends` = (n, x): the last n crosses reach x instead of
    x1 (an end cross run past the outline)."""
    pts, y, k = [], y0, 0
    rows = []
    while y <= y1 + 1e-9:
        rows.append(y)
        y += pitch
    for j, y in enumerate(rows):
        right = ends[1] if ends and j >= len(rows) - ends[0] else x1
        pts += [(x0, y), (right, y)] if k % 2 == 0 else [(right, y), (x0, y)]
        k += 1
    return pts


def word(*columns, text):
    """Columns as one colour block (a jump between letters) read by the
    letter reader -> (blocks, word_letters result)."""
    block = []
    for c in columns:
        block += c + [None]
    blocks = [block]
    pcs = stc.pieces(blocks)
    return blocks, stc.word_letters(pcs, text)


# --- the reader --------------------------------------------------------------

def test_letters_apart_read_the_visible_gap():
    # needles 1.0 mm apart: 1.0 less the 0.4 mm thread is visible
    _b, r = word(satin(0, 1.5, 0, 6), satin(2.5, 4.0, 0, 6), text="HH")
    assert r["note"] is None and len(r["letters"]) == 2
    (p,) = r["pairs"]
    assert p["gap_mm"] == pytest.approx(0.6, abs=0.1)
    assert p["contact_mm"] == 0.0 and not p["fused"]


def test_letters_overlapping_along_their_height_are_fused():
    # needles 0.2 mm apart: the 0.4 mm threads overlap the whole height
    _b, r = word(satin(0, 1.5, 0, 6), satin(1.7, 3.2, 0, 6), text="HH")
    assert r["units"] == 1 and len(r["letters"]) == 2
    (p,) = r["pairs"]
    assert p["gap_mm"] == 0.0 and p["fused"]
    assert p["contact_mm"] > 5.0


def hsatin(x0, x1, y0, y1, pitch=0.4):
    """A horizontal satin arm: vertical crosses between y0 and y1."""
    pts, x, k = [], x0, 0
    while x <= x1 + 1e-9:
        pts += [(x, y0), (x, y1)] if k % 2 == 0 else [(x, y1), (x, y0)]
        x += pitch
        k += 1
    return pts


def test_an_arm_tip_into_the_neighbour_is_a_tip_touch_not_fused():
    # the second letter's 0.4 mm arm (0.8 mm of thread) reaches 0.1 mm short of
    # the first's rail: the threads overlap, which a 0.55 mm opening keeps and a
    # 1.0 mm opening parts (a 1 mm disk does not fit in the arm)
    _b, r = word(satin(0, 1.5, 0, 6), hsatin(1.6, 3.0, 2.8, 3.2) + satin(3.0, 4.5, 0, 6), text="HH")
    assert r["units"] == 1
    (p,) = r["pairs"]
    assert p["gap_mm"] == 0.0 and not p["fused"]
    assert 0.0 < p["contact_mm"] < 1.0


def test_a_word_space_is_flagged_and_letters_follow_the_text():
    _b, r = word(satin(0, 1.5, 0, 6), satin(2.5, 4.0, 0, 6), satin(8.0, 9.5, 0, 6), text="AB C")
    assert [l["glyph"] for l in r["letters"]] == ["A", "B", "C"]
    assert [p["space"] for p in r["pairs"]] == [False, True]


def test_more_pieces_than_letters_is_named_not_read():
    _b, r = word(satin(0, 1.5, 0, 6), satin(2.5, 4.0, 0, 6), satin(5.0, 6.5, 0, 6), text="AB")
    assert r["letters"] == [] and "pieces for 2 letters" in r["note"]


def test_share_gives_the_wide_piece_the_extra_letters():
    # H | OTE-joined | L: the joined piece gets O, T and E
    assert stc._share([7.0, 20.0, 6.0], list("HOTEL")) == [(0, 1), (1, 4), (4, 5)]
    # a narrow I joined to an N beside a wide W stays with the N
    assert stc._share([10.4, 9.0], list("WIN")) == [(0, 1), (1, 3)]
    assert stc._share([1.0, 1.0, 1.0], list("AB")) is None


def test_text_lines_groups_by_height_and_place():
    blocks = [satin(0, 1.5, 0, 6) + [None] + satin(2.5, 4.0, 0, 6) + [None]
              + satin(0, 1.5, 10, 16) + [None] + satin(0, 1.0, 20, 22)]
    lines = stc.text_lines(stc.pieces(blocks))
    assert [len(ln["pieces"]) for ln in lines] == [2, 1]      # the 2 mm piece is under min_h


def test_word_rows_count_touching_and_fused_pairs():
    _b, r = word(satin(0, 1.5, 0, 6), satin(1.7, 3.2, 0, 6), satin(4.2, 5.7, 0, 6), text="ABC")
    (row,) = lgc.word_rows("ABC", r)
    assert row["min_gap"] == 0.0 and row["touch"] == ["AB"] and row["fused"] == ["AB"]
    assert row["gap_med"] == pytest.approx(0.6, abs=0.1)


@pytest.mark.parametrize("share_a,step", [(0.5, 0.225), (1.0, 0.45)])
def test_hold_back_opens_a_fused_pair_to_the_candidate_gap(share_a, step):
    # needles 0.2 apart; 0.25 visible needs 0.65: a shortfall of 0.45, shared
    blocks, r = word(satin(0, 1.5, 0, 6), satin(1.7, 3.2, 0, 6), text="AB")
    a, b = r["letters"]
    nb, moved, big = lgc.hold_back(blocks, lambda q: lgc._in_mask(a, *q), lambda q: lgc._in_mask(b, *q), share_a)
    assert moved["a"] > 0 and (moved["b"] > 0) == (share_a < 1.0)
    assert big == pytest.approx(step, abs=0.03)
    again = stc.word_letters(stc.pieces(nb), "AB")
    (p,) = again["pairs"]
    assert p["gap_mm"] == pytest.approx(lgc.HOLD_GAP_MM, abs=0.08)


def test_shape_member_matches_the_files_own_grid():
    geo = {"offset": [-1.0, -2.0], "runs": [{"id": "A", "kind": "satin", "points": [[-1.0, -2.0], [0.5, 1.25]]},
                                            {"id": "B", "kind": "satin", "points": [[3.0, 3.0]]}]}
    in_a = lgc.shape_member({"A"}, geo)
    assert in_a((0.0, 0.0)) and in_a((1.5, 3.2)) and not in_a((4.0, 5.0))


def test_letters_knocked_out_of_their_own_backdrop_are_named_not_read():
    # MFab's white letters, unsewn inside a black keyline: what is left of the
    # line is backdrop thread around holes, so the row says why it is not read
    # (the reader's frame starts at 0, as `read_blocks` leaves every file)
    frame = hsatin(1, 16, 1, 2) + [None] + hsatin(1, 16, 12, 13) + [None] \
        + satin(1, 2, 1, 13) + [None] + satin(15, 16, 1, 13)
    letters = satin(4, 5.5, 4, 10) + [None] + satin(6.5, 8.0, 4, 10)
    spec = {"lines": [("AB", 0.5, None)]}
    (same,) = lgc.read_side([frame + [None] + letters], spec)
    assert same["read"]["letters"] == [] and "knocked out" in same["read"]["note"]
    (apart,) = lgc.read_side([frame, letters], spec)        # the letters in a thread of their own
    assert apart["read"]["note"] is None and len(apart["read"]["letters"]) == 2


# --- attribution ---------------------------------------------------------------

def _geo(cols):
    """A plan of letters: (id, polygon box, needle points) -> geometry.json's
    shape, in the reader's frame (offset 0)."""
    from shapely.geometry import box
    return {"offset": [0.0, 0.0],
            "regions": [{"id": i, "wkt": box(*bx).wkt, "meta": {}} for i, bx, _p in cols],
            "planned": [],
            "runs": [{"id": i, "kind": "satin", "role": "", "block": 0, "points": [list(q) for q in pts]}
                     for i, _bx, pts in cols]}


def _attribute(cols, text="AB"):
    from shapely import wkt
    geo = _geo(cols)
    _b, r = word(*[pts for _i, _bx, pts in cols], text=text)
    (p,) = r["pairs"]
    assert p["gap_mm"] == 0.0, "the synthetic pair must touch"
    regions = {g["id"]: wkt.loads(g["wkt"]) for g in geo["regions"]}
    a, b = r["letters"]
    return lgc.attribute(a, b, geo, regions, {})


def test_attribute_trace_when_the_polygons_nearly_touch():
    # outlines 0.3 mm apart, needles on them: the thread touches whatever is sewn
    att = _attribute([("A", (0, 0, 1.5, 6), satin(0, 1.5, 0, 6)),
                      ("B", (1.8, 0, 3.3, 6), satin(1.8, 3.3, 0, 6))])
    assert att["cause"] == "trace" and att["d4"] == pytest.approx(0.3, abs=0.01)


def test_attribute_pull_comp_when_the_rails_close_it():
    # outlines 0.6 mm apart, every rail 0.15 mm outside its outline
    att = _attribute([("A", (0, 0, 1.5, 6), satin(-0.15, 1.65, 0, 6)),
                      ("B", (2.1, 0, 3.6, 6), satin(1.95, 3.75, 0, 6))])
    assert att["cause"] == "pull comp"
    assert att["comp_a"] == pytest.approx(0.15, abs=0.02) and att["comp_b"] == pytest.approx(0.15, abs=0.02)


def test_attribute_construction_when_an_end_cross_runs_past_the_outline():
    # outlines 1.0 mm apart, rails 0.1 outside; A's last two crosses reach 0.7 past
    att = _attribute([("A", (0, 0, 1.5, 6), satin(-0.1, 1.6, 0, 6, ends=(2, 2.2))),
                      ("B", (2.5, 0, 4.0, 6), satin(2.4, 4.1, 0, 6))])
    assert att["cause"] == "construction"
    assert att["over_a"] == pytest.approx(0.7, abs=0.02) and att["where_a"] == "end"
    assert att["excess_a"] > att["excess_b"]


# --- a committed pro file, end to end ----------------------------------------------

@pytest.mark.skipif(not BECKER_SMALL.is_file(), reason="reference DST not in this checkout")
def test_becker_small_hat_marine_reads_six_letters_apart():
    rows = lgc.read_side(stc.read_blocks(BECKER_SMALL), lgc.WORDS["becker_hat_small"])
    (line,) = rows
    (w,) = line["words"]
    assert w["word"] == "MARINE" and w["note"] is None
    assert w["touch"] == [] and len(w["gaps"]) == 5
    assert 12.5 < w["cap_mm"] < 14.0
    assert w["min_gap"] == pytest.approx(0.75, abs=0.1)
