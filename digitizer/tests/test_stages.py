"""Stage-level invariants on the committed golden fixtures."""
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import run_stages
from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_quantize import quantize
from digitizer_core.warnings_codes import (
    ABSORBED_SMALL_SHAPES,
    BACKGROUND_ABSENT,
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
    """Outcome preserved (still unstitched by default, warning still fires),
    mechanism changed (2026-08-04): the ring's donut hole is no longer
    quietly folded into `bg` and excluded before it can become a Region —
    it is now a REAL, tagged Region that a review screen could restore.
    See docs/superpowers/plans/2026-08-04-enclosed-background-restore-
    design.md.
    """
    assert BACKGROUND_ENCLOSED in codes(whitebg)

    enclosed = [r for r in whitebg.regions if r.meta.get("enclosed_background")]
    assert len(enclosed) == 1, "the ring's hole should be exactly one tagged region"
    ring_hole = enclosed[0]
    assert ring_hole.meta["stitched"] is False, "unstitched by default"

    ring = next(r for r in whitebg.regions if r.thread_number == "3902")
    # The hole sits inside the ring's own OUTER shell (ignore the ring's own
    # hole when testing this — the point under test is exactly that hole's
    # centroid), same relationship the old "it's a literal polygon hole"
    # mechanism guaranteed geometrically.
    ring_shell = Polygon(ring.polygon.exterior)
    assert ring_shell.buffer(0.5).contains(ring_hole.polygon.centroid)

    # And it must actually be excluded from what gets stitched by default.
    from digitizer_core import plan_stitches
    from .conftest import cfg as _cfg

    plan = plan_stitches(whitebg, _cfg(garment_id="left_chest"))
    stitched_shape_ids = {r.shape_id for _b, r in plan.iter_runs()}
    assert ring_hole.shape_id not in stitched_shape_ids


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


def test_full_bleed_art_keeps_all_of_itself():
    # Measured 2026-08-11 under the enclosed-regions semantics (c1b9e35):
    # this fixture has no background at all, and stage 1 invented one out of
    # a crimson band of its own ramp that happens to touch the border — 6.3%
    # of the image flooded as background outright, another 19.7% reported as
    # enclosed "holes" and unstitched by default. A quarter of the artwork
    # never sewn, on exactly the art the gradient tier exists to serve.
    p = prep(TESTDATA / "photo" / "repro_gradient_white_icon.png", cfg())
    assert not p.bg_mask.any(), f"{int(p.bg_mask.sum())} px still called background"
    got = {w["code"] for w in p.warnings}
    assert BACKGROUND_ABSENT in got
    assert BACKGROUND_ENCLOSED not in got, "there are no holes in art with no background"
    assert p.enclosed_mask is None


def test_tight_crop_pale_subject_survives_stage1():
    # The snowy-owl failure (2026-08-11): a pale subject fills a tight
    # portrait crop on a slightly-different pale wall. The subject dominates
    # the border ring (82.7% on this fixture), so _dominant_border_color
    # picks the SUBJECT's color, the ring agreement passes the
    # BACKGROUND_ABSENT bar (0.827 >= 0.75), and the flood deletes the
    # subject's whole body while the actual wall stays "foreground".
    # BACKGROUND_UNCERTAIN's intrusion guard never fires because the
    # surviving foreground is only wall slivers whose hulls the flood does
    # not enter. The rival-ring-color guard is what must catch this: the
    # wall shows through as a second coherent border color (17.3% of the
    # ring vs <= 2.1% measured on every real-background fixture).
    p = prep(TESTDATA / "photo" / "tight_crop_pale_subject.png", cfg())
    assert not p.bg_mask.any(), (
        f"{int(p.bg_mask.sum())} px flooded as background — the subject's body"
    )
    uncertain = [w for w in p.warnings if w["code"] == BACKGROUND_UNCERTAIN]
    assert uncertain and uncertain[0].get("reason") == "subject_dominated_border"
    assert BACKGROUND_ENCLOSED not in {w["code"] for w in p.warnings}


def test_tight_crop_pale_subject_survives_digitization():
    # End to end: the subject's body must come out the other side as sewable
    # regions, not vanish into the background mask. The subject occupies
    # ~86% of the frame; if it flooded out, the surviving regions (wall
    # slivers, eyes, beak) could never cover more than a third of the design.
    r = run_stages(TESTDATA / "photo" / "tight_crop_pale_subject.png", cfg())
    assert not r.background.detected
    design_area = r.design_size_mm[0] * r.design_size_mm[1]
    covered = sum(reg.area_mm2 for reg in r.regions)
    assert covered >= 0.6 * design_area, (
        f"regions cover {covered:.0f} of {design_area:.0f} mm^2 — subject lost"
    )


@pytest.mark.parametrize(
    "fixture",
    [
        "logo_whitebg.png",
        "logo_alpha.png",
        "bg_uncertain.png",
        "ribbon_curve.png",
        "photo/enthusiast_logo.png",
        "photo/drone_render.png",
        "photo/region_blobs.png",
        "photo/gradient_ramp_linear.png",
        "photo/gradient_ramp_radial.png",
    ],
)
def test_the_guards_leave_real_backgrounds_alone(fixture):
    # The regression net for the whole flat lane. Every fixture here has a
    # real background — the two ramps included, which are ramps WITH padding
    # (art bbox 70,70..930,580 inside a 1000x650 canvas), and are exactly the
    # case a "gradients have no background" shortcut would have broken. The
    # rival guard has margin here too: worst measured rival fraction is
    # drone_render's 0.021 against the 0.10 default.
    p = prep(TESTDATA / fixture, cfg())
    got = {w["code"] for w in p.warnings}
    assert BACKGROUND_ABSENT not in got
    assert not any(
        w.get("reason") == "subject_dominated_border" for w in p.warnings
    )
    assert p.bg_mask.any()


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

    # The ring's donut hole (BACKGROUND_ENCLOSED) is quantized separately
    # from the design's own foreground (2026-08-04) and is legitimately
    # near-white — it IS the enclosed white icon area, not an anti-alias
    # halo. Exclude whichever label(s) it landed on before checking the
    # design's OWN colors below.
    enclosed_labels = (
        set(np.unique(q.labels[p.enclosed_mask]))
        if p.enclosed_mask is not None
        else set()
    )

    # Anti-alias halos against the white background used to survive as pale
    # phantom threads ("Lavender", "Luster"). Nothing near-white may appear
    # among the design's OWN colors: the artwork's own foreground contains
    # no white.
    for label, t in enumerate(q.thread_indices):
        if label in enclosed_labels:
            continue
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


def test_small_enclosed_hole_is_not_absorbed_into_its_enclosing_letter():
    """Regression, 2026-08-06: `resolve_small_regions` used to treat ANY
    small region as ordinary segmentation noise and absorb it into whichever
    neighbor shared the most boundary — including a small but completely
    real enclosed hole (`Prep.enclosed_mask`), whose only possible neighbor
    IS the shape that encloses it. On the real benchmark fixture this
    silently filled in the "A" in ENTHUSIAST's triangular counter before
    stage 4 (`vectorize`/`tag_enclosed_background`) ever got a chance to see
    it as a real, separately-tagged Region — `tag_enclosed_background`'s
    overlap machinery was fully wired and working for every OTHER enclosed
    feature in this corpus (the donut-ring fixture above), but had nothing
    left to find for this one.

    Confirmed by direct measurement before this fix: `Prep.enclosed_mask`
    correctly finds a 2.08 mm² component at the "A"'s location (comfortably
    real, not noise — well above `cfg.min_detail_mm`'s sewable floor), yet
    the final "A" Region carried ZERO interior rings.
    """
    result = run_stages(TESTDATA / "photo" / "enthusiast_logo.png", cfg(target_width_mm=90.0))

    # The "A" in ENTHUSIAST is the only wordmark letter with a real enclosed
    # counter. Found by its own polygon carrying an interior ring, not by
    # shape_id: restoring the hole legitimately changes the polygon's
    # content hash, so a hardcoded id would be re-deriving this fix's own
    # effect instead of testing for it. `rescued_small_shape`/
    # `enclosed_background` regions are excluded so this can't accidentally
    # match a subline glyph (several already carry their own direct holes,
    # unaffected by this bug — see `test_textcluster.py`) or the hole
    # Region itself.
    holed = [r for r in result.regions
             if not r.meta.get("rescued_small_shape")
             and not r.meta.get("enclosed_background")
             and r.polygon.interiors]
    assert len(holed) == 1, (
        f"expected exactly one non-subline letter with a real interior ring "
        f"(the 'A'); got {len(holed)}"
    )
    a_region = holed[0]
    assert a_region.area_mm2 == pytest.approx(a_region.polygon.area)

    # And the hole pixels must have survived as their own tagged, unstitched
    # Region — not merely absent from the count above — per
    # `tag_enclosed_background`'s contract (same assertion shape as
    # `test_ring_hole_is_reported_as_enclosed_background`).
    a_shell = Polygon(a_region.polygon.exterior).buffer(0.5)
    enclosed_in_a = [r for r in result.regions
                     if r.meta.get("enclosed_background")
                     and a_shell.contains(r.polygon.centroid)]
    assert len(enclosed_in_a) == 1
    hole_region = enclosed_in_a[0]
    assert hole_region.meta["stitched"] is False
    assert hole_region.area_mm2 > 1.0, "the real counter, not a noise scrap"


def test_antialias_cleanup_is_not_reported_as_lost_artwork(whitebg):
    # ~30 sliver regions get cleaned up; reporting all of them would train
    # the user to ignore the warnings panel. Only intentional-sized art counts.
    absorbed = next(w for w in whitebg.warnings if w["code"] == ABSORBED_SMALL_SHAPES)
    assert absorbed["count"] < absorbed.get("cleaned_total", absorbed["count"]) + 1
    assert absorbed["count"] <= 3, absorbed


def test_touching_regions_of_different_colors_stay_separate(whitebg):
    # The rectangles are the LARGEST region of each thread, not the only one:
    # the fixture's orange layer also holds a 1 mm dot that the run-tier
    # rescue now keeps (it used to be dropped without a trace).
    purple = max((r for r in whitebg.regions if r.thread_number == "2905"),
                 key=lambda r: r.area_mm2)
    orange = max((r for r in whitebg.regions if r.thread_number == "1305"),
                 key=lambda r: r.area_mm2)
    assert purple.polygon.intersection(orange.polygon).area < 1.0


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
