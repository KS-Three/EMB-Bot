"""`resnap_mask_matches_grader` — the re-snap and the grader score the same
pixels. ON since 2026-09-10 (Kent's colour-bundle ruling), and folded into the
code 2026-11-19: the switch is gone, so there is no OFF arm to price against.
What stays is the ON behaviour, over `conftest.PRE_FLIP`. The OFF numbers in
this docstring were measured on the engine as it stood.

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

**It accounts for two of the three F-wall blocks that survive excess scoring**
— `gaulke` and `bridge_bar`; `screenshot` is the small-shape floor (both
footprints pick `0015` either way). An earlier version of this docstring put
`bridge_bar` in "neither" because the two masks agree to 1.3 dE00 on its
ASSIGNED thread; the re-snap's gate reads the improvement over the best LOADED
spool, and there they read 1.8 against 10.3 across a 3.0 threshold.

**And this flag cannot finish either one on its own.** Masking out the halo
SHRINKS the footprint, so a shape the raw raster floated over
`THREAD_REVALIDATE_MIN_PX = 200` drops under it — gaulke 247 -> 54 px,
bridge_bar 240 -> 156. What the flag buys on gaulke is therefore the value of
DECLINING a wrong re-snap, not of making a better one, which is what the
tests below pin.
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

from .conftest import PRE_FLIP, TESTDATA

# 2026-11-20 (bundle roll-forward): the numbers here were read with six colour switches
# False (`legacy_engine(**PRE_FLIP_FOLDED)` patched their False paths back). Those paths
# are gone, so the file runs on today's engine.

GAULKE = "photo/logo_gaulke_roofing.png"
# The region the flag exists for, and the spool the unmasked footprint picks.
# 2026-11-20 (bundle roll-forward): `Se6eddd27` no longer exists. It was a region of the
# engine before robust colour, edge snap, phantom-blend dissolve and the rest folded
# (that engine sewed 3971 Silver / 1375 Charcoal there; today's gaulke carries only
# 0015 and 0020). The premise -- a region whose raw footprint is BIMODAL and several
# times larger than the grader's -- is re-read on `S94b8296d` (raw 1485 px against 459,
# 291 near-black plus 899 near-white), the most lopsided region today.
BLOCKED_SHAPE = "S94b8296d"


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


@lru_cache(maxsize=None)
def _run(fixture: str):
    """One pipeline run per fixture. Cached for the reason
    `test_bind_resnap_all_classes` records: CI runners are 2-core, so a
    straight-through file pays for every repeated `digitize`."""
    art = TESTDATA / fixture
    result, plan = digitize(art, _cfg(**PRE_FLIP))
    coords = tuple(
        (round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
        for _b, run in plan.iter_runs() for x, y in run.points)
    threads = {r.shape_id: r.thread_number for r in result.regions}
    return coords, threads, result, plan


def test_the_two_masks_really_do_disagree_on_this_region():
    """The premise, pinned. If this stops failing to differ, the flag has
    nothing to fix and the rest of this file proves nothing."""
    _, _, result, plan = _run(GAULKE)
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

    It was not bit-for-bit and could not be: `_region_footprint` rounds
    mm->px (`np.round(...).astype(int32)`) and `_region_color_errors`
    truncated, so the two rasters differed by up to a pixel at a vertex
    before either mask was applied. Measured 2026-09-07 the residual was 80
    px out of 557,046 on gaulke and zero on `logo_alpha` — 99.99% and 100%
    IoU — because every vertex sat on a pixel centre. `subpixel_edges` (on
    by default since 2026-09-09) makes the vertices fractional, and
    truncation then shifts the whole mask half a pixel down and left of the
    footprint: 97.5% on alpha, 98.8% on gaulke. So `_region_color_errors`
    now rounds the same way, and this replica of it rounds too; the
    alignment touches preflight only, never `tag_enclosed_background`.

    **Re-measured 2026-09-12: the residual is now ZERO on gaulke** —
    553,014 / 553,014 px, exactly 100% IoU, not one pixel disagreeing. The
    threshold below stays `> 0.999` rather than becoming equality on
    purpose: 100% was measured on gaulke ONLY — `logo_alpha` was not
    re-measured exactly, it merely passes the threshold — so equality is not
    a proved property of every raster, and pinning a rasteriser tie-break
    would make this test fail for a reason that is not what it watches.
    """
    _, _, result, _ = _run(fixture)
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
            return np.round(np.column_stack([a[:, 0] * p.px_per_mm + cx,
                                             a[:, 1] * p.px_per_mm + cy])).astype(np.int32)
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


def test_the_resnap_does_not_choose_silver_for_near_black_artwork():
    """The behaviour the mask buys, stated on the SEWN thread rather than on a
    grade: `THREAD_MATCH_POOR` grades per thread on its worst patch, so a
    grade is not evidence here (DOCTRINE, and yardstick-disagreements row 1).
    (Before the mask the shipped engine sewed Silver `3971` here.)"""
    _, on_threads, _, _ = _run(GAULKE)
    assert on_threads.get(BLOCKED_SHAPE) != "3971", (
        "with the grader's mask the re-snap must not pick Silver for artwork "
        "its own core reads as near-black")


def _shape_delta_e() -> float:
    art = TESTDATA / GAULKE
    _, _, result, plan = _run(GAULKE)
    cfg = _cfg(**PRE_FLIP)
    p = pf.prep(art, cfg)
    rows = pf._region_color_errors(p, result, plan, cfg)
    mine = [r for r in rows
            if str(r["shape_id"]).split(" shade ")[0] == BLOCKED_SHAPE]
    assert mine, f"{BLOCKED_SHAPE} must still be scored"
    return max(r["delta_e"] for r in mine)


def test_the_graders_own_score_for_that_shape_is_improved():
    """End to end, in the instrument that condemned it -- at the size it
    actually is.

    **It does not fully clear.** Measured 2026-09-07: 63.6 (no mask) ->
    **16.7** dE00, still over `DELTA_E_CLEARLY_DIFFERENT`. With the halo
    pixels gone the re-snap DECLINES this region, so it keeps stage 2's
    `4174`, and the design's cone list has collapsed to three -- `1375 Dark
    Charcoal`, which sits 5.0 dE00 from this artwork, is no longer loaded for
    the small-shape rule to offer.
    """
    on = _shape_delta_e()
    # Re-captured 2026-11-20 (bundle roll-forward) on `S94b8296d`, the shape the 63.6 -> 16.7
    # row was read on no longer being there: 20.3 dE00 on today's engine, pinned within 1.
    assert abs(on - 20.3) < 1.0, f"20.3 expected: {on:.1f}"
    # Pinned as a KNOWN RESIDUAL, not as a target. If this starts passing,
    # something reached the shape and this file should say what.
    assert on > pf.DELTA_E_CLEARLY_DIFFERENT, (
        f"{on:.1f} dE00 -- the shape now CLEARS; update this test and the "
        "residual recorded in MASTER_SCOPE 28")


def test_the_halo_pixels_no_longer_invent_cones():
    """The effect that is bigger than one shape, and the reason the shape
    itself only gets halfway.

    MASTER_SCOPE 15's "resnap escape" has a second cause besides the missing
    palette binding `bind_resnap_all_classes` treats: the argmin was run on
    halo pixels, so it went looking for a spool that matches a colour the
    artwork does not contain. On gaulke the unmasked engine re-snapped its way
    to `1375 Dark Charcoal` and `3971 Silver`; with the grader's mask neither
    is reached at all.
    """
    _, _, on_result, _ = _run(GAULKE)
    on = {r.thread_number for r in on_result.regions}
    assert not (on & {"3971", "1375"}), (
        f"still escaping to {sorted(on & {'3971', '1375'})}")
