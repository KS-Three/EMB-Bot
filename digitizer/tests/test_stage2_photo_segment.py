"""Stage 2 (photo path) — SLIC + RAG region former.

`docs/superpowers/plans/2026-08-02-photo-digitizing-step4-region-former.md`,
"## Tests". Five tests: region-forming beats naive per-pixel clustering on a
soft edge, the min-area floor absorbs a deliberately tiny sliver,
determinism, full-pipeline integration through `run_stages()`, and the flat/
gradient lanes staying byte-identical to the pre-change golden (reusing
`test_flat_lane_byte_identical.py`'s own fixture list and snapshot helper
rather than re-implementing it — that file is the record of truth and is
not touched by this change).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.stage0_classify import classify
from digitizer_core.stage1_prep import prep
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.stage2_photo_segment import (
    split_tonal_regions,
    AREA_RATIO_MERGE_FACTOR,
    AREA_RATIO_MIN_SMALL_PX,
    AREA_RATIO_PROTECT_THRESH,
    BOUNDARY_CONTRAST_HARD_LAB,
    BOUNDARY_CONTRAST_MERGE_FACTOR,
    BOUNDARY_CONTRAST_MIN_SMALL_FRAC,
    BOUNDARY_CONTRAST_MIN_SMALL_PX,
    MERGE_DELTAE00_THRESH,
    segment,
)
from digitizer_core.stage2_quantize import quantize
from digitizer_core.stage3_segment import ClassicalSegmenter
from digitizer_core.threads import chart_for
from digitizer_core.warnings_codes import ABSORBED_SMALL_SHAPES, PHOTO_SEGMENT_REGION_COUNT

from .test_flat_lane_byte_identical import GOLDEN, _snapshot

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
PHOTO_DIR = TESTDATA / "photo"
FIXTURE = PHOTO_DIR / "region_blobs.png"


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- 1. Region-forming beats naive per-pixel clustering on a soft edge ------


def test_region_forming_beats_naive_clustering_on_soft_edges():
    cfg = _cfg()
    p = prep(FIXTURE, cfg)

    q = segment(p, cfg)
    region_count = len(q.thread_indices)
    # A tight, small range: proof the hierarchical merge actually
    # consolidated SLIC's raw output (which measures well over a thousand
    # superpixels on this fixture) rather than just relabeling it.
    assert 0 < region_count < 15, f"expected consolidated regions, got {region_count}"

    # The naive per-pixel path (today's flat-art quantizer) run on the same
    # foreground: connected-component count after its own color clustering,
    # with no spatial merging step at all.
    naive_q = quantize(p, cfg)
    naive_masks = ClassicalSegmenter().segment(naive_q, p, cfg)
    assert len(naive_masks) > 5 * region_count, (
        f"naive clustering only produced {len(naive_masks)} components against "
        f"{region_count} SLIC+RAG regions — the fixture's grain isn't tripping "
        "per-pixel dithering the way this test expects"
    )

    # Cleanliness proxy: a region eroded by 1px should still cover most of
    # its own area. Speckle (salt-and-pepper, no pixel more than 1 away from
    # a differently-labeled one) collapses to near-nothing under erosion; a
    # clean, solid region loses only its outer 1px rim.
    #
    # Below-floor labels are exempt (2026-08-04, when this fixture's own
    # tiny `Prep.enclosed_mask` — 16px, an incidental artifact of this
    # synthetic image, not something this test is about — started getting
    # its own trailing label block, quantized via the same, deliberately
    # un-floored `stage2_quantize._quantize_population` `quantize()` itself
    # has always used for enclosed content, see `segment`'s own enclosed-
    # population comment). Both `quantize()` and `segment()` rely on the
    # CALLER (`pipeline.run_stages`'s own downstream `resolve_small_regions`
    # pass over the whole `Quant`) to absorb an enclosed population's own
    # sub-floor slivers — this test calls `segment()` directly, bypassing
    # that pass, so a label this small was never going to represent
    # anything a real digitize job actually keeps; skipping it here tests
    # SLIC+RAG's OWN region quality (what this test is for) without also
    # re-asserting an absorption guarantee `resolve_small_regions` already
    # owns and is tested elsewhere.
    min_area_px = (cfg.min_detail_mm * p.px_per_mm) ** 2
    for label in range(region_count):
        mask = (q.labels == label).astype(np.uint8)
        area = int(mask.sum())
        assert area > 0
        if area < min_area_px:
            continue
        eroded = int(cv2.erode(mask, np.ones((3, 3), np.uint8)).sum())
        assert eroded >= 0.5 * area, (
            f"region {label} reads as speckle after erosion ({eroded}/{area} px survived)"
        )


# --- 2. Min-area floor absorbs a deliberately tiny sliver -------------------


def _sliver_image() -> np.ndarray:
    """Two big flat-ish blocks (BGR) plus a deliberately tiny sliver of a
    third, unrelated color straddling the boundary between the red block
    and open background — small enough that no cfg.min_detail_mm floor will
    ever consider it a real detail, and a different enough color that the
    RAG merge step (step 3) would NOT have absorbed it on color grounds
    alone. Only the min-area floor (step 4, color-agnostic: force-merge
    into the longest shared boundary) explains it disappearing.

    Sized deliberately larger than a single-digit-pixel speck: SLIC itself
    (not just the merge/floor steps) already discards anything much smaller
    than its own superpixel granularity by folding it into a neighboring
    superpixel before a RAG node for it ever exists — which would prove
    nothing about THIS module's min-area floor specifically. An 18x18px
    sliver survives as its own SLIC segment (and its own post-merge region)
    at this fixture's resolution, so its disappearance is attributable to
    `resolve_small_regions`, not SLIC's internal cleanup."""
    h, w = 220, 320
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.rectangle(img, (20, 20), (150, 190), (60, 60, 200), -1)    # red block
    cv2.rectangle(img, (160, 20), (290, 190), (200, 60, 60), -1)   # blue block
    cv2.rectangle(img, (140, 90), (158, 108), (60, 200, 60), -1)   # 18x18px green sliver
    return img


def test_min_area_floor_absorbs_a_tiny_sliver():
    # A smaller target_width_mm than the other tests here (still a
    # perfectly ordinary embroidery size) — raises px_per_mm, and with it
    # the min-area floor in PIXEL terms, without changing SLIC's own
    # superpixel granularity (fixed by the canvas's pixel dimensions). That
    # headroom is what lets the sliver above be simultaneously big enough to
    # survive as its own SLIC/RAG region and small enough to be sub-floor.
    cfg = _cfg(target_width_mm=20.0)
    p = prep(_sliver_image(), cfg)
    min_area_px = (cfg.min_detail_mm * p.px_per_mm) ** 2

    q = segment(p, cfg)

    # The sliver's own area (18*18 = 324px, drawn) is a precondition for
    # this test meaning anything — if it isn't actually below the floor,
    # absorption proves nothing.
    assert 324 < min_area_px, "fixture assumption violated: sliver would clear the floor"

    assert any(w["code"] == ABSORBED_SMALL_SHAPES for w in q.warnings), (
        "expected the min-area floor to fire and report an absorption"
    )
    # No surviving region reads as near-pure green (the sliver's own color)
    # at a tiny area — it must have been swallowed into a neighbor, not kept
    # as its own sub-floor region.
    for label in range(len(q.thread_indices)):
        mask = q.labels == label
        area = int(mask.sum())
        if area >= min_area_px:
            continue
        mean_rgb = p.rgb[mask].reshape(-1, 3).mean(axis=0)
        is_greenish = mean_rgb[1] > mean_rgb[0] + 20 and mean_rgb[1] > mean_rgb[2] + 20
        assert not is_greenish, f"the tiny green sliver survived as its own region ({area} px)"


# --- 3. Determinism ----------------------------------------------------------


def test_determinism():
    cfg = _cfg()
    p = prep(FIXTURE, cfg)
    a = segment(p, cfg)
    b = segment(p, cfg)
    assert np.array_equal(a.labels, b.labels)
    assert a.thread_indices == b.thread_indices


# --- 4. Full-pipeline integration -------------------------------------------


def test_full_pipeline_integration_forced_photo_scene():
    cfg = _cfg(forced_class="photo_scene")
    result = run_stages(FIXTURE, cfg)

    assert len(result.regions) > 0
    for r in result.regions:
        assert r.polygon.is_valid
        assert r.polygon.area > 0

    assert any(w["code"] == PHOTO_SEGMENT_REGION_COUNT for w in result.warnings)


# --- 5. Flat/gradient lanes untouched ----------------------------------------


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flat_and_gradient_lanes_still_match_golden_after_photo_dispatch(fixture):
    """Re-runs `test_flat_lane_byte_identical.py`'s own fixtures through its
    own snapshot helper — the same invariant that file pins, exercised again
    here as a side effect of `pipeline.py` gaining a third routing branch.
    That file itself is untouched."""
    assert _snapshot(fixture) == GOLDEN[fixture]


# --- 6. "gradient" now dispatches through SLIC+RAG, not plain k-means -------
#
# `docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-
# enclosed-white-defects.md`, "Direction 1" (routing) + "Direction 3"
# (threshold). Region counts pinned here are FULL-PIPELINE
# `len(PipelineResult.regions)` — the F4 acceptance metric the plan doc's
# 20-80 band is stated against — not a stage-2-only proxy. See
# `MERGE_DELTAE00_THRESH`'s own docstring in stage2_photo_segment.py for the
# full two-fixture sweep this threshold and these numbers were derived from.

# `summit_badge.png`: a second real busy commissioned-style gradient
# fixture, built for this pass because `drone_render.png` was the only
# existing gradient-classified fixture in this repo complex enough to
# exercise fragmentation at all (`gradient_ramp_*`/`repro_gradient_white_
# icon` are all much simpler). Not derived from any customer file. See
# `MERGE_DELTAE00_THRESH`'s docstring for its own sweep numbers.
BUSY_GRADIENT_FIXTURES = ("drone_render.png", "summit_badge.png")


def test_gradient_class_dispatches_to_photo_segment_not_quantize():
    """The actual routing change: a gradient-classified design now carries
    `PHOTO_SEGMENT_REGION_COUNT` (a stage2_photo_segment-only warning) —
    proof it took the SLIC+RAG path, not `stage2_quantize.quantize` (which
    never emits this code at all)."""
    cfg = PipelineConfig(target_width_mm=90.0)
    c = classify(str(PHOTO_DIR / "drone_render.png"), cfg)
    assert c.class_ == "gradient", "fixture drifted off the class this test needs"

    result = run_stages(str(PHOTO_DIR / "drone_render.png"), cfg)
    assert result.design_class == "gradient"
    assert any(w["code"] == PHOTO_SEGMENT_REGION_COUNT for w in result.warnings)


@pytest.mark.parametrize("fixture", BUSY_GRADIENT_FIXTURES)
def test_busy_gradient_fixtures_land_inside_the_accept_band(fixture):
    """The actual defect this pass fixes: plain k-means fragmented
    drone_render.png into 192+ final regions (measured pre-fix), ~10x the
    plan doc's own 20-80 accept band (F4 criteria). SLIC+RAG at the retuned
    threshold lands both independent real busy fixtures inside that band."""
    cfg = PipelineConfig(target_width_mm=90.0)
    result = run_stages(str(PHOTO_DIR / fixture), cfg)
    assert result.design_class == "gradient"
    assert 20 <= len(result.regions) <= 80, (
        f"{fixture}: {len(result.regions)} regions, outside the 20-80 accept band"
    )


@pytest.mark.parametrize("fixture", ["gradient_ramp_linear.png", "gradient_ramp_radial.png"])
def test_simple_gradient_ramps_are_not_over_merged(fixture):
    """The other half of the retune's own validation: a clean 2-color
    gradient badge must not collapse to FEWER regions than its real content
    needs (background excluded, foreground is genuinely one ramp) — this
    would be silent over-merging, the opposite failure from fragmentation.
    Both ramps are genuinely one foreground ramp each, so >=1 region is the
    real floor; asserting a small upper bound catches the ramp accidentally
    fragmenting instead."""
    cfg = PipelineConfig(target_width_mm=90.0)
    result = run_stages(str(PHOTO_DIR / fixture), cfg)
    assert result.design_class == "gradient"
    assert 1 <= len(result.regions) <= 4, (
        f"{fixture}: {len(result.regions)} regions — expected a simple ramp's "
        "handful, not fragmentation or collapse"
    )


def test_merge_threshold_is_the_documented_retuned_value():
    """A regression trip-wire, not a design opinion: if this constant moves
    without its docstring's two-fixture sweep being redone, the region-count
    band tests above are the ones that will actually catch it — this test
    just makes an accidental edit (a merge conflict, a stray revert) fail
    fast and close to the cause.

    26.0, not the SLIC-era 20.0 — retuned 2026-08-07 for the SLIC -> SEEDS
    superpixel swap (see `MERGE_DELTAE00_THRESH`'s own docstring for the
    full two-fixture sweep this value comes from)."""
    assert MERGE_DELTAE00_THRESH == 26.0


# --- 7. The corrected PHOTO_SEGMENT_REGION_COUNT warning --------------------

def test_region_count_warning_reports_real_regions_not_thread_colors():
    """The bug this pass fixes: the warning used to report
    `count=len(thread_indices)` (thread COLOR count, always <= region count)
    under a message claiming to report regions. `region_blobs.png` at the
    shipped threshold consolidates several regions onto shared spools (5
    threads for what SLIC+RAG keeps as more numerous pre-palette regions),
    so `count` and `thread_colors` must genuinely differ here — a fixture
    where they happened to be equal would not catch a regression back to
    the old, wrong field."""
    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(FIXTURE, cfg)
    q = segment(p, cfg)

    hits = [w for w in q.warnings if w["code"] == PHOTO_SEGMENT_REGION_COUNT]
    assert len(hits) == 1
    w = hits[0]
    assert w["count"] > 0
    assert w["thread_colors"] > 0
    assert "slic_segments" in w and "merged_regions" in w
    # The two numbers this fixture's own palette step is known to
    # consolidate (see PHOTO_PALETTE_SELECTED's own `regions`/`colors`
    # split, which this warning's fix now agrees with).
    assert w["count"] >= w["thread_colors"]
    assert f"{w['count']} region" in w["message"]
    assert f"{w['thread_colors']} thread color" in w["message"]


def test_region_count_warning_agrees_with_palette_selected_warning():
    """`count` here and `regions` in the neighboring `PHOTO_PALETTE_SELECTED`
    warning describe the same real region count (the fix makes them agree,
    where before this warning's own `count` silently meant something else)."""
    from digitizer_core.warnings_codes import PHOTO_PALETTE_SELECTED

    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(FIXTURE, cfg)
    q = segment(p, cfg)

    region_count = [w for w in q.warnings if w["code"] == PHOTO_SEGMENT_REGION_COUNT][0]
    palette = [w for w in q.warnings if w["code"] == PHOTO_PALETTE_SELECTED][0]
    assert region_count["count"] == palette["regions"]
    assert region_count["thread_colors"] == palette["colors"]


# --- 8. Enclosed-background pixels get their own population ----------------
#
# A real safety gap the gradient-routing switch exposed, found and fixed in
# the same pass: `stage2_photo_segment.segment` did not separate
# `Prep.enclosed_mask` pixels from the main population the way
# `stage2_quantize.quantize` always has, so routing a gradient design with
# enclosed white icon linework through SLIC+RAG silently RAG-merged that
# linework into its surrounding region before `tag_enclosed_background`'s
# post-vectorization overlap test ever ran — measured directly: 0 of 3
# enclosed regions survived as their own tagged, restorable shapes, down
# from 3 via the old `stage2_quantize` path. Fixed by giving `segment` the
# same population split `quantize` uses.

def test_enclosed_background_survives_gradient_routing_through_slic_rag():
    """`repro_gradient_white_icon.png` classifies gradient and has real
    enclosed white icon linework (BACKGROUND_ENCLOSED fires). After this
    pass's routing change, that linework must still end up as its own
    tagged, unstitched-by-default Region(s) — the whole point of the
    enclosed-background restore feature — not silently absorbed into the
    surrounding gradient.

    The background-existence guards are OFF here (2026-08-11): at defaults
    the guard now correctly refuses to flood this full-bleed fixture at all
    (border agreement 0.355 < bg_border_agreement_min, BACKGROUND_ABSENT),
    so nothing is enclosed and the routing machinery under test never runs.
    See test_enclosed_background.py's repro_cfg comment — same reasoning."""
    cfg = PipelineConfig(target_width_mm=90.0,
                         bg_border_agreement_min=0.0, bg_border_rival_min=0.0)
    fixture = str(PHOTO_DIR / "repro_gradient_white_icon.png")
    c = classify(fixture, cfg)
    assert c.class_ == "gradient", "fixture drifted off the class this test needs"

    result = run_stages(fixture, cfg)
    assert any(w["code"] == "BACKGROUND_ENCLOSED" for w in result.warnings)
    unstitched = [r for r in result.regions
                 if r.meta.get("enclosed_background") and not r.meta.get("stitched", True)]
    assert unstitched, (
        "no region survived tagged enclosed_background/unstitched after "
        "routing this gradient design through SLIC+RAG — the enclosed-"
        "population split regressed"
    )


# --- 9. Small-vs-large area-ratio merge protection (2026-08-05 regression) --
#
# `MERGE_DELTAE00_THRESH` 10.0 -> 20.0 (section 6 above) fixed fragmentation
# but opened a second, opposite bug the region-count band alone could not
# see: on `summit_badge.png`, the badge's black ring/inner-circle/crosshair
# complex — real design content, sharply distinct to a human — got RAG-
# merged wholesale into the huge background-colored superpixel cluster that
# fills the space around/behind the badge. Region count still landed inside
# [20, 80] (down for the RIGHT reason — less fragmentation — AND the WRONG
# one — real content vanishing — at once). Root-caused to a genuine ~13 dE00
# gap between the black complex and that background-lookalike cluster: real,
# but under the new 20.0 threshold (was over the old 10.0 one). Fixed with
# `AREA_RATIO_PROTECT_THRESH`/`AREA_RATIO_MERGE_FACTOR` in
# `stage2_photo_segment.py` — see those constants' own docstring for the
# full mechanism and calibration evidence. These tests pin the fix itself,
# not just the region-count band (which cannot distinguish "less
# fragmentation" from "content disappeared" — that blind spot is exactly how
# the bug shipped undetected in the first place).

def _lookalike_bg_with_thin_dark_ring() -> np.ndarray:
    """Small synthetic reproduction of `summit_badge.png`'s own failure
    shape: a big 'background-colored' foreground disc (same structural role
    as the gray canvas area inside summit_badge's ring — large, foreground,
    reads as background-ish) surrounding a much smaller but genuinely,
    humanly distinct dark ring + filled disc. The ring/disc's color is
    chosen so its raw (pre-merge) CIEDE2000 gap from the big disc is a real
    but MODERATE one (same magnitude class as summit_badge's own measured
    ~13-16 dE00 critical merge) — large enough that a human calls it a
    different color, small enough that the retuned global 20.0 threshold
    merges it once RAG's own internal consolidation dilutes the small
    cluster's mean color (measured: this fixture reproduces the bug
    byte-for-byte when area-ratio protection is disabled, see the test
    below — and stops reproducing it if the color gap is pushed much wider,
    since then even the UNPROTECTED 20.0 threshold already refuses to merge
    it; this exact color/geometry pairing is the one that actually
    discriminates the two code paths, not just an arbitrary "looks dark"
    choice). Area ratio between the two (big disc minus the dark shape, vs.
    the dark shape) is ~22:1 — past `AREA_RATIO_PROTECT_THRESH`, the same
    order of magnitude as summit_badge's own measured ~13.6:1 critical-merge
    ratio."""
    h = w = 500
    img = np.full((h, w, 3), 250, np.uint8)
    cv2.circle(img, (w // 2, h // 2), 240, (85, 80, 76), -1)
    cv2.circle(img, (w // 2, h // 2), 50, (15, 15, 20), 5)
    cv2.circle(img, (w // 2, h // 2), 28, (15, 15, 20), -1)
    return img


def test_small_high_contrast_element_survives_area_ratio_protection():
    """The regression itself, pinned on a synthetic fixture built for this
    fix: the dark ring/disc complex must survive as its OWN region, not get
    absorbed into the big lookalike-background region — a different, and
    stronger, assertion than 'some region count is in range' (the check that
    let the real bug through)."""
    cfg = PipelineConfig(target_width_mm=60.0, forced_class="gradient")
    p = prep(_lookalike_bg_with_thin_dark_ring(), cfg)
    q = segment(p, cfg)

    uniq, counts = np.unique(q.labels[q.labels >= 0], return_counts=True)
    assert len(uniq) >= 2, (
        "the dark ring/disc complex was absorbed into the background-"
        "lookalike region — area-ratio protection failed to fire"
    )
    chart = chart_for(cfg)
    mean_rgbs = [chart[q.thread_indices[int(lbl)]].rgb for lbl in uniq]
    darkest = min(mean_rgbs, key=lambda rgb: max(rgb))
    assert max(darkest) < 70, (
        f"no surviving region reads as the dark ring/disc complex "
        f"(darkest final region's rgb={tuple(int(v) for v in darkest)})"
    )


def test_area_ratio_protection_is_load_bearing_for_that_fixture():
    """Sanity check on the fixture itself: without area-ratio protection
    (the pre-fix code path), the same fixture DOES collapse to one region —
    proof the test above is actually exercising the fix, not a fixture that
    would have survived regardless.

    Re-verified 2026-08-07 for the SLIC -> SEEDS swap (`MERGE_DELTAE00_
    THRESH` 20.0 -> 26.0): still holds. This test's own assertion is
    threshold-sensitive (checked directly while investigating the real
    `summit_badge.png` regression documented in `AREA_RATIO_PROTECT_THRESH`'s
    own docstring) — at a low raw threshold this synthetic fixture survives
    even with protection disabled, but AT THE SHIPPED 26.0 it still
    reproduces the collapse, so the mechanism this test pins is still real
    and still load-bearing for this fixture, unlike the unrelated real
    regression on `summit_badge.png` itself."""
    import digitizer_core.stage2_photo_segment as seg_mod

    cfg = PipelineConfig(target_width_mm=60.0, forced_class="gradient")
    p = prep(_lookalike_bg_with_thin_dark_ring(), cfg)

    old_thresh = seg_mod.AREA_RATIO_PROTECT_THRESH
    seg_mod.AREA_RATIO_PROTECT_THRESH = 10.0 ** 9  # never triggers
    try:
        q = seg_mod.segment(p, cfg)
    finally:
        seg_mod.AREA_RATIO_PROTECT_THRESH = old_thresh

    uniq = np.unique(q.labels[q.labels >= 0])
    assert len(uniq) == 1, (
        "fixture drifted: it must reproduce the bug (single merged region) "
        "with area-ratio protection disabled, or the test above isn't "
        "actually pinning anything"
    )


def test_summit_badge_black_complex_survives_full_pipeline():
    """Re-verify the real regression fixture directly, full pipeline
    (`run_stages`, the coordinator's own exact repro config): the badge's
    black ring/inner-circle/crosshair area must come out close to the source
    image's own near-black pixel area, not near zero. Measures TOTAL dark-
    thread stitched area against the source's own near-black pixel count —
    the same 'is the content still there' question region count cannot
    answer on its own.

    **History — this test was `xfail(strict=True)` between 2026-08-07's
    SLIC -> SEEDS superpixel swap and the boundary-contrast fix later the
    same day, and is a real passing assertion again.** The swap regressed
    recovery from the SLIC era's 83.7% to 9.1%, and no re-derivation of the
    `AREA_RATIO_*` constant family recovered it without pushing
    `drone_render.png` out of the 20-80 accept band; rather than delete,
    skip, or silently lower this test's bound, that pass left it xfail-strict
    so a future fix would flip it to an unexpected pass that pytest reports
    loudly. `BOUNDARY_CONTRAST_HARD_LAB` and friends in
    `stage2_photo_segment.py` are that fix (recovery 9.1% -> 106.9%, with
    `drone_render.png` unchanged at 74 regions and both gradient ramps
    unchanged at 2) — see that constant's own docstring for why the
    area-ratio family could never have been the right tool here, and for the
    full sweep behind each new constant. The marker is removed rather than
    inverted because the bar it guards is met by real measurement again, not
    because the regression was reinterpreted as acceptable."""
    cfg = PipelineConfig(target_width_mm=120.0, garment_id="left_chest")
    fixture = PHOTO_DIR / "summit_badge.png"
    result = run_stages(str(fixture), cfg)
    assert result.design_class == "gradient"

    chart = chart_for(cfg)
    dark_area_mm2 = sum(
        r.area_mm2 for r in result.regions
        if r.meta.get("stitched", True) and max(chart[r.thread_index].rgb) < 60
    )

    img = cv2.cvtColor(cv2.imread(str(fixture)), cv2.COLOR_BGR2RGB)
    blackish = (img[:, :, 0] < 45) & (img[:, :, 1] < 45) & (img[:, :, 2] < 45)
    source_black_area_mm2 = blackish.sum() / (result.px_per_mm ** 2)

    # Not a tight bound (palette snapping and the min-area floor both trim a
    # bit off the top) -- the bug's own signature was near-total loss (under
    # 1% recovered, measured while root-causing this), so a generous floor
    # is exactly the right bar: comfortably clears "the black complex is
    # basically gone" while not overfitting to one run's exact fraction.
    recovery = dark_area_mm2 / source_black_area_mm2
    assert recovery > 0.5, (
        f"black-complex area recovered only {recovery * 100:.1f}% of the "
        f"source's near-black pixel area ({dark_area_mm2:.1f} / "
        f"{source_black_area_mm2:.1f} mm2) -- the ring/circle/crosshair "
        "complex is being swallowed by the background region again"
    )


def test_area_ratio_protection_constants_are_the_documented_tuned_values():
    """Trip-wire, same spirit as `test_merge_threshold_is_the_documented_
    retuned_value` above: an accidental edit to either constant should fail
    fast here rather than surface only as a mysterious region-count drift on
    the busy fixtures."""
    assert AREA_RATIO_PROTECT_THRESH == 18.0
    assert AREA_RATIO_MERGE_FACTOR == 0.6
    assert AREA_RATIO_MIN_SMALL_PX == 1000


# --- 10. Boundary-contrast merge protection (2026-08-07 SEEDS regression) ---
#
# The fix that un-xfailed `test_summit_badge_black_complex_survives_full_
# pipeline` above. Where area-ratio protection guards against an extreme
# SIZE mismatch, this one guards two COMPARABLE-size regions that meet
# across a genuinely hard image edge — the shape summit_badge.png's fatal
# merge actually had (65,467 px into 348,309 px, ratio only 5.3, at dE00
# 16.06 under the 26.0 threshold). See `BOUNDARY_CONTRAST_HARD_LAB`'s own
# docstring in `stage2_photo_segment.py` for the full measurement trail.


def test_boundary_contrast_protection_constants_are_the_documented_tuned_values():
    """Same trip-wire discipline the two constant families above already get.
    Each bound has a real measured window behind it (see the constants' own
    docstring): contrast 6.0 sits in (0.64, 31.31], the smaller-side fraction
    0.09 in (0.074, 0.113].

    The merge factor is asserted as the ABSOLUTE local threshold it derives,
    not as a ratio — same reasoning (and same test shape) as
    `test_face_priors.py`'s check on `FACE_MERGE_FACTOR`: 13.0 dE00 is the
    number that actually has to stay below summit_badge's fatal 16.06 dE00
    merge, and it must keep deriving that figure if `MERGE_DELTAE00_THRESH`
    is ever retuned again."""
    assert BOUNDARY_CONTRAST_HARD_LAB == 6.0
    assert MERGE_DELTAE00_THRESH * BOUNDARY_CONTRAST_MERGE_FACTOR == pytest.approx(13.0)
    assert BOUNDARY_CONTRAST_MIN_SMALL_FRAC == 0.09
    assert BOUNDARY_CONTRAST_MIN_SMALL_PX == 1000


def test_boundary_contrast_separates_a_drawn_edge_from_a_gradient_interior():
    """The load-bearing NEW signal, pinned directly on the statistic rather
    than only through a fixture's region count: `_boundary_contrast_stats`
    must read a hard drawn edge and a smooth gradient's interior as
    categorically different, not merely different by a few percent.

    This is what the whole mechanism rests on — `merge_hierarchical` compares
    region MEAN colors, which cannot tell "two halves of one ramp, cut at an
    arbitrary interior position" from "two design elements meeting at a drawn
    edge" when both pairs of means happen to sit ~16 dE00 apart. Asserting a
    wide multiplicative gap (not just `>`) is deliberate: the shipped
    `BOUNDARY_CONTRAST_HARD_LAB = 6.0` is only defensible if the two
    populations are orders of magnitude apart, which is what the real
    fixtures measure (ramp interiors 0.54-0.64, drawn edges 18-40)."""
    from digitizer_core.stage2_photo_segment import _boundary_contrast_stats
    from digitizer_core.threads import rgb_to_lab

    h = w = 120
    # Left half: a smooth horizontal ramp. Right half: a flat block meeting
    # the ramp's end at a hard step.
    img = np.zeros((h, w, 3), np.uint8)
    for x in range(w // 2):
        v = int(round(40 + (x / (w // 2 - 1)) * 120))
        img[:, x] = (v, v, v)
    img[:, w // 2:] = (10, 10, 10)

    # Superpixels: cut the ramp in half (an arbitrary interior boundary at
    # x=30), and give the flat block its own label. Label 0 is reserved for
    # background by this module's convention, so labels start at 1.
    labels = np.zeros((h, w), np.int64)
    labels[:, :30] = 1
    labels[:, 30:w // 2] = 2
    labels[:, w // 2:] = 3

    lab_img = rgb_to_lab(img.reshape(-1, 3)).reshape(h, w, 3)
    acc = _boundary_contrast_stats(lab_img, labels)
    K = int(labels.max()) + 1

    def contrast(a, b):
        s, c = acc[min(a, b) * K + max(a, b)]
        assert c > 0
        return s / c

    ramp_interior = contrast(1, 2)
    drawn_edge = contrast(2, 3)
    assert ramp_interior < BOUNDARY_CONTRAST_HARD_LAB < drawn_edge, (
        f"ramp interior {ramp_interior:.2f} / drawn edge {drawn_edge:.2f} no "
        f"longer straddle BOUNDARY_CONTRAST_HARD_LAB={BOUNDARY_CONTRAST_HARD_LAB}"
    )
    assert drawn_edge > 10 * ramp_interior, (
        f"the two populations are only {drawn_edge / max(ramp_interior, 1e-9):.1f}x "
        "apart — the constant's whole safety margin is that this gap is large"
    )


def test_boundary_contrast_survives_merging_as_a_length_weighted_mean():
    """`_weight_mean_color` recombines `bsum`/`blen` from both sides of a
    merge; this pins that the recombination is the length-weighted mean (the
    only combination that stays honest through an arbitrarily deep merge
    tree), not an unweighted average of the two means.

    Exercised through the real `RAG.merge_nodes` call path rather than by
    calling the helper directly, because the property that actually matters
    is that BOTH constituent edges are still readable at recompute time —
    skimage removes `src` only after every neighbour's weight has been
    recomputed, and the whole mechanism silently degrades to "whatever one
    side happened to have" if that ordering ever changes."""
    import digitizer_core.stage2_photo_segment as seg_mod
    from skimage.graph import RAG

    g = RAG()
    for n in (1, 2, 3):
        g.add_node(n)
        # `labels` is skimage's own required per-node attribute (RAG.merge_
        # nodes concatenates them); the rest are what `rag_mean_color` +
        # `_init_fg_pixel_counts` would have seeded on a real graph.
        g.nodes[n]["labels"] = [n]
        g.nodes[n]["mean color"] = np.array([50.0, 0.0, 0.0])
        g.nodes[n]["total color"] = np.array([50.0, 0.0, 0.0])
        g.nodes[n]["pixel count"] = 1
        g.nodes[n]["fg pixel count"] = 1
    # 1 and 2 both border 3, with very different boundary lengths.
    g.add_edge(1, 3, weight=1.0, bsum=100.0, blen=10)
    g.add_edge(2, 3, weight=1.0, bsum=30.0, blen=90)
    g.add_edge(1, 2, weight=1.0, bsum=0.0, blen=0)

    seg_mod._merge_mean_color(g, 1, 2)
    g.merge_nodes(1, 2, seg_mod._weight_mean_color)

    e = g[2][3]
    assert e["blen"] == 100
    assert e["bsum"] == pytest.approx(130.0)
    # Length-weighted mean 1.30, NOT the unweighted mean of 10.0 and 0.333.
    assert e["bsum"] / e["blen"] == pytest.approx(1.30)


def test_face_local_threshold_still_avoids_fragmenting_a_solid_block():
    """Companion to `test_face_priors.py::test_face_local_threshold_splits_
    shades_that_merge_outside_a_face` (that test's own fixture is what
    exposed the need for `AREA_RATIO_MIN_SMALL_PX` — a first pass at area-
    ratio protection blocked the small upscale-interpolation-seam slivers
    that fixture's two solid blocks produce from doing their ordinary small-
    into-large absorb, fragmenting `with_face` from 2 regions to 7). Pinned
    here too, since it is really an area-ratio property, not just a face-
    priors one."""
    from digitizer_core.stage1_prep import prep as _prep
    from digitizer_core.warnings_codes import PHOTO_SEGMENT_REGION_COUNT as _CODE

    img = np.full((200, 200, 3), 255, np.uint8)
    img[50:150, 50:100] = 118
    img[50:150, 100:150] = 138
    cfg = PipelineConfig(target_width_mm=80.0, min_px_per_mm=4.0)
    p = _prep(img, cfg)
    q = segment(p, cfg, face_regions=None)
    w = [x for x in q.warnings if x["code"] == _CODE][0]
    assert w["merged_regions"] == 1, (
        f"a solid two-shade block fragmented into {w['merged_regions']} raw "
        "merged regions instead of consolidating to 1 -- area-ratio "
        "protection is firing on interpolation-seam noise again"
    )


# --- Tonal region splitting ---------------------------------------------------
#
# A region is the unit that owns one thread, so a region whose own pixels span
# more tone than one thread can express sews as a flat average whatever the
# fill tier does. `split_tonal_regions` cuts those into parts that each get
# their own mean, palette weight and spool. Measured motivation: Kent's owl
# body, 4200 mm2 spanning 81 points of L*, sewn as one pale mass.

def _tonal_prep(gradient: bool, px_per_mm: float = 6.0):
    """A prep whose single foreground blob is either a strong light-to-dark
    sweep (splittable) or one flat colour (not)."""
    h, w = 240, 240
    rgb = np.full((h, w, 3), 250, np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    blob = (np.hypot(xx - w / 2.0, yy - h / 2.0) < 100)
    if gradient:
        ramp = np.clip((xx - 20) * (235.0 / (w - 40)), 10, 245).astype(np.uint8)
        for c in range(3):
            rgb[:, :, c] = np.where(blob, ramp, 250)
    else:
        rgb[blob] = (90, 90, 90)
    bg = ~blob
    return _PrepStub(rgb=rgb, bg_mask=bg, px_per_mm=px_per_mm), blob


class _PrepStub:
    """Only the fields `split_tonal_regions` reads. A real `Prep` carries a
    dozen more that this function never touches, and building one here would
    couple the test to stage 1's own signature."""

    def __init__(self, rgb, bg_mask, px_per_mm):
        self.rgb = rgb
        self.bg_mask = bg_mask
        self.px_per_mm = px_per_mm
        self.enclosed_mask = None


def test_split_tonal_regions_is_off_unless_asked():
    p, blob = _tonal_prep(gradient=True)
    kept = [RegionMask(mask=blob, layer=0)]
    out, n = split_tonal_regions(p, PipelineConfig(), kept)
    assert n == 0 and out is kept, "the split must be strictly opt-in"


def test_split_tonal_regions_splits_a_strong_sweep():
    p, blob = _tonal_prep(gradient=True)
    kept = [RegionMask(mask=blob, layer=0)]
    out, n = split_tonal_regions(p, PipelineConfig(split_tonal_regions=True), kept, split_tonal=True)
    assert n == 1, "a full light-to-dark sweep must split"
    assert len(out) >= 2

    # The three properties stage 5 depends on, and the reason this is done with
    # masks rather than polygons: parts are disjoint, they never leave the
    # region they came from, and together they are exactly it. Any of these
    # failing means artwork silently vanishing or regions overlapping.
    union = np.zeros_like(blob)
    total = 0
    for r in out:
        assert not (union & r.mask).any(), "parts overlap"
        assert (r.mask & ~blob).sum() == 0, "a part escaped its region"
        union |= r.mask
        total += int(r.mask.sum())
    assert (union == blob).all(), "parts do not cover the original region"
    assert total == int(blob.sum()), "pixels were lost or double-counted"


def test_split_tonal_regions_leaves_a_flat_region_alone():
    p, blob = _tonal_prep(gradient=False)
    kept = [RegionMask(mask=blob, layer=0)]
    out, n = split_tonal_regions(p, PipelineConfig(split_tonal_regions=True), kept, split_tonal=True)
    assert n == 0 and len(out) == 1


def test_split_tonal_regions_leaves_small_regions_alone():
    """Kent's owl irises carry real tonal range in 4-17 mm2 and must stay
    whole — splitting them manufactures slivers for stage 3 to absorb again.
    Same artwork as the splitting test, at a scale that puts the blob under
    the area floor."""
    p, blob = _tonal_prep(gradient=True, px_per_mm=60.0)
    kept = [RegionMask(mask=blob, layer=0)]
    out, n = split_tonal_regions(p, PipelineConfig(split_tonal_regions=True), kept, split_tonal=True)
    assert n == 0 and len(out) == 1


def test_split_tonal_regions_preserves_layer_and_source():
    p, blob = _tonal_prep(gradient=True)
    kept = [RegionMask(mask=blob, layer=3, source="sam2")]
    out, n = split_tonal_regions(p, PipelineConfig(split_tonal_regions=True), kept, split_tonal=True)
    assert n == 1
    assert all(r.layer == 3 and r.source == "sam2" for r in out), (
        "a split part belongs to the same layer and segmenter as its parent"
    )
