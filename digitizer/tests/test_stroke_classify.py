"""`stage6_satin.classify_strokes` — the per-stroke DT reading, which nothing
in the pipeline consults.

PR 2 of `docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`.
`classify_ribbon` pools the distance transform over a whole region's skeleton
and returns one bool, so a branchy letterform — wide at its junctions, thin
along its arms — can fail `2 sigma < mu` as a unit while every arm of it is a
clean ribbon. These tests pin the per-stroke reading's arithmetic and, more
importantly, the two invariants a routing change would have to keep.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_satin import (
    _STROKE_AREA_FRAC_MIN,
    classify_ribbon,
    classify_strokes,
)
from tests.conftest import TESTDATA

BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])
T_SHAPE = Polygon([(0, 0), (20, 0), (20, 3), (11.5, 3),
                   (11.5, 20), (8.5, 20), (8.5, 3), (0, 3)])
PLUS = Polygon([(9, 0), (12, 0), (12, 9), (21, 9), (21, 12), (12, 12),
                (12, 21), (9, 21), (9, 12), (0, 12), (0, 9), (9, 9)])
BLOB = Point(0, 0).buffer(8.0)


def _cv(stats) -> float:
    return (stats.std / stats.mean) if stats and stats.mean else 0.0


def test_a_shape_that_is_one_stroke_reads_the_same_either_way():
    """The anti-drift pin.

    The two per-stroke gates are re-expressed rather than shared with
    `classify_ribbon`, because this module's shipped path must stay
    byte-identical while the per-stroke code is inert. That duplication is
    only safe if something notices when the two readings diverge, and a plain
    bar is the case where they must agree by construction: one stroke, so the
    pooled reading and the per-stroke reading are computed over the same
    skeleton.
    """
    v = classify_strokes(BAR, machine.SATIN_MAX_WIDTH_MM)
    assert len(v.strokes) == 1, f"a bar is one stroke, got {len(v.strokes)}"
    assert v.region.reason == "satin"
    assert v.strokes[0].reason == v.region.reason
    assert v.strokes[0].satin is v.region.satin


def test_the_partition_gives_back_exactly_the_polygons_own_area():
    """A filled raster carries a half-pixel skin all round, so the pixel count
    runs high by about `perimeter / (2 * scale)` — on the bar below that is
    7.2 mm2 against 120, a 6% inflation that would land straight in every
    `explained`. `_partition_area_mm2` normalizes it away, and this is what
    says so.
    """
    for poly in (BAR, T_SHAPE, PLUS):
        v = classify_strokes(poly, machine.SATIN_MAX_WIDTH_MM)
        assert v.strokes, "fixture must decompose into at least one stroke"
        assert v.area_mm2 == pytest.approx(poly.area, rel=1e-9)
        assert sum(s.area_mm2 for s in v.strokes) == pytest.approx(poly.area,
                                                                   rel=1e-9)


@pytest.mark.parametrize("name,poly", [("T_SHAPE", T_SHAPE), ("PLUS", PLUS)])
def test_pooling_over_a_junction_costs_regularity_that_the_strokes_have(name, poly):
    """The whole premise, on a shape simple enough to reason about.

    A branchy shape's skeleton runs through a junction where the inscribed
    circle is much larger than it is along the arms, so the POOLED radii
    spread. Every arm on its own is a constant-width ribbon. The claim is not
    that the region flips — these two are regular enough to pass either way —
    but that the pooled cv is strictly worse than the worst arm's.
    """
    v = classify_strokes(poly, machine.SATIN_MAX_WIDTH_MM)
    assert len(v.strokes) >= 2, f"{name} must decompose into arms"
    region_cv = v.region.metrics["dt_cv"]
    worst_stroke_cv = max(_cv(s.stats) for s in v.strokes)
    assert region_cv > worst_stroke_cv, (
        f"{name}: pooled cv {region_cv:.3f} should exceed every arm's, "
        f"worst arm {worst_stroke_cv:.3f}")


def test_the_p90_cap_stays_per_stroke_and_still_refuses():
    """DOCTRINE's measured negative is what happens if a too-wide stroke sews
    anyway: `_rail_points`' per-station guard holds each cross to the cap and
    leaves bare cloth down the middle. So the cap must survive the split, not
    be averaged away by thin neighbours.

    A wide bar with a thin one hanging off it: the wide arm must read
    `dt_p90_cap` on its own, and the region must not reach the area fraction.
    """
    wide = Polygon([(0, 0), (40, 0), (40, 8), (0, 8)])
    tee = wide.union(Polygon([(18, 8), (22, 8), (22, 30), (18, 30)]))
    v = classify_strokes(tee, machine.SATIN_MAX_WIDTH_MM)
    capped = [s for s in v.strokes if s.reason == "dt_p90_cap"]
    assert capped, f"the 8 mm arm must blow a 5 mm cap: {[s.reason for s in v.strokes]}"
    assert max(s.area_mm2 for s in capped) > 0.4 * v.area_mm2, \
        "the capped arm is the bulk of this shape and must dominate the fraction"
    assert v.passing_frac < _STROKE_AREA_FRAC_MIN


def test_a_shape_with_no_strokes_is_an_empty_answer_not_a_refusal(monkeypatch):
    """`classify_ribbon` names this case `dt_degenerate` and reads it as "the
    DT has no opinion", never as a rejection. The per-stroke path has to say
    the same thing, and an empty stroke list with `passing_frac` 0.0 is how:
    a caller must go read `region.reason`, not treat 0.0 as a no.

    Forced rather than carved, and that is the finding: `_rasterize` RAISES
    resolution for a thin shape (`need = max(6.0, 8.0 / wall)`), so shapes
    that ought to be too small to skeletonize get a bigger raster instead of
    an empty one. Measured 2026-09-05: a 0.3 x 0.05 mm speck comes back with
    one stroke, and so do a 200 x 0.01 mm sliver and a 300 x 0.005 mm one. No
    committed fixture reaches this branch, so it is entered directly — the
    alternative is an untested guard.
    """
    from digitizer_core import stage6_satin

    monkeypatch.setattr(stage6_satin, "extract_strokes",
                        lambda poly, **kw: ([], 0.0, None))
    v = classify_strokes(BAR, machine.SATIN_MAX_WIDTH_MM)
    assert v.strokes == []
    assert v.area_mm2 == 0.0
    assert v.passing_frac == 0.0
    assert v.region.reason == "satin", "the region verdict is where the answer is"


def test_a_blob_is_not_rescued_by_splitting_it():
    """The failure mode a per-stroke rung could plausibly introduce: chopping
    a compact shape into arms until each arm looks like a ribbon. A disc has
    no arms — it skeletonizes to a point or a short spur — so it must not come
    back with a passing area fraction.
    """
    v = classify_strokes(BLOB, machine.SATIN_MAX_WIDTH_MM)
    assert not v.region.satin, "a disc is not a ribbon"
    assert v.passing_frac < _STROKE_AREA_FRAC_MIN, (
        f"a disc must not pass on its strokes: frac {v.passing_frac:.2f} from "
        f"{[(s.reason, round(s.area_mm2, 1)) for s in v.strokes]}")


def test_the_starburst_refuses_on_its_own_strokes_with_no_extra_guard():
    """The invariant the plan flagged (§4), and the measurement that settled
    how to keep it.

    `photo/enthusiast_logo.png`'s `Sff37b029` — the emblem's 4-point star —
    reads `explained` 0.974 at elongation 8.3, so the plan expected the
    per-stroke path to need `_PROMOTE_ELONGATION_MIN` carried onto it to keep
    refusing. It does not: measured 2026-09-05, the star's two arms are
    themselves irregular (cv 0.55 and 0.52, both past the 0.50 the gate sits
    at), so the area fraction comes back 0.00 with no extra guard at all.

    The margin is thin — 9% and 4% past the gate — which is why this is a test
    and not a remark. If a segmentation change moves the star's arms under
    0.50, a per-stroke rung WOULD start sewing a starburst as satin, and this
    is where that gets caught.
    """
    result, _plan = digitize(TESTDATA / "photo/enthusiast_logo.png",
                             PipelineConfig(target_width_mm=90.0))
    by_id = {r.shape_id: r for r in result.regions}
    assert "Sff37b029" in by_id, \
        f"benchmark fixture regions moved: Sff37b029 not in {sorted(by_id)}"

    v = classify_strokes(by_id["Sff37b029"].polygon, machine.SATIN_MAX_WIDTH_MM)
    assert not v.region.satin, "the shipped call already refuses the star"
    assert v.passing_frac < _STROKE_AREA_FRAC_MIN, (
        f"a per-stroke rung must not rescue a starburst: frac "
        f"{v.passing_frac:.2f} from "
        f"{[(s.reason, round(_cv(s.stats), 3)) for s in v.strokes]}")


def test_the_regularity_reading_does_not_move_when_the_artwork_is_scaled():
    """`cv` is a ratio, so scaling a polygon must not change it — and the
    check matters because Becker's whole region set sits within +-0.10 of the
    0.50 gate, where any drift decides verdicts.

    Measured on Becker's own largest regions: cv moves by under 0.02 across a
    1.25x scale while `p90` scales linearly and takes shapes over the machine
    cap, which is the one verdict change scaling is ALLOWED to cause.
    """
    for poly in (BAR, T_SHAPE, PLUS):
        small = classify_strokes(poly, machine.SATIN_MAX_WIDTH_MM)
        big_poly = affinity.scale(poly, 1.25, 1.25, origin="centroid")
        big = classify_strokes(big_poly, machine.SATIN_MAX_WIDTH_MM)
        assert len(small.strokes) == len(big.strokes), \
            "a scaled shape must decompose the same way"
        for a, b in zip(small.strokes, big.strokes):
            assert _cv(a.stats) == pytest.approx(_cv(b.stats), abs=0.05), \
                f"cv must be scale-free: {_cv(a.stats):.3f} vs {_cv(b.stats):.3f}"
            # p90 quantizes to the raster: a radius is an integer pixel
            # count, so a doubled radius moves in steps of 2 / scale
            # (0.33 mm at the 6 px/mm base). The bar goes 2.33 -> 2.67 where
            # exact scaling wants 2.92 — one pixel short, not a scale error.
            assert b.stats.p90_mm > a.stats.p90_mm, \
                "p90 is a length and must grow with the artwork"
            assert b.stats.p90_mm == pytest.approx(1.25 * a.stats.p90_mm,
                                                   abs=2.0 / 6.0), \
                "p90 must scale to within one raster pixel of the artwork"


def test_nothing_in_the_pipeline_consults_the_per_stroke_path():
    """This PR is deliberately inert: the flag, the wiring and the flip are
    later slices. If a future change starts calling `classify_strokes` from
    the engine, that is a decision to make on purpose — with the scorecard
    recapture and the `ribbon_stability` re-run the plan (§4, §7) requires —
    not a thing to discover from a moved golden.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "digitizer_core"
    callers = []
    for p in sorted(root.glob("*.py")):
        if p.name == "stage6_satin.py":
            continue
        if "classify_strokes(" in p.read_text():
            callers.append(p.name)
    assert callers == [], f"classify_strokes is wired into {callers}"
