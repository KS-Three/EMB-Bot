#!/usr/bin/env python
"""Render tatami against the "fur" fill, and measure what fur changes.

Three arms on one artwork: plain tatami (the shipped default), fur "short"
and fur "long" (`machine.FUR_STYLES`, gate-1 candidates). Writes

  <out>/<stem>_full.png ... the whole design, one panel per arm
  <out>/<stem>_zoom.png ... the largest fill shape, close up, one panel per arm
  <out>/<stem>.json ....... per arm: design sha256, stitch / trim counts, and
                            the along-row fill stitch lengths (min, median,
                            max, how many under MIN_STITCH_MM)

and prints the JSON. Run it twice and compare the sha256 values to check fur
is deterministic across processes.

    python -m tools.fur_render photo/fur_ramp.png --width 40 \
        --out ../docs/renders/claude-fur-tatami

Report-only; changes nothing. Written 2026-10-14 with the fur fill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize, machine  # noqa: E402
from digitizer_core import stitches as st  # noqa: E402
from digitizer_core.adapter import UNITS_PER_MM, plan_to_design  # noqa: E402
from digitizer_core.stitchviz import _frame, render_design  # noqa: E402

ARMS = {
    "tatami": {},
    "fur short": {"fill_technique": "fur", "fur_style": "short"},
    "fur long": {"fill_technique": "fur", "fur_style": "long"},
}
PAD_MM = 2.0


def _design_sha(design: dict) -> str:
    recs = [(s["x"], s["y"], s["type"]) for s in design["stitches"]]
    return hashlib.sha256(json.dumps(recs).encode()).hexdigest()


def _along_row(plan) -> list[float]:
    """Fill stitch lengths that run along a row: both ends on the same row
    line, i.e. the step is parallel to the shape's fill direction. A row
    turn moves one row across and is left out."""
    out = []
    for block, run in plan.iter_runs():
        if run.kind != st.FILL or len(run.points) < 2:
            continue
        pts = run.points
        steps = list(zip(pts, pts[1:]))
        # The row direction is the run's most common step direction.
        angs = [round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0, 2)
                for a, b in steps if math.dist(a, b) > 1.5]
        if not angs:
            continue
        row_deg = max(set(angs), key=angs.count)
        t = math.radians(row_deg)
        for a, b in steps:
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy)
            # parallel to the row to within a hundredth of a degree
            if abs(-dx * math.sin(t) + dy * math.cos(t)) < 1e-3 * d + 1e-9:
                out.append(d)
    return out


def _label(img, text):
    cv2.putText(img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (img.shape[1] - 1, img.shape[0] - 1), (150, 150, 150), 1)
    return img


def _hstack(imgs):
    h = max(i.shape[0] for i in imgs)
    padded = [cv2.copyMakeBorder(i, 0, h - i.shape[0], 0, 6, cv2.BORDER_CONSTANT,
                                 value=(255, 255, 255)) for i in imgs]
    return np.concatenate(padded, axis=1)


def render(fixture: str, width_mm: float, out: Path, garment: str = "left_chest",
           full_ppm: float = 20.0, zoom_ppm: float = 60.0) -> dict:
    stem = Path(fixture).stem
    rows, full, zoom = {}, [], []
    box_mm = None
    for arm, kw in ARMS.items():
        cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment, **kw)
        _result, plan = digitize(ROOT / "testdata" / fixture, cfg)
        design = plan_to_design(plan)
        along = _along_row(plan)
        rows[arm] = {
            "sha256": _design_sha(design),
            "stitches": sum(1 for s in design["stitches"] if s["type"] == "stitch"),
            "trims": sum(1 for s in design["stitches"] if s["type"] == "trim"),
            "along_row_n": len(along),
            "along_row_min_mm": round(min(along), 3) if along else None,
            "along_row_median_mm": round(float(np.median(along)), 3) if along else None,
            "along_row_max_mm": round(max(along), 3) if along else None,
            "along_row_under_min": sum(1 for d in along if d < machine.MIN_STITCH_MM - 1e-6),
        }
        if box_mm is None:
            # The largest fill shape on the first (tatami) arm, so every arm
            # crops the same millimetres.
            by_shape: dict[str, list] = {}
            for _b, run in plan.iter_runs():
                if run.kind == st.FILL:
                    by_shape.setdefault(run.shape_id, []).extend(run.points)
            pts = max(by_shape.values(), key=len)
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            box_mm = (min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5)
        full.append(_label(render_design(design, px_per_mm=full_ppm, pad_mm=PAD_MM), arm))
        big = render_design(design, px_per_mm=zoom_ppm, pad_mm=PAD_MM)
        (_h, _w), to_px = _frame(design["stitches"], zoom_ppm, PAD_MM)
        x0, y0 = to_px({"x": round(box_mm[0] * UNITS_PER_MM), "y": round(-box_mm[1] * UNITS_PER_MM)})
        x1, y1 = to_px({"x": round(box_mm[2] * UNITS_PER_MM), "y": round(-box_mm[3] * UNITS_PER_MM)})
        zoom.append(_label(big[max(0, y0):y1, max(0, x0):x1].copy(), arm))
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / f"{stem}_full.png"), _hstack(full))
    cv2.imwrite(str(out / f"{stem}_zoom.png"), _hstack(zoom))
    report = {"fixture": fixture, "width_mm": width_mm, "garment": garment,
              "zoom_box_mm": [round(v, 2) for v in box_mm],
              "fur_styles": {k: list(v) for k, v in machine.FUR_STYLES.items()},
              "arms": rows}
    (out / f"{stem}.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", help="path under testdata/")
    ap.add_argument("--width", type=float, default=40.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    print(json.dumps(render(args.fixture, args.width, args.out, args.garment), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
