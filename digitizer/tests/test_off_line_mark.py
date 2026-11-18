"""`lettering_columns_off_line_mark` (2026-11-18, built OFF): a text-cluster
member whose centre is outside its cluster's line is not a letter, so the
Column lane refuses it. MFab Hat's pointed mark at the foot of the M's inner V
was tagged into the "AND" cluster and sewed as crossing satin."""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core import PipelineConfig
from digitizer_core.columns import (OFF_LINE_MIN_MATES, is_lettering, off_line_marks,
                                    tag_off_line_marks)
from digitizer_core.regions import Region


def _r(sid, poly, cid="TC1", **meta):
    m = {"text_candidate": True, "text_cluster_id": cid}
    m.update(meta)
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="0",
                  area_mm2=poly.area, meta=m)


def _line(n=4):
    # letters 6.8 mm tall on y 25..31.8
    return [_r(f"L{i}", box(8 * i, 25, 8 * i + 5, 31.8)) for i in range(n)]


def test_default_is_on_since_kent_2026_11_18_and_the_snapshot_and_pre_flip_pin_it_off():
    import json
    from pathlib import Path
    from .conftest import OFF_LINE_MARK_2026_11_18_OFF
    assert PipelineConfig().lettering_columns_off_line_mark is True
    assert PipelineConfig(**OFF_LINE_MARK_2026_11_18_OFF).lettering_columns_off_line_mark is False
    snap = json.loads((Path(__file__).parent / "engine_2026_10_27.json").read_text())
    assert snap["lettering_columns_off_line_mark"] is False


def test_mark_stacked_above_the_line_is_flagged():
    regs = _line() + [_r("M", box(9, 21, 14, 27))]       # centre y 24, line top 25
    assert off_line_marks(regs) == ["M"]


def test_second_line_of_a_cluster_is_not_flagged():
    regs = _line() + [_r(f"S{i}", box(8 * i, 40, 8 * i + 5, 46.8)) for i in range(3)]
    assert off_line_marks(regs) == []


def test_lone_glyph_beside_the_line_but_not_stacked_is_not_flagged():
    regs = _line() + [_r("far", box(80, 10, 85, 16))]    # off the line, over no mate
    assert off_line_marks(regs) == []


def test_letter_on_the_line_is_not_flagged():
    regs = _line() + [_r("N", box(40, 25.5, 45, 32))]
    assert off_line_marks(regs) == []


def test_dot_above_the_line_is_not_flagged():
    regs = _line() + [_r("dot", box(9, 22, 10.5, 23.5))]  # 1.5 mm tall, under half
    assert off_line_marks(regs) == []


def test_needs_enough_mates():
    regs = _line(OFF_LINE_MIN_MATES - 1) + [_r("M", box(9, 21, 14, 27))]
    assert off_line_marks(regs) == []


def test_other_cluster_is_not_a_mate():
    regs = _line() + [_r("M", box(9, 21, 14, 27), cid="TC2")]
    assert off_line_marks(regs) == []


def test_tag_writes_key_only_on_the_mark():
    regs = _line() + [_r("M", box(9, 21, 14, 27))]
    assert tag_off_line_marks(regs) == 1
    assert [r.shape_id for r in regs if r.meta.get("lettering_off_line")] == ["M"]
    assert regs[-1].meta["tier"] == "fill"
    assert all("tier" not in r.meta for r in regs[:-1])


def test_tag_keeps_an_explicit_tier():
    mark = _r("M", box(9, 21, 14, 27), tier="satin")
    regs = _line() + [mark]
    tag_off_line_marks(regs)
    assert mark.meta["tier"] == "satin"


def test_is_lettering_reads_the_flag_only_when_on():
    r = _r("M", box(9, 21, 14, 27), lettering_off_line=True)
    base = dict(lettering_columns_skip_blobs=False)       # the box is a blob; isolate the flag
    assert is_lettering(r, PipelineConfig(lettering_columns_off_line_mark=False, **base)) is True
    assert is_lettering(r, PipelineConfig(lettering_columns_off_line_mark=True, **base)) is False
    plain = _r("N", box(40, 25.5, 45, 32))
    assert is_lettering(plain, PipelineConfig(lettering_columns_off_line_mark=True, **base)) is True


def test_far_dot_like_mark_is_not_flagged():
    # stacked over a mate by x, but 12 mm above it: a tittle whose stem is not in the cluster
    regs = _line() + [_r("tittle", box(9, 6, 12, 11.5))]
    assert off_line_marks(regs) == []


def test_dot_centred_over_a_narrow_stem_is_not_flagged():
    stem = _r("stem", box(40, 27, 42, 32))
    dot = _r("dot", box(40, 20.5, 42, 25.5))              # stem's width, centred, 1.5 mm gap
    assert off_line_marks(_line() + [stem, dot]) == []


# --- `cfg.extra["off_line_mark_single_only"]` (built OFF 2026-11-18) ---------
# The test above reads "stacked on a mate, no row-mate" on axis-aligned boxes,
# which is also every letter down the side of a ring: the DEA seal at 90 mm
# had 11 of its 50 ring letters marked and sewn bold beside their line-mates.

def _column(n=5):
    # letters down the side of a ring: one above the next, 0.6 mm apart, each
    # 1 mm further round (so none is "a dot centred over a stem")
    return [_r(f"V{i}", box(40 + i, 10 + 7.4 * i, 45 + i, 16.8 + 7.4 * i)) for i in range(n)]


def test_letters_down_the_side_of_a_ring_are_marked_today():
    assert len(off_line_marks(_column())) > 1                  # the fault


def test_single_only_marks_none_when_several_read_off_line():
    assert off_line_marks(_column(), single_only=True) == []


def test_single_only_still_marks_the_one_mark_in_a_row():
    regs = _line() + [_r("M", box(9, 21, 14, 27))]
    assert off_line_marks(regs, single_only=True) == ["M"]


def test_single_only_judges_each_cluster_alone():
    regs = (_line() + [_r("M", box(9, 21, 14, 27))]
            + [_r(r.shape_id, r.polygon, cid="TC2") for r in _column()])
    assert off_line_marks(regs, single_only=True) == ["M"]


def test_single_only_is_off_by_default_and_tag_passes_it_through():
    assert not (PipelineConfig().extra or {}).get("off_line_mark_single_only")
    regs = _column()
    assert tag_off_line_marks(regs, single_only=True) == 0
    assert all("lettering_off_line" not in r.meta for r in regs)
