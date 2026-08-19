"""Shape identity edits (contract v1.5): merge and split.

The other half of the shape-recognition gap `test_shape_overrides.py`'s
`boundary_override` tests closed one side of: that reshapes ONE shape's
outline, this pair changes the SET of shapes. What this file pins, in the
same "cost to the shop if it broke" order that file's own docstring uses:

- a merge actually unions the source geometry into ONE new shape, under a
  NEW id derived from the operation (not geometry), and the merged shape's
  styling seeds from its largest source — never a stale hand-edited boundary
  that no longer describes the new polygon;
- merge's v1 guardrails are real ValueErrors, not silent misbehavior: mixed
  threads, a present hole, or a union that isn't one polygon (the source
  shapes don't actually touch);
- a split actually cuts one shape into exactly two new shapes along the
  given line, preserving an untouched hole and rejecting a line that would
  cross one;
- both are a warn-and-skip for a stale/unknown id, never an error — the
  same posture every other shape-layers key already has;
- both participate in the job cache key;
- and `cfg.merge_shape_ids` / `cfg.split_shapes` really do reach
  `regions.apply_shape_merges` / `apply_shape_splits` from a real
  `digitize()` call, proven against the same real fixture
  `test_shape_overrides.py` uses (not just a synthetic Region list).
"""
from __future__ import annotations

import math

import pytest
from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core.pipeline import digitize
from digitizer_core.regions import (
    Region,
    _merge_shape_id,
    _split_shape_id,
    apply_shape_merges,
    apply_shape_splits,
)
from digitizer_core.warnings_codes import (
    SHAPE_EDIT_UNKNOWN_ID,
    SHAPE_SPLIT_BY_USER,
    SHAPES_MERGED_BY_USER,
)

from .conftest import TESTDATA, cfg

ART = TESTDATA / "logo_whitebg.png"


# --- helpers (mirroring test_shape_overrides.py's own) -----------------------

def bar(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def region(poly: Polygon, sid: str, thread: str = "1000", meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id=sid, polygon=poly, thread_index=0,
                  thread_number=thread, area_mm2=poly.area, meta=m)


# --- merge: the happy path ---------------------------------------------------

def test_merge_unions_two_adjacent_same_thread_shapes_into_one_new_shape():
    a = region(bar(10, 10, cx=0), "A")
    b = region(bar(10, 10, cx=10), "B")   # shares the x=5..15 edge with A
    regs, warns = apply_shape_merges([a, b], [["A", "B"]])

    assert [w["code"] for w in warns] == [SHAPES_MERGED_BY_USER]
    assert warns[0]["groups"] == [{"from": ["A", "B"], "into": _merge_shape_id(["A", "B"])}]
    assert {r.shape_id for r in regs} == {_merge_shape_id(["A", "B"])}
    merged = regs[0]
    assert merged.area_mm2 == pytest.approx(200.0)
    assert merged.polygon.equals(Polygon([(-5, -5), (15, -5), (15, 5), (-5, 5)]))
    assert merged.thread_number == "1000"


def test_merge_id_is_deterministic_from_sorted_source_ids_not_geometry():
    """Argument order must not matter (the ids are sorted before hashing), and
    the id depends only on WHICH shapes, never their polygons — so an
    identical merge request is one stable id/cache key regardless of how the
    two source shapes happen to be positioned."""
    a = region(bar(10, 10, cx=0), "A")
    b = region(bar(10, 10, cx=10), "B")
    forward, _ = apply_shape_merges([a, b], [["A", "B"]])
    backward, _ = apply_shape_merges([a, b], [["B", "A"]])
    assert forward[0].shape_id == backward[0].shape_id == _merge_shape_id(["A", "B"])

    # Same ids, shapes moved further apart (still touching) -> same id.
    a2 = region(bar(10, 10, cx=100), "A")
    b2 = region(bar(10, 10, cx=110), "B")
    moved, _ = apply_shape_merges([a2, b2], [["A", "B"]])
    assert moved[0].shape_id == forward[0].shape_id


def test_merge_seeds_meta_from_the_largest_source_shape_and_drops_boundary_override():
    small = region(bar(10, 10, cx=0), "A", meta={"tier": "run"})
    big = region(
        bar(10, 20, cx=10), "B",
        meta={"tier": "satin", "fill_angle_deg": 30.0,
              "boundary_override": [(5.0, -10.0), (15.0, -10.0), (15.0, 10.0), (5.0, 10.0)]},
    )
    regs, _ = apply_shape_merges([small, big], [["A", "B"]])
    merged = regs[0]
    assert merged.meta.get("tier") == "satin"          # from the larger shape (B, area 200 > 100)
    assert merged.meta.get("fill_angle_deg") == 30.0
    assert "boundary_override" not in merged.meta      # describes B's OLD polygon, not the union


def test_merge_preserves_untouched_regions_and_removes_only_the_consumed_ones():
    a = region(bar(10, 10, cx=0), "A")
    b = region(bar(10, 10, cx=10), "B")
    c = region(bar(6, 6, cx=200), "C")   # far away, not in the merge group
    regs, _ = apply_shape_merges([a, b, c], [["A", "B"]])
    ids = {r.shape_id for r in regs}
    assert "C" in ids
    assert "A" not in ids and "B" not in ids
    assert len(regs) == 2


# --- merge: the v1 guardrails, real ValueErrors ------------------------------

def test_merge_rejects_shapes_that_do_not_touch_or_overlap():
    a = region(bar(5, 5, cx=0), "A")
    b = region(bar(5, 5, cx=100), "B")
    with pytest.raises(ValueError, match="does not touch or overlap"):
        apply_shape_merges([a, b], [["A", "B"]])


def test_merge_rejects_mixed_threads():
    a = region(bar(10, 10, cx=0), "A", thread="1000")
    b = region(bar(10, 10, cx=10), "B", thread="2000")
    with pytest.raises(ValueError, match="mixes threads"):
        apply_shape_merges([a, b], [["A", "B"]])


def test_merge_rejects_shapes_with_a_hole():
    shell = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(4, 4), (6, 4), (6, 6), (4, 6)]
    a = region(Polygon(shell, [hole]), "A")
    b = region(bar(10, 10, cx=10), "B")
    with pytest.raises(ValueError, match="hole"):
        apply_shape_merges([a, b], [["A", "B"]])


def test_merge_requires_at_least_two_distinct_shapes():
    a = region(bar(10, 10, cx=0), "A")
    with pytest.raises(ValueError, match="at least 2 distinct shapes"):
        apply_shape_merges([a], [["A"]])
    # A group naming the same id twice collapses to one distinct id.
    with pytest.raises(ValueError, match="at least 2 distinct shapes"):
        apply_shape_merges([a], [["A", "A"]])


def test_merge_rejects_a_union_under_the_sewability_floor():
    tiny = region(bar(0.05, 0.05, cx=0), "A")
    tiny2 = region(bar(0.05, 0.05, cx=0.05), "B")
    with pytest.raises(ValueError, match="too small to sew"):
        apply_shape_merges([tiny, tiny2], [["A", "B"]])


# --- merge: stale ids warn, never error --------------------------------------

def test_merge_unknown_id_warns_and_skips_the_whole_group_not_a_partial_merge():
    a = region(bar(10, 10, cx=0), "A")
    b = region(bar(10, 10, cx=10), "B")
    regs, warns = apply_shape_merges([a, b], [["A", "ZZZ"]])
    assert {r.shape_id for r in regs} == {"A", "B"}, "nothing merged: the group was skipped whole"
    assert warns[0]["code"] == SHAPE_EDIT_UNKNOWN_ID
    assert warns[0]["ids"] == ["ZZZ"]


def test_merge_no_groups_is_a_no_op():
    a = region(bar(10, 10, cx=0), "A")
    regs, warns = apply_shape_merges([a], [])
    assert regs == [a]
    assert warns == []


# --- split: the happy path ---------------------------------------------------

def test_split_cuts_a_shape_into_two_pieces_of_the_expected_area():
    sq = region(bar(10, 10), "Q")
    line = [[0.0, -6.0], [0.0, 6.0]]   # vertical cut through the middle
    regs, warns = apply_shape_splits([sq], {"Q": line})

    assert [w["code"] for w in warns] == [SHAPE_SPLIT_BY_USER]
    assert len(regs) == 2
    assert sorted(round(r.area_mm2, 3) for r in regs) == [50.0, 50.0]
    assert {r.thread_number for r in regs} == {"1000"}
    ids = {r.shape_id for r in regs}
    assert ids == {_split_shape_id("Q", line, 0), _split_shape_id("Q", line, 1)}
    assert "Q" not in ids


def test_split_piece_ids_are_stable_regardless_of_which_side_is_which():
    """The two pieces are ordered by centroid (leftmost-then-topmost first),
    never by whatever order shapely's split() happens to emit them in — so
    the SAME cut on the SAME shape always names the same two ids."""
    sq = region(bar(10, 10), "Q")
    line = [[0.0, -6.0], [0.0, 6.0]]
    a, _ = apply_shape_splits([sq], {"Q": line})
    b, _ = apply_shape_splits([region(bar(10, 10), "Q")], {"Q": [[0.0, 6.0], [0.0, -6.0]]})
    # Reversing the line's own endpoint order must not change piece identity.
    assert {r.shape_id for r in a} == {r.shape_id for r in b}


def test_split_seeds_meta_from_the_source_onto_both_pieces_and_drops_boundary_override():
    sq = region(bar(10, 10), "Q", meta={
        "tier": "fill", "sew_order": 2,
        "boundary_override": [(-5.0, -5.0), (5.0, -5.0), (5.0, 5.0), (-5.0, 5.0)],
    })
    regs, _ = apply_shape_splits([sq], {"Q": [[0.0, -6.0], [0.0, 6.0]]})
    for r in regs:
        assert r.meta.get("tier") == "fill"
        assert r.meta.get("sew_order") == 2
        assert "boundary_override" not in r.meta


def test_split_preserves_a_hole_the_line_does_not_cross():
    shell = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(4, 7), (6, 7), (6, 9), (4, 9)]   # sits near the top, y in 7..9
    ring = region(Polygon(shell, [hole]), "O")
    # Cut low, at y=2 -- well clear of the hole at y in 7..9.
    regs, _ = apply_shape_splits([ring], {"O": [[-1.0, 2.0], [11.0, 2.0]]})
    assert len(regs) == 2
    holed = [r for r in regs if r.polygon.interiors]
    assert len(holed) == 1
    assert holed[0].polygon.interiors[0].coords[:] and \
        Polygon(shell, [hole]).area - sum(r.area_mm2 for r in regs) == pytest.approx(0.0, abs=1e-6)


# --- split: the v1 guardrails, real ValueErrors ------------------------------

def test_split_rejects_a_line_crossing_a_hole():
    shell = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(4, 4), (6, 4), (6, 6), (4, 6)]
    ring = region(Polygon(shell, [hole]), "O")
    with pytest.raises(ValueError, match="crosses one of this shape's own holes"):
        apply_shape_splits([ring], {"O": [[-1.0, 5.0], [11.0, 5.0]]})


def test_split_rejects_a_zero_length_line():
    sq = region(bar(10, 10), "Q")
    with pytest.raises(ValueError, match="zero length"):
        apply_shape_splits([sq], {"Q": [[1.0, 1.0], [1.0, 1.0]]})


def test_split_rejects_a_line_that_would_divide_a_concave_shape_into_more_than_two_pieces():
    """A "comb" with two teeth: a horizontal cut through both teeth crosses
    the exterior 4 times, not 2, producing 3 pieces — not a valid single
    straight-line split (v1 scope: one line, exactly two results)."""
    comb = region(Polygon([(0, 0), (2, 10), (4, 0), (6, 10), (8, 0), (8, -2), (0, -2)]), "Q")
    with pytest.raises(ValueError, match="exactly two pieces"):
        apply_shape_splits([comb], {"Q": [[-5.0, 5.0], [15.0, 5.0]]})


def test_split_rejects_a_piece_under_the_sewability_floor():
    sq = region(bar(10, 10), "Q")
    # A cut 0.001mm from the edge leaves a sliver (0.01 mm2) far under the
    # sewability floor (machine.RUN_MIN_AREA_MM2 == 0.16 mm2).
    with pytest.raises(ValueError, match="too small to sew"):
        apply_shape_splits([sq], {"Q": [[4.999, -6.0], [4.999, 6.0]]})


# --- split: stale ids warn, never error --------------------------------------

def test_split_unknown_id_warns_and_skips():
    regs, warns = apply_shape_splits([], {"ZZZ": [[0.0, -1.0], [0.0, 1.0]]})
    assert regs == []
    assert warns[0]["code"] == SHAPE_EDIT_UNKNOWN_ID
    assert warns[0]["ids"] == ["ZZZ"]


def test_split_no_lines_is_a_no_op():
    sq = region(bar(10, 10), "Q")
    regs, warns = apply_shape_splits([sq], {})
    assert regs == [sq]
    assert warns == []


# --- the cache seam -----------------------------------------------------------

def test_cache_key_sees_merge_and_split_fields():
    pytest.importorskip("fastapi", reason="service extra not installed")
    from digitizer_service.jobs import content_key

    img = b"pretend png"
    plain = {"target_width_mm": 80.0}
    merged = {**plain, "merge_shape_ids": [["A", "B"]]}
    merged2 = {**plain, "merge_shape_ids": [["A", "C"]]}
    split = {**plain, "split_shapes": {"Q": [[0, -1], [0, 1]]}}

    assert content_key(img, plain) != content_key(img, merged)
    assert content_key(img, merged) != content_key(img, merged2)
    assert content_key(img, plain) != content_key(img, split)
    assert content_key(img, merged) == content_key(img, dict(merged))


# --- real pipeline wiring: cfg.merge_shape_ids / cfg.split_shapes reach ------
# --- regions.apply_shape_merges / apply_shape_splits from a real digitize() -

def test_cfg_merge_shape_ids_reaches_the_real_pipeline_and_rejects_non_adjacent_real_shapes():
    """`digitizer/testdata/logo_whitebg.png` (the same fixture
    `test_shape_overrides.py` uses) has two real "1305" (orange) regions,
    measured 13.8mm apart -- proving the config really does reach
    `apply_shape_merges` from a full `digitize()` call, not just a synthetic
    Region list, and that its adjacency guardrail is enforced on real
    geometry, not just in the unit tests above."""
    base, _ = digitize(ART, cfg())
    orange = [r for r in base.regions if r.thread_number == "1305"]
    assert len(orange) == 2, "fixture assumption: two separate orange regions"
    ids = sorted(r.shape_id for r in orange)

    with pytest.raises(ValueError, match="does not touch or overlap"):
        digitize(ART, cfg(merge_shape_ids=[ids]))


def test_cfg_split_shapes_reaches_the_real_pipeline_and_cuts_a_real_shape_in_two():
    """Splits the fixture's real purple rectangle ("2905") down its own
    vertical midline -- proving `cfg.split_shapes` reaches
    `apply_shape_splits` from a full `digitize()` call and that the two new
    shapes actually reach stage 5-7 and sew (no degenerate stitches)."""
    base, _ = digitize(ART, cfg())
    purple = next(r for r in base.regions if r.thread_number == "2905")
    minx, miny, maxx, maxy = purple.polygon.bounds
    midx = (minx + maxx) / 2
    line = [[midx, miny - 1.0], [midx, maxy + 1.0]]

    result2, plan2 = digitize(ART, cfg(split_shapes={purple.shape_id: line}))

    new_purple = [r for r in result2.regions if r.thread_number == "2905"]
    assert len(new_purple) == 2, "the split replaced one shape with two"
    assert purple.shape_id not in {r.shape_id for r in new_purple}
    assert sum(r.area_mm2 for r in new_purple) == pytest.approx(purple.area_mm2, rel=0.02)

    # The split warning is produced in run_stages (stage 1-4), so it rides
    # result2.warnings, not plan2.warnings (stage 5-7 only).
    assert any(w["code"] == SHAPE_SPLIT_BY_USER for w in result2.warnings)

    for b in plan2.blocks:
        for run in b.runs:
            assert run.points
            for x, y in run.points:
                assert math.isfinite(x) and math.isfinite(y)
