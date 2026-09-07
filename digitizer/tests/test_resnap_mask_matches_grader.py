"""`cfg.resnap_mask_matches_grader` — the re-snap and the grader score the same
pixels. DEFAULT OFF.

`stage4_vectorize.revalidate_threads` and `preflight._region_color_errors`
claim the same estimator and have it: both take the median of the per-pixel
CIEDE2000. **They do not share a mask.** Preflight erodes the polygon raster
one pixel and drops `p.bg_mask` — *"to keep anti-alias halo pixels from
dragging a flat color toward the background"* — while `_region_footprint` is a
bare `cv2.fillPoly` and does neither.

Measured 2026-09-07 (`tools/spool_remedy.py --masks`) on
`logo_gaulke_roofing`'s `Se6eddd27`, 0.58 mm² at 16.1 px/mm: **247 px against
54**, and stage 4's set is BIMODAL — 103 near-black plus 65 near-white — so
its median makes `3971 Silver` the chart-wide argmin at **11.4 dE00** while the
region's own core is near-black and scores that same Silver **63.6**. The
re-snap picks a thread on pixels the grader refuses, and the grader then
condemns the thread the re-snap picked.

That is the failure `_region_color_errors`' own docstring calls this
instrument's original sin — *"the per-channel median of a bimodal pool is a
colour almost no pixel carries"* — fixed on preflight's side 2026-08-11 and
never inherited here.

**It is not a general cure and these tests do not claim it is.** On the other
two F-wall blocks that survive excess scoring the two masks agree to 0.4 dE00
(`screenshot`, which is the small-shape floor) and 1.3 (`bridge_bar`, open).
One fixture, named.
"""
from functools import lru_cache

import cv2
import numpy as np
import pytest

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.stage4_vectorize import _region_footprint
from digitizer_core.threads import chart_for

from .conftest import TESTDATA

GAULKE = "photo/logo_gaulke_roofing.png"
# The region the flag exists for, and the spool the unmasked footprint picks.
BLOCKED_SHAPE = "Se6eddd27"
# A flat fixture and a photo fixture, neither of which has the halo problem —
# the controls that say "byte-identical off" is a claim about the SHIPPED
# default, not an artifact of testing one design.
CONTROLS = ["logo_alpha.png", "photo/photo_dof_meadow.png"]


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


@lru_cache(maxsize=None)
def _run(fixture: str, on: bool):
    """One pipeline run per (fixture, flag). Cached for the reason
    `test_bind_resnap_all_classes` records: CI runners are 2-core, so a
    straight-through file pays for every repeated `digitize`."""
    art = TESTDATA / fixture
    result, plan = digitize(art, _cfg(resnap_mask_matches_grader=on))
    coords = tuple(
        (round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
        for _b, run in plan.iter_runs() for x, y in run.points)
    threads = {r.shape_id: r.thread_number for r in result.regions}
    return coords, threads, result, plan


@pytest.mark.parametrize("fixture", [GAULKE, *CONTROLS])
def test_off_is_byte_identical_to_the_shipped_engine(fixture):
    """The flag's price of admission on this lane. `_region_footprint` is used
    by `tag_enclosed_background` too, so an edit that leaked out of the OFF
    path would move far more than the re-snap."""
    shipped, _, _, _ = _run(fixture, False)
    art = TESTDATA / fixture
    result, plan = digitize(art, _cfg())          # no keyword at all
    coords = tuple(
        (round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
        for _b, run in plan.iter_runs() for x, y in run.points)
    assert coords == shipped


def test_the_two_masks_really_do_disagree_on_this_region():
    """The premise, pinned. If this stops failing to differ, the flag has
    nothing to fix and the rest of this file proves nothing."""
    _, _, result, plan = _run(GAULKE, False)
    art = TESTDATA / GAULKE
    p = pf.prep(art, _cfg())
    reg = next(r for r in result.regions if r.shape_id == BLOCKED_SHAPE)
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    raw = _region_footprint(reg, p.rgb.shape[:2], cx, cy, p.px_per_mm)
    eroded = cv2.erode(raw.astype(np.uint8), np.ones((3, 3), np.uint8))
    grader = (eroded > 0) & (~p.bg_mask)

    assert raw.sum() > 3 * grader.sum(), (
        f"raw {int(raw.sum())} px vs grader {int(grader.sum())} px — the gap "
        "this flag closes")
    lum = p.rgb[raw].reshape(-1, 3).mean(axis=1)
    assert (lum < 64).sum() > 50 and (lum >= 192).sum() > 50, (
        "the raw footprint must be BIMODAL — that is why its median lands on "
        "a colour almost no pixel carries")


@pytest.mark.parametrize("fixture", [GAULKE, "logo_alpha.png"])
def test_the_flagged_mask_really_matches_the_graders(fixture):
    """The flag's NAME is a claim, so it gets an invariant.

    It is not bit-for-bit and cannot be: `_region_footprint` rounds mm->px
    (`np.round(...).astype(int32)`) and `_region_color_errors` truncates, so
    the two rasters differ by up to a pixel at a vertex before either mask is
    applied. Measured 2026-09-07 the residual is 80 px out of 557,046 on
    gaulke and zero on `logo_alpha` — 99.99% and 100% IoU. Aligning the
    rasteriser itself would touch `tag_enclosed_background`, which shares
    `_region_footprint`, so it is deliberately NOT done here; this pins how
    close the cheap version gets.
    """
    _, _, result, _ = _run(fixture, False)
    p = pf.prep(TESTDATA / fixture, _cfg())
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h, w = p.rgb.shape[:2]
    inter = union = 0
    for r in result.regions:
        if r.meta.get("enclosed_background"):
            continue
        fp = _region_footprint(r, (h, w), cx, cy, p.px_per_mm)
        er = cv2.erode(fp.astype(np.uint8), np.ones((3, 3), np.uint8))
        mine = (er > 0) & (~p.bg_mask)
        if not mine.any():
            mine = fp & (~p.bg_mask)

        m = np.zeros((h, w), np.uint8)
        def to_px(c):
            a = np.asarray(c, np.float64)
            return np.column_stack([a[:, 0] * p.px_per_mm + cx,
                                    a[:, 1] * p.px_per_mm + cy]).astype(np.int32)
        cv2.fillPoly(m, [to_px(r.polygon.exterior.coords)], 1)
        for ring in r.polygon.interiors:
            cv2.fillPoly(m, [to_px(ring.coords)], 0)
        e2 = cv2.erode(m, np.ones((3, 3), np.uint8))
        theirs = (e2 > 0) & (~p.bg_mask)
        if not theirs.any():
            theirs = (m > 0) & (~p.bg_mask)

        inter += int((mine & theirs).sum())
        union += int((mine | theirs).sum())
    assert union > 0
    iou = inter / union
    assert iou > 0.999, f"{fixture}: masks agree on only {iou:.4%} of pixels"


def test_on_the_resnap_stops_choosing_silver_for_near_black_artwork():
    """The behaviour the flag buys, stated on the SEWN thread rather than on a
    grade: `THREAD_MATCH_POOR` grades per thread on its worst patch, so a
    grade is not evidence here (DOCTRINE, and yardstick-disagreements row 1)."""
    _, off_threads, _, _ = _run(GAULKE, False)
    _, on_threads, on_result, _ = _run(GAULKE, True)
    assert off_threads.get(BLOCKED_SHAPE) == "3971", (
        "premise: the shipped engine sews Silver here")
    assert on_threads.get(BLOCKED_SHAPE) != "3971", (
        "with the grader's mask the re-snap must not pick Silver for artwork "
        "its own core reads as near-black")


def _shape_delta_e(on: bool) -> float:
    art = TESTDATA / GAULKE
    _, _, result, plan = _run(GAULKE, on)
    cfg = _cfg(resnap_mask_matches_grader=on)
    p = pf.prep(art, cfg)
    rows = pf._region_color_errors(p, result, plan, cfg)
    mine = [r for r in rows
            if str(r["shape_id"]).split(" shade ")[0] == BLOCKED_SHAPE]
    assert mine, f"{BLOCKED_SHAPE} must still be scored (flag {on})"
    return max(r["delta_e"] for r in mine)


def test_on_the_graders_own_score_for_that_shape_improves():
    """End to end, in the instrument that condemned it — and stated at the
    size it actually is.

    **It does not fully clear, and an earlier draft of this test asserted it
    would.** Measured 2026-09-07: 63.6 -> **16.7** dE00, still over
    `DELTA_E_CLEARLY_DIFFERENT`. The reason is the next test: with the halo
    pixels gone the re-snap DECLINES this region, so it keeps stage 2's
    `4174`, and the design's cone list has collapsed to three — `1375 Dark
    Charcoal`, which sits 5.0 dE00 from this artwork, is no longer loaded for
    the small-shape rule to offer. `revalidate_small_shapes` does not rescue
    it either (byte-identical to this arm on gaulke), for the same reason.
    """
    off, on = _shape_delta_e(False), _shape_delta_e(True)
    assert off > 60.0, f"premise: the shipped engine earns {off:.1f}, not >60"
    assert on < off / 3, f"63.6 -> {on:.1f}: the flag did not reach it"
    # Pinned as a KNOWN RESIDUAL, not as a target. If this starts passing,
    # something reached the shape and this file should say what.
    assert on > pf.DELTA_E_CLEARLY_DIFFERENT, (
        f"{on:.1f} dE00 — the shape now CLEARS; update this test and the "
        "residual recorded in MASTER_SCOPE 28")


def test_the_halo_pixels_were_inventing_cones():
    """The effect that is bigger than one shape, and the reason the shape
    itself only gets halfway.

    MASTER_SCOPE 15's "resnap escape" — the pass adds 34 cones corpus-wide,
    25 outside the selected palette — has a second cause besides the missing
    palette binding `bind_resnap_all_classes` treats: the argmin is being run
    on halo pixels, so it goes looking for a spool that matches a colour the
    artwork does not contain. On gaulke the shipped engine re-snaps its way to
    `1375 Dark Charcoal` and `3971 Silver`; with the grader's mask neither is
    reached at all.
    """
    _, off_threads, off_result, _ = _run(GAULKE, False)
    _, on_threads, on_result, _ = _run(GAULKE, True)
    off = {r.thread_number for r in off_result.regions}
    on = {r.thread_number for r in on_result.regions}
    assert "3971" in off and "1375" in off, "premise: the escape happens"
    assert not (on & {"3971", "1375"}), (
        f"still escaping to {sorted(on & {'3971', '1375'})}")
    assert len(on) < len(off), f"{len(off)} -> {len(on)} cones"


def test_the_flag_never_grows_the_cone_set():
    """The rule `bind_resnap_all_classes` learned the hard way: a re-snap that
    pulls in a new spool makes the operator load a cone the plan never named,
    and each new spool is another row `THREAD_MATCH_POOR` scores."""
    for fixture in (GAULKE, *CONTROLS):
        _, _, off_result, _ = _run(fixture, False)
        _, _, on_result, _ = _run(fixture, True)
        off = {r.thread_number for r in off_result.regions}
        on = {r.thread_number for r in on_result.regions}
        assert len(on) <= len(off), (
            f"{fixture}: {len(off)} -> {len(on)} cones")
