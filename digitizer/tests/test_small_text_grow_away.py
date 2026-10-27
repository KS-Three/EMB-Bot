"""`cfg.extra["small_text_reset_grow_away"]` (W4-04, 2026-10-26, built OFF):
the re-set (`small_text_cap_letter_gap_mm`) widens each letter by the stroke
of the letters it actually grows, and grows a line AWAY from its nearer
neighbour.

W3-11 (`docs/reset-room-2026-10-25.md`, PR #1099) found the two faults only
work as a pair. The widening used the tagger's stroke tag, measured on other
polygons: on ProSeal and Drone the retraced letters are 0.67-0.91 of it, so
they sewed 0.70-0.81 mm against a 0.85 target. Fixed alone, the ProSeal
beanie's tagline went `no_room`: the bigger widening grew the halo past the
room between its bar and the design's edge. The professional grows the line
away from the neighbour under ~2 mm: the edge facing it moves at most
0.46 mm, and the rest of the growth goes the other way, past the design's
edge on ProSeal.

The synthetic scene is `tests/test_small_text.py`'s: tan 2 mm lettering on a
white raster, one solid polygon per glyph as the tracer hands them over,
here with a rule across the design 1.5 mm from the line (ProSeal's bar is
1.65-1.8 mm over its tagline) and the line standing on the design's other
edge. The scene's tag is set FAT (0.5 mm for a 0.31 mm retraced stroke), as
the stage-4 tracer's is on a coarse JPEG.
"""
from __future__ import annotations

import hashlib
import sys

import numpy as np
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, small_text
from digitizer_core.regions import Region
from digitizer_core.small_text import enlarge_small_text
from digitizer_core.textcluster import _stats_of_polygon
from tests.test_small_text import _glyphs, _scene, _tag
from tests.test_small_text_reset import KW

KEY = "small_text_reset_grow_away"
ON = {**KW, "reach_edges": True}        # the re-set as it ships (reach_edges ON since 2026-10-24)
#: the rule's gap to the line: under `GROW_AWAY_NEAR_MM`, like ProSeal's bar
RULE_GAP_MM = 1.5
#: the tagger's half-stroke, fat against the retraced letters' ~0.156
FAT_HALF_MM = 0.25

#: md5 of `_rule_scene("above")` re-set WITHOUT the flag -- regions and report
#: -- captured on main's engine (46949f78), before this flag existed, on
#: Windows. Linux CI reads 0f7d2332... for the same tree (both of #1113's
#: first runs, before main moved), so it is asserted where it was captured.
OFF_MD5 = "1dc31d545ed992da5ae2d5f57babae8b"


def _rule_scene(side: str, gap: float = RULE_GAP_MM, half: float = FAT_HALF_MM):
    """The 1895 line with a rule across the design `gap` mm `side` of it
    ("above" or "below"), the line standing on the design's OTHER edge: its
    ground ends where the letters do. -> (regions, p, art top, art bottom)."""
    regions, p = _scene()
    g = _glyphs(regions)
    bottom = max(r.polygon.bounds[3] for r in g)
    top = min(r.polygon.bounds[1] for r in g)
    base = next(r for r in regions if r.shape_id == "Sbase")
    if side == "above":
        base.polygon = box(-20, -10, 20, bottom)
        rule = box(-20, top - gap - 0.5, 20, top - gap)
    else:
        base.polygon = box(-20, top, 20, 10)
        rule = box(-20, bottom + gap, 20, bottom + gap + 0.5)
    regions.append(Region("Srule", rule, 2, "2", 20.0))
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"}, stroke_half_mm=half)
    return regions, p, top, bottom


def _md5(regions, rep) -> str:
    h = hashlib.md5()
    for r in regions:
        h.update(repr((r.shape_id, r.thread_index, r.polygon.wkb.hex(), sorted(r.meta.items()))).encode())
    h.update(repr(rep).encode())
    return h.hexdigest()


def _row(rep):
    return next(r for r in rep if r["cluster"] == "TCtest")


def _drawn(regions) -> float:
    """Median drawn stroke of the line, by the tag's own measure."""
    return float(np.median([2.0 * _stats_of_polygon(r.polygon).mean_mm for r in _glyphs(regions)]))


def _frame(regions):
    g = _glyphs(regions)
    return min(r.polygon.bounds[1] for r in g), max(r.polygon.bounds[3] for r in g)


def _rule_distance(regions) -> float:
    rule = next(r for r in regions if r.shape_id == "Srule")
    return min(r.polygon.distance(rule.polygon) for r in _glyphs(regions))


# --- OFF -------------------------------------------------------------------------

def test_off_by_default():
    assert KEY not in PipelineConfig().extra


def test_off_is_byte_identical_to_main():
    """Platform-safe: absent and False are the same bytes everywhere; the
    cross-commit pin is asserted where it was captured
    (`test_cut_every_jump`'s pattern). `test_the_flag_is_only_its_two_parts`
    is the in-process proof on every platform."""
    a, p, _t, _b = _rule_scene("above")
    rep_a = enlarge_small_text(a, p, **ON)
    b, p, _t, _b = _rule_scene("above")
    rep_b = enlarge_small_text(b, p, **ON, grow_away=False)
    assert _md5(a, rep_a) == _md5(b, rep_b)
    if sys.platform == "win32":
        assert _md5(a, rep_a) == OFF_MD5


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("grow-away code reached with the flag off")
    for name in ("_traced_stroke", "_near_side", "_grow_away"):
        monkeypatch.setattr(small_text, name, boom)
    regions, p, _t, _b = _rule_scene("above")
    assert "skipped" not in _row(enlarge_small_text(regions, p, **ON))


def test_the_flag_is_only_its_two_parts(monkeypatch):
    """Platform-safe, in process: ON with the traced stroke unmeasured and no
    near side read sews exactly OFF's regions. The flag's only effects are
    `_traced_stroke` and `_near_side` / `_grow_away`."""
    a, p, _t, _b = _rule_scene("above")
    enlarge_small_text(a, p, **ON)
    monkeypatch.setattr(small_text, "_traced_stroke", lambda _s: 0.0)
    monkeypatch.setattr(small_text, "_near_side", lambda _l: {"near": 0, "up": None, "down": None, "edge": 0.0})
    b, p, _t, _b = _rule_scene("above")
    enlarge_small_text(b, p, **ON, grow_away=True)
    assert _md5(a, []) == _md5(b, [])


def test_the_flag_needs_the_re_set():
    a, p, _t, _b = _rule_scene("above")
    rep_a = enlarge_small_text(a, p, cap_mm=3.7, min_stroke_mm=0.85)
    b, p, _t, _b = _rule_scene("above")
    rep_b = enlarge_small_text(b, p, cap_mm=3.7, min_stroke_mm=0.85, grow_away=True)
    assert _md5(a, rep_a) == _md5(b, rep_b)


def test_off_the_line_grows_toward_the_rule_on_a_stale_stroke():
    """What W3-11 measured on ProSeal: the line on the design's edge grows UP,
    into the room the rule leaves, and its letters land under the floor."""
    regions, p, top, bottom = _rule_scene("above")
    row = _row(enlarge_small_text(regions, p, **ON))
    assert "skipped" not in row and row["scale"] < 1.5, row
    t, b = _frame(regions)
    assert top - t > 0.5 and b - bottom < top - t, (t - top, b - bottom)
    assert _drawn(regions) < KW["min_stroke_mm"] - 0.05


# --- ON: the stroke ----------------------------------------------------------------

def test_on_widens_by_the_traced_stroke():
    regions, p, _t, _b = _rule_scene("above")
    row = _row(enlarge_small_text(regions, p, **ON, grow_away=True))
    tag, traced = row["stroke_mm"]
    assert tag == 2.0 * FAT_HALF_MM and 0.2 < traced < 0.8 * tag, row["stroke_mm"]
    # widened to the target from the letters' own stroke (the measure reads
    # round-ended letters a little wide; under it, the stale tag did)
    assert _drawn(regions) >= KW["min_stroke_mm"] - 0.03, _drawn(regions)
    for r in _glyphs(regions):
        assert abs(2.0 * r.meta["text_cluster_stroke_mm"] - (traced * min(row["scale"], row["width_scale"])
                                                              + 2.0 * row["widened_mm"])) < 2e-3


# --- ON: the placement --------------------------------------------------------------

def test_on_the_line_holds_the_edge_facing_the_rule_and_grows_away_from_it():
    off, p, _t, _b = _rule_scene("above")
    s_off = _row(enlarge_small_text(off, p, **ON))["scale"]
    regions, p, top, bottom = _rule_scene("above")
    row = _row(enlarge_small_text(regions, p, **ON, grow_away=True))
    ga = row["grow_away"]
    assert ga["near"] == -1 and abs(ga["up"] - RULE_GAP_MM) < 0.05 and ga["down"] is None, ga
    assert row["scale"] > s_off + 0.3, (row["scale"], s_off)
    t, b = _frame(regions)
    growth = (row["scale"] - 1.0) * row["cap_mm"]
    # the near edge stays where the art has it (the widening on top), the far
    # one takes the growth -- past the design's edge by MORE than the half
    # growth `reach_edges` alone allows
    assert top - t <= row["widened_mm"] + small_text.GROW_AWAY_NEAR_GIVE_MM + 1e-6, top - t
    assert b - bottom >= 0.8 * growth > 0.5 * growth, (b - bottom, growth)
    # and still clear of the rule by the halo, every glyph one valid polygon
    assert _rule_distance(regions) >= small_text.CLEAR_MM - 1e-6
    assert all(isinstance(r.polygon, Polygon) and r.polygon.is_valid for r in _glyphs(regions))


def test_on_a_rule_below_holds_the_baseline_and_grows_up():
    regions, p, top, bottom = _rule_scene("below")
    row = _row(enlarge_small_text(regions, p, **ON, grow_away=True))
    assert row["grow_away"]["near"] == 1 and "skipped" not in row, row
    t, b = _frame(regions)
    growth = (row["scale"] - 1.0) * row["cap_mm"]
    assert b - bottom <= row["widened_mm"] + small_text.GROW_AWAY_NEAR_GIVE_MM + 1e-6, b - bottom
    assert top - t >= 0.8 * growth, (top - t, growth)
    assert _rule_distance(regions) >= small_text.CLEAR_MM - 1e-6


def test_on_a_line_off_had_no_room_for_fits():
    """The pair: a widening the halo cannot fit beside the rule leaves OFF
    `no_room` (the beanie's case); grown away from the rule it fits."""
    off, p, _t, _b = _rule_scene("above", half=0.125)
    assert _row(enlarge_small_text(off, p, **ON)).get("skipped") == "no_room"
    regions, p, _t, _b = _rule_scene("above", half=0.125)
    row = _row(enlarge_small_text(regions, p, **ON, grow_away=True))
    assert "skipped" not in row and row["scale"] > small_text.MIN_SCALE, row


def test_on_with_no_near_neighbour_the_line_is_placed_as_before(monkeypatch):
    """Fremont's THE, 2.2 / 2.25 mm from its neighbours either side: no near
    side, so the placement is today's (only the stroke changes)."""
    seen = []
    real = small_text._place_line_reset
    monkeypatch.setattr(small_text, "_place_line_reset",
                        lambda *a, **k: (seen.append(k.get("near")), real(*a, **k))[1])
    regions, p, _t, _b = _rule_scene("above", gap=3.0)
    row = _row(enlarge_small_text(regions, p, **ON, grow_away=True))
    assert row["grow_away"]["near"] == 0 and seen == [None], (row, seen)


def test_on_a_line_that_cannot_hold_its_near_edge_is_placed_as_before(monkeypatch):
    """No scale holds the near edge (here: no move is offered at all), so
    the line takes today's placement, and its row says so."""
    regions, p, _t, _b = _rule_scene("above")
    monkeypatch.setattr(small_text, "_near_side", lambda _l: {"near": 0, "up": None, "down": None, "edge": 0.0})
    enlarge_small_text(regions, p, **ON, grow_away=True)
    want = _md5(regions, [])
    monkeypatch.undo()
    monkeypatch.setattr(small_text, "_grow_away", lambda _n, _r, room, _s: (room, []))
    regions, p, _t, _b = _rule_scene("above")
    row = _row(enlarge_small_text(regions, p, **ON, grow_away=True))
    assert row["grow_away"]["near"] == -1 and row["grow_away"]["held"] is False, row
    assert "skipped" not in row and _md5(regions, []) == want


# --- the pieces -----------------------------------------------------------------------

def _item(shapes, obstacles):
    from shapely.ops import unary_union
    hull = unary_union(shapes).convex_hull
    return {"shapes": shapes, "hull": hull, "obstacles": obstacles}


def test_near_side_reads_the_tighter_side_at_the_tightest_column():
    letter = box(0, 0, 0.5, 2.0)
    above, below = box(-5, -1.7, 5, -1.2), box(-5, 3.6, 5, 4.0)
    from shapely.ops import unary_union
    got = small_text._near_side([_item([letter], unary_union([above, below]))])
    assert got["near"] == -1 and abs(got["up"] - 1.2) < 1e-6 and abs(got["down"] - 1.6) < 1e-6
    assert got["edge"] == 0.0
    # a shape beside the line, in its band, is not above or below it
    got = small_text._near_side([_item([letter], box(1.0, -0.5, 2.0, 2.5))])
    assert got == {"near": 0, "up": None, "down": None, "edge": 2.0}
    # nothing under GROW_AWAY_NEAR_MM: no side
    far = unary_union([box(-5, -3.0, 5, -2.5), box(-5, 4.2, 5, 5.0)])
    assert small_text._near_side([_item([letter], far)])["near"] == 0
    # read on the ART: a neighbour line already grown to 1.2 mm away, drawn
    # 2.5 mm away (Fremont's THE under its grown date), names no side
    grown = {**_item([letter], box(-5, -1.7, 5, -1.2)), "art_obstacles": box(-5, -3.0, 5, -2.5)}
    assert small_text._near_side([grown])["near"] == 0


def test_grow_away_holds_the_near_edge_first_then_gives_toward_it():
    shifts = small_text._offsets(4.0)
    resets = [{"hull": box(0, -1.0, 4, 3.0), "widen": 0.2}]
    room, moves = small_text._grow_away({"near": -1, "edge": 0.0}, resets, box(-10, -10, 10, 3.0), shifts)
    assert moves[0] == (0, 1.0)                             # top back on the art's 0.0
    assert moves[1] == (0.25, 0.75)                         # then a step toward the rule
    assert moves[2] == (0.25, 1.25)                         # then a step away
    give = small_text.GROW_AWAY_NEAR_GIVE_MM
    assert max(c for c, d in moves if d < 1.0) == give       # toward the rule at most this
    assert max(d for _c, d in moves) == 1.0 + give            # and away: never the long slide
    assert room.bounds[3] >= 3.0 + 1.0 + 0.2                # the far edge gives the whole growth
    assert room.bounds[:3] == (-10.0, -10.0, 10.0)


def test_grow_away_also_tries_todays_grid():
    """A held edge off today's grid: today's moves are tried too, costed by
    how far they move the near edge (Drone's AND DRONE fits only 0.50 up)."""
    shifts = small_text._offsets(4.0)
    resets = [{"hull": box(0, -0.9, 4, 3.0), "widen": 0.2}]
    _room, moves = small_text._grow_away({"near": -1, "edge": 0.0}, resets, box(-10, -10, 10, 3.0), shifts)
    got = [(round(c, 6), round(d, 6)) for c, d in moves[:5]]
    assert got == [(0.0, 0.9), (0.1, 1.0), (0.15, 0.75), (0.25, 0.65), (0.25, 1.15)], got
    # mirrored: a neighbour below, the baseline held, toward it is DOWN
    resets = [{"hull": box(0, 0.0, 4, 3.1), "widen": 0.2}]
    room, moves = small_text._grow_away({"near": 1, "edge": 3.0}, resets, box(-10, 0.0, 10, 10), shifts)
    assert [round(d, 6) for _c, d in moves[:3]] == [-0.1, 0.0, -0.25]
    assert room.bounds[1] <= 0.0 - 0.1 - 0.2


# --- the wiring ------------------------------------------------------------------------

def test_the_key_reaches_small_text_through_the_pipeline(monkeypatch):
    """`cfg.extra["small_text_reset_grow_away"]` is read by the pipeline's one
    call to the growth: absent, the call carries no `grow_away` (today's
    call, word for word); set, `grow_away=True`."""
    from digitizer_core.pipeline import build_generation
    from tests.conftest import own_thread_only

    img = np.full((160, 260, 3), 255, np.uint8)
    img[30:130, 20:120] = (40, 40, 200)
    img[30:130, 140:240] = (30, 160, 60)
    calls = []
    real = small_text.enlarge_small_text
    monkeypatch.setattr(small_text, "enlarge_small_text", own_thread_only(
        lambda *a, **k: (calls.append(dict(k)), real(*a, **k))[1], real))
    cfg = dict(target_width_mm=60.0, max_colors=4)
    build_generation(img, PipelineConfig(**cfg))
    build_generation(img, PipelineConfig(**cfg, extra={KEY: True}))
    assert len(calls) == 2, calls
    assert "grow_away" not in calls[0]
    assert calls[1]["grow_away"] is True
    assert {k: v for k, v in calls[1].items() if k != "grow_away"} == calls[0]

