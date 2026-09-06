#!/usr/bin/env python
"""Render WHERE a design's `ARTWORK_UNCOVERED` is — thread over artwork, with
the bare cells picked out.

Preflight reports uncovered artwork as a number and a shape id. A number does
not tell you whether 23.8 mm2 is a hairline seam nobody would see or a 6 mm
hole at a junction, and those want different fixes. This draws it.

  artwork the design sews ....... pale grey fill
  emitted stitches .............. satin blue-dark, everything else green
                                  (a tatami junction patch has to be
                                   visible against the claim fill)
  BARE cells (preflight's own) .. solid red
  the worst patch ............... circled, with its area

The bare cells are `_coverage_map`'s grid under `_COVERAGE_FLOOR_UNITS`,
intersected with what the plan claims — the same two halves preflight uses, so
what is drawn red is what preflight counted, not a lookalike computed here.

  .venv/bin/python tools/bare_patch_render.py becker_marine_logo.png --width 80
  .venv/bin/python tools/bare_patch_render.py logo_alpha.png --out /tmp/x.png
  .venv/bin/python tools/bare_patch_render.py becker_marine_logo.png \
      --width 80 --patch-junctions          # the same design with the FIX on

Written 2026-09-06 for the finding in `DOCTRINE` — 2 of the corpus's 255 satin
shapes leave bare cloth, and four cross-length knobs did not reach it. The
question it was built to answer was whether that reads as a junction hole, and
the answer was yes: both patches are letter junctions, and the big one is the
crotch of the K in BECKER at 80 AND 90 mm. `--patch-junctions` then draws the
same design under `cfg.satin_patch_junctions`, which is how the before/after
pair in `docs/renders/junction-bare-2026-09-06/` was made.
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

from digitizer_core import PipelineConfig, stitches                # noqa: E402
from digitizer_core.pipeline import digitize                       # noqa: E402
from digitizer_core import preflight as pf                         # noqa: E402
from digitizer_core.preflight import run_preflight                 # noqa: E402


def render(art: Path, width_mm: float, garment: str, out: Path,
           px_per_mm: float = 12.0, **cfg_kw) -> None:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         **cfg_kw)
    result, plan = digitize(art, cfg)
    report = run_preflight(result, plan, cfg, image=art)

    xs = [p[0] for _b, r in plan.iter_runs() for p in r.points]
    ys = [p[1] for _b, r in plan.iter_runs() for p in r.points]
    if not xs:
        raise SystemExit("no stitches")
    pad = 4.0
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad
    W = int((x1 - x0) * px_per_mm)
    H = int((y1 - y0) * px_per_mm)
    img = np.full((H, W, 3), 250, np.uint8)

    def to_px(pts):
        return np.asarray([[int((x - x0) * px_per_mm), int((y - y0) * px_per_mm)]
                           for x, y in pts], np.int32)

    # 1. the artwork the plan claims, pale
    sewn = {r.shape_id for _b, r in plan.iter_runs() if r.shape_id}
    for r in result.regions:
        if r.shape_id not in sewn:
            continue
        cv2.fillPoly(img, [to_px(r.polygon.exterior.coords)], (238, 238, 238))
        for ring in r.polygon.interiors:
            cv2.fillPoly(img, [to_px(ring.coords)], (250, 250, 250))

    # 2. thread. Satin darker than the rest so a junction reads as a junction.
    for _b, run in plan.iter_runs():
        if run.jump or len(run.points) < 2:
            continue
        col = (150, 60, 40) if run.kind == stitches.SATIN else (120, 165, 120)
        cv2.polylines(img, [to_px(run.points)], False, col, 1, cv2.LINE_AA)

    # 3. preflight's own bare cells, in red
    got = pf._coverage_map(plan, cell_mm=pf._UNCOVERED_CELL_MM)
    n_patch = 0
    if got is not None:
        grid, (gx0, gy0) = got
        covered = grid >= pf._COVERAGE_FLOOR_UNITS
        ny, nx = grid.shape
        gy_i, gx_i = np.mgrid[0:ny, 0:nx]
        C = pf._UNCOVERED_CELL_MM
        GX = (gx_i + 0.5) * C + gx0
        GY = (gy_i + 0.5) * C + gy0
        from shapely import contains_xy
        claimed = np.zeros(grid.shape, bool)
        for r in result.regions:
            if r.shape_id in sewn:
                claimed |= contains_xy(r.polygon, GX, GY)
        missing = (claimed & ~covered).astype(np.uint8)
        n, _lab, st, cents = cv2.connectedComponentsWithStats(missing, connectivity=8)
        areas = st[1:, cv2.CC_STAT_AREA] * C * C
        for iy, ix in zip(*np.nonzero(missing)):
            px = int((GX[iy, ix] - C / 2 - x0) * px_per_mm)
            py = int((GY[iy, ix] - C / 2 - y0) * px_per_mm)
            s = max(1, int(C * px_per_mm))
            cv2.rectangle(img, (px, py), (px + s, py + s), (40, 40, 220), -1)
        for i in np.argsort(-areas)[:3]:
            if areas[i] < pf._UNCOVERED_MIN_PATCH_MM2:
                continue
            n_patch += 1
            cx = int((cents[i + 1][0] * C + gx0 - x0) * px_per_mm)
            cy = int((cents[i + 1][1] * C + gy0 - y0) * px_per_mm)
            rad = int(max(10.0, (areas[i] ** 0.5) * px_per_mm))
            cv2.circle(img, (cx, cy), rad, (40, 40, 220), 2, cv2.LINE_AA)
            cv2.putText(img, f"{areas[i]:.1f} mm2", (cx + rad + 4, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 220), 1, cv2.LINE_AA)

    m = report["metrics"]
    cv2.putText(img, f"{art.name} @ {width_mm:g}mm/{garment}   "
                     f"{report['grade']} {report['score']}   "
                     f"uncovered {m.get('uncovered_total_mm2')} mm2 "
                     f"(worst {m.get('uncovered_worst_mm2')}), "
                     f"{n_patch} patch(es) over {pf._UNCOVERED_MIN_PATCH_MM2} mm2",
                (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1, cv2.LINE_AA)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)
    print(f"{art.name} @ {width_mm:g}mm  {report['grade']} {report['score']}  "
          f"uncovered {m.get('uncovered_total_mm2')} mm2  -> {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--px-per-mm", type=float, default=12.0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--patch-junctions", action="store_true",
                    help="cfg.satin_patch_junctions — sew what the satin "
                         "tier missed, so the render shows the FIX")
    a = ap.parse_args()
    art = Path(a.fixture)
    if not art.is_absolute():
        art = ROOT / "testdata" / a.fixture
    if not art.exists():
        print(f"no such fixture: {a.fixture}", file=sys.stderr)
        return 2
    out = a.out or (ROOT.parent / "docs" / "renders"
                    / f"bare-{art.stem}-{a.width:g}mm.png")
    render(art, a.width, a.garment, out, a.px_per_mm,
           satin_patch_junctions=a.patch_junctions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
