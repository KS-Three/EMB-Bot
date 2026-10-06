#!/usr/bin/env python
"""What if a small mixed region read its INK, not its centre? — a probe, kept
so its numbers can be re-run. It is not a fix and builds nothing.

The SLIC+RAG lane hands the palette one colour per region: the modal mean
(`cfg.robust_region_colour`, ON since 2026-09-10), which sits on the region's
median. That cured the big flat region full of drawn-on inclusions. It cannot
cure a SMALL shape on a low-resolution logo, because there the median itself
is anti-aliasing: `art/logo_mfab_lc.png` is 148 x 389 px, 4.71 px/mm at
80 mm, so a 0.5 mm white stroke is ~2.4 source pixels and most of its pixels
are a grey nobody drew. The palette then rightly buys grey cones: 6 on a
black-and-white logo, 2,718 stitches of grey and 30 of white.

This probe rewrites the raster `kept_masks_to_quant` reads so that a region
whose grey spans at least `--span` between its 10th and 90th percentile takes
the mean of its extreme decile instead — the light end when the region is
mostly light, the dark end otherwise — and reports cones and per-block
stitches against the unpatched engine. `--max-src-px` limits it to regions at
most that many SOURCE pixels wide (0 = no width gate).

WHERE IT STANDS (measured 2026-10-05, nine gradient logos, the defaults
below; DOCTRINE "A small shape on a low-resolution logo has no pixel of its
own ink"): an OPEN LEAD, not a fix. `logo_golke_roofing` 5 cones -> 2 by
rewriting 27.8 mm2; `logo_mfab_lc` white 30 -> 1,859 stitches with 909 left
in off-shades; `logo_toat_beanie` not cured; `drone_render`,
`logo_golden_tee` and both Fremonts unmoved; and `logo_bridge_bar` WORSE —
teal 227 -> 1,882 stitches — because its thin bands are JPEG ringing, and a
halo wants dissolving where a stroke wants its ink. The rule plus
`cfg.dissolve_phantom_blends` is untested.

`--side` exists because the choice it names once changed silently between
two scratch copies of this probe, and a whole nine-logo run was read as "the
width gate cures nothing" when the side rule had moved. `relative` is that
broken variant, kept so the difference can be shown rather than remembered.

It is an instrument: it monkeypatches one function for the length of a run
and changes nothing in the engine.

    .venv/bin/python -m tools.stroke_colour_probe                    # nine gradient logos
    .venv/bin/python -m tools.stroke_colour_probe --fixture art/logo_mfab_lc.png
    .venv/bin/python -m tools.stroke_colour_probe --max-src-px 0     # no width gate
    .venv/bin/python -m tools.stroke_colour_probe --json build/stroke_colour.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from digitizer_core import stage2_photo_segment as s2
from tools._console import utf8_console
from tools.eye_pairs.features import base_cfg, digitize_once

# The nine gradient-class logos of the 2026-10-05 run: (path under testdata/,
# width mm, garment). `screenshot` is left out (Kent, 2026-09-30: not artwork
# a customer sends) and `logo_toat_machine` is `logo_toat_beanie`'s artwork.
FIXTURES: dict[str, tuple[float, str]] = {
    "photo/drone_render.png": (80.0, "left_chest"),
    "photo/logo_golden_tee.jpg": (80.0, "left_chest"),
    "photo/logo_bridge_bar.jpg": (80.0, "left_chest"),
    "photo/logo_hotel_fremont.webp": (92.5, "patch"),
    "photo/logo_gaulke_roofing.png": (80.0, "left_chest"),
    "art/logo_hotel_fremont_patch.png": (80.0, "left_chest"),
    "art/logo_golke_roofing.png": (80.0, "left_chest"),
    "art/logo_mfab_lc.png": (80.0, "left_chest"),
    "art/logo_toat_beanie.png": (80.0, "left_chest"),
}


def region_features(p, r) -> dict | None:
    """One region's grey statistics, or None when it has no pixels."""
    y0, x0 = r.origin
    h, w = r.crop.shape
    px = p.rgb[y0:y0 + h, x0:x0 + w][r.crop].astype(float)
    if not len(px):
        return None
    g = px.mean(1)
    lo, hi = np.percentile(g, 10), np.percentile(g, 90)
    dt = cv2.distanceTransform(np.pad(r.crop, 1).astype(np.uint8), cv2.DIST_L2, 5)
    width_mm = 2.0 * float(dt.max()) / p.px_per_mm
    src = float(p.input_px_per_mm or p.px_per_mm)
    a, b = lo + 0.3 * (hi - lo), lo + 0.7 * (hi - lo)
    return {
        "area_mm2": round(float(r.crop.sum()) / p.px_per_mm ** 2, 2),
        "width_mm": round(width_mm, 2),
        "width_src_px": round(width_mm * src, 1),
        "mean": round(float(g.mean())),
        "p10": round(float(lo)),
        "p90": round(float(hi)),
        # share of pixels in the middle 40% of the region's own grey range
        "mid": round(float(((g > a) & (g < b)).mean()), 2),
        "chroma": round(float((px.max(1) - px.min(1)).mean())),
    }


def _blocks(design: dict) -> list[tuple[str, int]]:
    """[(hex, stitches)] per colour block, in sewing order."""
    cols, out, n = design.get("colors") or [], [], 0
    for s in design.get("stitches") or []:
        if s["type"] == "color":
            out.append(n)
            n = 0
        elif s["type"] == "stitch":
            n += 1
    out.append(n)
    return [("#%02x%02x%02x" % (c["r"], c["g"], c["b"]), k) for c, k in zip(cols, out)]


def run(art: Path, width_mm: float, garment: str, *, probe: bool,
        span: float, max_src_px: float, side: str = "absolute") -> dict:
    """Digitize `art` at the Studio's config, with or without the rule."""
    seen: dict = {"wide": [], "regions": 0}
    orig = s2.kept_masks_to_quant

    def patched(p, cfg, kept, *a, **kw):
        rgb = p.rgb.copy() if probe else p.rgb
        seen["regions"] = len(kept)
        for r in kept:
            f = region_features(p, r)
            if f is None or f["p90"] - f["p10"] < span:
                continue
            f["hit"] = bool(max_src_px <= 0 or f["width_src_px"] <= max_src_px)
            seen["wide"].append(f)
            if probe and f["hit"]:
                y0, x0 = r.origin
                h, w = r.crop.shape
                win = rgb[y0:y0 + h, x0:x0 + w]
                px = win[r.crop].astype(float)
                g = px.mean(1)
                lo, hi = np.percentile(g, 10), np.percentile(g, 90)
                cut = 128.0 if side == "absolute" else (lo + hi) / 2
                pick = g >= hi if g.mean() >= cut else g <= lo
                win[r.crop] = px[pick].mean(0).round().astype(np.uint8)
        return orig(replace(p, rgb=rgb) if probe else p, cfg, kept, *a, **kw)

    s2.kept_masks_to_quant = patched
    try:
        gen, _result, _plan, design = digitize_once(art, base_cfg(width_mm, garment))
    finally:
        s2.kept_masks_to_quant = orig
    blocks = _blocks(design)
    hit = [f for f in seen["wide"] if f["hit"]]
    return {
        "class": gen.classification_class,
        "cones": len({c for c, _ in blocks}),
        "stitches": sum(n for _, n in blocks),
        "blocks": blocks,
        "regions": seen["regions"],
        "wide_span": len(seen["wide"]),
        "wide_span_mm2": round(sum(f["area_mm2"] for f in seen["wide"]), 1),
        "hit": len(hit),
        "hit_mm2": round(sum(f["area_mm2"] for f in hit), 1),
        "features": seen["wide"],
    }


def main(argv: list[str]) -> int:
    utf8_console()          # the table below carries →
    from tests.conftest import TESTDATA

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fixture", action="append", default=None,
                    help="path under testdata/ (repeatable); default: the nine gradient logos")
    ap.add_argument("--span", type=float, default=60.0,
                    help="minimum p10..p90 grey span for a region to qualify (default 60)")
    ap.add_argument("--max-src-px", type=float, default=4.0,
                    help="widest region, in SOURCE pixels, the rule rewrites; 0 = no gate (default 4)")
    ap.add_argument("--side", choices=("absolute", "relative"), default="absolute",
                    help="which end a region takes: light when its mean grey is >= 128 "
                         "(absolute), or >= the midpoint of its own p10..p90 (relative)")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    names = args.fixture or list(FIXTURES)
    print(f"rule: p10..p90 span >= {args.span:g}, "
          f"width <= {args.max_src_px:g} source px" + (" (no gate)" if args.max_src_px <= 0 else "")
          + f", side {args.side}")
    print("| fixture (class) | cones base → probe | stitches base → probe "
          "| wide-span regions / mm² | rewritten / mm² |")
    print("|---|---|---|---|---|")
    out = {}
    for name in names:
        width_mm, garment = FIXTURES.get(name, (80.0, "left_chest"))
        rows = [run(TESTDATA / name, width_mm, garment, probe=on,
                    span=args.span, max_src_px=args.max_src_px, side=args.side)
                for on in (False, True)]
        base, probe = rows
        out[name] = {"base": base, "probe": probe}
        print(f"| `{Path(name).stem}` ({base['class']}) | {base['cones']} → {probe['cones']} "
              f"| {base['stitches']} → {probe['stitches']} "
              f"| {base['wide_span']} / {base['wide_span_mm2']} "
              f"| {base['hit']} / {base['hit_mm2']} |", flush=True)
        for label, row in (("base", base), ("probe", probe)):
            print(f"|   {label} blocks | " + ", ".join(f"{c} {n}" for c, n in row["blocks"]) + " | | | |")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
