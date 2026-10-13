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
second look `_refine` gives an over-long one.

The glyph tests read the pipeline's own traced polygons at 120 mm
(`testdata/synthetic/lowercase_aileron_letters_120.json`), so they need no
digitize; one module fixture digitizes the word at 80 mm both ways.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, digitize, outline_cut
from tools import lowercase_angle as la

SHOULDERS = "ubgm"          # glyphs that fold OFF and come apart ON


@pytest.fixture(scope="module")
def glyphs() -> dict[str, Polygon]:
    """Each glyph as the pipeline traced it at 120 mm (`--dump-letters`)."""
    data = json.loads(la.LETTERS.read_text(encoding="utf-8"))["letters"]
    return {ch: Polygon(v["exterior"], v["holes"]) for ch, v in data.items()}


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
def test_a_lowercase_shoulder_folds_off_and_is_cut_on(glyphs, ch):
    off = outline_cut.letter_columns(glyphs[ch])
    on = outline_cut.letter_columns(glyphs[ch], fold_cuts=True)
    assert _folded(off) >= outline_cut.FOLD_MIN
    assert _folded(on) == 0
    assert len(on.cuts) > len(off.cuts) and not on.unsewn


def test_fold_cuts_leave_every_capital_alone(glyphs, caps_off):
    """ON changes nothing a capital's construction already does right."""
    for ch, off in caps_off.items():
        on = outline_cut.letter_columns(glyphs[ch], fold_cuts=True)
        assert [c.stations for c in on.columns] == [c.stations for c in off.columns], ch


def test_off_never_enters_the_new_code(glyphs, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("_fold_refine reached with fold_cuts off")
    monkeypatch.setattr(outline_cut, "_fold_refine", boom)
    for ch in SHOULDERS:
        outline_cut.letter_columns(glyphs[ch])


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
        mp.setattr(outline_cut, "_fold_refine", boom)
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
    upper = set()
    for r in result.regions:
        g = la._glyph_at(meta, *to_px(r.polygon.centroid.x, r.polygon.centroid.y))
        if g and g["ch"].isupper():
            upper.add(r.shape_id)

    def runs(plan, ids):
        return [(r.shape_id, r.kind, [(round(x, 4), round(y, 4)) for x, y in r.points])
                for _, r in plan.iter_runs() if r.shape_id in ids]
    assert upper and runs(on, upper) == runs(off, upper)

    def folds(plan):
        recs = la.cross_records(plan, {r.shape_id for r in result.regions} - upper)
        st = [r["station_lean"] for r in recs if r["station_lean"] is not None]
        return sum(v > 45.0 for v in st), len(st)
    f_off, n_off = folds(off)
    f_on, n_on = folds(on)
    # 5 -> 2 of ~365 lowercase station crosses on Kent's box (the a's and
    # the e's, which the cut does not reach, are the 2)
    assert f_off >= 3 and f_on < f_off, (f_off, n_off, f_on, n_on)
    assert on.stats.trims == off.stats.trims
    assert math.isclose(on.stats.stitch_count, off.stats.stitch_count, rel_tol=0.03)
