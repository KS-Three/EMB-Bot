"""Stage-level invariants on the committed golden fixtures."""
import numpy as np
import pytest
from shapely.geometry import Point

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_quantize import quantize
from digitizer_core.warnings_codes import (
    ABSORBED_SMALL_SHAPES,
    BACKGROUND_ENCLOSED,
    BACKGROUND_UNCERTAIN,
    DROPPED_SMALL_SHAPES,
)

from .conftest import EXPECTED_THREADS, TESTDATA, codes, cfg

# --- stage 1: background -------------------------------------------------


def test_white_background_is_detected_without_crying_uncertain(whitebg):
    # The common case: a clean logo of several separated elements on white.
    # A global-convex-hull guard fired here (background between elements sits
    # inside the hull) — that false positive is what per-element hulls fixed,
    # and it must stay fixed or the warning becomes noise users learn to skip.
    assert whitebg.background.detected
    assert BACKGROUND_UNCERTAIN not in codes(whitebg)


def test_ring_hole_is_reported_as_enclosed_background(whitebg):
    assert BACKGROUND_ENCLOSED in codes(whitebg)


def test_border_flood_reaching_inside_a_shape_warns(uncertain):
    # A white notch cut in from the border: the flood legitimately eats it,
    # but the user must be told, because that is exactly what happens when
    # white lettering touches a white canvas edge.
    assert BACKGROUND_UNCERTAIN in codes(uncertain)


def test_alpha_and_opaque_variants_agree_on_the_artwork():
    a = prep(TESTDATA / "logo_alpha.png", cfg())
    w = prep(TESTDATA / "logo_whitebg.png", cfg())
    fa, fw = ~a.bg_mask, ~w.bg_mask
    iou = np.logical_and(fa, fw).sum() / np.logical_or(fa, fw).sum()
    assert iou >= 0.98, f"foreground IoU {iou:.4f}"


def test_px_per_mm_follows_the_artwork_not_the_canvas(whitebg):
    x0, _, x1, _ = prep(TESTDATA / "logo_whitebg.png", cfg()).art_bbox
    assert abs((x1 - x0) / whitebg.px_per_mm - 80.0) < 0.01


# --- stage 2: quantization + thread snapping ------------------------------


def test_quantize_finds_the_real_colors_and_no_antialias_phantoms():
    p = prep(TESTDATA / "logo_whitebg.png", cfg())
    q = quantize(p, cfg())
    from digitizer_core.threads import CHART

    numbers = {CHART[t].number for t in q.thread_indices}
    assert set(EXPECTED_THREADS).issubset(numbers)
    # Anti-alias halos against the white background used to survive as pale
    # phantom threads ("Lavender", "Luster"). Nothing near-white may appear:
    # the artwork contains no white.
    for t in q.thread_indices:
        r, g, b = CHART[t].rgb
        assert min(r, g, b) < 200, f"phantom pale thread {CHART[t].number} {CHART[t].name}"


def test_quantize_is_deterministic():
    p = prep(TESTDATA / "logo_whitebg.png", cfg())
    a = quantize(p, cfg())
    b = quantize(p, cfg())
    assert np.array_equal(a.labels, b.labels)
    assert a.thread_indices == b.thread_indices


# --- stage 3: small-region policy ----------------------------------------


def test_subsewable_details_are_absorbed_or_dropped_but_always_reported(whitebg):
    # The fixture has a ~1 mm teal patch on the circle's edge (absorbed into
    # the circle) and an isolated ~1 mm dot (nothing to absorb into: dropped).
    assert ABSORBED_SMALL_SHAPES in codes(whitebg)
    assert DROPPED_SMALL_SHAPES in codes(whitebg)
    teal = [r for r in whitebg.regions if r.thread_number == "4531"]
    assert teal == [], "the sub-sewable teal patch should not survive as a region"


def test_antialias_cleanup_is_not_reported_as_lost_artwork(whitebg):
    # ~30 sliver regions get cleaned up; reporting all of them would train
    # the user to ignore the warnings panel. Only intentional-sized art counts.
    absorbed = next(w for w in whitebg.warnings if w["code"] == ABSORBED_SMALL_SHAPES)
    assert absorbed["count"] < absorbed.get("cleaned_total", absorbed["count"]) + 1
    assert absorbed["count"] <= 3, absorbed


def test_touching_regions_of_different_colors_stay_separate(whitebg):
    purple = [r for r in whitebg.regions if r.thread_number == "2905"]
    orange = [r for r in whitebg.regions if r.thread_number == "1305"]
    assert len(purple) == 1 and len(orange) == 1
    assert purple[0].polygon.intersection(orange[0].polygon).area < 1.0


# --- stage 4: vectorization ----------------------------------------------


def test_ring_keeps_exactly_one_hole(whitebg):
    ring = next(r for r in whitebg.regions if r.thread_number == "3902")
    assert len(ring.polygon.interiors) == 1
    # and the hole is really empty space, not covered by the ring
    hole_center = Point(ring.polygon.interiors[0].centroid)
    assert not ring.polygon.contains(hole_center)


def test_all_polygons_are_valid_and_sewable(whitebg):
    assert whitebg.regions
    for r in whitebg.regions:
        assert r.polygon.is_valid, r.shape_id
        assert not r.polygon.is_empty
        assert r.area_mm2 > 0.5


def test_design_matches_the_requested_size(whitebg):
    assert abs(whitebg.design_size_mm[0] - 80.0) < 0.5


def test_coordinates_are_y_down_and_centered(whitebg):
    # Contract pins y-DOWN. The green bar sits above the purple rectangle in
    # the artwork, so its y must be SMALLER. (EMB-Bot's own engine is +y up —
    # the browser adapter owns that flip, and this test is what makes a
    # silent mirror there detectable.)
    bar = next(r for r in whitebg.regions if r.thread_number == "5510")
    rect = next(r for r in whitebg.regions if r.thread_number == "2905")
    assert bar.polygon.centroid.y < rect.polygon.centroid.y

    xs = [r.polygon.centroid.x for r in whitebg.regions]
    assert min(xs) < 0 < max(xs), "origin should be inside the design, at its center"
