"""The fill-reorder memo: it must be invisible in the output and only in the clock.

`_reorder_for_cover` is the largest runtime bill in the pipeline -- 41.67 s of
owl_kent's 72.42 s edit tail, measured 2026-09-17 -- and almost all of it is
re-done work, because a review edit changes one shape and leaves the rest
byte-identical. The memo exploits exactly that.

Its safety rests on ONE property: both reorders are pure functions of a single
shape's own inputs. `_reorder_for_cover`'s `sewn` accumulator starts at None
and unions only the paths it was handed, so it never sees another shape, the
sew order, or anything global. These tests pin that property and the
consequence -- same bytes, warm or cold -- because if it ever stops holding,
the memo turns into a silent corruption rather than a failure.
"""
import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig
from digitizer_core import stage6_fill as F
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.adapter import plan_to_design


@pytest.fixture(autouse=True)
def _clean_memo():
    F.clear_fill_reorder_memo()
    yield
    F.clear_fill_reorder_memo()


def _art():
    """Two filled blobs on white -- enough shapes to exercise the memo without
    paying for a photograph in a unit test."""
    img = np.full((160, 260, 3), 255, np.uint8)
    img[30:130, 20:120] = (40, 40, 200)
    img[30:130, 140:240] = (30, 160, 60)
    return img


def _plan(gen, **kw):
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=4, **kw)
    return plan_to_design(plan_stitches(finish_generation(gen.fork(), cfg), cfg), name="t")


def test_warm_memo_returns_byte_identical_stitches():
    """The whole point. A second plan of the same design must be the same
    bytes, not merely the same stitch COUNT -- a count matches while every
    coordinate moves."""
    gen = build_generation(_art(), PipelineConfig(target_width_mm=60.0, max_colors=4))
    cold = _plan(gen)
    assert F._reorder_memo_stats["miss"] > 0, "nothing was memoized; the test proves nothing"
    warm = _plan(gen)
    assert F._reorder_memo_stats["hit"] > 0, "second plan did not hit the memo"
    assert cold["stitches"] == warm["stitches"]


def test_an_edit_gets_the_same_bytes_warm_as_cold():
    """The case the memo exists for: one shape edited, the rest served from
    the memo. The result must equal the same edit computed from an empty memo
    -- that is what makes this a cache and not an approximation."""
    gen = build_generation(_art(), PipelineConfig(target_width_mm=60.0, max_colors=4))
    base = _plan(gen)
    sid = next(r["shape"] for r in base["runs"] if r.get("shape") and not r["shape"].startswith("__"))

    warm = _plan(gen, shape_overrides={sid: {"tier": "fill"}})   # memo warm from `base`
    F.clear_fill_reorder_memo()
    cold = _plan(gen, shape_overrides={sid: {"tier": "fill"}})   # same edit, empty memo
    assert warm["stitches"] == cold["stitches"]


def test_a_different_shape_does_not_collide_onto_a_cached_answer():
    """The key must separate two shapes that differ. A collision would hand
    one shape another's stitches -- the failure mode worth a test of its own,
    since it would look like a rendering bug three stages downstream."""
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    wide = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]
    paths = [[(1.0, 1.0), (9.0, 1.0)], [(1.0, 3.0), (9.0, 3.0)], [(1.0, 5.0), (9.0, 5.0)]]
    k1 = F._reorder_key(b"cover", paths, Polygon(sq), Polygon(sq), Polygon(sq), (0.0, 0.0), 3.0, 0.4)
    k2 = F._reorder_key(b"cover", paths, Polygon(wide), Polygon(sq), Polygon(sq), (0.0, 0.0), 3.0, 0.4)
    assert k1 != k2, "a different polygon must not share a key"
    # ...and every scalar is in the key too, not just the geometry.
    k3 = F._reorder_key(b"cover", paths, Polygon(sq), Polygon(sq), Polygon(sq), (0.0, 0.0), 3.0, 0.5)
    assert k1 != k3, "row_mm must be in the key"
    k4 = F._reorder_key(b"cuts", paths, Polygon(sq), Polygon(sq), Polygon(sq), (0.0, 0.0), 3.0, 0.4)
    assert k1 != k4, "the two reorders must not share a key"


def test_the_memo_hands_out_copies():
    """A caller mutating its result must not rewrite the cached answer -- the
    next shape to hit that key would otherwise get corrupted paths."""
    key = b"k" * 32
    F._memoized(key, lambda: [[(0.0, 0.0), (1.0, 1.0)]])
    first = F._memoized(key, lambda: [[(9.0, 9.0)]])
    first[0].append((5.0, 5.0))
    second = F._memoized(key, lambda: [[(9.0, 9.0)]])
    assert second == [[(0.0, 0.0), (1.0, 1.0)]], "the cached list was mutated by a caller"


def test_the_memo_is_bounded_by_points_not_only_entries():
    """An entry-count cap is not a memory bound: one dense fill can be
    thousands of times bigger than one small shape."""
    F.clear_fill_reorder_memo()
    big = [[(float(i), float(i)) for i in range(2000)]]
    for n in range(60):
        F._memoized(bytes([n]) * 32, lambda: big)
    assert F._reorder_memo_points <= F._REORDER_MEMO_MAX_POINTS
    assert len(F._REORDER_MEMO) <= F._REORDER_MEMO_MAX
