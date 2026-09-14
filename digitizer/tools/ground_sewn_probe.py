#!/usr/bin/env python
"""Probe: would a GROUND_SEWN check fire, and only where it should?

The candidate test: a region that SPANS the design and wears the artwork's
own border colour is the page behind the logo rather than part of it.

Two candidate colour readings are printed side by side, because they do not
agree and the difference is the whole design question:

  dE_thread  — the SPOOL the region sews against the border colour. What the
               customer sees on the cloth, but a cap/snap can move it a long
               way from the artwork (summit's vignette sews Charcoal 4174).
  dE_art     — the region's OWN artwork pixels (median RGB inside an eroded
               mask, background excluded) against the border colour. What the
               region actually IS, before any thread decision.

Run from digitizer/:  .venv/Scripts/python tools/ground_sewn_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from skimage.color import deltaE_ciede2000  # noqa: E402

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import run_stages  # noqa: E402
from digitizer_core.stage1_prep import _dominant_border_color, prep  # noqa: E402
from digitizer_core.threads import CHART, rgb_to_lab  # noqa: E402

# name, path, is this design's ground ACTUALLY being sewn (ground truth by eye)
CASES = [
    ("golke",        "testdata/photo/logo_gaulke_roofing.png", True),
    ("summit",       "testdata/photo/summit_badge.png",        True),
    ("tires",        "testdata/logo_script_tires.png",         False),
    ("logo_whitebg", "testdata/logo_whitebg.png",              False),
    ("logo_alpha",   "testdata/logo_alpha.png",                False),
    ("ribbon_curve", "testdata/ribbon_curve.png",              False),
    ("bg_uncertain", "testdata/bg_uncertain.png",              False),
    ("becker",       "testdata/becker_marine_logo.png",        False),
    ("enthusiast",   "testdata/photo/enthusiast_logo.png",     False),
    ("bridge_bar",   "testdata/photo/logo_bridge_bar.jpg",     False),
    ("golden_tee",   "testdata/photo/logo_golden_tee.jpg",     False),
    ("drone",        "testdata/photo/drone_render.png",        False),
]


def de(a, b) -> float:
    la = rgb_to_lab(np.asarray(a, np.uint8).reshape(1, 3))
    lb = rgb_to_lab(np.asarray(b, np.uint8).reshape(1, 3))
    return float(deltaE_ciede2000(la, lb)[0])


def region_art_rgb(p, region, px_per_mm, art_bbox):
    """Median artwork RGB under `region`, same transform preflight uses."""
    x0, y0, x1, y1 = art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h, w = p.rgb.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    rings = [region.polygon.exterior] + list(region.polygon.interiors)
    for i, ring in enumerate(rings):
        pts = np.asarray(ring.coords, np.float64)
        pts[:, 0] = pts[:, 0] * px_per_mm + cx
        pts[:, 1] = pts[:, 1] * px_per_mm + cy
        cv2.fillPoly(mask, [pts.astype(np.int32)], 0 if i else 1)
    mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
    sel = (mask > 0) & (~p.bg_mask)
    if sel.sum() < 30:
        return None
    return np.median(p.rgb[sel], axis=0)


print(f"{'case':14s} {'span%':>7s} {'area%':>7s} {'dE_thread':>10s} {'dE_art':>8s}  truth")
print("-" * 70)
for name, rel, truth in CASES:
    path = ROOT / rel
    if not path.exists():
        print(f"{name:14s}  MISSING {rel}")
        continue
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    try:
        result = run_stages(path, cfg)
        p = prep(path, cfg)
    except Exception as exc:
        print(f"{name:14s}  ERROR {type(exc).__name__}: {exc}")
        continue

    border_rgb = _dominant_border_color(p.rgb)
    total = sum(r.area_mm2 for r in result.regions) or 1.0
    dw, dh = result.design_size_mm

    rows = []
    for r in result.regions:
        bx0, by0, bx1, by1 = r.polygon.bounds
        span = (min(1.0, (bx1 - bx0) / dw if dw else 0)
                * min(1.0, (by1 - by0) / dh if dh else 0))
        art = region_art_rgb(p, r, result.px_per_mm, p.art_bbox)
        rows.append((r.area_mm2 / total, span,
                     de(CHART[r.thread_index].rgb, border_rgb),
                     de(art, border_rgb) if art is not None else float("nan")))
    rows.sort(reverse=True)
    frac, span, d_thread, d_art = rows[0]
    print(f"{name:14s} {span*100:6.1f}% {frac*100:6.1f}% {d_thread:10.2f} {d_art:8.2f}  "
          f"{'GROUND' if truth else 'clean'}")
