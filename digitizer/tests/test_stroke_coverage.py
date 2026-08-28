"""`tools/letterform_fidelity/stroke_coverage.py` — the dropped-feature lens.

The claim under test is narrow and the fixtures are built to match it: a letter
with a limb the thread never reached must read BAD on the worst stroke while
still reading fine on the mean, because "the mean hides it" is the entire
reason this instrument exists.

Fixtures are synthetic block letters with thread modelled as a buffer around
the paths a digitizer would sew. That is deliberate — the real capture
(`s1_cap.py`) needs a full digitize of `drone_render.png`, which is minutes of
work and pins the numbers to one fixture at one size. The numbers in
`stroke_coverage.py`'s own docstring come from that capture; these tests pin
the BEHAVIOUR.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from shapely.geometry import LineString, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.letterform_fidelity.stroke_coverage import (  # noqa: E402
    mean_coverage, stroke_coverage, worst_stroke,
)

THREAD_HALF_MM = 0.2          # half a 0.4 mm thread, as `s11_iou.py` uses


def block_E() -> "box":
    """Stem plus three arms. Arms are long enough to survive `MIN_STROKE_MM`
    and to be visible as separate medial-axis strokes."""
    return unary_union([
        box(0.0, 0.0, 2.0, 18.0),
        box(2.0, 0.0, 10.0, 2.0),
        box(2.0, 8.0, 10.0, 10.0),
        box(2.0, 16.0, 10.0, 18.0),
    ])


def thread_over(paths: list[list[tuple[float, float]]]):
    return unary_union([LineString(p).buffer(THREAD_HALF_MM, cap_style=1)
                        for p in paths])


def sew_everything(shape) -> "unary_union":
    """Thread covering the whole letter — a perfect sew-out, modelled as the
    shape itself so no sampling gap can make a good letter look bad."""
    return shape.buffer(0.01)


def test_a_fully_sewn_letter_reads_clean():
    E = block_E()
    cov = stroke_coverage(E, sew_everything(E))
    assert cov, "the E should decompose into measurable strokes"
    assert worst_stroke(cov) == pytest.approx(1.0, abs=0.01)


def test_a_dropped_arm_shows_up_on_the_WORST_stroke_not_the_mean():
    """The defect this instrument exists for. DRONE's `E` sews as an "L" and
    bare-fabric coverage calls it fine; the mean is what lets that happen."""
    E = block_E()
    # Everything except the middle arm — an E sewn as a C, in effect.
    sewn = unary_union([
        box(0.0, 0.0, 2.0, 18.0),
        box(2.0, 0.0, 10.0, 2.0),
        box(2.0, 16.0, 10.0, 18.0),
    ]).buffer(0.01)
    cov = stroke_coverage(E, sewn)

    assert worst_stroke(cov) < 0.35, "the unsewn arm should read badly"
    assert mean_coverage(cov) > 0.65, \
        "the mean should still look acceptable — that is the point"


def test_the_gap_between_worst_and_mean_is_the_signal():
    """A letter that is uniformly thin-covered is a different failure from one
    with a missing limb, and the pair has to tell them apart. Uniform damage
    moves both numbers together; local damage opens a gap."""
    E = block_E()
    local = unary_union([
        box(0.0, 0.0, 2.0, 18.0),
        box(2.0, 0.0, 10.0, 2.0),
        box(2.0, 16.0, 10.0, 18.0),
    ]).buffer(0.01)
    cov_local = stroke_coverage(E, local)
    cov_whole = stroke_coverage(E, sew_everything(E))

    gap_local = mean_coverage(cov_local) - worst_stroke(cov_local)
    gap_whole = mean_coverage(cov_whole) - worst_stroke(cov_whole)
    assert gap_local > 0.25, f"local damage should open a gap, got {gap_local:.2f}"
    assert gap_whole < 0.05, f"undamaged letter should have none, got {gap_whole:.2f}"


def test_a_short_junction_stub_is_not_scored_as_a_stroke():
    """`MIN_STROKE_MM` exists because a two-sample stub reports 0% or 100% with
    nothing between, and in a WORST-of measure that noise would swamp the
    signal every time."""
    E = block_E()
    everything = sew_everything(E)
    normal = stroke_coverage(E, everything)
    # A floor above every stroke in the fixture leaves nothing to score.
    none_left = stroke_coverage(E, everything, min_stroke_mm=1000.0)
    assert normal and not none_left
    assert worst_stroke(none_left) is None
    assert mean_coverage(none_left) is None


def test_a_shape_that_will_not_field_fails_open():
    """Same discipline as the modules this borrows from: a degenerate shape
    contributes nothing rather than raising. An instrument that crashes on one
    bad region cannot be run over a corpus."""
    ring = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    from shapely.geometry import Polygon
    degenerate = Polygon(ring, [ring])          # zero area, empty raster
    assert stroke_coverage(degenerate, sew_everything(block_E())) == []


def test_thread_that_misses_the_letter_entirely_reads_zero():
    """The floor of the scale is real, not an artifact of sampling."""
    E = block_E()
    elsewhere = thread_over([[(100.0, 100.0), (110.0, 100.0)]])
    cov = stroke_coverage(E, elsewhere)
    assert cov, "strokes should still be found — it is the thread that is absent"
    assert worst_stroke(cov) == 0.0
    assert mean_coverage(cov) == 0.0


def test_a_finer_step_resolves_a_gap_a_coarse_one_smears():
    """`STEP_MM` is a claim, not decoration. It is pinned as a COMPARISON
    between two step sizes rather than against an absolute number, because the
    absolute is not stable: `_merge_through_junctions` welds limbs, so a 1.5 mm
    break lands on a 31.8 mm chain here and moves the figure only a few points
    either way. What must hold is the direction — sampling finer sees more of a
    break, never less.

    Measured: 95.3% at the documented 0.25 mm step, 96.9% at 1.0 mm. A test
    asserting "< 0.97" would pass on both and pin nothing, which is what the
    first version of this test did."""
    E = block_E()
    sewn = unary_union([
        box(0.0, 0.0, 2.0, 3.0),            # stem, lower part
        box(0.0, 4.5, 2.0, 18.0),           # stem, above a 1.5 mm break
        box(2.0, 0.0, 10.0, 2.0),
        box(2.0, 8.0, 10.0, 10.0),
        box(2.0, 16.0, 10.0, 18.0),
    ]).buffer(0.01)

    fine = worst_stroke(stroke_coverage(E, sewn, step_mm=0.25))
    coarse = worst_stroke(stroke_coverage(E, sewn, step_mm=1.0))
    assert fine < coarse, \
        f"the finer step should resolve more of the break: {fine:.3f} vs {coarse:.3f}"

    # And the step the CALLER asked for is the step used. Direction alone does
    # not pin that: a function quietly scaling every step by 4 preserves the
    # ordering above and fails here. Safe to assert absolutely because this
    # fixture is pure shapely with no platform numerics in it — 0.9531 at both
    # 0.25 and 0.5 mm, 0.9688 at 1.0 mm.
    assert fine == pytest.approx(0.9531, abs=0.005)
