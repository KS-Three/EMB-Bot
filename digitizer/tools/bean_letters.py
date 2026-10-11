#!/usr/bin/env python
"""Bean letters OFF beside ON, as STITCHES — the render Kent flips
`cfg.bean_letter_max_stroke_mm` on (`docs/superpowers/specs/2026-10-02-bean-
letters-design.md`).

Each logo is digitized once (stages 0-4), then finished and planned with the
knob OFF and at the line, and every text cluster is rendered both ways in
thread through `stitchviz`, the same renderer the review screen's preview
matches. Per logo it prints stitches, trims, how many shapes went bean, and
`legibility.measure`'s OCR score — which needs the tesseract binary and reads
None without it. The score is a yardstick for lettering only (ROADMAP gate 4:
no quality claim on a raw agreement number); the renders are the evidence.

The low-resolution arms are the logos downsampled the way
`tools/lowres_detail.py` does it (INTER_AREA; a JPEG stays a JPEG, q90).

    .venv/Scripts/python tools/bean_letters.py OUTDIR
    .venv/Scripts/python tools/bean_letters.py OUTDIR --logos bridge fremont5 --line 0.8
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# name -> (fixture, source px/mm to downsample to, or None for the file as committed)
LOGOS = {
    "bridge": ("photo/logo_bridge_bar.jpg", None),
    "enthusiast5": ("photo/enthusiast_logo.png", 5.0),
    "fremont5": ("photo/logo_hotel_fremont.webp", 5.0),
    "screenshot5": ("photo/screenshot_phone_ui_golke.jpg", 5.0),
    "fremont": ("photo/logo_hotel_fremont.webp", None),
}
RENDER_PX_PER_MM = 12.0


def _source(logo: str, scratch: Path, width: float) -> Path:
    from digitizer_core import PipelineConfig
    from digitizer_core.stage1_prep import prep

    rel, src = LOGOS[logo]
    path = ROOT / "testdata" / rel
    if src is None:
        return path
    native = prep(str(path), PipelineConfig(target_width_mm=width, garment_id="left_chest", work_px_per_mm=None))
    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    scale = src / native.input_px_per_mm
    if scale < 1.0:
        raw = cv2.resize(raw, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    jpeg = path.suffix.lower() in (".jpg", ".jpeg")
    out = scratch / f"{logo}{'.jpg' if jpeg else '.png'}"
    cv2.imwrite(str(out), raw, [cv2.IMWRITE_JPEG_QUALITY, 90] if jpeg else [])
    return out


def _label(img: np.ndarray, text: str) -> np.ndarray:
    bar = np.full((28, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def run(logo: str, line: float, width: float, out: Path, scratch: Path) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.beanletters import BEAN_LETTER_KEY
    from digitizer_core.legibility import cluster_boxes, measure, render_crop
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.stitchviz import render_design

    path = _source(logo, scratch, width)
    base = dict(target_width_mm=width, garment_id="left_chest", max_colors=6)
    gen = build_generation(str(path), PipelineConfig(**base))
    row: dict = {"logo": logo, "source_px_per_mm": round(gen.p.input_px_per_mm, 2), "line_mm": line}
    crops: dict[str, list[np.ndarray]] = {}
    for arm, extra in (("off", {}), ("on", {"bean_letter_max_stroke_mm": line})):
        cfg = PipelineConfig(**base, **extra)
        result = finish_generation(gen.fork(), cfg)
        plan = plan_stitches(result, cfg)
        m = measure(gen.p, result, plan)
        row[arm] = {"stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
                    "bean_shapes": sum(1 for r in result.regions if r.meta.get(BEAN_LETTER_KEY)),
                    "legibility": m.get("legibility")}
        design = plan_to_design(plan)
        img = render_design(design, px_per_mm=RENDER_PX_PER_MM)
        for cid, box in cluster_boxes(result.regions):
            crop = render_crop(img, design, box, px_per_mm=RENDER_PX_PER_MM)
            if crop is not None and crop.size:
                crops.setdefault(cid, []).append(_label(np.ascontiguousarray(crop), f"{logo} {cid[:6]} {arm.upper()}"))
    for cid, pair in crops.items():
        w = max(c.shape[1] for c in pair)
        pair = [np.pad(c, ((0, 0), (0, w - c.shape[1]), (0, 0)), constant_values=255) for c in pair]
        cv2.imwrite(str(out / f"{logo}_{cid[:6]}_off_above_on.jpg"), np.vstack(pair), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--logos", nargs="+", default=list(LOGOS), choices=list(LOGOS))
    ap.add_argument("--line", type=float, default=1.0)
    ap.add_argument("--width", type=float, default=80.0)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory() as scratch:
        for logo in a.logos:
            r = run(logo, a.line, a.width, a.out, Path(scratch))
            rows.append(r)
            off, on = r["off"], r["on"]
            print(f"{logo:12s} src {r['source_px_per_mm']:5.2f} px/mm  bean shapes {on['bean_shapes']:3d}  "
                  f"stitches {off['stitches']:6d} -> {on['stitches']:6d}  trims {off['trims']:4d} -> {on['trims']:4d}  "
                  f"legibility {off['legibility']} -> {on['legibility']}", flush=True)
    (a.out / "bean_letters.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
