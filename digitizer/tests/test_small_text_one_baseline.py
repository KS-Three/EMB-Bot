"""`cfg.small_text_reset_one_baseline` (built OFF 2026-11-13 as an extra, ON
since 2026-11-14 by Kent's flip, "Flip both ON"): the
height classes of a lowercase line are re-set as ONE line, on one baseline.

Kent graded +Jakarta and Bukit Asam Bad on 2026-11-12 ("the letters jumped in
elevation and are not inline with the rest of the text"). The tagger keeps
one line at one size (`textcluster.LETTER_HEIGHT_RATIO`), so a lowercase line
is two clusters: its x-height letters and its ascender/descender letters.
The re-set grouped lines on the same 0.8, grew the two as two lines, each
the other's obstacle, and slid them apart: Jakarta's tagline sewed as two
rows 4.7 mm apart, Bukit Asam's e-o-n 2.53 mm above b-y-d.

The invariant pinned here, on a synthetic line that mixes the three classes
("beyond coal": b d l ascend, y descends, e o n c o a sit on the x-height):
after the re-set every letter of the line sits on the line's baseline, in
the art's order, at one scale, its letters one sewn gap apart inside a word.
"""
from __future__ import annotations

import hashlib

import numpy as np

from digitizer_core.small_text import enlarge_small_text
from tests.test_small_text import _glyphs, _scene, _tag
from tests.test_small_text_reset import KW

#: the re-set as it ships (reach edges, bay mouths, grow away: all ON)
SHIPS = {**KW, "reach_edges": True, "bay_mouth": True, "grow_away": True}
WORD = "beyond coal"
#: Hershey simplex at the scene's size: b e y o n d | c o a l
DESCENDER = "Sg2"          # the y
SPACE_AFTER = "Sg5"        # the d, before the word space


def _line(word: str = WORD):
    """The scene's tan line, tagged the way the letter door tags it: the
    letters under 0.8 of the tallest one cluster (`TCxh`), the rest another
    (`TCasc`). -> (regions, p, {id: art bounds}, x-height ids)."""
    regions, p = _scene(text_at=((180, 262),), words=(word,))
    g = _glyphs(regions)
    hs = {r.shape_id: r.polygon.bounds[3] - r.polygon.bounds[1] for r in g}
    tallest = max(hs.values())
    short = {sid for sid, h in hs.items() if h < 0.8 * tallest}
    _tag(regions, short, cid="TCxh")
    _tag(regions, set(hs) - short, cid="TCasc")
    return regions, p, {r.shape_id: r.polygon.bounds for r in g}, short


def _md5(regions, rep) -> str:
    h = hashlib.md5()
    for r in regions:
        h.update(repr((r.shape_id, r.thread_index, r.polygon.wkb.hex(), sorted(r.meta.items(), key=repr))).encode())
    h.update(repr(rep).encode())
    return h.hexdigest()


def _bottoms(regions, skip=(DESCENDER,)):
    return [r.polygon.bounds[3] for r in _glyphs(regions) if r.shape_id not in skip]


def test_the_scene_is_two_height_classes_the_way_the_tagger_splits_a_lowercase_line():
    _regions, _p, art, short = _line()
    assert len(art) == 10 and len(short) == 6, (len(art), sorted(short))
    hs = {sid: b[3] - b[1] for sid, b in art.items()}
    assert max(hs[s] for s in short) < 0.8 * max(hs.values()) <= min(hs[s] for s in set(art) - short)
    # one baseline in the art, the descender below it
    bottoms = [b[3] for sid, b in art.items() if sid != DESCENDER]
    assert max(bottoms) - min(bottoms) < 0.06
    assert art[DESCENDER][3] > max(bottoms) + 0.3


def test_off_the_two_classes_are_grown_as_two_lines_and_leave_their_baseline():
    """The fault, pinned so a fix elsewhere is noticed: OFF, each class is
    its own line and the two land millimetres apart, out of the art's order."""
    regions, p, art, _short = _line()
    enlarge_small_text(regions, p, **SHIPS)
    bottoms = _bottoms(regions)
    assert max(bottoms) - min(bottoms) > 1.0, bottoms
    order = [r.shape_id for r in sorted(_glyphs(regions), key=lambda r: r.polygon.bounds[0])]
    assert order != sorted(art, key=lambda s: art[s][0])


def test_on_every_letter_sits_on_one_baseline_in_the_arts_order_at_one_scale():
    regions, p, art, _short = _line()
    rep = enlarge_small_text(regions, p, **SHIPS, one_baseline=True)
    rows = {r["cluster"]: r for r in rep}
    assert rows["TCxh"].get("merged_into") == "TCasc" or rows["TCasc"].get("merged_into") == "TCxh", rows
    row = next(r for r in rep if "one_baseline" in r)
    assert "skipped" not in row and row["letters"] == 10, row
    s, widen = row["scale"], row["widened_mm"]
    # one baseline: every letter's foot stands off the line's baseline by its
    # own art offset grown by the line's one scale -- the descender's depth,
    # and the 0.04 mm Hershey's n and l sit above the others -- to 0.03 mm
    base = float(np.median(_bottoms(regions)))
    base_art = float(np.median([b[3] for sid, b in art.items() if sid != DESCENDER]))
    for r in _glyphs(regions):
        off = r.polygon.bounds[3] - base
        off_art = art[r.shape_id][3] - base_art
        assert abs(off - s * off_art) < 0.03, (r.shape_id, off, off_art, s)
    bottoms = _bottoms(regions)
    assert max(bottoms) - min(bottoms) < 0.1, bottoms
    # one scale: every letter's height, less the widening, over its art height
    for r in _glyphs(regions):
        b, a = r.polygon.bounds, art[r.shape_id]
        assert abs(((b[3] - b[1]) - 2 * widen) / (a[3] - a[1]) - s) < 0.08, (r.shape_id, b, a)
    # the art's order, left to right
    now = [r.shape_id for r in sorted(_glyphs(regions), key=lambda r: r.polygon.bounds[0])]
    assert now == sorted(art, key=lambda sid: art[sid][0])


def test_on_letters_of_a_word_are_one_gap_apart_and_the_word_space_stays():
    regions, p, art, _short = _line()
    enlarge_small_text(regions, p, **SHIPS, one_baseline=True)
    g = sorted(_glyphs(regions), key=lambda r: art[r.shape_id][0])
    gaps = {a.shape_id: a.polygon.distance(b.polygon) for a, b in zip(g, g[1:])}
    space = gaps.pop(SPACE_AFTER)
    assert max(gaps.values()) - min(gaps.values()) < 0.06, gaps
    # the space between words is the art's, kept as drawn (`_reset_word`)
    d, c = art[SPACE_AFTER], art["Sg6"]
    assert space >= c[0] - d[2] - 0.01 and space > max(gaps.values()) + 0.15, (space, gaps)


def test_a_class_beside_a_line_already_tall_enough_is_left_as_drawn():
    """Bukit Asam's b-y-d were tall enough and stayed; its e-o-n were grown
    alone and slid 2.53 mm up out of their word. ON, half a line is never
    grown: the short class is left exactly as drawn."""
    regions, p, art, short = _line()
    tall_cap = float(np.median([b[3] - b[1] for sid, b in art.items() if sid not in short]))
    cap = tall_cap / 0.95                  # the tall class clears 0.9 x cap, the short one does not
    off = enlarge_small_text(regions, p, **{**SHIPS, "cap_mm": cap})
    rows = {r["cluster"]: r for r in off}
    # OFF the short class is weighed for growth on its own (here it finds no
    # room within a cap's move; Bukit Asam's, asked 4 mm, slid 2.53 mm up)
    assert rows["TCasc"]["skipped"] == "tall_enough" and rows["TCxh"].get("skipped") != "tall_enough", rows

    regions, p, _art, _short = _line()
    before = _md5(regions, None)
    rep = enlarge_small_text(regions, p, **{**SHIPS, "cap_mm": cap}, one_baseline=True)
    rows = {r["cluster"]: r for r in rep}
    assert rows["TCasc"]["skipped"] == "tall_enough"
    assert rows["TCxh"]["skipped"] == "tall_enough_line"
    assert _md5(regions, None) == before, "nothing moved"


def test_false_is_the_call_without_the_flag_byte_for_byte():
    regions, p, _art, _short = _line()
    rep = enlarge_small_text(regions, p, **SHIPS)
    a = _md5(regions, rep)
    regions, p, _art, _short = _line()
    rep = enlarge_small_text(regions, p, **SHIPS, one_baseline=False)
    assert _md5(regions, rep) == a


def test_one_height_class_is_left_to_the_line_test_it_had():
    """Two clusters the line test already puts on one line (one size, one
    middle: Fremont's EST and 1895) are not merged: their re-set is today's."""
    from digitizer_core.small_text import _one_line, _same_line_today
    a = {"thread": 7, "cap": 2.0, "band": (0.0, 2.0), "x": (0.0, 5.0), "mid": 1.0}
    b = {"thread": 7, "cap": 2.0, "band": (0.0, 2.0), "x": (6.0, 9.0), "mid": 1.0}
    assert _same_line_today(a, b) and _one_line(a, b)
    # an x-height class beside its ascenders: the line test refuses, one line accepts
    xh = {"thread": 7, "cap": 1.3, "band": (0.45, 1.75), "x": (0.0, 9.0), "mid": 1.1}
    asc = {"thread": 7, "cap": 1.75, "band": (0.0, 1.75), "x": (0.5, 8.0), "mid": 0.9}
    assert not _same_line_today(xh, asc) and _one_line(xh, asc)
    # another ink, a row below, or a word far off: not one line
    assert not _one_line(xh, {**asc, "thread": 8})
    assert not _one_line(xh, {**asc, "band": (2.5, 4.25)})
    assert not _one_line(xh, {**asc, "x": (20.0, 25.0)})


def test_on_an_i_keeps_its_dot_and_a_thin_t_is_a_letter_not_a_bar():
    """Jakarta's i-dots stood over the hull's chord between the short and the
    tall letters, so the line read its own dots as a neighbour 0.375 mm above
    and held its top against them; its first t (thin, ascender-tall) read as
    a "|" bar and was left hanging below the grown line. ON the dot rides
    with its i, and the t is laid with its word."""
    regions, p = _scene(text_at=((180, 262),), words=("a city by the",))
    g = {r.shape_id: r for r in _glyphs(regions)}
    hs = {sid: r.polygon.bounds[3] - r.polygon.bounds[1] for sid, r in g.items()}
    dot = min(hs, key=hs.get)                       # the i's dot, untagged
    letters = {sid for sid in hs if sid != dot}
    short = {sid for sid in letters if hs[sid] < 0.8 * max(hs.values())}
    # a c i e short; the first t (Sg4) tagged with them, where `_core` drops
    # it at 1.33 x their height, as the tagger's band adoption put Jakarta's
    _tag(regions, short | {"Sg4"}, cid="TCxh")
    _tag(regions, letters - short - {"Sg4"}, cid="TCasc")
    stem = "Sg2"
    art_gap = g[stem].polygon.bounds[1] - g[dot].polygon.bounds[3]
    rep = enlarge_small_text(regions, p, **SHIPS, one_baseline=True)
    row = next(r for r in rep if "one_baseline" in r)
    assert "skipped" not in row and row["grow_away"]["near"] == 0, row
    assert row["one_baseline_back"] == 1, row       # the t came back to its line
    d, i = g[dot].polygon.bounds, g[stem].polygon.bounds
    assert i[0] - 0.05 <= (d[0] + d[2]) / 2.0 <= i[2] + 0.05, (d, i)
    assert 0.0 < i[1] - d[3] <= row["scale"] * art_gap + 1e-6, (d, i, art_gap)
    t = g["Sg4"].polygon.bounds
    bottoms = [r.polygon.bounds[3] for sid, r in g.items() if sid in short]
    assert abs(t[3] - max(bottoms)) < 0.1, (t, bottoms)
    assert g["Sg4"].meta.get("small_text_enlarged") and not g["Sg4"].meta.get("small_text_bar_moved_mm")
