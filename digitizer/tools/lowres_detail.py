#!/usr/bin/env python
"""Fine detail on low-resolution artwork, scored against the same logo's
full-resolution file.

Why a new instrument (2026-09-30, Kent: bridge's "RESTAURANT" is completely
missing). Bridge is the corpus's only gradient-lane logo that arrives under
5 px/mm, so no fixture could say whether what it lost was bridge's or the
engine's. Every other real logo here is 9-31 px/mm — and a customer's file
is whatever their website serves. This makes the missing fixtures: each
logo is downsampled (INTER_AREA; a JPEG stays a JPEG, q90) to a chosen
source density, digitized under each arm, and compared with the SAME logo
digitized from the file as committed. The reference is the engine's own
reading of the full-resolution artwork, so the score says what the
resolution cost, not what the engine cannot do at any resolution.

Read on the REGIONS (stages 0-4 and the review defaults), rasterised at
10 px/mm in the design's own millimetre frame, in thread colours:

  agree     share of the reference's sewn area the arm sews in the same
            colour.
  fine      the same over the reference's FINE ink only — what an opening by
            a 1.5 mm disc removes from each colour, i.e. strokes under 1.5 mm,
            less the corner crumbs the same opening takes off every large
            shape. Lettering lives here; `agree` is dominated by grounds.
  fine_mm2  how much fine ink the reference has (the denominator).

"Same colour" is CIE76 <= 25 between threads (two runs of one logo pick
neighbouring spools for one ink) and position is forgiven 0.3 mm. Stitches
and trims ride along from the plan, since the detail that comes back is not
free.

A logo whose BACKGROUND reads differently at the two resolutions has a
different artwork box, so a different design, and is refused rather than
scored (`logo_gaulke_roofing` at 5 px/mm: the art box moves and "agreement"
reads 0.03).

    .venv/Scripts/python tools/lowres_detail.py                       # 5 px/mm, traced at 4 and at 8
    .venv/Scripts/python tools/lowres_detail.py --src 6.5 --grids 6.5 8
    .venv/Scripts/python tools/lowres_detail.py --logos enthusiast fremont --workers 4 --json out.json

Measured 2026-09-30, `docs/fine-detail-work-grid-2026-09-30.md`.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

RASTER_PX_PER_MM = 10.0
FINE_MM = 1.5            # ink an opening by this disc removes is "fine"
FINE_CRUMB_MM2 = 0.5     # ...unless it is a corner crumb (`_fine_ink`)
POSITION_TOL_MM = 0.3
SAME_COLOUR_DE = 25.0
# The art box may differ by this much between the reference and an arm before
# the pair is refused as two different designs.
FRAME_TOL_MM = 3.0

LOGOS = {
    "enthusiast": "photo/enthusiast_logo.png",
    "fremont": "photo/logo_hotel_fremont.webp",
    "golden_tee": "photo/logo_golden_tee.jpg",
    "screenshot": "photo/screenshot_phone_ui_golke.jpg",
    "drone": "photo/drone_render.png",
    "whitebg": "logo_whitebg.png",
    "tires": "logo_script_tires.png",
    "gaulke": "photo/logo_gaulke_roofing.png",
}


def _disc(diameter_mm: float) -> np.ndarray:
    """A disc of that diameter, on an ODD kernel so it reaches the same
    distance both ways (an even one forgives a shift to one side only)."""
    k = max(1, int(round(diameter_mm * RASTER_PX_PER_MM))) | 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))


def _fine_ink(ink: np.ndarray) -> np.ndarray:
    """The part of one colour's mask that is strokes under FINE_MM: what an
    opening by a FINE_MM disc removes, less the crumbs it also removes from
    every CORNER of a large shape (a right angle loses 0.12 mm² to a 1.5 mm
    disc — a block's four corners would otherwise score as "fine ink" that
    no arm can lose). A crumb is a removed component under FINE_CRUMB_MM2."""
    opened = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, _disc(FINE_MM)) > 0
    removed = (ink & ~opened).astype(np.uint8)
    n, cc, stats, _ = cv2.connectedComponentsWithStats(removed, connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= FINE_CRUMB_MM2 * RASTER_PX_PER_MM ** 2
    return keep[cc]


def _fit(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Centre-crop or pad `a` to `shape`: both frames are design-centred."""
    out = np.zeros(shape + a.shape[2:], a.dtype)
    h, w = a.shape[:2]
    H, W = shape
    sy, sx = max(0, (h - H) // 2), max(0, (w - W) // 2)
    dy, dx = max(0, (H - h) // 2), max(0, (W - w) // 2)
    hh, ww = min(h, H), min(w, W)
    out[dy:dy + hh, dx:dx + ww] = a[sy:sy + hh, sx:sx + ww]
    return out


def score(ref_rgb: np.ndarray, ref_mask: np.ndarray,
          arm_rgb: np.ndarray, arm_mask: np.ndarray) -> dict:
    """`agree`, `fine` and `fine_mm2` (module docstring) for one arm's region
    raster against the reference's. Rasters are (H, W, 3) thread RGB and
    (H, W) sewn masks at RASTER_PX_PER_MM, each centred on its design."""
    from digitizer_core.threads import rgb_to_lab

    ref_mask = ref_mask.astype(bool)
    arm_rgb = _fit(arm_rgb, ref_mask.shape)
    arm_mask = _fit(arm_mask.astype(np.uint8), ref_mask.shape) > 0
    arm_lab = rgb_to_lab(arm_rgb.reshape(-1, 3).astype(np.float64)).reshape(arm_rgb.shape)
    colours = np.unique(ref_rgb[ref_mask].reshape(-1, 3), axis=0)
    hit = fine_px = fine_hit = 0
    for c, c_lab in zip(colours, rgb_to_lab(colours.astype(np.float64))):
        ref_c = ref_mask & (ref_rgb == c).all(axis=2)
        same = arm_mask & (np.linalg.norm(arm_lab - c_lab, axis=2) <= SAME_COLOUR_DE)
        same = cv2.dilate(same.astype(np.uint8), _disc(2 * POSITION_TOL_MM)) > 0
        fine = _fine_ink(ref_c)
        hit += int((ref_c & same).sum())
        fine_px += int(fine.sum())
        fine_hit += int((fine & same).sum())
    return {"agree": round(hit / max(1, int(ref_mask.sum())), 3),
            "fine": round(fine_hit / max(1, fine_px), 3),
            "fine_mm2": round(fine_px / RASTER_PX_PER_MM ** 2, 1)}


def _rasterise(result, chart) -> tuple[np.ndarray, np.ndarray]:
    w_mm, h_mm = result.design_size_mm
    half_w, half_h = w_mm / 2 + 2.0, h_mm / 2 + 2.0
    W, H = int(round(2 * half_w * RASTER_PX_PER_MM)), int(round(2 * half_h * RASTER_PX_PER_MM))
    rgb = np.zeros((H, W, 3), np.uint8)
    mask = np.zeros((H, W), np.uint8)

    def px(coords):
        a = np.asarray(coords, np.float64)
        return np.round(np.column_stack([(a[:, 0] + half_w) * RASTER_PX_PER_MM,
                                         (a[:, 1] + half_h) * RASTER_PX_PER_MM])).astype(np.int32)

    for r in result.regions:                       # layer order: later regions sew on top
        if not r.meta.get("stitched", True):
            continue
        layer = np.zeros((H, W), np.uint8)
        for poly in ([r.polygon] if r.polygon.geom_type == "Polygon" else list(r.polygon.geoms)):
            cv2.fillPoly(layer, [px(poly.exterior.coords)], 1)
            for hole in poly.interiors:
                cv2.fillPoly(layer, [px(hole.coords)], 0)
        rgb[layer > 0] = chart[r.thread_index].rgb
        mask[layer > 0] = 1
    return rgb, mask


def _one(args) -> dict:
    """One digitize: (logo, rel path, width, src px/mm or None for the
    reference, working grid or None, plan?, scratch dir)."""
    logo, rel, width, src, grid, plan_too, scratch = args
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.stage1_prep import prep
    from digitizer_core.threads import chart_for

    path = ROOT / "testdata" / rel
    base = dict(target_width_mm=width, garment_id="left_chest", max_colors=6)
    if src is not None:
        native = prep(str(path), PipelineConfig(**base, work_px_per_mm=None))
        scale = src / native.input_px_per_mm
        raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if scale < 1.0:
            raw = cv2.resize(raw, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        jpeg = path.suffix.lower() in (".jpg", ".jpeg")
        path = Path(scratch) / f"{logo}__{src:g}{'.jpg' if jpeg else '.png'}"
        cv2.imwrite(str(path), raw, [cv2.IMWRITE_JPEG_QUALITY, 90] if jpeg else [])
    cfg = PipelineConfig(**base) if src is None else PipelineConfig(**base, work_px_per_mm=grid)
    gen = build_generation(str(path), cfg)
    result = finish_generation(gen.fork(), cfg)
    rgb, mask = _rasterise(result, chart_for(cfg))
    row = {"logo": logo, "arm": "ref" if src is None else f"grid {grid:g}", "class": gen.classification_class,
           "source_px_per_mm": round(gen.p.input_px_per_mm, 2), "traced_px_per_mm": round(gen.p.px_per_mm, 2),
           "regions": sum(1 for r in result.regions if r.meta.get("stitched", True)),
           "size_mm": [round(v, 1) for v in result.design_size_mm]}
    if plan_too:
        plan = plan_stitches(result, cfg)
        row.update(stitches=plan.stats.stitch_count, trims=plan.stats.trims)
    return {"row": row, "rgb": rgb, "mask": mask}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--logos", nargs="+", default=list(LOGOS), choices=list(LOGOS))
    ap.add_argument("--src", type=float, default=5.0, help="source px/mm the logos are downsampled to")
    ap.add_argument("--grids", type=float, nargs="+", default=[4.0, 8.0],
                    help="working grids to trace the downsampled file on (at or under --src: no enlargement)")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--no-plan", action="store_true", help="skip stitch planning (no stitches/trims columns)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)

    with tempfile.TemporaryDirectory() as scratch:
        jobs = []
        for logo in a.logos:
            jobs.append((logo, LOGOS[logo], a.width, None, None, not a.no_plan, scratch))
            jobs += [(logo, LOGOS[logo], a.width, a.src, g, not a.no_plan, scratch) for g in a.grids]
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            done = list(ex.map(_one, jobs))

    by_logo: dict[str, list[dict]] = {}
    for d in done:
        by_logo.setdefault(d["row"]["logo"], []).append(d)
    rows = []
    print(f"source {a.src:g} px/mm at {a.width:g} mm, scored against each logo's full-resolution file")
    print(f"{'logo':12s} {'arm':9s} {'class':12s} {'traced':>6s} {'regions':>7s} {'stitches':>8s} "
          f"{'trims':>5s} {'agree':>6s} {'fine':>6s} {'fine_mm2':>8s}")
    for logo, ds in by_logo.items():
        ref = next(d for d in ds if d["row"]["arm"] == "ref")
        for d in ds:
            r = d["row"]
            moved = max(abs(x - y) for x, y in zip(r["size_mm"], ref["row"]["size_mm"]))
            if moved > FRAME_TOL_MM:
                r["refused"] = f"art box differs from the reference by {moved:.1f} mm"
                print(f"{logo:12s} {r['arm']:9s} refused: {r['refused']}")
            else:
                r.update(score(ref["rgb"], ref["mask"] > 0, d["rgb"], d["mask"] > 0))
                print(f"{logo:12s} {r['arm']:9s} {r['class']:12s} {r['traced_px_per_mm']:6.1f} {r['regions']:7d} "
                      f"{r.get('stitches', 0):8d} {r.get('trims', 0):5d} {r['agree']:6.3f} {r['fine']:6.3f} "
                      f"{r['fine_mm2']:8.1f}")
            rows.append(r)
    if a.json:
        a.json.write_text(json.dumps({"src_px_per_mm": a.src, "width_mm": a.width, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
