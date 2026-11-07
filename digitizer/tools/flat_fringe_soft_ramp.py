#!/usr/bin/env python
"""flat_fringe_soft_ramp: the flat lane's soft-edge cure, measured (2026-11-06).

`stage0_scale_relative_grad` sends `logo_bridge_bar.jpg` (a 400 px JPEG) down
the FLAT lane, where its blue lettering sewed pale Vintage Blue 4752 with a
pale-blue ring round every spoke, and its black waves sewed olive. Two
mechanisms, both the enlarged raster's soft edge (`docs/flat-fringe-soft-
ramp-2026-11-06.md`); the cure is two flags, both OFF on main and both read an
enlarged raster only:

    CURE = flat_page_fringe_soft_ramp + flat_ramp_blend_dissolve

Two modes, committed test art only (no pro file is read or drawn):

    .venv/Scripts/python -m tools.flat_fringe_soft_ramp sheets OUT_DIR [--skip-gradient]
    .venv/Scripts/python -m tools.flat_fringe_soft_ramp md5 [--json OUT] [--off-only]
    .venv/Scripts/python -m tools.flat_fringe_soft_ramp pairs OUT_DIR NAME...

`sheets`: Bridge (113.5 mm hat, 96 mm left chest), golden_tee and the
screenshot (80 mm left chest), each digitized the Studio's way
(`tools.pro_pair.digitize`) as main ships it (gradient routing), under the
flip's routing (`stage0_scale_relative_grad` True), and under the flip's
routing with CURE. One side-by-side JPEG per job, plus a 30 px/mm crop of the
lettering band; one JSON line per arm (stitches, trims, regions, thread ->
sewn mm2).

`md5`: the 15 real flat logos of `tools.stage0_scale_relative` at 80 mm left
chest. Per routing (main, flip), the lane stage 0 picks; where it is "flat",
the md5 of the stitch list with CURE OFF and ON. A non-flat lane never calls
`stage2_quantize.quantize`, the only reader of the two flags, so OFF == ON
there by construction and it is not digitized. `--off-only` runs the OFF arm
alone: the byte-identity check against a checkout without the flags.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
TESTDATA = DIGITIZER / "testdata"

CURE = {"flat_page_fringe_soft_ramp": True, "flat_ramp_blend_dissolve": True}
FLIP = {"stage0_scale_relative_grad": True}
ARMS = (("main", {}), ("flip", FLIP), ("flip+cure", {**FLIP, **CURE}))

JOBS = [
    ("bridge_hat", "photo/logo_bridge_bar.jpg", 113.5, "hat_front"),
    ("bridge_lc", "photo/logo_bridge_bar.jpg", 96.0, "left_chest"),
    ("golden_tee", "photo/logo_golden_tee.jpg", 80.0, "left_chest"),
    ("screenshot", "photo/screenshot_phone_ui_golke.jpg", 80.0, "left_chest"),
]
PPM = 8.0
BAND_PPM = 30.0


def _label(img, text):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 26), (255, 255, 255), -1)
    cv2.putText(out, text, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def _row(imgs):
    h = max(i.shape[0] for i in imgs)
    return np.hstack([cv2.copyMakeBorder(i, 0, h - i.shape[0], 0, 6, cv2.BORDER_CONSTANT,
                                         value=(255, 255, 255)) for i in imgs])


def _band_box(result):
    boxes = [r.polygon.bounds for r in result.regions
             if (getattr(r, "meta", None) or {}).get("text_cluster_id") is not None]
    if not boxes:
        return None
    return (min(b[0] for b in boxes) - 2, min(b[1] for b in boxes) - 2,
            max(b[2] for b in boxes) + 2, max(b[3] for b in boxes) + 2)


def _crop(design, box_mm):
    from digitizer_core import stitchviz
    img = stitchviz.render_design(design, px_per_mm=BAND_PPM)
    x0, _x1, _y0, y1 = stitchviz._bounds(design.get("stitches") or [])
    fx, fy, pad = x0 / 10.0, -y1 / 10.0, 2.0
    bx0, by0, bx1, by1 = box_mm
    px = [int(round((v - o + pad) * BAND_PPM)) for v, o in
          ((bx0, fx), (by0, fy), (bx1, fx), (by1, fy))]
    h, w = img.shape[:2]
    return img[max(0, px[1]):max(1, min(h, px[3])), max(0, px[0]):max(1, min(w, px[2]))]


def stats(d, slug: str, arm: str) -> dict:
    area: dict[str, float] = defaultdict(float)
    small: dict[str, int] = defaultdict(int)
    for r in d.result.regions:
        if not r.meta.get("stitched", True):
            continue
        area[str(r.thread_number)] += r.polygon.area
        small[str(r.thread_number)] += int(r.polygon.area < 3.0)
    return {"slug": slug, "arm": arm, "lane": d.result.design_class,
            "stitches": d.plan.stats.stitch_count, "trims": d.plan.stats.trims,
            "regions": len(d.result.regions), "colours": len(d.design.get("colors", [])),
            "thread_mm2": {k: round(v, 1) for k, v in sorted(area.items(), key=lambda kv: -kv[1])},
            "thread_sub3mm2": dict(small), "secs": round(d.secs, 1)}


def sheets(out_dir: str, skip_gradient: bool = False) -> int:
    from digitizer_core import stitchviz
    from tools import pro_pair as pp
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for slug, rel, width, garment in JOBS:
        done = []
        for arm, extra in ARMS:
            if skip_gradient and arm == "main":
                continue
            d = pp.digitize(TESTDATA / rel, width, garment, extra)
            s = stats(d, slug, arm)
            print(json.dumps(s), flush=True)
            done.append((arm, d, s))
        whole = [_label(stitchviz.render_design(d.design, px_per_mm=PPM),
                        f"{arm}  {s['lane']}  {s['stitches']} st  {s['trims']} trims")
                 for arm, d, s in done]
        cv2.imwrite(str(out / f"{slug}.jpg"), _row(whole), [cv2.IMWRITE_JPEG_QUALITY, 85])
        box = next((b for b in (_band_box(d.result) for _a, d, _s in done) if b), None)
        if box is not None:
            crops = [_label(_crop(d.design, box), f"{arm} lettering") for arm, d, _s in done]
            cv2.imwrite(str(out / f"{slug}_lettering.jpg"), _row(crops),
                        [cv2.IMWRITE_JPEG_QUALITY, 85])
    return 0


def md5(json_out: str | None = None, off_only: bool = False) -> int:
    from digitizer_core import PipelineConfig
    from digitizer_core.stage0_classify import classify
    from digitizer_service.app import _decode as svc_decode, _parse_config
    from tools import pro_pair as pp
    from tools.stage0_scale_relative import rows
    real = [(n, p) for n, p, lab, prov in rows(corpus=False, local=True)
            if lab == "flat" and prov == "real"]
    out = []
    for name, path in real:
        row = {"name": name}
        for routing, extra in (("main", {}), ("flip", FLIP)):
            cfg = PipelineConfig(**_parse_config(json.dumps(pp.request(80.0, "left_chest", extra))))
            lane = classify(svc_decode(path.read_bytes()), cfg).class_
            row[f"{routing}_lane"] = lane
            if lane != "flat":
                continue
            for cure, more in (("off", {}),) + (() if off_only else (("on", CURE),)):
                d = pp.digitize(path, 80.0, "left_chest", {**extra, **more})
                st = json.dumps(d.design.get("stitches"), separators=(",", ":"))
                row[f"{routing}_{cure}"] = {
                    "md5": hashlib.md5(st.encode()).hexdigest()[:12],
                    "stitches": d.plan.stats.stitch_count, "trims": d.plan.stats.trims,
                    "regions": len(d.result.regions), "colours": len(d.design.get("colors", []))}
        print(json.dumps(row), flush=True)
        out.append(row)
    if json_out:
        Path(json_out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0


def pairs(out_dir: str, names: list[str]) -> int:
    """flip | flip+cure at 80 mm left chest for named `stage0_scale_relative`
    rows (the md5 movers): one side-by-side JPEG each."""
    from digitizer_core import stitchviz
    from tools import pro_pair as pp
    from tools.stage0_scale_relative import rows
    paths = {n: p for n, p, _lab, _prov in rows(corpus=False, local=True)}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        imgs = []
        for arm, extra in ARMS[1:]:
            d = pp.digitize(paths[name], 80.0, "left_chest", extra)
            s = stats(d, name, arm)
            print(json.dumps(s), flush=True)
            imgs.append(_label(stitchviz.render_design(d.design, px_per_mm=PPM * 1.5),
                               f"{arm}  {s['lane']}  {s['stitches']} st  {s['trims']} trims"))
        cv2.imwrite(str(out / f"{name}.jpg"), _row(imgs), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    sys.path.insert(0, str(DIGITIZER))
    if argv and argv[0] == "sheets":
        return sheets(argv[1] if len(argv) > 1 else "debug_out/flat_fringe_soft_ramp",
                      skip_gradient="--skip-gradient" in argv)
    if argv and argv[0] == "pairs":
        return pairs(argv[1], argv[2:])
    if argv and argv[0] == "md5":
        return md5(argv[argv.index("--json") + 1] if "--json" in argv else None,
                   off_only="--off-only" in argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
