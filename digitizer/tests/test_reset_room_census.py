"""`tools/reset_room_census.py` -- how the pro makes room for a re-set line.

Synthetic shifted lines: a row of satin "letters" with a bar above, drawn as
needle runs, then the same line moved / grown / spread and the bar re-laid,
and the census's readers asked what moved. No pro file, no art, no digitize:
everything here runs anywhere in well under a second each.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import reset_room_census as rr  # noqa: E402

PITCH = 0.3


def satin_box(x0, y0, x1, y1, block, vertical=True):
    """A satin column filling a box: crosses along x, stations every PITCH
    down y (or the transpose) -- a letter stem, or a bar."""
    pts = []
    a, b = (y0, y1) if vertical else (x0, x1)
    for k, v in enumerate(np.linspace(a, b, max(2, int(round((b - a) / PITCH)) + 1))):
        v = float(v)
        ends = [(x0, v), (x1, v)] if vertical else [(v, y0), (v, y1)]
        pts += ends if k % 2 == 0 else ends[::-1]
    return {"pts": pts, "block": block}


def letters(x0, top, h, n=5, w=1.0, gap=0.6, block=1):
    """`n` letters of stem width `w`, cap line `top`, height `h`."""
    return [satin_box(x0 + i * (w + gap), top, x0 + i * (w + gap) + w, top + h, block) for i in range(n)]


def bar(x0, x1, y0, y1, block=2):
    return satin_box(x0, y0, x1, y1, block, vertical=False)


def poly_box(x0, y0, x1, y1):
    from shapely.geometry import box
    return {"wkt": box(x0, y0, x1, y1).wkt, "thread": 0, "cluster": None}


# --- geometry ----------------------------------------------------------------

def test_line_frame_reads_median_cap_and_baseline_not_an_overshoot():
    boxes = [(0, 1.0, 1, 4.0), (1.5, 1.0, 2.5, 4.0), (3, 0.8, 4, 4.2), (4.5, 1.0, 5.5, 4.0)]  # an O overshoots
    assert rr.line_frame(boxes) == (0, 1.0, 5.5, 4.0)


def test_move_signs_y_down_and_scales():
    art = (0.0, 10.0, 20.0, 12.0)
    sewn = (-1.0, 9.5, 21.0, 13.0)          # grown both ways, more downward
    m = rr.move(art, sewn)
    assert (m["dy_top"], m["dy_bottom"], m["dy"], m["dx"]) == (-0.5, 1.0, 0.25, 0.0)
    assert m["h_scale"] == 1.75 and m["w_scale"] == 1.1


def test_gaps_per_column_min_and_median():
    line = np.zeros((40, 10), bool)
    other = np.zeros((40, 10), bool)
    line[20:25, :] = True
    other[10, :5] = True           # 9 px clear above on the left half
    other[14, 5:] = True           # 5 px clear above on the right half
    g = rr.gaps(line, other, ppm=10.0)
    assert g["up_min"] == 0.5 and g["up_cols"] == 10
    assert g["down_min"] is None


# --- the art -----------------------------------------------------------------

def art_scene(line_top=10.0, cap=2.0, bar_y=(6.5, 7.5)):
    shapes = [poly_box(i * 2.0, line_top, i * 2.0 + 1.0, line_top + cap) for i in range(5)]
    shapes.append(poly_box(-2.0, bar_y[0], 11.0, bar_y[1]))           # a bar above
    shapes.append(poly_box(-50, -50, 50, 50))                          # the ground: never a neighbour
    return shapes


def test_art_line_and_its_bar_above():
    art = art_scene()
    idx, fr, h = rr.art_line(art, (-0.5, 9.5, 9.5, 12.5))
    assert idx == [0, 1, 2, 3, 4] and fr == (0.0, 10.0, 9.0, 12.0) and h == 2.0
    nb = rr.art_neighbours(art, idx, fr, h)
    assert [(n["role"], n["gap"], n["bar"]) for n in nb] == [("above", 2.5, True)]


def test_art_room_up_is_the_gap_to_the_bar():
    art = art_scene()
    idx, fr, h = rr.art_line(art, (-0.5, 9.5, 9.5, 12.5))
    nb = rr.art_neighbours(art, idx, fr, h)
    win = rr.Window((-4, 3, 13, 15))
    r = rr.room(win, win.polys([art[i]["_poly"] for i in idx]), nb, [win.polys([art[n["i"]]["_poly"]]) for n in nb])
    assert r["up_min"] == pytest.approx(2.5, abs=0.1)
    assert "down_min" not in r


# --- a machine file ----------------------------------------------------------

def scene_runs(top=10.0, h=2.0, x0=0.0, w=1.0, gap=1.0, bar_y=(6.5, 7.5), bar_x=(-2.0, 11.0)):
    return letters(x0, top, h, w=w, gap=gap) + [bar(bar_x[0], bar_x[1], *bar_y)]


def read(runs, art, box=(-0.5, 9.5, 9.5, 12.5), win_box=(-6, 2, 16, 20)):
    idx, fr, h = rr.art_line(art, box)
    nb = rr.art_neighbours(art, idx, fr, h)
    side = rr.read_side(runs, rr.Window(win_box), rr.search_box(box, h), h,
                        lambda b: b, lambda b: b, fr, nb)
    return side, nb


def test_a_line_sewn_where_the_art_draws_it_has_not_moved():
    side, _nb = read(scene_runs(), art_scene())
    m = side["move"]
    assert abs(m["dy"]) <= 0.1 and abs(m["dx"]) <= 0.1
    assert m["h_scale"] == pytest.approx(1.0, abs=0.05)


def test_a_line_moved_down_and_grown_reads_its_move():
    # the pro's EST 1895: down 2 mm into free space, and 1.5x taller
    side, _nb = read(scene_runs(top=11.5, h=3.0), art_scene())
    m = side["move"]
    assert m["dy_top"] == pytest.approx(1.5, abs=0.1)
    assert m["dy_bottom"] == pytest.approx(2.5, abs=0.1)
    assert m["h_scale"] == pytest.approx(1.5, abs=0.06)


def test_a_line_grown_down_keeps_its_room_to_the_bar():
    # the pro's ProSeal tagline: cap line kept, baseline lowered
    side, nb = read(scene_runs(top=10.0, h=3.0), art_scene())
    assert side["move"]["dy_top"] == pytest.approx(0.0, abs=0.1)
    assert side["move"]["dy_bottom"] == pytest.approx(1.0, abs=0.1)
    assert side["room"]["up_min"] == pytest.approx(2.5 - 0.3, abs=0.15)    # thread edge to thread edge


def test_a_line_grown_up_eats_the_room_to_the_bar():
    # ours: baseline kept, the growth goes up into the bar's clearance
    side, _nb = read(scene_runs(top=9.0, h=3.0), art_scene())
    assert side["move"]["dy_bottom"] == pytest.approx(0.0, abs=0.1)
    assert side["room"]["up_min"] == pytest.approx(1.5 - 0.3, abs=0.15)


def test_a_re_laid_bar_is_matched_and_its_move_read():
    # the bar moved up 0.6 mm and made 2 mm longer; it is sewn joined to a
    # frame in its own block, so only its clip can find it
    runs = scene_runs(bar_y=(5.9, 6.9), bar_x=(-3.0, 12.0))
    runs.append(satin_box(12.0, 4.0, 12.6, 16.0, 2))         # a frame, same block, touching the bar's end
    side, nb = read(runs, art_scene())
    m = side["neighbours"][0]
    assert nb[0]["bar"] and m is not None
    assert m["dy"] == pytest.approx(-0.6, abs=0.1)
    assert m["dw"] >= 1.0


def test_a_neighbour_the_file_dropped_is_not_found():
    runs = letters(0.0, 10.0, 2.0, gap=1.0)                  # no bar at all
    side, nb = read(runs, art_scene())
    assert nb and side["neighbours"][0] is None
    assert "up_min" not in side["room"]


def test_a_spread_line_reads_wider_not_moved():
    # the pro's beanie tagline: same letters spread to the bar's width
    side, _nb = read(letters(-0.5, 10.0, 2.0, gap=1.25), art_scene())
    m = side["move"]
    assert m["w_scale"] == pytest.approx(1.1, abs=0.03)
    assert abs(m["dx"]) <= 0.1 and abs(m["dy"]) <= 0.1


# --- the line reader ---------------------------------------------------------

def test_a_line_moved_past_the_census_reach_is_still_read():
    # the floor census reads a letter only within max(1.5, cap) of the art
    # line's centre: a line the pro moved ~2 caps down reads DROPPED there
    from tools import small_text_floor_census as stf
    runs = letters(0.0, 13.0, 3.0, gap=1.0)                # art line at 10-12, sewn 13-16
    box = (-0.5, 9.5, 9.5, 12.5)
    sbox = rr.search_box(box, 2.0)
    assert stf.read_element(runs, sbox, 2.0, 11.0)["verdict"] == "DROPPED"
    got = rr.sewn_line(runs, sbox, (0.0, 10.0, 9.0, 12.0), 2.0)
    assert got is not None and got["frame"][1] == pytest.approx(13.0, abs=0.1)


def test_the_reach_default_is_the_census_own():
    from tools import small_text_floor_census as stf
    runs = letters(0.0, 10.0, 2.0, gap=1.0)
    box = (-3.0, 7.0, 12.0, 15.0)
    a = stf.read_element(runs, box, 2.0, 11.0)
    b = stf.read_element(runs, box, 2.0, 11.0, reach=None)
    assert a == b and a["verdict"] != "DROPPED"


def test_letters_joined_by_travel_to_a_dash_part_in_the_opened_read():
    # Drone's E sewn on into the dash beside it: the plain read sees one
    # piece running out of the search box, the opened read parts them
    runs = letters(0.0, 10.0, 2.0, gap=1.0)
    runs[-1]["pts"] = runs[-1]["pts"] + [(9.0, 11.0), (11.0, 11.0), (13.0, 11.0), (15.0, 11.0), (17.0, 11.0),
                                         (19.0, 11.0), (21.0, 11.0)]   # run stitches, 2 mm each
    got = rr.sewn_line(runs, rr.search_box((-0.5, 9.5, 9.5, 12.5), 2.0), (0.0, 10.0, 9.0, 12.0), 2.0)
    assert got is not None and got["opened"]
    assert got["frame"][2] == pytest.approx(9.0, abs=0.2)     # a join leaves a stub this long


def test_a_rope_of_strewn_twists_is_not_a_row_of_type():
    twists = [satin_box(x, 10.6, x + 0.8, 11.4, 1) for x in (-8.0, 0.0, 8.0, 16.0)]
    got = rr.sewn_line(twists, rr.search_box((-0.5, 9.5, 9.5, 12.5), 2.0), (0.0, 10.0, 9.0, 12.0), 2.0)
    assert got is None


def test_the_line_beats_the_next_line_down():
    # THE above the first letters of a longer word: the word is nearer the
    # search box's foot but further from the art line
    runs = letters(0.0, 10.0, 2.0, n=3, gap=1.0) + letters(0.5, 14.5, 2.4, n=2, gap=1.2, block=3)
    got = rr.sewn_line(runs, rr.search_box((-0.5, 9.5, 5.5, 12.5), 2.0), (0.0, 10.0, 5.0, 12.0), 2.0)
    assert got["frame"][1] == pytest.approx(10.0, abs=0.1)


# --- the carry ---------------------------------------------------------------

def test_to_ours_inverts_to_pro():
    from tools.pro_parity.pairframe import Reg
    reg = Reg(scale=0.96, flip_y=False, dx=1.5, dy=-2.0, iou=1.0)
    b = (-10.0, 3.0, 12.0, 7.5)
    back = rr.to_ours(rr.to_pro(b, reg), reg)
    assert back == pytest.approx(b)
