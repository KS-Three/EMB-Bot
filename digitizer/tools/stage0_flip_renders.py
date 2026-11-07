#!/usr/bin/env python
"""stage0_flip_renders: OFF | ON sheets for `stage0_scale_relative_grad` (PR #1282).

Kent's call on the bucket-(c) tests is a RENDER verdict, not a count: this
digitizes the committed test art the Studio's way (`tools.pro_pair.digitize`,
the service's parser) once with `stage0_scale_relative_grad` False and once
True, renders both with `digitizer_core.stitchviz`, and writes one side-by-side
JPEG per job plus a crop of the lettering band where the art has text clusters.
Committed test art only; no pro file is read or rendered.

    .venv/Scripts/python -m tools.stage0_flip_renders OUT_DIR

Prints one JSON line per job (stitches, trims, colours, threads, lane, tagged
letters), the numbers the PR's table cites.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
TESTDATA = DIGITIZER / "testdata"

# (slug, art, width mm, garment): the pro's boxes for Bridge (hat 113.5 x 64,
# left chest 96 x 76.5), 80 mm left chest for the others (no pro size is read).
JOBS = [
    ("bridge_hat", "photo/logo_bridge_bar.jpg", 113.5, "hat_front"),
    ("bridge_lc", "photo/logo_bridge_bar.jpg", 96.0, "left_chest"),
    ("golden_tee", "photo/logo_golden_tee.jpg", 80.0, "left_chest"),
    ("screenshot", "photo/screenshot_phone_ui_golke.jpg", 80.0, "left_chest"),
]
PPM = 10.0          # whole-design render
BAND_PPM = 30.0     # lettering crop


def _label(img, text):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 26), (255, 255, 255), -1)
    cv2.putText(out, text, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def _pair(a, b):
    h = max(a.shape[0], b.shape[0])
    pad = lambda im: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, 6, cv2.BORDER_CONSTANT,
                                        value=(255, 255, 255))
    return np.hstack([pad(a), pad(b)])


def _band_box(result):
    """Plan-mm (x0, y0, x1, y1) of the tagged text letters, padded; None if none."""
    boxes = [r.polygon.bounds for r in result.regions
             if (getattr(r, "meta", None) or {}).get("text_cluster_id") is not None]
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes) - 2
    y0 = min(b[1] for b in boxes) - 2
    x1 = max(b[2] for b in boxes) + 2
    y1 = max(b[3] for b in boxes) + 2
    return x0, y0, x1, y1


def _crop(design, box_mm):
    from digitizer_core import stitchviz
    img = stitchviz.render_design(design, px_per_mm=BAND_PPM)
    x0, x1, y0, y1 = stitchviz._bounds(design.get("stitches") or [])
    fx, fy = x0 / 10.0, -y1 / 10.0
    pad = 2.0
    bx0, by0, bx1, by1 = box_mm
    px = (int(round((bx0 - fx + pad) * BAND_PPM)), int(round((by0 - fy + pad) * BAND_PPM)),
          int(round((bx1 - fx + pad) * BAND_PPM)), int(round((by1 - fy + pad) * BAND_PPM)))
    h, w = img.shape[:2]
    return img[max(0, px[1]):max(1, min(h, px[3])), max(0, px[0]):max(1, min(w, px[2]))]


def main(out_dir: str) -> int:
    sys.path.insert(0, str(DIGITIZER))
    from digitizer_core import stitchviz
    from tools import pro_pair as pp

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for slug, rel, width, garment in JOBS:
        arms = {}
        for name, flag in (("OFF", False), ("ON", True)):
            d = pp.digitize(TESTDATA / rel, width, garment, {"stage0_scale_relative_grad": flag})
            tagged = sum(1 for r in d.result.regions
                         if (getattr(r, "meta", None) or {}).get("text_cluster_id") is not None)
            threads = sorted({str(r.thread_number) for r in d.result.regions
                              if r.meta.get("stitched", True)})
            arms[name] = (d, {
                "slug": slug, "arm": name, "width_mm": width, "garment": garment,
                "lane": d.result.design_class, "stitches": d.plan.stats.stitch_count,
                "trims": d.plan.stats.trims, "colours": len(d.design.get("colors", [])),
                "regions": len(d.result.regions), "tagged_letters": tagged, "threads": threads,
                "secs": round(d.secs, 1)})
            print(json.dumps(arms[name][1]), flush=True)
        a, b = arms["OFF"][0], arms["ON"][0]
        left = _label(stitchviz.render_design(a.design, px_per_mm=PPM),
                      f"OFF  {arms['OFF'][1]['lane']}  {arms['OFF'][1]['stitches']} st")
        right = _label(stitchviz.render_design(b.design, px_per_mm=PPM),
                       f"ON   {arms['ON'][1]['lane']}  {arms['ON'][1]['stitches']} st")
        cv2.imwrite(str(out / f"{slug}.jpg"), _pair(left, right), [cv2.IMWRITE_JPEG_QUALITY, 88])
        box = _band_box(a.result) or _band_box(b.result)
        if box is not None:
            ca, cb = _crop(a.design, box), _crop(b.design, box)
            cv2.imwrite(str(out / f"{slug}_lettering.jpg"),
                        _pair(_label(ca, "OFF lettering band"), _label(cb, "ON lettering band")),
                        [cv2.IMWRITE_JPEG_QUALITY, 88])
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "debug_out/stage0_flip_renders"))
