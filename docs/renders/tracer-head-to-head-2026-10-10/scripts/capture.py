"""Run pipeline stages 0-4 on one image and dump what stage 4 was handed
(the region masks) plus what it returned, shipped and plain-DP.

usage: python -m ... capture.py SRC OUT PXMM FORCED WORK
  PXMM   0 = native, else INTER_AREA downscale so width = PXMM * 80 px
  FORCED '-' = let stage 0 decide, else forced_class
  WORK   'default' or 'none' (work_px_per_mm=None, native grid)
"""
import dataclasses
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from digitizer_core import pipeline
from digitizer_core.config import PipelineConfig

W_MM = 80.0
PAD = 2


def downscale(img, w):
    h = int(round(img.shape[0] * w / img.shape[1]))
    if img.ndim == 3 and img.shape[2] == 4:
        f = img.astype(np.float32)
        a = f[..., 3:4] / 255.0
        pm = cv2.resize(f[..., :3] * a, (w, h), interpolation=cv2.INTER_AREA)
        aa = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)[..., None]
        rgb = np.where(aa > 1e-6, pm / np.maximum(aa, 1e-6), 255.0)
        return np.clip(np.dstack([rgb, aa * 255.0]), 0, 255).round().astype(np.uint8)
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def regions_json(regions):
    return [{"wkt": r.polygon.wkt, "layer": int(r.meta.get("layer", -1)),
             "thread": int(r.thread_index)} for r in regions]


def main(src, out, pxmm, forced, work):
    out = Path(out)
    (out / "masks").mkdir(parents=True, exist_ok=True)
    path = Path(src)
    if pxmm > 0:
        img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
        img = downscale(img, int(round(pxmm)))
        path = out / "input.png"
        cv2.imwrite(str(path), img)

    cap = {}
    orig = pipeline.vectorize

    def wrap(masks, ti, p, cfg):
        res = orig(masks, ti, p, cfg)
        cap.update(masks=masks, p=p, shipped=res[0])
        plain = dataclasses.replace(cfg, subpixel_edges=False, curve_turn_deg=None)
        cap["plain"] = orig(masks, ti, p, plain)[0]
        return res

    pipeline.vectorize = wrap
    kw = {"target_width_mm": W_MM}
    if forced != "-":
        kw["forced_class"] = forced
    if work == "none":
        kw["work_px_per_mm"] = None
    t = time.time()
    gen = pipeline.build_generation(str(path), PipelineConfig(**kw))
    dt = time.time() - t

    p = cap["p"]
    H, Wd = p.rgb.shape[:2]
    labels = np.zeros((H, Wd), np.int32)
    mm = []
    for i, rm in enumerate(cap["masks"]):
        y0, x0 = rm.origin
        h, w = rm.crop.shape
        labels[y0:y0 + h, x0:x0 + w][rm.crop.astype(bool)] = i + 1
        pad = np.full((h + 2 * PAD, w + 2 * PAD), 255, np.uint8)
        pad[PAD:-PAD, PAD:-PAD][rm.crop.astype(bool)] = 0
        cv2.imwrite(str(out / "masks" / f"m{i:04d}.png"), pad)
        mm.append({"i": i, "y0": int(y0), "x0": int(x0), "layer": int(rm.layer)})
    np.save(out / "labels.npy", labels)
    cv2.imwrite(str(out / "prep_rgb.png"), cv2.cvtColor(p.rgb, cv2.COLOR_RGB2BGR))
    x0, y0, x1, y1 = p.art_bbox
    cls = gen.classification_class
    meta = {
        "src": str(src), "pxmm_req": pxmm, "forced": forced, "work": work,
        "class": cls, "px_per_mm": float(p.px_per_mm),
        "input_px_per_mm": float(p.input_px_per_mm), "upscale": [float(u) for u in p.upscale],
        "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "frame": [H, Wd],
        "pad": PAD, "masks": mm, "seconds": round(dt, 1),
    }
    (out / "meta.json").write_text(json.dumps(meta))
    (out / "arm_shipped.json").write_text(json.dumps(regions_json(cap["shipped"])))
    (out / "arm_plain.json").write_text(json.dumps(regions_json(cap["plain"])))
    print(f"{out.name}: class={cls} px/mm={p.px_per_mm:.2f} in={p.input_px_per_mm:.2f} "
          f"frame={Wd}x{H} masks={len(mm)} shipped={len(cap['shipped'])} "
          f"plain={len(cap['plain'])} {dt:.1f}s")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], float(a[2]), a[3], a[4])
