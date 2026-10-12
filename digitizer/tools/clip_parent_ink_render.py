#!/usr/bin/env python
"""Render what `cfg.clip_parent_keeps_ink` changes: artwork | before | after.

Stage 5 clips each grown shape by the colours already sewn; when the clip
cuts it in pieces the engine before defect 61 kept the LARGEST, which can be
a piece of pure underlap tongue while the shape's ink is thrown away. This
draws, for one design, the shapes whose sewing polygon changes (the parent now
sews its ink piece), three panels over the same window:

  artwork ... the traced regions, in their thread colours
  before .... stage 5's planned sewing polygons, both settings off
  after ..... the same, the shipped default (`clip_parent_keeps_ink` on)

The shape that switched is outlined in red on every panel, so a roof line that
is missing in "before" is a red outline round a hole of ground colour.

    python -m tools.clip_parent_ink_render photo/logo_gaulke_roofing.png \
        --out ../docs/renders/clip-parent-ink-2026-10-12/gaulke.png

Report-only; changes nothing. Written 2026-10-12 for defect 61.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, run_stages  # noqa: E402
from digitizer_core.pipeline import fabric_for  # noqa: E402
from digitizer_core.stage5_overlap import resolve_overlaps  # noqa: E402
from digitizer_core.threads import chart_for  # noqa: E402

LEGACY = dict(clip_parent_keeps_ink=False, clip_keep_pieces=False)


def _fill(img, poly, bgr, x0, y0, s, outline=None):
    def px(ring):
        return np.asarray([[int((x - x0) * s), int((y - y0) * s)] for x, y in ring.coords],
                          np.int32)
    geoms = getattr(poly, "geoms", [poly])
    for g in geoms:
        if g.geom_type != "Polygon" or g.is_empty:
            continue
        cv2.fillPoly(img, [px(g.exterior)], bgr)
        for ring in g.interiors:
            cv2.fillPoly(img, [px(ring)], (255, 255, 255))
        if outline:
            cv2.polylines(img, [px(g.exterior)], True, outline, 2, cv2.LINE_AA)


def render(rel: str, out: Path, width_mm: float = 80.0, garment: str = "left_chest",
           px_per_mm: float = 14.0, shape: str | None = None) -> dict:
    kw = dict(target_width_mm=width_mm, garment_id=garment)
    cfg = PipelineConfig(**kw)
    result = run_stages(ROOT / "testdata" / rel, cfg)
    regions = [r for r in result.regions if r.meta.get("stitched", True)]
    fabric = fabric_for(cfg)
    before, _ = resolve_overlaps(regions, fabric, PipelineConfig(**kw, **LEGACY),
                                 result.design_class)
    after, _ = resolve_overlaps(regions, fabric, cfg, result.design_class)
    b_by = {p.shape_id: p for p in before}
    switched = [p.shape_id for p in after
                if p.shape_id in b_by and not p.polygon.equals_exact(b_by[p.shape_id].polygon, 0.0)]
    chart = chart_for(cfg)
    # The switched shape with the most artwork gained.
    def gain(sid):
        a = next(p for p in after if p.shape_id == sid)
        art = a.region.polygon
        return a.polygon.intersection(art).area - b_by[sid].polygon.intersection(art).area
    switched.sort(key=gain, reverse=True)
    focus = shape or (switched[0] if switched else None)
    if focus is None:
        raise SystemExit("no shape switches on this design")
    reg = {r.shape_id: r for r in regions}
    fx0, fy0, fx1, fy1 = reg[focus].polygon.buffer(3.0).bounds
    s = px_per_mm
    W, H = int((fx1 - fx0) * s), int((fy1 - fy0) * s)

    def layered(planned):
        order = sorted(planned, key=lambda p: p.sew_index)
        return [(p.sew_index, p.polygon, chart[p.region.thread_index].rgb, p.shape_id)
                for p in order]

    def draw(polys):
        img = np.full((H, W, 3), 255, np.uint8)
        for _l, poly, rgb, _sid in polys:
            _fill(img, poly, (rgb[2], rgb[1], rgb[0]), fx0, fy0, s)
        return img

    art_polys = [(r.meta.get("layer", 0), r.polygon, chart[r.thread_index].rgb, r.shape_id)
                 for r in sorted(regions, key=lambda r: r.meta.get("layer", 0))]
    panels = [draw(art_polys), draw(layered(before)), draw(layered(after))]
    labels = ["artwork", "before", "after"]
    for img, lab in zip(panels, labels):
        # the focus shape's artwork, outlined
        for g in getattr(reg[focus].polygon, "geoms", [reg[focus].polygon]):
            pts = np.asarray([[int((x - fx0) * s), int((y - fy0) * s)] for x, y in g.exterior.coords],
                             np.int32)
            cv2.polylines(img, [pts], True, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(img, lab, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.rectangle(img, (0, 0), (W - 1, H - 1), (160, 160, 160), 1)
    sheet = np.concatenate(panels, axis=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sheet)
    return {"focus": focus, "switched": switched, "art_mm2": round(reg[focus].polygon.area, 2),
            "ink_before_mm2": round(b_by[focus].polygon.intersection(reg[focus].polygon).area, 2),
            "ink_after_mm2": round(next(p for p in after if p.shape_id == focus)
                                   .polygon.intersection(reg[focus].polygon).area, 2),
            "sewn_before_mm2": round(b_by[focus].polygon.area, 2),
            "sewn_after_mm2": round(next(p for p in after if p.shape_id == focus).polygon.area, 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", help="path under testdata/")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--shape", default=None, help="shape id to window on (default: the biggest gain)")
    args = ap.parse_args(argv)
    print(render(args.fixture, args.out, args.width, args.garment, shape=args.shape))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
