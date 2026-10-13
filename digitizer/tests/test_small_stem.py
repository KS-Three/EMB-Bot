"""A thin lettering stem under the area floor and the Column lane (2026-10-13).

PR #887 found that at 80 mm the synthetic 'i' stem is tagged as lettering and
sews no satin. `tools/stem_trace.py` traces it: the stem is its own region of
2.124 mm^2 (0.57 x 3.73 mm), under the small-shape rescue's floor
(`min_detail_mm`^2 = 2.25), so stage 7's `routes_to_run` sends it to the run
tier BEFORE the Column lane is asked, while the capital I at the same 0.57 mm
width is 2.771 mm^2 and sews satin. Not dropped, not merged with its dot (the
dot is a separate 0.446 mm^2 region that stage 3's run-tier loop floor drops
at 80 mm).

`cfg.lettering_columns_small_stem` (default OFF) lets a lettering stem under
the floor into the lane. These tests pin:

- the trace: the stem is a lettering region under the floor, sewn as run
  only, with the capital stem satin beside it (measured negative on the rule:
  the rescue itself is right for a dot, so it stays);
- ON, the stem sews satin and no run, and every other shape in the design
  sews the same thread (run for run);
- capitals are identical ON and OFF;
- OFF is byte-identical: the hook is never entered, and the OFF plan's md5
  equals the one computed on main's `digitizer_core`.

The word is drawn at test time in Pillow's bundled CC0 face (no image is
added to testdata) at the fixture's 28.1 px/mm, so the stem is the 80 mm one.
"""
from __future__ import annotations

import hashlib

import pytest
from shapely.geometry import Point, box

from digitizer_core import PipelineConfig, digitize
from digitizer_core import columns, stage7_sequence
from digitizer_core.columns import is_lettering, is_thin_stem

#: `tools/stem_trace.py --word tsivyl 15.9` / `--word HILTIL`: the fixture's
#: 28.1 px per mm, where the i stem is 0.57 x 3.73 mm.
LOWER = ("tsivyl", 15.9)
CAPS = ("HILTIL", 20.7)

#: md5 of the OFF plan, computed on main's digitizer_core at the merge base
#: (the same hash `plan_md5` takes) and on this branch: equal.
OFF_MD5 = {"tsivyl": "d94c1b95f29bb045bb003b08e95c36c2", "HILTIL": "9eb5d7bd7c751b8b3afb6a9fae1f7d23"}


def plan_md5(plan, skip=()):
    h = hashlib.md5()
    for _b, run in plan.iter_runs():
        if run.shape_id in skip:
            continue
        h.update(f"{run.shape_id}|{run.kind}".encode())
        for p in run.points:
            h.update(f"{p[0]:.4f},{p[1]:.4f};".encode())
    return h.hexdigest()


def kinds_of(plan):
    out = {}
    for _b, run in plan.iter_runs():
        out.setdefault(run.shape_id, set()).add(run.kind)
    return out


def draw(text, path):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=200)
    w = int(font.getlength(text)) + 120
    img = Image.new("RGB", (w, 440), "white")
    ImageDraw.Draw(img).text((60, 60), text, font=font, fill="black")
    img.save(path)
    return path


def run(tmp_path_factory, word, small_stem, guard=False):
    text, width = word
    path = draw(text, tmp_path_factory.mktemp(f"w{text}{int(small_stem)}") / "w.png")
    cfg = PipelineConfig(target_width_mm=width, forced_class="flat",
                         **({"lettering_columns_small_stem": True} if small_stem else {}))
    if not guard:
        return digitize(path, cfg), cfg

    def boom(*_a, **_k):
        raise AssertionError("is_thin_stem reached with the flag OFF")
    mp = pytest.MonkeyPatch()
    mp.setattr(stage7_sequence, "is_thin_stem", boom)
    try:
        return digitize(path, cfg), cfg
    finally:
        mp.undo()


@pytest.fixture(scope="module")
def lower_off(tmp_path_factory):
    return run(tmp_path_factory, LOWER, False, guard=True)


@pytest.fixture(scope="module")
def lower_on(tmp_path_factory):
    return run(tmp_path_factory, LOWER, True)


@pytest.fixture(scope="module")
def caps_off(tmp_path_factory):
    return run(tmp_path_factory, CAPS, False, guard=True)


@pytest.fixture(scope="module")
def caps_on(tmp_path_factory):
    return run(tmp_path_factory, CAPS, True)


def i_stem(result, cfg):
    """The lowercase i's stem: the only lettering region under the floor."""
    floor = cfg.min_detail_mm ** 2
    under = [r for r in result.regions if is_lettering(r, cfg) and r.polygon.area < floor]
    assert len(under) == 1
    return under[0]


# --- the predicate --------------------------------------------------------

def test_a_stem_is_thin_and_long_a_dot_or_blob_is_not():
    assert is_thin_stem(box(0, 0, 0.57, 3.73), 1.5)            # the i stem, 6.5
    assert is_thin_stem(box(0, 0, 3.73, 0.57), 1.5)            # same, lying down
    assert not is_thin_stem(Point(0, 0).buffer(0.375), 1.5)   # the 80 mm dot
    assert not is_thin_stem(box(0, 0, 1.4, 1.4), 1.5)         # a blob
    assert not is_thin_stem(box(0, 0, 0.3, 1.2), 1.5)         # thin but under the floor's length
    assert not is_thin_stem(box(0, 0, 1.0, 2.5), 1.5)         # aspect 2.5
    # the phone screenshot's lettering stems under the floor (measured by
    # `tools/stem_trace.py --census screenshot`): none reaches the lane
    assert not is_thin_stem(box(0, 0, 0.39, 3.29), 1.5)       # 8.4, but under the 0.5 cross floor
    assert not is_thin_stem(box(0, 0, 0.31, 3.29), 1.5)
    assert not is_thin_stem(box(0, 0, 0.63, 2.51), 1.5)       # aspect 4.0
    assert not is_thin_stem(box(0, 0, 0.63, 1.96), 1.5)       # 3.1
    assert not is_thin_stem(box(0, 0, 0.90, 3.70), 1.5)       # 4.1
    assert columns.STEM_MIN_ASPECT == 6.0


def test_the_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_small_stem is False


# --- the trace (measured, no flag) ----------------------------------------

def test_the_i_stem_is_a_lettering_region_under_the_floor_sewn_as_a_run(lower_off):
    (result, plan), cfg = lower_off
    stem = i_stem(result, cfg)
    assert stem.polygon.area == pytest.approx(2.126, abs=0.01)
    assert cfg.min_detail_mm ** 2 == pytest.approx(2.25)
    assert stem.polygon.area < cfg.min_detail_mm ** 2          # the rule: 2.126 < 2.25
    assert kinds_of(plan)[stem.shape_id] == {"run"}            # no satin, no underlay
    # not merged with a dot: the stem is the whole 0.57 x 3.73 mm column
    x0, y0, x1, y1 = stem.polygon.bounds
    assert (x1 - x0, y1 - y0) == pytest.approx((0.57, 3.73), abs=0.05)
    # the l beside it clears the floor and sews satin
    others = [r for r in result.regions if r.shape_id != stem.shape_id and is_lettering(r, cfg)]
    assert others and all(r.polygon.area >= cfg.min_detail_mm ** 2 for r in others)
    assert all("satin" in kinds_of(plan)[r.shape_id] for r in others)


# --- ON -------------------------------------------------------------------

def test_on_the_stem_sews_satin_and_no_run(lower_off, lower_on):
    (res_off, _p), cfg_off = lower_off
    (res_on, plan_on), cfg_on = lower_on
    sid = i_stem(res_off, cfg_off).shape_id
    assert sid == i_stem(res_on, cfg_on).shape_id
    assert kinds_of(plan_on)[sid] == {"satin"}


def test_on_every_other_shape_sews_the_same_tier_and_the_ones_before_it_the_same_thread(
        lower_off, lower_on):
    """Only the stem changes tier. A letter sewn AFTER it starts its column
    walk near where the stem ended (`start_near`), so its crosses may be laid
    in another order -- the same ink, the same tier -- while every run before
    the stem in the sew order is byte-identical."""
    (res_off, plan_off), cfg_off = lower_off
    (_r, plan_on), _c = lower_on
    sid = i_stem(res_off, cfg_off).shape_id
    k_off, k_on = kinds_of(plan_off), kinds_of(plan_on)
    assert {s: k for s, k in k_off.items() if s != sid} == {s: k for s, k in k_on.items() if s != sid}

    def before(plan):
        out = []
        for _b, run in plan.iter_runs():
            if run.shape_id == sid:
                break
            out.append(run)
        return out
    h = lambda runs: hashlib.md5(repr([(r.shape_id, r.kind, [tuple(p) for p in r.points])
                                       for r in runs]).encode()).hexdigest()
    pre = before(plan_off)
    assert pre and h(pre) == h(before(plan_on))
    assert plan_on.stats.trims == plan_off.stats.trims
    assert plan_on.stats.stitch_count == pytest.approx(plan_off.stats.stitch_count, rel=0.08)


def test_capitals_are_identical_on_and_off(caps_off, caps_on):
    (_r1, p1), _c1 = caps_off
    (_r2, p2), _c2 = caps_on
    assert plan_md5(p1) == plan_md5(p2)


# --- OFF is byte-identical ------------------------------------------------

def test_off_matches_main_byte_for_byte(lower_off, caps_off):
    # `lower_off` / `caps_off` were digitized with `is_thin_stem` patched to
    # raise: reaching them at all proves the OFF path never enters the hook.
    assert plan_md5(lower_off[0][1]) == OFF_MD5["tsivyl"]
    assert plan_md5(caps_off[0][1]) == OFF_MD5["HILTIL"]


# --- the rule is the area floor, not the letter case -----------------------

SMALL_CAPS = ("HILTIL", 18.42)   # 31.6 px/mm: the capital I is 0.51 x 4.34 mm, 2.196 mm^2


def test_a_capital_i_under_the_floor_takes_the_same_road(tmp_path_factory):
    """The cause is the area floor, so a capital stem that small runs too
    (the Ls, 2.465 mm^2, clear it) -- and ON it sews satin."""
    got = {}
    for on in (False, True):
        (result, plan), cfg = run(tmp_path_factory, SMALL_CAPS, on)
        floor = cfg.min_detail_mm ** 2
        stems = [r for r in result.regions if is_lettering(r, cfg) and r.polygon.area < floor]
        assert len(stems) == 2 and all(is_thin_stem(r.polygon, cfg.min_detail_mm) for r in stems)
        got[on] = {kind for r in stems for kind in kinds_of(plan)[r.shape_id]}
    assert got[False] == {"run"}
    assert got[True] == {"satin"}
