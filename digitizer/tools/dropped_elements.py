"""What did the engine LOSE? Element-level, not shape-level.

Kent reviewed fourteen stitch-outs on 2026-08-27 and named the same failure on
seven of them, in his own words: *"the red arm on the right side of the logo was
lost"*, *"EAT | STAY | PLAY was completely lost"*, *"Resturant was dropped
completely"*, *"the left side trees were lost"*, *"text on the bottom was
dropped out"*. Whole elements, gone.

**Nothing in this repo could see it.** Measured the same day:

  * `preflight.ARTWORK_UNCOVERED` fired on ONE of the seven and reported
    `0.0 mm2` missing on the rest — with `uncovered_checked: True`, so it ran
    and saw nothing. Its own message says why: the area it measures is
    *"claimed by a shape the design sews"*. It is scoped to shapes that made
    it into the design, so it catches thread missing INSIDE a shape that
    exists (becker_marine's C, 18.8 mm2 — correctly found) and is structurally
    blind to an element that never became a shape at all.
  * `artfidelity_self`'s `coverage` is a global IoU, so a lost limb costs a few
    points out of a hundred. Both designs Kent marked "out of place" are the
    two that lost an element, ranked 5th and 7th of 8.
  * `preflight` graded `logo_whitebg` **A 100** on a design he says is not
    smooth, and `enthusiast_logo` **B 88** with a limb missing.

## What it measures

Per-pixel CIEDE2000 between the artwork **painted on white cloth** and the
rendered stitch-out, thresholded at `LOST_DELTA_E`, opened at half a millimetre
to drop the hairline of disagreement every shape boundary carries, then split
into connected regions. Each region is somewhere the stitch-out does not look
like the artwork, and its size and position say what and where.

Painting the artwork on white is what makes one test cover all three ways Kent
described the failure:

    never sewn          white cloth where a colour belongs
    knockout filled in  a colour where bare cloth belongs
    wrong thread        one colour where another belongs

## `lost_frac` is a SUM, and a fixture can be entirely one of its halves

Read the total as "coverage" and you will chase the wrong defect. Every region
carries `ink`, so the total splits cleanly and both halves are reported:

  * `unsewn_frac` — regions ON the ink. Artwork the stitch-out never covered.
    This is the one Kent named ("the red arm was lost").
  * `overshoot_frac` — regions OFF it. Thread standing on cloth the artwork
    leaves bare: a column sewing wider than the shape it belongs to.

Measured 2026-09-20, all four at 80 mm left_chest:

    enthusiast  lost_frac 0.3002   unsewn   0%   overshoot 100%
    tires       lost_frac 0.1270   unsewn   0%   overshoot 100%
    becker      lost_frac 0.0509   unsewn  44%   overshoot  56%
    bridge      lost_frac 0.1070   unsewn 100%   overshoot   0%

They move in OPPOSITE directions under one engine change — satin rails placed
further out cover more artwork AND spill more thread — so the total cannot say
which one a change bought, and a wordmark's total says nothing about coverage
at all. That is not hypothetical: a session read `enthusiast`'s 0.3006 as lost
coverage and set out to recover artwork that was never uncovered
(`tools/rail_edge.py --bare` does not move across the change it blamed).

## Segment the disagreement, not the artwork

Three definitions of "element" were tried first and each had a hole. They are
recorded here because the holes are the instructive part, and because each one
looked correct until it was run against a design Kent had already told us was
broken:

  1. **Connected ink components.** Merges a red arm into the shield it touches,
     and on alpha-keyed art the whole badge is one blob. Reported ZERO lost
     elements on `enthusiast_logo`, which is visibly missing a limb.
  2. **Ink plus enclosed ground.** Meant to catch a knockout sewn over. Still
     missed it: that shield's hexagon has BREAKS, so its interior white reaches
     the frame edge and no flood test calls it enclosed. Found 1.1 mm2 of a
     failure an order of magnitude larger.
  3. **Whole-frame colour components.** Makes the background ONE component
     spanning the frame, and a median over it hides a small filled-in patch
     entirely.

Per-pixel first, components second, has none of those holes — the same ordering
lesson as `artfidelity_self`'s colour component, where taking medians before
the subtraction produced a metric that could not fire at all.

## What this does NOT measure

Kent's other complaint, on eight of fourteen designs: *"shapes are accurate but
smoothness is not"*, *"sawtoothed and jaged"*. That lives in the boundary
hairline `HALO_OPEN_PX` deliberately removes here, because a half-millimetre
band around every shape would otherwise swamp the lost elements this instrument
exists to find. Removing it is not a claim that it does not matter — it is the
second instrument, and that band is where it should look.

Usage:
    python -m tools.dropped_elements <image> [<image> ...]
    python -m tools.dropped_elements --all
    python -m tools.dropped_elements --all --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from skimage.color import deltaE_ciede2000  # noqa: E402

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from digitizer_core.stitchviz import render_design  # noqa: E402
from digitizer_core.threads import rgb_to_lab  # noqa: E402
from tools.artfidelity_self import (FIXTURES, RES, Registered, art_ink_field,  # noqa: E402
                                    ink_is_ambiguous, ink_saturation,
                                    INK_SATURATION_MAX, register,
                                    stitch_coverage_field)

MIN_ELEMENT_MM2 = 1.0
# Ink blobs smaller than this are not "elements" — they are anti-alias crumbs,
# JPEG ringing and the odd stray pixel, and a detector that reports them buries
# a lost word under fifty specks. JUDGEMENT, but anchored: `preflight`'s own
# uncovered check reports in mm2 and called becker_marine's genuinely-missing
# piece 18.8 mm2 with a worst patch of 11 mm2, an order of magnitude above this
# floor, and the smallest thing Kent named by name (the "E" on DRONE) is
# lettering, which cannot be sewn at all below roughly 1 mm2 of ink.

HALO_OPEN_PX = 5
# Morphological opening kernel, in pixels at RES (so 0.5 mm), applied to the
# disagreement mask before it is broken into elements. Every shape boundary
# disagrees by a hairline — thread lands a fraction of a millimetre off the ink
# edge — and that is Kent's OTHER complaint (smoothness), not a lost element.
# Opening at half a millimetre removes those outlines and keeps anything with
# real width. JUDGEMENT: 5 px at RES is 0.50 mm, the smallest odd kernel at or
# above one thread width (machine.COVERAGE_THREAD_W_MM, 0.40 mm) — so it clears
# up to about one stitch and keeps anything wider.

LOST_DELTA_E = 20.0
# Median CIEDE2000 between an artwork element's own colour and what the
# stitch-out actually shows there. Above this the element does not read as
# itself any more — it is missing, or sewn in something else, or a knockout
# filled in. JUDGEMENT, sanity-anchored on the shipped scale: preflight calls
# 10.0 "clearly different", and this is deliberately well above that, because
# the question here is not "is the colour off" but "is the element GONE".

def _components(mask: np.ndarray, min_px: int):
    """Connected components of `mask`, as (label_image, [stats...]) filtered to
    those at least `min_px` in area. 8-connectivity: a diagonal hairline is one
    element to the eye, and 4-connectivity would split it into a dotted line."""
    n, lab, stats, cent = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    out = []
    for i in range(1, n):                       # 0 is background
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_px:
            continue
        out.append({
            "label": i,
            "area_px": area,
            "x": int(stats[i, cv2.CC_STAT_LEFT]),
            "y": int(stats[i, cv2.CC_STAT_TOP]),
            "w": int(stats[i, cv2.CC_STAT_WIDTH]),
            "h": int(stats[i, cv2.CC_STAT_HEIGHT]),
            "cx": float(cent[i][0]),
            "cy": float(cent[i][1]),
        })
    return lab, out


def art_colour_field(art_path, width_mm):
    """Artwork RGB + opacity at the design's physical size, same sizing rule as
    `artfidelity_self.art_ink_field` so the two register identically: crop to the
    ink bbox, scale that bbox to `width_mm`.

    -> (rgb uint8 HxWx3, opaque bool HxW)
    """
    im = Image.open(art_path).convert("RGBA")
    a = np.asarray(im)
    if a[..., 3].min() < 255:
        ink = a[..., 3] > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    ys, xs = np.nonzero(ink)
    if len(xs) == 0:
        return np.zeros((1, 1, 3), np.uint8), np.zeros((1, 1), bool)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgb = a[y0:y1, x0:x1, :3]
    ink = ink[y0:y1, x0:x1]
    tw = max(1, int(round(width_mm * RES)))
    scale = tw / rgb.shape[1]
    th = max(1, int(round(rgb.shape[0] * scale)))
    rgb = cv2.resize(rgb, (tw, th), interpolation=cv2.INTER_AREA)
    ink = cv2.resize(ink.astype(np.uint8), (tw, th),
                     interpolation=cv2.INTER_NEAREST).astype(bool)
    return rgb, ink


def sewn_colour_field(design):
    """What the stitch-out SHOWS, as RGB at `RES`, on white cloth.

    White deliberately: an element the engine never sewed then reads as white,
    which is a large colour distance from any real ink and so registers as lost —
    the same way it reads to the eye on a white garment. `lit=False` because the
    lit renderer shades a filament as a cylinder for looks, and that shading is
    a lighting model, not thread colour.
    """
    bgr = render_design(design, px_per_mm=RES, fabric_bgr=(255, 255, 255),
                        lit=False)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def disagreement(a_rgb: np.ndarray, s_rgb: np.ndarray) -> tuple:
    """-> (per-pixel CIEDE2000, boolean mask of where it exceeds LOST_DELTA_E
    after the boundary hairline is opened away).

    Split out from `analyse` so the part with the judgement in it can be tested
    on hand-built arrays, without running the engine.
    """
    de = deltaE_ciede2000(
        rgb_to_lab(a_rgb.reshape(-1, 3).astype(np.float64)),
        rgb_to_lab(s_rgb.reshape(-1, 3).astype(np.float64)),
    ).reshape(a_rgb.shape[:2])
    k = np.ones((HALO_OPEN_PX, HALO_OPEN_PX), np.uint8)
    wrong = cv2.morphologyEx((de > LOST_DELTA_E).astype(np.uint8),
                             cv2.MORPH_OPEN, k) > 0
    return de, wrong


def analyse(image_path: str | Path, cfg: PipelineConfig | None = None) -> dict:
    """Digitize `image_path`, then report what `analyse_design` finds lost."""
    cfg = cfg or PipelineConfig()
    image_path = Path(image_path)
    result, plan = digitize(image_path, cfg)
    return analyse_design(image_path, plan_to_design(plan),
                          route=result.design_class)


def analyse_design(image_path: str | Path, design: dict,
                   route: str | None = None, *,
                   registered: Registered | None = None) -> dict:
    """Report the artwork elements the stitch-out `design` lost.

    An element is a connected run of ONE artwork colour. It is "lost" when the
    stitch-out no longer shows that colour there — which covers all three ways
    Kent described the failure in one test:

      * never sewn        -> white cloth shows through, far from any ink colour
      * sewn in the wrong thread -> the colour there is not this element's
      * a knockout filled in     -> the light letter now reads as the dark panel

    Registration is `artfidelity_self.register` on the ink masks, so an element
    counted lost here is lost at the same alignment that instrument scores.
    `registered` is that registration already made by a caller that holds
    several instruments (`tools.eye_pairs`); None registers here.
    """
    image_path = Path(image_path)

    # Align on the same binary fields artfidelity_self uses, then carry that
    # shift to the colour rasters so every layer sits on one canvas.
    if registered is None:
        ours_f = stitch_coverage_field(design)
        art_f = art_ink_field(image_path, float(design["widthMM"]))
        _, O_f, A_f, dx, dy = register(ours_f, art_f)
    else:
        O_f, A_f, dx, dy = (registered.O_f, registered.A_f,
                            registered.dx_mm, registered.dy_mm)
    H, W = O_f.shape

    art_rgb, art_ink = art_colour_field(image_path, float(design["widthMM"]))
    sewn_rgb = sewn_colour_field(design)

    def place_rgb(img, ddx=0.0, ddy=0.0):
        c = np.full((H, W, 3), 255, np.uint8)
        oy = (H - img.shape[0]) // 2 + int(round(ddy * RES))
        ox = (W - img.shape[1]) // 2 + int(round(ddx * RES))
        y0, x0 = max(0, oy), max(0, ox)
        y1, x1 = min(H, oy + img.shape[0]), min(W, ox + img.shape[1])
        if y1 > y0 and x1 > x0:
            c[y0:y1, x0:x1] = img[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        return c

    def place_mask(m, ddx=0.0, ddy=0.0):
        c = np.zeros((H, W), bool)
        oy = (H - m.shape[0]) // 2 + int(round(ddy * RES))
        ox = (W - m.shape[1]) // 2 + int(round(ddx * RES))
        y0, x0 = max(0, oy), max(0, ox)
        y1, x1 = min(H, oy + m.shape[0]), min(W, ox + m.shape[1])
        if y1 > y0 and x1 > x0:
            c[y0:y1, x0:x1] = m[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        return c

    A_rgb = place_rgb(art_rgb, dx, dy)
    A_ink = place_mask(art_ink, dx, dy)
    S_rgb = place_rgb(sewn_rgb)

    px_per_mm2 = RES * RES
    min_px = max(1, int(round(MIN_ELEMENT_MM2 * px_per_mm2)))

    # Compare what the artwork SHOULD look like on white cloth against what the
    # stitch-out actually shows, over the whole frame. Not ink-vs-ground: that
    # distinction is what defeated the two earlier versions of this function.
    #
    #   * ink-only elements miss a knockout that got sewn over, because the
    #     knockout is not ink — `enthusiast_logo`'s white X is invisible that way.
    #   * adding "enclosed ground" does not rescue it either: that shield's
    #     hexagon has BREAKS, so its interior white reaches the frame edge and
    #     is not enclosed by any flood test.
    #
    # Painting the artwork onto white and diffing the whole frame has no such
    # hole. Every failure Kent named is the same measurement here: ink not sewn
    # (white where colour belongs), a knockout filled (colour where white
    # belongs), or the wrong thread (colour where other colour belongs).
    A_show = np.where(A_ink[..., None], A_rgb, np.uint8(255))

    # Segment the DISAGREEMENT, not the artwork. Three versions of this function
    # tried to define an "element" first and then test it, and each definition
    # had a hole:
    #   * ink components merge a red arm into the shield it touches;
    #   * ink + enclosed ground misses a knockout whose outline has breaks;
    #   * whole-frame colour components make the background ONE component, and a
    #     median over it hides a small filled-in patch completely.
    # Per-pixel first, components second, has no such hole: whatever does not
    # look like the artwork is flagged, and contiguous runs of it are the
    # elements. This is the same ordering lesson as `artfidelity_self`'s colour
    # component — subtract per pixel, aggregate afterwards.
    de_px, wrong = disagreement(A_show, S_rgb)

    lab, comps = _components(wrong, min_px)
    thread = O_f >= 0.5
    lost = []
    for c in comps:
        sel = lab == c["label"]
        lost.append({**c,
                     "delta_e": round(float(np.median(de_px[sel])), 1),
                     "cover": round(float(thread[sel].mean()), 3),
                     "ink": bool(A_ink[sel].mean() > 0.5),
                     "mm2": round(c["area_px"] / px_per_mm2, 1)})

    ink_mm2 = float(A_ink.sum()) / px_per_mm2
    lost_mm2 = sum(x["mm2"] for x in lost)

    # COVERAGE, WITHOUT COLOUR AND WITHOUT THE OPENING. Artwork ink carrying no
    # thread -- a set difference of two masks, no CIEDE2000, no `LOST_DELTA_E`,
    # no `HALO_OPEN_PX`, no `MIN_ELEMENT_MM2`. It exists because every filter
    # above it is tuned around a half-millimetre, and on a knit that is exactly
    # the size of the thing being filtered: `pique_knit`'s `pull_comp_mm` is
    # 0.3 and `stitchviz.THREAD_MM` is 0.4, so a correctly-sewn shape already
    # stands 0.3 + 0.2 = 0.50 mm proud of its artwork -- and `HALO_OPEN_PX` is
    # 5 px at RES, which is 0.50 mm. The opening sits ON the pedestal, so the
    # headline number is a threshold detector balanced on a fabric constant and
    # its MAGNITUDE is not quotable (measured 2026-09-20: the same design reads
    # 182.7 / 108.5 / 32.9 / 10.2 / 5.7 / 0.0 mm2 at kernels 3/5/7/9/11/13 px).
    # These three are not: a mask difference cannot be moved by re-tuning a
    # filter, so "did the artwork get sewn" has an answer that survives.
    # `enthusiast_logo` at 80 mm reads 3.5 mm2 of 395.5 (0.90%), largest
    # component 0.88 mm2, NOTHING at or over 1 mm2 -- a rim, not an element --
    # while thread covers 1.51x the ink and the thread field matches the
    # artwork DILATED BY 0.30 mm to IoU 0.856, which is `pull_comp_mm` exactly.
    uncov = A_ink & ~thread
    _n, _lab, _st, _ = cv2.connectedComponentsWithStats(
        uncov.astype(np.uint8), 8)
    _areas = sorted((float(_st[i, cv2.CC_STAT_AREA]) / px_per_mm2
                     for i in range(1, _n)), reverse=True)
    uncovered_ink_mm2 = float(uncov.sum()) / px_per_mm2
    uncovered_worst_mm2 = _areas[0] if _areas else 0.0
    uncovered_elements = sum(1 for a in _areas if a >= MIN_ELEMENT_MM2)

    # THE TOTAL IS TWO DIFFERENT DEFECTS ADDED TOGETHER, and a fixture can be
    # entirely one of them. Each region already knows which (`ink`): a region
    # ON the artwork's ink is somewhere the stitch-out failed to put thread
    # (Kent's "the red arm was lost"); a region OFF it is thread standing on
    # cloth that should be bare -- a column sewing wider than its artwork.
    # Split, because reading the total as "coverage" has already sent a
    # session the wrong way (2026-09-20): a lettering guard was written to
    # recover "lost coverage" on `enthusiast_logo`, whose `lost_frac` of
    # 0.3006 is 118.7 mm2 of overshoot and ZERO mm2 of unsewn ink, and whose
    # `tools/rail_edge.py --bare` coverage reading does not move at all
    # across the change that was blamed for it. Measured the same day, same
    # config, 80 mm left_chest -- the split is not a corner case, it is the
    # normal state of affairs:
    #
    #     enthusiast  lost_frac 0.3002   unsewn   0%   overshoot 100%
    #     tires       lost_frac 0.1270   unsewn   0%   overshoot 100%
    #     becker      lost_frac 0.0509   unsewn  44%   overshoot  56%
    #     bridge      lost_frac 0.1070   unsewn 100%   overshoot   0%
    #
    # The two also move in OPPOSITE directions under the same engine change:
    # satin rails placed further out cover more artwork and spill more
    # thread, so a single number hides which one a change bought. Pin the half
    # a fixture is actually made of, and pin the other half alongside it so the
    # first cannot be bought with it
    # (`tests/test_lettering_coverage_regression.py` does both).
    unsewn_mm2 = sum(x["mm2"] for x in lost if x["ink"])
    overshoot_mm2 = sum(x["mm2"] for x in lost if not x["ink"])

    # Same refusals as the scoring instrument: where the ink mask is unreliable,
    # every number here is unreliable in the same way and for the same reason.
    sat = ink_saturation(image_path)
    if sat > INK_SATURATION_MAX:
        refusal = f"ink mask saturates the frame, {sat:.0%}"
    elif ink_is_ambiguous(image_path):
        refusal = "ink ambiguous (knocked-out lettering)"
    else:
        refusal = None

    lost.sort(key=lambda d: -d["mm2"])
    return {
        "fixture": image_path.name,
        "route": route,
        "lost": len(lost),
        "lost_mm2": round(lost_mm2, 1),
        "lost_frac": round(lost_mm2 / ink_mm2, 4) if ink_mm2 else 0.0,
        # Both halves are expressed against the SAME denominator (the artwork's
        # ink area), so they sum to `lost_frac` (to the last decimal place kept
        # -- three independent roundings, so do not assert equality on them)
        # and either can be compared against it directly.
        # `overshoot_frac` can exceed 1.0 in principle -- it is thread outside
        # the ink measured in units of the ink -- and that is the honest
        # reading, not a bug to clamp.
        "unsewn_mm2": round(unsewn_mm2, 1),
        "unsewn_frac": round(unsewn_mm2 / ink_mm2, 4) if ink_mm2 else 0.0,
        "overshoot_mm2": round(overshoot_mm2, 1),
        "overshoot_frac": round(overshoot_mm2 / ink_mm2, 4) if ink_mm2 else 0.0,
        # Colour-free, unfiltered coverage. `uncovered_elements` is the one to
        # gate on: it counts artwork blobs at or over `MIN_ELEMENT_MM2` with no
        # thread, which is Kent's "the red arm was lost" and nothing else.
        "uncovered_ink_mm2": round(uncovered_ink_mm2, 1),
        "uncovered_ink_frac": (round(uncovered_ink_mm2 / ink_mm2, 4)
                               if ink_mm2 else 0.0),
        "uncovered_worst_mm2": round(uncovered_worst_mm2, 2),
        "uncovered_elements": uncovered_elements,
        "worst_mm2": lost[0]["mm2"] if lost else 0.0,
        "shift_x_mm": round(dx, 1),
        "shift_y_mm": round(dy, 1),
        "refusal": refusal,
        "_lost": lost,
    }


def _resolve(names: list[str]) -> list[Path]:
    out = []
    for n in names:
        p = Path(n)
        out.append(p if p.exists() else ROOT / "testdata" / n)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Report artwork elements the stitch-out lost, from the "
                    "artwork's side — independent of whether the engine ever "
                    "made a shape there.")
    ap.add_argument("images", nargs="*")
    ap.add_argument("--all", action="store_true",
                    help="run over the tracked fixture set")
    ap.add_argument("--csv", type=Path, default=None)
    ap.add_argument("--detail", action="store_true",
                    help="list every lost element with its size and place")
    args = ap.parse_args(argv)

    names = list(FIXTURES) if args.all else args.images
    if not names:
        ap.error("give image paths or --all")

    rows = []
    paths = _resolve(names)
    for i, p in enumerate(paths, 1):
        if not p.exists():
            print(f"skip (missing): {p}", file=sys.stderr)
            continue
        print(f"[{i}/{len(paths)}] {p.name} ...", file=sys.stderr, flush=True)
        r = analyse(p)
        rows.append(r)
        print(f"[{i}/{len(paths)}] {p.name}: {r['lost']} regions "
              f"({r['lost_mm2']} mm2, {100 * r['lost_frac']:.1f}%)",
              file=sys.stderr, flush=True)

    if not rows:
        print("nothing analysed", file=sys.stderr)
        return 1

    head = (f"{'fixture':26s} {'route':12s} {'regions':>8} "
            f"{'mm2':>8} {'% of art':>9} {'worst':>8}")
    print(head)
    print("-" * len(head))
    for r in rows:
        print(f"{r['fixture']:26s} {r['route']:12s} {r['lost']:>8} "
              f"{r['lost_mm2']:>8.1f} {100 * r['lost_frac']:>8.1f}% "
              f"{r['worst_mm2']:>8.1f}"
              + ("   REFUSED" if r["refusal"] else ""))
        # On its own line rather than as two more columns: the table is already
        # 76 characters and this is the reading most fixtures are decided by.
        print(f"{'':26s}   unsewn {r['unsewn_mm2']:>7.1f} mm2 "
              f"({100 * r['unsewn_frac']:.1f}%)   |   "
              f"overshoot {r['overshoot_mm2']:>7.1f} mm2 "
              f"({100 * r['overshoot_frac']:.1f}%)")
        if args.detail and r["_lost"]:
            for d in r["_lost"][:6]:
                print(f"{'':26s}   {d['mm2']:>6.1f} mm2 at "
                      f"({d['cx'] / RES:.0f},{d['cy'] / RES:.0f}) mm, "
                      f"dE {d['delta_e']:>5.1f}, {d['cover'] * 100:.0f}% sewn, "
                      f"{'unsewn ink' if d['ink'] else 'thread on ground'}")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        cols = [k for k in rows[0] if not k.startswith("_")]
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
