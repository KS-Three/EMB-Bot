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

So this instrument asks the question from the ARTWORK's side. It never looks at
the region list, which is exactly the blind spot: it takes the artwork's own
connected components of ink and asks, for each one, how much thread landed on
it. An element the pipeline dropped before stage 3 ever made a region has no
shape to be "uncovered" — but it is still a blob of ink with no thread on it,
and that is visible here.

Two directions, because Kent's notes contain both:

    dropped   artwork ink that carries (almost) no thread — a limb, a word, a
              detail the stitch-out simply does not have.
    flooded   artwork GROUND enclosed by ink that carries thread anyway — a
              knocked-out letter sewn over, so the lettering disappears into
              the panel. `logo_hotel_fremont`'s "EAT | STAY | PLAY" is this
              shape of failure, not the first one.

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
from tools.artfidelity_self import (FIXTURES, RES, art_ink_field,  # noqa: E402
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

DROPPED_COVER_MAX = 0.15
# An ink component with less than this fraction of its area carrying thread is
# reported as dropped. JUDGEMENT. Not 0.0: a satin border that clips the edge of
# a component, or a travel stitch crossing it, puts a little thread on something
# that is otherwise absent, and a detector that demanded exactly zero would miss
# those. Not high either — above ~0.3 a partially-sewn element starts being a
# coverage problem (which `preflight.ARTWORK_UNCOVERED` already owns for shapes
# that exist) rather than a missing one.

COLOUR_BIN = 24
# Channel width, 0-255, for grouping artwork pixels into one "colour". An
# element is a connected run of pixels within one bin — which is what makes the
# red arm a separate element from the shield it sits on. JUDGEMENT: wide enough
# that JPEG ringing and anti-alias fringe do not shatter a flat colour into
# stripes, narrow enough to keep visibly different colours apart. Flat
# spot-colour art (what this instrument is for) has colours far further apart
# than one bin; a smooth gradient shatters into bands, which is why gradient
# artwork is refused rather than scored here.

HALO_OPEN_PX = 5
# Morphological opening kernel, in pixels at RES (so 0.5 mm), applied to the
# disagreement mask before it is broken into elements. Every shape boundary
# disagrees by a hairline — thread lands a fraction of a millimetre off the ink
# edge — and that is Kent's OTHER complaint (smoothness), not a lost element.
# Opening at half a millimetre removes those outlines and keeps anything with
# real width. JUDGEMENT: one thread is 0.4 mm, so this is "thinner than a
# stitch" rounded up to an odd kernel.

LOST_DELTA_E = 20.0
# Median CIEDE2000 between an artwork element's own colour and what the
# stitch-out actually shows there. Above this the element does not read as
# itself any more — it is missing, or sewn in something else, or a knockout
# filled in. JUDGEMENT, sanity-anchored on the shipped scale: preflight calls
# 10.0 "clearly different", and this is deliberately well above that, because
# the question here is not "is the colour off" but "is the element GONE".

FLOODED_COVER_MIN = 0.85
# The mirror: an enclosed GROUND component (a counter, a knockout) with more
# than this fraction sewn has been filled in, and whatever it was supposed to
# read as is gone. Deliberately strict — a little thread bleeding into a counter
# from the surrounding satin is normal and is a pull-compensation question, not
# a lost element.


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


def _enclosed_ground(ink: np.ndarray) -> np.ndarray:
    """Ground fully enclosed by ink — counters, knockouts, the hole in an O.

    Flood the ground inward from the frame border; whatever the flood cannot
    reach is enclosed. The border itself is padded first so a component touching
    the edge is still reachable and therefore still counted as outside.
    """
    h, w = ink.shape
    ground = (~ink).astype(np.uint8)
    pad = np.zeros((h + 2, w + 2), np.uint8)
    pad[1:-1, 1:-1] = ground
    ff = pad.copy()
    mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, mask, (0, 0), 2)
    outside = (ff[1:-1, 1:-1] == 2)
    return (ground > 0) & ~outside


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


def colour_elements(rgb, ink, min_px):
    """Connected runs of one artwork colour -> (label image, [component stats]).

    This is what makes an "element" the thing Kent's eye calls one: the red arm
    is its own element even though it touches the shield, because it is a
    different colour. Ink-vs-ground connectivity cannot see that — on an
    alpha-keyed logo the whole badge is one blob, which is exactly why the first
    version of this instrument reported zero dropped elements on a design with a
    visibly missing limb.
    """
    binned = (rgb.astype(np.int32) // COLOUR_BIN).astype(np.int32)
    key = binned[..., 0] * 10000 + binned[..., 1] * 100 + binned[..., 2]
    key = np.where(ink, key, -1)
    out_lab = np.zeros(key.shape, np.int32)
    comps = []
    next_label = 1
    for k in np.unique(key):
        if k < 0:
            continue
        lab, cs = _components(key == k, min_px)
        for c in cs:
            out_lab[lab == c["label"]] = next_label
            comps.append({**c, "label": next_label})
            next_label += 1
    return out_lab, comps


def analyse(image_path: str | Path, cfg: PipelineConfig | None = None) -> dict:
    """Digitize `image_path` and report the artwork elements the stitch-out lost.

    An element is a connected run of ONE artwork colour. It is "lost" when the
    stitch-out no longer shows that colour there — which covers all three ways
    Kent described the failure in one test:

      * never sewn        -> white cloth shows through, far from any ink colour
      * sewn in the wrong thread -> the colour there is not this element's
      * a knockout filled in     -> the light letter now reads as the dark panel

    Registration is `artfidelity_self.register` on the ink masks, so an element
    counted lost here is lost at the same alignment that instrument scores.
    """
    cfg = cfg or PipelineConfig()
    image_path = Path(image_path)

    result, plan = digitize(image_path, cfg)
    design = plan_to_design(plan)

    # Align on the same binary fields artfidelity_self uses, then carry that
    # shift to the colour rasters so every layer sits on one canvas.
    ours_f = stitch_coverage_field(design)
    art_f = art_ink_field(image_path, float(design["widthMM"]))
    _, O_f, A_f, dx, dy = register(ours_f, art_f)
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
    de_px = deltaE_ciede2000(
        rgb_to_lab(A_show.reshape(-1, 3).astype(np.float64)),
        rgb_to_lab(S_rgb.reshape(-1, 3).astype(np.float64)),
    ).reshape(A_show.shape[:2])
    wrong = de_px > LOST_DELTA_E

    # Open with a small kernel first: every shape boundary carries a hairline of
    # disagreement (thread lands a fraction of a millimetre off the ink edge, and
    # that is a smoothness question, not a lost element). Without this the report
    # is a list of one-pixel outlines around everything.
    k = np.ones((HALO_OPEN_PX, HALO_OPEN_PX), np.uint8)
    wrong = cv2.morphologyEx(wrong.astype(np.uint8), cv2.MORPH_OPEN, k) > 0

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
        "route": result.design_class,
        "elements": len(comps),
        "lost": len(lost),
        "lost_mm2": round(lost_mm2, 1),
        "lost_frac": round(lost_mm2 / ink_mm2, 4) if ink_mm2 else 0.0,
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
        print(f"[{i}/{len(paths)}] {p.name}: {r['lost']} lost of "
              f"{r['elements']} elements ({r['lost_mm2']} mm2)",
              file=sys.stderr, flush=True)

    if not rows:
        print("nothing analysed", file=sys.stderr)
        return 1

    head = (f"{'fixture':26s} {'route':12s} {'elems':>6} {'lost':>6} "
            f"{'mm2':>8} {'% ink':>7} {'worst':>8}")
    print(head)
    print("-" * len(head))
    for r in rows:
        print(f"{r['fixture']:26s} {r['route']:12s} {r['elements']:>6} "
              f"{r['lost']:>6} {r['lost_mm2']:>8.1f} "
              f"{100 * r['lost_frac']:>6.1f}% {r['worst_mm2']:>8.1f}"
              + ("   REFUSED" if r["refusal"] else ""))
        if args.detail and r["_lost"]:
            for d in r["_lost"][:6]:
                print(f"{'':26s}   {d['mm2']:>6.1f} mm2 at "
                      f"({d['cx'] / RES:.0f},{d['cy'] / RES:.0f}) mm, "
                      f"dE {d['delta_e']:>5.1f}, {d['cover'] * 100:.0f}% sewn")

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
