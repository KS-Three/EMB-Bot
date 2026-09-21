"""Tests for `cfg.classify_area_weighted` — the satin/fill gates pooled over
the distance transform weighted by radius.

Cheap: `_dt_stats` on hand-built polygons, no pipeline run.
"""
import sys
from pathlib import Path

from shapely.geometry import Point, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import stage6_satin as s6  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402


def test_the_flag_defaults_off():
    assert PipelineConfig().classify_area_weighted is False


def test_equal_widths_make_weighting_a_no_op():
    """Where every skeleton pixel carries the same radius, the weighted
    arithmetic reduces to the shipped arithmetic — which is why
    `area_weighted=False` is byte-identical rather than merely close.

    An ANNULUS, not a bar: a bar's skeleton tapers at its caps, so its radii
    are not constant and weighting legitimately moves its mean (9.31 -> 9.73
    on a 40 x 3 mm bar, measured while writing this)."""
    ring = Point(0, 0).buffer(20, quad_segs=64).difference(
        Point(0, 0).buffer(14, quad_segs=64))
    off = s6._dt_stats(ring)
    on = s6._dt_stats(ring, area_weighted=True)
    assert off is not None and on is not None
    assert abs(on.mean - off.mean) < 0.02 * off.mean
    assert abs(on.std - off.std) < 0.05 * off.mean
    assert on.p90_mm == off.p90_mm


def test_a_wide_body_with_a_thin_tail_reads_wider_when_weighted():
    """The defect in one shape: a long thin tail outvotes a wide body by
    pixel COUNT, and the regularity gate reads a shape that is mostly one
    clean width as irregular. Weighted by the area each pixel stands for, the
    body counts for what it is."""
    shape = unary_union([box(0, 0, 20, 8), box(20, 3.5, 60, 4.5)])
    off = s6._dt_stats(shape)
    on = s6._dt_stats(shape, area_weighted=True)
    assert off is not None and on is not None
    assert on.mean > off.mean
    assert on.std / on.mean < off.std / off.mean, "the regularity gate reads cleaner"


def test_the_width_cap_is_never_weighted():
    """MEASURED CORRECTION, 2026-09-16. Weighting `p90` too asks the widest
    part about itself twice: on becker it demoted `S579cb1c2` satin ->
    `dt_p90_cap` (p90 4.96 -> 5.01 against the 5.0 mm cap) and the rope
    border `Sead76620` promoted_ribbon -> dt_irregular, taking the design's
    sewn satin share 0.468 -> 0.193 at 80 mm. The cap is a question about the
    MAXIMUM; only the regularity gate is about the typical width."""
    shape = unary_union([box(0, 0, 20, 8), box(20, 3.5, 60, 4.5)])
    off = s6._dt_stats(shape)
    on = s6._dt_stats(shape, area_weighted=True)
    assert on.p90_mm == off.p90_mm
    assert on.explained == off.explained, "`explained` stays on the swept width"
    assert on.elongation == off.elongation


def test_stage7_passes_the_flag():
    import inspect

    from digitizer_core import stage7_sequence as s7

    assert "area_weighted=cfg.classify_area_weighted" in inspect.getsource(s7)
    for fn in (s6.classify_ribbon, s6.is_satin_candidate, s6._dt_stats):
        assert "area_weighted" in inspect.signature(fn).parameters, fn.__name__


def test_a_weighting_rescue_must_still_be_a_stroke():
    """SCOPED 2026-09-16, on the render rather than on the stitch count.

    Where the weighted reading is what flips a shape into satin, the shape has
    to BE a stroke. Rendered, it often is not: of the ten shapes the flag
    promotes, Fremont's 33.1 mm2 blob (elongation 7.0) and enthusiast's
    19.9 mm2 star (8.1) sew a criss-cross over ground the fill handled
    cleanly, while drone's 14.7 mm2 edge strip (16.8) becomes the satin column
    it wanted to be. Promotions across the three designs go 10 -> 2.

    This star is that shape class: the weighting DOES make it regular --
    cv 0.58 -> 0.45, under the 0.5 gate -- and its elongation 9.4 is under
    the promote path's own bar, so the verdict stays `dt_irregular`.
    """
    from digitizer_core import machine
    from digitizer_core.stage6_satin import _PROMOTE_ELONGATION_MIN, classify_ribbon

    star = unary_union([box(0, 3.2, 9, 4.8), box(3.7, 0, 5.3, 8),
                        Point(4.5, 4).buffer(2.6)])
    plain = classify_ribbon(star, machine.SATIN_MAX_WIDTH_MM, full_metrics=True)
    weighted = classify_ribbon(star, machine.SATIN_MAX_WIDTH_MM,
                               full_metrics=True, area_weighted=True)

    assert plain.reason == "dt_irregular", "the plain gates refuse this shape"
    assert 2.0 * weighted.metrics["dt_std"] < weighted.metrics["dt_mean"],         "the weighting makes it regular -- without the bar it would sew satin"
    assert weighted.metrics["elongation"] < _PROMOTE_ELONGATION_MIN
    assert not weighted.satin and weighted.reason == "dt_irregular"


def test_the_scope_leaves_a_shape_the_plain_reading_already_took():
    """The bar applies ONLY where the weighting flipped the verdict: a shape
    the unweighted gates already pass keeps its satin call, weighted or not,
    however stubby it is."""
    from digitizer_core import machine
    from digitizer_core.stage6_satin import classify_ribbon

    bar = box(0, 0, 14, 2.2)
    plain = classify_ribbon(bar, machine.SATIN_MAX_WIDTH_MM, full_metrics=True)
    weighted = classify_ribbon(bar, machine.SATIN_MAX_WIDTH_MM,
                               full_metrics=True, area_weighted=True)
    assert plain.satin and weighted.satin
    assert weighted.reason == plain.reason
