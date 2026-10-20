"""Lowercase vs capitals under the Column lane, and the shoulder cut.

MASTER_SCOPE area 1 said of the stitch-angle rule: "Capitals measured,
lowercase not." `tools/lowercase_angle.py` is that measurement, on a
synthetic word set in one font at one size (`testdata/synthetic/
lowercase_aileron.png`, Pillow's bundled CC0 Aileron). Its finding: the
Column lane lays every capital station cross within 45 deg of its column's
own perpendicular (0.0% past it, 80 and 120 mm) but folds lowercase
crosses through a SHOULDER -- the u's bowl into its right stem, the b's and
g's bowl into the stem, the m's arch off its first stem -- because the
junction rules leave a concave corner uncut when its far side is smooth.
`cfg.lettering_columns_fold_cuts` (ON since 2026-10-20) gives such a piece the
second look `_refine` gives an over-long one -- and, since the follow-up
(claude/fold-cuts-junctions), refuses a cut that leaves a stub (the u's
spur), opens a ring with a PAIR of cuts (the a's bowl, which one cut
cannot open), and ranks what is left so a stem sews whole.

The glyph tests read the pipeline's own traced polygons at 120 and 80 mm
(`testdata/synthetic/lowercase_aileron_letters_{120,80}.json`), so they
need no digitize; one module fixture digitizes the word at 80 mm both ways.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, digitize, outline_cut
from digitizer_core.columns import lettering_columns_shape
from tools import lowercase_angle as la
from tests.conftest import own_thread_only

SHOULDERS = "ubgma"         # glyphs that fold OFF and come apart ON (120 mm)


def _load(path) -> dict[str, Polygon]:
    data = json.loads(path.read_text(encoding="utf-8"))["letters"]
    return {ch: Polygon(v["exterior"], v["holes"]) for ch, v in data.items()}


@pytest.fixture(scope="module")
def glyphs() -> dict[str, Polygon]:
    """Each glyph as the pipeline traced it at 120 mm (`--dump-letters`)."""
    return _load(la.LETTERS)


@pytest.fixture(scope="module")
def glyphs80() -> dict[str, Polygon]:
    """The same at 80 mm (`--dump-letters 80`)."""
    return _load(la.LETTERS_80)


@pytest.fixture(scope="module")
def glyphs50() -> dict[str, Polygon]:
    """The same at 50 mm with `small_text_true_size` OFF (`--dump-letters 50`):
    the pre-flip engine, where the word's 3.1 mm capitals reach the lane."""
    return _load(la.LETTERS_50)


@pytest.fixture(scope="module")
def shoulders_on(glyphs):
    return {ch: outline_cut.letter_columns(glyphs[ch], fold_cuts=True) for ch in SHOULDERS}


def _folded(cut) -> int:
    return sum(outline_cut._folded(c) for c in cut.columns)


# --- the instrument's own arithmetic ------------------------------------------

def test_target_lean_is_the_rule_fade():
    t = la.target_lean(np.array([0.0, 20.0, 30.0, 60.0, 90.0, 180.0]), 0.0)
    assert np.allclose(t, [0.0, 20.0, 30.0, 15.0, 0.0, 0.0])


def test_parts_split_by_advance_against_the_line():
    assert la.part_of(90.0) == "stem" and la.part_of(-85.0) == "stem"
    assert la.part_of(0.0) == "bar" and la.part_of(170.0) == "bar"
    assert la.part_of(45.0) == "slant"


def test_folded_reads_a_straight_column_as_clean():
    col = outline_cut.letter_columns(Polygon([(0, 0), (1.2, 0), (1.2, 10), (0, 10)])).columns[0]
    assert outline_cut._folded(col) == 0


# --- the finding: lowercase shoulders fold, capitals do not --------------------

@pytest.fixture(scope="module")
def caps_off(glyphs):
    return {ch: outline_cut.letter_columns(p) for ch, p in glyphs.items() if ch.isupper()}


def test_capitals_never_fold_off(caps_off):
    assert len(caps_off) == 18
    assert {ch: _folded(cut) for ch, cut in caps_off.items()} == {ch: 0 for ch in caps_off}


@pytest.mark.parametrize("ch", list(SHOULDERS))
def test_a_lowercase_shoulder_folds_off_and_is_cut_on(glyphs, shoulders_on, ch):
    off = outline_cut.letter_columns(glyphs[ch])
    on = shoulders_on[ch]
    assert _folded(off) >= outline_cut.FOLD_MIN
    assert _folded(on) == 0
    assert len(on.cuts) > len(off.cuts) and not on.unsewn


@pytest.mark.parametrize("ch", list(SHOULDERS))
def test_no_cut_leaves_a_stub(shoulders_on, ch):
    """#887's u cut its spur off the stem and sewed it as a knot of short
    crosses; no column ON is shorter than STUB_WIDTHS stroke widths."""
    cut = shoulders_on[ch]
    assert all(outline_cut._column_len(c) >= outline_cut.STUB_WIDTHS * cut.W
               for c in cut.columns), ch


def test_the_u_stem_sews_whole_with_its_spur(glyphs, shoulders_on):
    """ON the u is two columns: the bowl, and the right stem straight from
    its top to the foot of the spur (one cut, along the stem's inner edge),
    not three with the spur a piece of its own (#887)."""
    on = shoulders_on["u"]
    assert len(on.cuts) == 1 and len(on.columns) == 2
    stem = next(c for c in on.columns if c.kind == "straight")
    y0, y1 = glyphs["u"].bounds[1], glyphs["u"].bounds[3]
    ys = [p[1] for st in stem.stations for p in st]
    assert max(ys) > y1 - 0.2 and min(ys) < y0 + 0.2     # top to foot


def test_the_a_ring_is_opened_by_a_pair_of_cuts(glyphs, shoulders_on):
    """The a's bowl still holds the foot of its stem and is a ring one cut
    cannot open (#887 left it folding). ON a PAIR opens it: no ring is
    left, and the stem below the bowl's top sews as a straight column."""
    off = outline_cut.letter_columns(glyphs["a"])
    on = shoulders_on["a"]
    assert any(c.kind == "ring" for c in off.columns)
    assert not any(c.kind == "ring" for c in on.columns)
    assert len(on.cuts) == len(off.cuts) + 2
    assert any(c.kind == "straight" for c in on.columns)


def test_no_column_is_carried_round_a_corner(shoulders_on):
    for ch, cut in shoulders_on.items():
        assert all(outline_cut._max_turn(c, cut.W) <= outline_cut.TURN_MAX_DEG
                   for c in cut.columns), ch


def test_fold_cuts_leave_every_capital_alone(glyphs, caps_off):
    """ON changes nothing a capital's construction already does right."""
    for ch, off in caps_off.items():
        on = outline_cut.letter_columns(glyphs[ch], fold_cuts=True)
        assert [c.stations for c in on.columns] == [c.stations for c in off.columns], ch


def test_fold_cuts_leave_every_capital_alone_at_80mm(glyphs80):
    """The same at 80 mm, where the stub refusal also reaches the
    over-long second look: it applies only to a piece that folds, and no
    capital piece does."""
    caps = {ch: p for ch, p in glyphs80.items() if ch.isupper()}
    assert len(caps) == 18
    for ch, p in caps.items():
        off = outline_cut.letter_columns(p)
        on = outline_cut.letter_columns(p, fold_cuts=True)
        assert [c.stations for c in on.columns] == [c.stations for c in off.columns], ch


def test_the_80mm_a_spur_is_no_longer_a_stub(glyphs80):
    """At 80 mm the over-long look cut the a's spur off as a 4-cross
    column (OFF and #887 alike); ON, a folding piece refuses that cut."""
    W = outline_cut.letter_columns(glyphs80["a"]).W
    off = outline_cut.letter_columns(glyphs80["a"])
    on = outline_cut.letter_columns(glyphs80["a"], fold_cuts=True)
    assert min(outline_cut._column_len(c) for c in off.columns) < outline_cut.STUB_WIDTHS * W
    assert min(outline_cut._column_len(c) for c in on.columns) >= outline_cut.STUB_WIDTHS * W


def test_the_80mm_e_ring_is_opened_at_its_bar(glyphs80):
    """At 80 mm the junction rules miss the through cut at the e's bar's
    left end by a hair (alignment 0.937 against 0.94), the over-long look
    cuts the left wall under the bar instead, and what is left is a ring of
    counter AND bar that fans 83 deg round the bar's ends (`_max_turn`) --
    one sewn cross past 45 deg, which `_folded` cannot see. ON a pair of
    cuts opens that ring at the bar's two ends: the bar sews as a straight
    column, nothing is carried round a corner, nothing is a stub."""
    W = outline_cut.letter_columns(glyphs80["e"]).W
    off = outline_cut.letter_columns(glyphs80["e"])
    on = outline_cut.letter_columns(glyphs80["e"], fold_cuts=True)
    ring = next(c for c in off.columns if c.kind == "ring")
    assert outline_cut._max_turn(ring, W) > outline_cut.TURN_MAX_DEG
    assert not any(c.kind == "ring" for c in on.columns) and not on.unsewn
    assert len(on.cuts) == len(off.cuts) + 2
    assert any(c.kind == "straight" for c in on.columns)
    assert all(outline_cut._max_turn(c, W) <= outline_cut.TURN_MAX_DEG for c in on.columns)
    assert all(outline_cut._column_len(c) >= outline_cut.STUB_WIDTHS * W for c in on.columns)
    assert _folded(on) == 0


@pytest.mark.parametrize("mitre", [False, True])
def test_the_50mm_g_sews_as_off(glyphs50, mitre):
    """At 50 mm the G's bowl tail and stem foot are one over-long piece
    unless the tail is cut off at 2.2 W -- a stub. The stub refusal (#893)
    turned that cut down, and with no other cure the piece sewed whole and
    folded (2 crosses; 1 of 144 capital stations past 45 deg sewn, #921).
    ON now takes OFF's cut when nothing else cures: the G sews as OFF."""
    off = outline_cut.letter_columns(glyphs50["G"], mitre_ends=mitre)
    on = outline_cut.letter_columns(glyphs50["G"], fold_cuts=True, mitre_ends=mitre)
    assert min(outline_cut._column_len(c) for c in off.columns) < outline_cut.STUB_WIDTHS * off.W
    assert [c.stations for c in on.columns] == [c.stations for c in off.columns]
    assert _folded(on) == 0


def test_fold_cuts_leave_every_capital_alone_at_50mm(glyphs50):
    caps = {ch: p for ch, p in glyphs50.items() if ch.isupper()}
    assert len(caps) == 18
    for ch, p in caps.items():
        off = outline_cut.letter_columns(p, mitre_ends=True)
        on = outline_cut.letter_columns(p, fold_cuts=True, mitre_ends=True)
        assert [c.stations for c in on.columns] == [c.stations for c in off.columns], ch


def _stalls(cut, pitch_mm=0.4) -> int:
    """Curved columns' end stations on a fold-look cut whose neighbour's
    rail end has barely moved (`outline_cut._drop_stalls`)."""
    lines = [outline_cut.LineString([c[0], c[1]]) for c in cut.cuts if c[2] == "fold"]
    n = 0
    for col in cut.columns:
        if col.kind != "curved" or len(col.stations) < 3:
            continue
        for i0, i1 in ((0, 1), (-1, -2)):
            (a0, b0), (a1, b1) = col.stations[i0], col.stations[i1]
            tol = 0.25 * col.width_mm
            on_fold = any(outline_cut.Point(a0).distance(ln) < tol
                          and outline_cut.Point(b0).distance(ln) < tol for ln in lines)
            n += on_fold and min(math.dist(a0, a1), math.dist(b0, b1)) < \
                outline_cut.STALL_FRAC * pitch_mm
    return n


def test_the_120mm_b_bowl_end_does_not_stall(glyphs, monkeypatch):
    """ON the 120 mm b's bowl ends on the fold cut at its stem foot, a
    concave corner, and the next station's outer end had moved 0.1 mm along
    the rail: sewn, its leg is SHORT (0.56 against a 1.17 mm median, the one
    short leg at the b's junctions ON against none OFF). That station goes."""
    on = outline_cut.letter_columns(glyphs["b"], fold_cuts=True, mitre_ends=True)
    assert _stalls(on) == 0 and _folded(on) == 0 and not on.unsewn
    monkeypatch.setattr(outline_cut, "_drop_stalls", lambda col, *_a: col)
    kept = outline_cut.letter_columns(glyphs["b"], fold_cuts=True, mitre_ends=True)
    assert _stalls(kept) == 1
    assert sum(len(c.stations) for c in kept.columns) == sum(len(c.stations) for c in on.columns) + 1


def test_drop_stalls_reads_only_a_curved_end_on_a_fold_cut():
    from digitizer_core.columns import Column
    from shapely.geometry import LineString
    st = [((0.0, 0.0), (0.0, 1.0)), ((0.05, 0.0), (0.4, 1.0)), ((0.4, 0.0), (0.8, 1.0)),
          ((0.8, 0.0), (1.2, 1.0)), ((1.2, 0.0), (1.6, 1.0))]
    col = Column(stations=st, piece=Polygon([(0, 0), (2, 0), (2, 1), (0, 1)]), kind="curved",
                 axis=None, width_mm=1.0)
    fold = [LineString([(0.0, -0.1), (0.0, 1.1)])]
    out = outline_cut._drop_stalls(col, fold, 0.4)
    assert out.stations == [st[0]] + st[2:]
    assert outline_cut._drop_stalls(col, [], 0.4) is col                   # no fold cut
    assert outline_cut._drop_stalls(col, [LineString([(5, 0), (5, 1)])], 0.4) is col
    from dataclasses import replace
    assert outline_cut._drop_stalls(replace(col, kind="straight"), fold, 0.4).stations == st


def test_the_120mm_e_is_left_as_it_was(glyphs):
    """At 120 mm the junction rules already cut the e at its bar (a through
    cut and an edge extension): ON leaves it alone."""
    off = outline_cut.letter_columns(glyphs["e"])
    on = outline_cut.letter_columns(glyphs["e"], fold_cuts=True)
    assert [c.stations for c in on.columns] == [c.stations for c in off.columns]


def test_a_tight_o_is_not_a_carried_ring():
    """A ring that turns hard but holds no junction corner is a round
    counter, not a stroke carried round a junction: no second look."""
    from shapely.geometry import Point
    o = Point(0, 0).buffer(1.6, 16).difference(Point(0, 0).buffer(1.0, 16))
    W = outline_cut.stroke_width(o)
    col = outline_cut.build_column(o, [], W, 0.4)
    assert col is not None and col.kind == "ring"
    assert not outline_cut._carried_ring(o, col, W)


#: md5 of every glyph's OFF stations on the stored polygons, computed with
#: this branch's outline_cut AND with main's at the merge base (e982ce25):
#: both 780d0990... (2026-10-13). The end-to-end OFF plans agree too, on the
#: same pair of codebases: synthetic at 80 mm f40e59bd..., toat at 80 mm
#: 6b336916... (PR body).
OFF_CONSTRUCTION_MD5 = "780d099076b6610380d36df2a06de1a6"


def test_off_construction_is_pinned(glyphs):
    import hashlib
    rows = []
    for ch in sorted(glyphs):
        cut = outline_cut.letter_columns(glyphs[ch])
        rows.append([ch, [[[round(a[0], 4), round(a[1], 4), round(b[0], 4), round(b[1], 4)]
                           for a, b in c.stations] for c in cut.columns]])
    assert hashlib.md5(json.dumps(rows).encode()).hexdigest() == OFF_CONSTRUCTION_MD5


def test_off_never_enters_the_new_code(glyphs, glyphs80, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("fold_cuts code reached with fold_cuts off")
    for name in ("_fold_refine", "_folded", "_column_len", "_max_turn", "_ring_opener",
                 "_carried_ring", "_drop_stalls", "_judged_overlong", "sewn_knots",
                 "_uncovered"):
        monkeypatch.setattr(outline_cut, name,
                            own_thread_only(boom, getattr(outline_cut, name)))
    for ch in SHOULDERS + "e":
        outline_cut.letter_columns(glyphs[ch])
        outline_cut.letter_columns(glyphs80[ch])
        outline_cut.letter_columns(glyphs[ch], mitre_ends=True)
    # nor does the Column lane's letter entry build the sewn judge OFF
    lettering_columns_shape(glyphs80["b"], "S", **SHIPPED)


# --- the sewn judge (claude/fold-cuts-p-crossed) --------------------------------
# The construction does not show the knot a cut sews at its new junctions: on
# main ON the 80 mm b and g sewed 10 and 15 crossed legs against OFF's 5 and
# 10, the 120 mm p 3 folds, 2 short and 9 crossed legs against 0/0/4. With
# `fold_cuts` the Column lane now judges a fold-look candidate SEWN
# (`outline_cut.sewn_knots` over `column_runs`). These read the stored
# polygons through the lane's own letter entry, with the shipped settings and
# no neighbour to start or end near.

#: the Column lane's arguments on the synthetic word (80 and 120 mm alike)
SHIPPED = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.3, pull_floor_mm=1.5,
               underlay_style="center_run", square_ends=True, inside_connectors=True)


def _sewn(poly, fold: bool):
    runs, _ = lettering_columns_shape(poly, "S", **SHIPPED,
                                      **({"fold_cuts": True} if fold else {}))
    return tuple(int(v) for v in outline_cut.sewn_knots(runs))


@pytest.mark.parametrize("size,ch", [("80", c) for c in "abegmp"] + [("120", c) for c in "abgmp"])
def test_the_judged_fold_look_knots_no_more_than_off(glyphs, glyphs80, size, ch):
    """Station folds / short / crossed legs, OFF vs ON, sewn: ON never sews
    more short or more crossed legs than OFF, nor more folds."""
    poly = (glyphs80 if size == "80" else glyphs)[ch]
    off, on = _sewn(poly, False), _sewn(poly, True)
    assert on[0] <= off[0] and on[1] <= off[1] and on[2] <= off[2], (off, on)


def _bare(poly, runs) -> float:
    """The glyph's area outside every triangle of consecutive satin points:
    what the sewn satin leaves bare, read from the RUNS (not the columns)."""
    from shapely.ops import unary_union
    tris = []
    for r in runs:
        if r.kind != "satin":
            continue
        pts = list(r.points)
        for i in range(len(pts) - 2):
            t = Polygon([pts[i], pts[i + 1], pts[i + 2]])
            if t.is_valid and t.area > 0:
                tris.append(t)
    return poly.difference(unary_union(tris)).area if tris else poly.area


def test_uncovered_reads_the_area_outside_the_crosses():
    """`_uncovered`: the piece's area outside every cross-to-cross quad of
    its columns; a None column sews nothing, no column leaves it all bare."""
    from digitizer_core.columns import Column
    box = Polygon([(0, 0), (2, 0), (2, 1), (0, 1)])
    st = [((x, 0.0), (x, 1.0)) for x in (0.0, 0.4, 0.8, 1.2, 1.6)]
    col = Column(stations=st, piece=box, kind="straight", axis=None, width_mm=1.0)
    assert math.isclose(outline_cut._uncovered(box, [col]), 0.4, abs_tol=1e-9)
    full = Column(stations=st + [((2.0, 0.0), (2.0, 1.0))], piece=box, kind="straight",
                  axis=None, width_mm=1.0)
    assert math.isclose(outline_cut._uncovered(box, [full]), 0.0, abs_tol=1e-9)
    assert math.isclose(outline_cut._uncovered(box, [None, full]), 0.0, abs_tol=1e-9)
    assert math.isclose(outline_cut._uncovered(box, []), 2.0, abs_tol=1e-9)


def test_the_80mm_b_cure_sews_its_bowl_shoulder(glyphs80, monkeypatch):
    """The judge counts knots, and a column that sews nothing knots nothing:
    with COVER_SLACK patched out the 80 mm b's winning ring pair sews 0/0/0
    and leaves 1.4 W^2 of its bowl shoulder bare, against OFF's 0.5 W^2.
    Guarded (a candidate may leave at most COVER_SLACK W^2 more of its piece
    outside its crosses than the piece's own construction), the pair kept
    sews 0/0/0 AND no more of the b bare than OFF (0.3 W^2)."""
    poly = glyphs80["b"]
    W2 = outline_cut.stroke_width(poly) ** 2
    off_runs, _ = lettering_columns_shape(poly, "S", **SHIPPED)
    on_runs, _ = lettering_columns_shape(poly, "S", fold_cuts=True, **SHIPPED)
    assert tuple(int(v) for v in outline_cut.sewn_knots(on_runs)) == (0, 0, 0)
    assert _bare(poly, on_runs) <= _bare(poly, off_runs)
    monkeypatch.setattr(outline_cut, "COVER_SLACK", 1e9)
    loose_runs, _ = lettering_columns_shape(poly, "S", fold_cuts=True, **SHIPPED)
    assert tuple(int(v) for v in outline_cut.sewn_knots(loose_runs)) == (0, 0, 0)
    assert _bare(poly, loose_runs) > _bare(poly, off_runs) + 0.5 * W2


@pytest.mark.parametrize("ch,off_want", [("b", (3, 0, 5)), ("g", (1, 0, 6))])
def test_the_80mm_b_and_g_rings_open_without_a_knot(glyphs80, ch, off_want):
    """On main ON the ring pair the fold look kept read clean in construction
    and sewed 10 (b) and 15 (g) crossed legs; the judge keeps a pair that
    sews no fold and no knot at all."""
    assert _sewn(glyphs80[ch], False) == off_want
    assert _sewn(glyphs80[ch], True) == (0, 0, 0)


def test_the_120mm_p_keeps_off_stem_cut(glyphs):
    """OFF cuts the p's stem top off its bowl as a 2.4 W straight column --
    a stub by STUB_WIDTHS -- and sews 0/0/4. The stub refusal sent it to a
    ring pair that sewed 3/2/9; judged sewn, OFF's cut stands."""
    off = outline_cut.letter_columns(glyphs["p"], mitre_ends=True)
    assert min(outline_cut._column_len(c) for c in off.columns) < outline_cut.STUB_WIDTHS * off.W
    assert _sewn(glyphs["p"], True) == _sewn(glyphs["p"], False) == (0, 0, 4)


def test_the_120mm_b_is_cured_on_both_polygons(glyphs):
    """#972: the stored 120 mm b (rounded to 1e-4 mm) and the pipeline's own
    polygon pick different ring pairs. Judged sewn, both sew fewer folds than
    OFF and no more knots."""
    raw = json.loads(la.FIXTURE.with_name("lowercase_aileron_b_120_unrounded.json")
                     .read_text(encoding="utf-8"))
    pipeline = Polygon(raw["exterior"], raw["holes"])
    assert 0 < pipeline.symmetric_difference(glyphs["b"]).area < 0.002
    for poly in (glyphs["b"], pipeline):
        off, on = _sewn(poly, False), _sewn(poly, True)
        assert off[0] == 3 and on[0] <= 1 and on[1] <= off[1] and on[2] <= off[2], (off, on)


def test_the_judge_leaves_every_capital_alone(glyphs80):
    """The over-long look's judged branch reaches a capital piece that folds
    (the B's, the G's): it may leave OFF's cut only for FEWER sewn folds, and
    none sews fewer. All 18 capitals sew as OFF at 80 mm."""
    caps = {ch: p for ch, p in glyphs80.items() if ch.isupper()}
    assert len(caps) == 18
    for ch, p in caps.items():
        off, _ = lettering_columns_shape(p, "S", **SHIPPED)
        on, _ = lettering_columns_shape(p, "S", fold_cuts=True, **SHIPPED)
        assert [r.points for r in on] == [r.points for r in off], ch


# --- end to end, OFF arm vs the default (ON since 2026-10-20) --------------------

def _md5(plan) -> str:
    import hashlib
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.fixture(scope="module")
def word():
    kw = dict(target_width_mm=80.0, forced_class="flat")

    def boom(*_a, **_k):
        raise AssertionError("fold_cuts code reached with fold_cuts off")
    with pytest.MonkeyPatch.context() as mp:      # OFF never runs the new code
        for name in ("_fold_refine", "_judged_overlong", "sewn_knots", "_uncovered"):
            mp.setattr(outline_cut, name, own_thread_only(boom, getattr(outline_cut, name)))
        off_r, off = digitize(la.FIXTURE.with_suffix(".png"),
                              PipelineConfig(lettering_columns_fold_cuts=False, **kw))
    # the default IS the ON arm since Kent's flip 2026-10-20
    _on_r, on = digitize(la.FIXTURE.with_suffix(".png"), PipelineConfig(**kw))
    return off_r, off, on


def test_the_flag_is_on_by_default():
    # Kent's flip 2026-10-20, after PR #986's sewn judge; False is the pre-flip lane
    assert PipelineConfig().lettering_columns_fold_cuts is True
    assert PipelineConfig() == PipelineConfig(lettering_columns_fold_cuts=True)


def test_on_moves_only_lowercase_and_cuts_its_folds(word):
    result, off, on = word
    assert _md5(on) != _md5(off)
    meta = json.loads(la.FIXTURE.with_suffix(".json").read_text(encoding="utf-8"))
    to_px, _s = la.mm_to_px(result, meta["image"])
    upper, e_ids = set(), set()
    for r in result.regions:
        g = la._glyph_at(meta, *to_px(r.polygon.centroid.x, r.polygon.centroid.y))
        if g and g["ch"].isupper():
            upper.add(r.shape_id)
        if g and g["ch"] == "e":
            e_ids.add(r.shape_id)

    def runs(plan, ids):
        return [(r.shape_id, r.kind, [(round(x, 4), round(y, 4)) for x, y in r.points])
                for _, r in plan.iter_runs() if r.shape_id in ids]
    assert upper and runs(on, upper) == runs(off, upper)

    def folds(plan, ids=None):
        recs = la.cross_records(plan, ids or {r.shape_id for r in result.regions} - upper)
        st = [r["station_lean"] for r in recs if r["station_lean"] is not None]
        return sum(v > 45.0 for v in st), len(st)
    f_off, n_off = folds(off)
    f_on, n_on = folds(on)
    # 5 -> 0 of ~365 lowercase station crosses on Kent's box (#887 left 2,
    # the a's and the e's; #893 cut the a's, claude/lowercase-e-folds the e's)
    assert f_off >= 3 and f_on < f_off, (f_off, n_off, f_on, n_on)
    # the e: one sewn cross past 45 deg OFF, at its bar's end; none ON
    assert e_ids and folds(off, e_ids)[0] >= 1 and folds(on, e_ids)[0] == 0
    assert on.stats.trims == off.stats.trims
    assert math.isclose(on.stats.stitch_count, off.stats.stitch_count, rel_tol=0.03)


def _by_glyph(result, plan) -> dict[str, tuple[int, int, int]]:
    """The tool's per-glyph reading: station folds / short / crossed legs."""
    meta = json.loads(la.FIXTURE.with_suffix(".json").read_text(encoding="utf-8"))
    to_px, _s = la.mm_to_px(result, meta["image"])
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="flat")
    from digitizer_core.columns import is_lettering
    ids = {r.shape_id for r in result.regions if is_lettering(r, cfg)}
    out: dict[str, list[int]] = {}

    def ch_at(x, y):
        g = la._glyph_at(meta, *to_px(x, y))
        return g["ch"] if g else None
    for r in la.cross_records(plan, ids):
        if r["station_lean"] is not None and r["station_lean"] > 45.0 and ch_at(r["x"], r["y"]):
            out.setdefault(ch_at(r["x"], r["y"]), [0, 0, 0])[0] += 1
    for k, recs in enumerate(la.junction_knots(plan, ids)):
        for x, y, _l in recs:
            if ch_at(x, y):
                out.setdefault(ch_at(x, y), [0, 0, 0])[k + 1] += 1
    return {ch: tuple(v) for ch, v in out.items()}


def test_no_lowercase_glyph_knots_more_than_off_at_80mm(word):
    """End to end at 80 mm, by the tool's own per-glyph reading: no lowercase
    glyph sews more short or more crossed legs ON than OFF (main ON: the b 10
    against 5, the g 15 against 10, the m 4 against 0), and the b, the g and
    the e sew no fold."""
    result, off, on = word
    g_off, g_on = _by_glyph(result, off), _by_glyph(result, on)
    for ch in set(g_off) | set(g_on):
        if ch.islower():
            o, n = g_off.get(ch, (0, 0, 0)), g_on.get(ch, (0, 0, 0))
            assert n[1] <= o[1] and n[2] <= o[2], (ch, o, n)
    assert all(g_on.get(ch, (0, 0, 0))[0] == 0 for ch in "bge")
    assert g_off["b"][0] >= 1 and g_on.get("b", (0, 0, 0))[2] < g_off["b"][2]


def test_sewn_knots_reads_as_the_tool(word):
    """`outline_cut.sewn_knots` restates `tools/lowercase_angle.py`'s reading
    so the engine need not import a tool: per lettering shape, both plans,
    the two agree count for count."""
    result, off, on = word
    from digitizer_core.columns import is_lettering
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="flat")
    ids = {r.shape_id for r in result.regions if is_lettering(r, cfg)}
    checked = 0
    for plan in (off, on):
        by_shape: dict[str, list] = {}
        for _b, r in plan.iter_runs():
            if r.shape_id in ids:
                by_shape.setdefault(r.shape_id, []).append(r)
        for sid, runs in by_shape.items():
            st = [r["station_lean"] for r in la.cross_records(plan, {sid})
                  if r["station_lean"] is not None]
            short, crossed = la.junction_knots(plan, {sid})
            tool = (sum(v > 45.0 for v in st), len(short), len(crossed))
            assert tuple(int(v) for v in outline_cut.sewn_knots(runs)) == tool, sid
            checked += sum(tool) > 0
    assert checked >= 10
