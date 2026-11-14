"""Like shapes decided once per group (`cfg.group_consistent_tier` and
`cfg.group_consistent_outline_body`, both built OFF 2026-11-13).

Two thresholds split lines of like letters on main (`docs/group-consistency-
2026-11-13.md`): the art-outline body test (AHORA: AH, RA fill under a loop,
O, ! satin) and the run tier's area floor (K-Line's subline: 17 bean
outlines, 6 satin). ON, a line of like shapes decides each once: members more
than `MARGIN` off the threshold are the evidence, members inside the band take
their side, and nothing is forced onto a construction its shape cannot take.
OFF, nothing calls it.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core import group_consistency as gc
from digitizer_core.art_outline import find_art_outlines
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.lettering_thread import STRAY_HEIGHT_RATIO
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence
from digitizer_core.textcluster import MIN_CLUSTER_MEMBERS


def _region(sid, poly, thread, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def _word(widths, *, height=14.0, gap=3.0, x0=-50.0, y=0.0, thread=2, prefix="L"):
    """Bars of `widths` on one baseline, `gap` apart."""
    out, x = [], x0
    for i, w in enumerate(widths):
        out.append(_region(f"{prefix}{i}", box(x, y - height / 2, x + w, y + height / 2), thread))
        x += w + gap
    return out


# ---------------------------------------------------------------- grouping

def test_one_line_of_like_shapes_is_one_group():
    word = _word([3, 4, 3, 5, 3])
    groups = gc.like_lines(word)
    assert [[r.shape_id for r in g] for g in groups] == [["L0", "L1", "L2", "L3", "L4"]]


def test_another_thread_a_dot_and_another_line_are_not_members():
    word = _word([3, 4, 3, 5])
    other_ink = _word([3], x0=-50 + 4 * 7 + 3, thread=9, prefix="X")      # beside it, another thread
    dot = [_region("D", box(-20, 6.0, -19, 7.0), 2)]                        # 1 mm high: not like
    line2 = _word([3, 3, 3, 3], y=30.0, prefix="M")                        # its own line
    groups = gc.like_lines(word + other_ink + dot + line2)
    ids = sorted(sorted(r.shape_id for r in g) for g in groups)
    assert ids == [["L0", "L1", "L2", "L3"], ["M0", "M1", "M2", "M3"]]


def test_a_pair_is_not_a_group():
    assert gc.like_lines(_word([3, 3])) == []
    assert MIN_CLUSTER_MEMBERS == 3


def test_heights_just_inside_the_stray_ratio_still_group():
    a = _word([3, 3], height=10.0)
    b = [_region("T", box(-50 + 2 * 6, -5, -50 + 2 * 6 + 3, -5 + 10.0 * STRAY_HEIGHT_RATIO + 0.01), 2)]
    assert len(gc.like_lines(a + b)) == 1


# ---------------------------------------------------------------- the verdict

def test_decided_members_set_the_side():
    # 0.5 x and 0.4 x the threshold decide "under"; 1.2 x and 1.4 x follow
    assert gc.group_verdict([0.5, 0.4, 1.2, 1.4], 1.0) is False
    assert gc.group_verdict([2.0, 1.6, 0.8], 1.0) is True


def test_no_decided_member_reads_the_median():
    assert gc.group_verdict([0.8, 0.9, 1.3], 1.0) is False      # median 0.9
    assert gc.group_verdict([0.9, 1.1, 1.3], 1.0) is True       # median 1.1


def test_decided_members_that_disagree_give_no_verdict():
    assert gc.group_verdict([0.4, 1.6, 1.0], 1.0) is None
    assert gc.follow(_word([3, 3, 3]), lambda r: {"L0": 0.4, "L1": 1.6, "L2": 1.1}[r.shape_id], 1.0) == {}


def test_margin_is_a_factor_either_side():
    assert not gc.decided(1.0 * gc.MARGIN, 1.0) and gc.decided(1.0 * gc.MARGIN + 1e-6, 1.0)
    assert not gc.decided(1.0 / gc.MARGIN, 1.0) and gc.decided(1.0 / gc.MARGIN - 1e-6, 1.0)


# ---------------------------------------------------------------- the run floor (K-Line)

FLOOR = 1.5 ** 2   # cfg.min_detail_mm ** 2 at its default


def _areas(areas, **kw):
    """Bars 2.6 mm tall with the given areas."""
    return _word([a / 2.6 for a in areas], height=2.6, gap=0.8, **kw)


def test_klines_subline_goes_one_way():
    # K-Line's 2.5 mm subline on main: bean outlines under the floor, satin over
    areas = [1.13, 1.21, 1.52, 1.56, 1.72, 1.79, 2.17, 2.24, 2.54, 2.66, 2.92, 3.07]
    word = _areas(areas)
    out = gc.run_floor_overrides(word, FLOOR, can_leave_run=lambda r: True)
    over = {r.shape_id for r in word if r.polygon.area >= FLOOR}
    assert set(out) == over and all(out.values())        # the four over it join the run tier


def test_a_line_mostly_over_the_floor_leaves_run_only_where_satin_will_take_it():
    word = _areas([4.0, 4.2, 3.9, 2.0, 1.9])               # three decided over, two inside the band
    under = {r.shape_id for r in word if r.polygon.area < FLOOR}
    assert gc.run_floor_overrides(word, FLOOR, can_leave_run=lambda r: True) == {s: False for s in under}
    assert gc.run_floor_overrides(word, FLOOR, can_leave_run=lambda r: False) == {}


def test_a_member_far_over_the_floor_keeps_its_own_tier():
    word = _areas([1.0, 1.1, 1.2, 4.0])                    # 4.0 is 1.8 x: decided, and disagrees
    assert gc.run_floor_overrides(word, FLOOR, can_leave_run=lambda r: True) == {}


# ---------------------------------------------------------------- the outline body (AHORA)

def _field(widths):
    """A field round a line of 14 mm bars, 3 mm apart: an art outline whose
    holes hold them. Wide bars read as bodies (stroke / band over 1.0)."""
    word = _word(widths)
    x1 = max(r.polygon.bounds[2] for r in word)
    field = Polygon(box(-53, -10.5, x1 + 3.0, 10.5).exterior, [r.polygon.exterior for r in word])
    return [_region("Sfield", field, 1)] + word


def test_ahora_field_is_mixed_off_and_one_way_on():
    regs = _field([9.0, 3.0, 9.5, 2.6])     # AH-like, O-like, RA-like, !-like
    off = find_art_outlines(regs, PipelineConfig(), line_art_guard=False)
    assert [b for b, _h in off["Sfield"]] == ["L0", "L2"]                   # the straddle
    on = find_art_outlines(regs, PipelineConfig(group_consistent_outline_body=True), line_art_guard=False)
    assert on == {}                                                         # every letter its own
    # the run-floor flag alone does not reach the outline test
    tier_only = find_art_outlines(regs, PipelineConfig(group_consistent_tier=True), line_art_guard=False)
    assert tier_only == off


def test_outline_decider_keeps_a_line_of_clear_bodies():
    regs = _field([9.0, 9.5, 10.0])
    off = find_art_outlines(regs, PipelineConfig(), line_art_guard=False)
    on = find_art_outlines(regs, PipelineConfig(group_consistent_outline_body=True), line_art_guard=False)
    assert [b for b, _h in on["Sfield"]] == [b for b, _h in off["Sfield"]] == ["L0", "L1", "L2"]


def test_outline_decider_never_makes_a_thin_body():
    # a line of bodies in the band, one thin member under it: it may join
    # only when it is at least the fill floor across
    word = _word([3, 3, 3])
    cands = [(r, Polygon(r.polygon.exterior), 1.0, s) for r, s in zip(word, (1.3, 1.3, 0.8))]
    keep_all = gc.outline_body_decider(0.5)(None, cands)
    assert [b.shape_id for b, _h in keep_all] == ["L0", "L1", "L2"]
    keep_thick = gc.outline_body_decider(0.9)(None, cands)
    assert [b.shape_id for b, _h in keep_thick] == ["L0", "L1"]


# ---------------------------------------------------------------- stage 7, end to end

def _rings(letters, height=2.6, gap=0.8):
    """O-like letters (width, stroke) on one baseline: a hole each, so none is
    a fine bar or a small solid -- the run tier or the classifier decides."""
    out, x = [], -10.0
    for i, (w, s) in enumerate(letters):
        outer = box(x, -height / 2, x + w, height / 2)
        inner = box(x + s, -height / 2 + s, x + w - s, height / 2 - s)
        out.append(_region(f"L{i}", Polygon(outer.exterior, [inner.exterior]), 2))
        x += w + gap
    return out


#: 1.20 and 1.24 mm^2 (0.53 / 0.55 x the floor: decided, run), 2.90 and
#: 3.19 mm^2 (1.29 / 1.42 x: over the floor, inside the band; satin OFF)
RING_WORD = [(0.8, 0.2), (0.9, 0.2), (1.3, 0.5), (1.4, 0.55)]


def test_ring_word_straddles_the_floor():
    areas = [r.polygon.area for r in _rings(RING_WORD)]
    assert [a < FLOOR for a in areas] == [True, True, False, False]
    assert [gc.decided(a, FLOOR) for a in areas] == [True, True, False, False]


def _kinds(letters, **cfg_kw):
    word = _rings(letters)
    planned = [PlannedRegion(region=r, polygon=r.polygon, sew_index=0) for r in word]
    cfg = PipelineConfig(underlay=False, **cfg_kw)
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg)
    out: dict[str, set] = {}
    for blk in blocks:
        for run in blk.runs:
            if run.kind not in (stitches.TRAVEL, stitches.TIE, stitches.UNDERLAY):
                out.setdefault(run.shape_id, set()).add(run.kind)
    return out


@pytest.mark.parametrize("flag", [False, True])
def test_sequence_sews_a_mixed_line_one_way_with_the_flag(flag):
    kinds = _kinds(RING_WORD, group_consistent_tier=flag)
    assert set(kinds) == {"L0", "L1", "L2", "L3"}
    run_like = {stitches.RUN, stitches.BEAN}
    if flag:
        assert all(k <= run_like for k in kinds.values()), kinds
    else:
        assert kinds["L0"] <= run_like and kinds["L1"] <= run_like
        assert not (kinds["L2"] <= run_like) and not (kinds["L3"] <= run_like), kinds


def test_off_is_the_engine_as_it_was():
    a = _kinds(RING_WORD)
    b = _kinds(RING_WORD, group_consistent_tier=False)
    assert a == b
    assert PipelineConfig().group_consistent_tier is False
    assert PipelineConfig().group_consistent_outline_body is False
    assert machine.OUTLINE_BODY_RATIO == 1.0     # the census numbers above are read against it


# ---------------------------------------------------------------- the word's thread (Bridge's U)

from digitizer_core import lettering_thread as lt  # noqa: E402
from digitizer_core.threads import CHART  # noqa: E402

CARIBBEAN, SWISS_IVY, FIRE_ENGINE = 335, 360, 174     # 18.4 dE00 apart; red far off both


def _cluster(threads, cid="TC1"):
    word = _word([3] * len(threads))
    for r, t in zip(word, threads):
        r.thread_index, r.thread_number = t, CHART[t].number
        r.meta.update(text_candidate=True, text_cluster_id=cid)
    return word


def test_a_lone_letter_takes_its_words_thread():
    assert CHART.delta_e(CARIBBEAN, SWISS_IVY) <= lt.STRAY_MAX_DE00
    word = _cluster([CARIBBEAN] * 10 + [SWISS_IVY])
    assert lt.word_thread(word, CHART, {}) == 1
    assert {r.thread_index for r in word} == {CARIBBEAN}
    assert word[-1].meta["lettering_word_thread_from"] == CHART[SWISS_IVY].number


def test_a_far_colour_a_pinned_letter_and_a_two_colour_word_keep_their_threads():
    far = _cluster([CARIBBEAN] * 10 + [FIRE_ENGINE])
    assert CHART.delta_e(CARIBBEAN, FIRE_ENGINE) > lt.STRAY_MAX_DE00
    assert lt.word_thread(far, CHART, {}) == 0
    pinned = _cluster([CARIBBEAN] * 10 + [SWISS_IVY])
    assert lt.word_thread(pinned, CHART, {"L10": {"thread_index": SWISS_IVY}}) == 0
    two_tone = _cluster([CARIBBEAN] * 6 + [SWISS_IVY] * 4)      # 40 %: a colour of the word's own
    assert lt.word_thread(two_tone, CHART, {}) == 0


def test_word_thread_is_off_by_default():
    word = _cluster([CARIBBEAN] * 10 + [SWISS_IVY])
    lt.apply_lettering_thread(word, CHART, PipelineConfig(), {})
    assert word[-1].thread_index == SWISS_IVY
    lt.apply_lettering_thread(word, CHART, PipelineConfig(group_consistent_thread=True), {})
    assert word[-1].thread_index == CARIBBEAN
    assert PipelineConfig().group_consistent_thread is False


def test_a_moved_dark_ink_bean_letter_takes_the_ladder_with_its_word():
    from digitizer_core.beanletters import BEAN_LETTER_KEY
    from digitizer_core.thin_ink import DARK_INK_GROUND_KEY
    word = _cluster([CARIBBEAN] * 10 + [SWISS_IVY])
    word[-1].meta.update({BEAN_LETTER_KEY: [[(0, 0), (1, 1)]], DARK_INK_GROUND_KEY: "Sground", "dark_ink": True})
    lt.word_thread(word, CHART, {})
    assert BEAN_LETTER_KEY not in word[-1].meta and word[-1].meta["lettering_word_unbeaned"]
    # a word whose other letters are beans too keeps the bean
    word = _cluster([CARIBBEAN] * 10 + [SWISS_IVY])
    for r in word:
        r.meta.update({BEAN_LETTER_KEY: [[(0, 0), (1, 1)]], DARK_INK_GROUND_KEY: "Sground"})
    lt.word_thread(word, CHART, {})
    assert BEAN_LETTER_KEY in word[-1].meta
