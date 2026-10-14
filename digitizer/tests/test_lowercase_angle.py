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
`cfg.lettering_columns_fold_cuts` (default OFF) gives such a piece the
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
                 "_carried_ring"):
        monkeypatch.setattr(outline_cut, name,
                            own_thread_only(boom, getattr(outline_cut, name)))
    for ch in SHOULDERS + "e":
        outline_cut.letter_columns(glyphs[ch])
        outline_cut.letter_columns(glyphs80[ch])


# --- end to end, default OFF ---------------------------------------------------

def _md5(plan) -> str:
    import hashlib
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.fixture(scope="module")
def word():
    kw = dict(target_width_mm=80.0, forced_class="flat")

    def boom(*_a, **_k):
        raise AssertionError("_fold_refine reached on the default config")
    with pytest.MonkeyPatch.context() as mp:      # OFF never runs the new code
        mp.setattr(outline_cut, "_fold_refine",
                   own_thread_only(boom, outline_cut._fold_refine))
        off_r, off = digitize(la.FIXTURE.with_suffix(".png"), PipelineConfig(**kw))
    _on_r, on = digitize(la.FIXTURE.with_suffix(".png"),
                         PipelineConfig(lettering_columns_fold_cuts=True, **kw))
    return off_r, off, on


def test_the_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_fold_cuts is False


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
