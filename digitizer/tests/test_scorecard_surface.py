"""The pro-parity scorecard's visible-surface model must respect sew order.

`surface()` decides which thread the customer actually SEES at each pixel, and
`agree` -- a headline parity number -- is the fraction of visible pixels where
our surface matches the pro's. It used to be handed colour-keyed buckets and
paint each at the position of its EARLIEST block, so a colour that recurs later
in the sequence was painted at its first appearance and then buried by whatever
ran between.

That is the "outline last" build: black fill, red, then a black outline sewn ON
TOP of the red. Ordinary in the professional corpus. The grader was scoring us
against a picture of the pro's design that the pro's own customer would never
see -- and, worse, doing the same to ours, so a genuinely correct outline-last
result could be marked wrong and a genuinely buried one marked right.

Found by a sibling-pattern sweep 2026-08-26: the same bug shape as
app/src/lib/preview.js drawThreads, which had it in both draw paths.

These tests use colour_runs and surface directly rather than a rendered
fixture -- the ordering rule is the whole content of the fix, and a raster
fixture would test numpy more than it tests this.
"""
import numpy as np
import pytest

from tools.pro_parity.scorecard import colour_runs, surface


BLACK = (0, 0, 0)
RED = (200, 20, 20)


def blocks(*specs):
    return [{"block": i, "rgb": rgb} for i, rgb in enumerate(specs)]


def test_colour_runs_splits_a_recurring_colour_into_separate_runs():
    # black, red, black -- the outline-last build.
    runs = colour_runs(blocks(BLACK, RED, BLACK))
    assert runs == [(BLACK, [0]), (RED, [1]), (BLACK, [2])]
    # The old colour-keyed grouping produced {black: [0, 2], red: [1]}, which
    # cannot say that the second black comes after the red.


def test_colour_runs_keeps_a_split_word_together():
    # Prep legitimately splits one word across adjacent blocks. Those ARE
    # consecutive, so they stay one run -- the property colour_groups' docstring
    # cares about is preserved, without the one it accidentally also had.
    runs = colour_runs(blocks(BLACK, BLACK, BLACK, RED))
    assert runs == [(BLACK, [0, 1, 2]), (RED, [3])]


def test_colour_runs_handles_the_degenerate_inputs():
    assert colour_runs([]) == []
    assert colour_runs([{"block": 0}]) == [((0, 0, 0), [0])]  # missing rgb -> black


def test_surface_paints_later_runs_over_earlier_ones():
    # surface() rasterises real segments, so drive the ordering directly with a
    # stub raster: each block id paints one column.
    import tools.pro_parity.scorecard as sc

    W = 3
    calls = []

    def fake_raster(segs, bb, only_blocks=None):
        calls.append(sorted(only_blocks))
        m = np.zeros((1, W), bool)
        for b in only_blocks:
            m[0, :] = True  # every run covers the whole strip -> last one wins
        return m

    monkey = pytest.MonkeyPatch()
    monkey.setattr(sc, "raster", fake_raster)
    monkey.setattr(sc, "solid", lambda m: m)
    monkey.setattr(sc, "_grid", lambda bb, res: (W, 1))
    try:
        lab = sc.surface(None, None, [(0, [0]), (1, [1]), (0, [2])])
    finally:
        monkey.undo()

    # Colour 0 recurs LAST, so it is what shows.
    assert lab.tolist() == [[0, 0, 0]]
    # ...and it really was painted three times, in order -- not merged into two.
    assert calls == [[0], [1], [2]]


def test_surface_leaves_unpainted_pixels_as_bare_fabric():
    import tools.pro_parity.scorecard as sc

    monkey = pytest.MonkeyPatch()
    monkey.setattr(sc, "raster", lambda *a, **k: np.zeros((1, 2), bool))
    monkey.setattr(sc, "solid", lambda m: m)
    monkey.setattr(sc, "_grid", lambda bb, res: (2, 1))
    try:
        lab = sc.surface(None, None, [(0, [0])])
    finally:
        monkey.undo()
    assert lab.tolist() == [[-1, -1]]
