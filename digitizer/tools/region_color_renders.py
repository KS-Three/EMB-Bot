#!/usr/bin/env python
"""Contact sheets for `cfg.region_color`: the same logo sewn by each arm.

This is a COLOUR change, and DOCTRINE's standing rule is that a claim about
what something looks like is settled by a picture, not by a cone list. One
row per design, one panel per arm, the artwork on the left, each panel
captioned with its cone count, stops, stitches and trims.

    .venv/Scripts/python -m tools.region_color_renders           # the three
    .venv/Scripts/python -m tools.region_color_renders --out D   # elsewhere

Renders are gitignored (`renders/` is not in the repo); this writes PNGs and
prints their paths for a session to hand to Kent.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OMP_NUM_THREADS", "1")

import cv2                                                     # noqa: E402
import numpy as np                                             # noqa: E402

from digitizer_core.adapter import plan_to_design              # noqa: E402
from digitizer_core.config import PipelineConfig               # noqa: E402
from digitizer_core.pipeline import digitize                   # noqa: E402
from digitizer_core.stitchviz import render_design             # noqa: E402

ARMS = ("mean", "median", "modal")

# The three logos Kent reviewed on 2026-09-03, which is the panel this change
# has to be judged on — real customer art on the gradient lane.
DESIGNS = [
    ("bridge_bar", "photo/logo_bridge_bar.jpg"),
    ("hotel_fremont", "photo/logo_hotel_fremont.webp"),
    ("golden_tee", "photo/logo_golden_tee.jpg"),
]

PANEL_H = 520
CAPTION_H = 54


def _panel(img: np.ndarray, caption: str, sub: str) -> np.ndarray:
    h, w = img.shape[:2]
    scale = (PANEL_H - CAPTION_H) / max(h, 1)
    img = cv2.resize(img, (max(1, int(w * scale)), PANEL_H - CAPTION_H),
                     interpolation=cv2.INTER_AREA)
    pad = np.full((CAPTION_H, img.shape[1], 3), 250, np.uint8)
    cv2.putText(pad, caption, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(pad, sub, (8, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (90, 90, 90), 1, cv2.LINE_AA)
    return np.vstack([img, pad])


def _row(panels: list[np.ndarray]) -> np.ndarray:
    h = max(p.shape[0] for p in panels)
    out = []
    for p in panels:
        if p.shape[0] < h:
            p = np.vstack([p, np.full((h - p.shape[0], p.shape[1], 3), 250,
                                      np.uint8)])
        out.append(p)
        out.append(np.full((h, 8, 3), 250, np.uint8))
    return np.hstack(out[:-1])


def sheet(name: str, rel: str, out: Path, mm: float, colors: int) -> Path:
    src = ROOT / "testdata" / rel
    art = cv2.imread(str(src), cv2.IMREAD_COLOR)
    panels = [_panel(art, f"{name} - artwork", f"{src.name}")]
    for arm in ARMS:
        result, plan = digitize(str(src), PipelineConfig(
            target_width_mm=mm, max_colors=colors, satin=True,
            garment_id="left_chest", region_color=arm))
        img = render_design(plan_to_design(plan))
        cones = {c.get("number") for c in plan.palette}
        panels.append(_panel(
            img, f"region_color = {arm}",
            f"{len(cones)} cones, {len(plan.blocks)} blocks, "
            f"{plan.stats.stitch_count} st, {plan.stats.trims} tr"))
    path = out / f"region_color_{name}_{colors}c_{int(mm)}mm.png"
    cv2.imwrite(str(path), _row(panels))
    return path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "renders")
    ap.add_argument("--colors", type=int, default=6)
    ap.add_argument("--mm", type=float, default=80.0)
    ap.add_argument("--design", action="append", dest="only")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rel in DESIGNS:
        if args.only and name not in args.only:
            continue
        if not (ROOT / "testdata" / rel).exists():
            print(f"  (missing: {rel})")
            continue
        print(sheet(name, rel, args.out, args.mm, args.colors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
