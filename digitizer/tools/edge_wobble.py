#!/usr/bin/env python
"""Does the sewn edge wander about the outline it was given?

Kent, 2026-09-19: *"Right shapes, bad edges … wobbly / lumpy curves bothers me
most … it needs to be perfect."* The same sentence as 2026-08-27's *"shapes are
accurate but smoothness is not"* (`edge_smoothness.py`), and this time a spike
located it. Offset removed, same unit on both sides:

                 outline vs artwork      sewn rails vs outline
    enthusiast   std 0.011  p95 0.023    std 0.071  p95 0.185   (0.068 mm source px)
    becker       std 0.074  p95 0.154    std 0.082  p95 0.195   (0.552 mm source px)
    whitebg      std 0.049  p95 0.039    std 0.029  p95 0.058   (synthetic control)

On decent artwork stage 4's polygon tracks the art to a hundredth of a
millimetre and the STITCHING adds six times that about a clean outline. On a
low-resolution upload both sides wobble. The synthetic control sews clean,
which is why no suite ever saw this. `satin_rails_follow_edge` ON moved the
rail figure about 10% (0.071 -> 0.064, 0.082 -> 0.074) — Kent's eye had
already called that flag invisible. (The spike ran on `da6606e4`, BEFORE
2026-09-19's satin flips; this tool's own satin row was re-measured after
them and barely moved. Its live numbers are in DOCTRINE 2026-09-19 — quote
those, not this table.)

## Why this is not `edge_smoothness` or `curve_fidelity`

`edge_smoothness.ragged_mm` compares a rendered thread raster with the
artwork's ink mask: it needs registration, it sees outline error and stitch
error summed, and its floor is the raster's pixel. `curve_fidelity` reads turn
angles off the stitch path and answers "is this curve a polygon", with no
outline to compare against. Neither can say WHICH STAGE a wobble was born in.

This reads the two things the engine already holds in one frame —
`result.regions[].polygon` and `plan.iter_runs()` — so there is no raster, no
registration, and nothing about the artwork in it at all. It is the
stitch-side half of the table above, and only that half.

## The measurement

Every visible edge penetration — satin and border rail points, fill row ends,
bean/run outline points — gets a SIGNED distance to its own shape's boundary
(+ outside, - inside). Penetrations are ordered along the boundary ring they
sit nearest, per run and per rail, and the series is high-passed over
`WINDOW_MM`: a constant standoff is pull compensation and a slow drift is a
taper, and neither is what Kent is looking at. What is left is wobble.

The baseline is a 3-point median (so one dent cannot drag it) followed by a
trapezoid-weighted mean (whose alternating sum is exactly zero, so a sawtooth
reads at its own amplitude instead of double or nil — a plain rolling median
INVERTS an alternation and reads it 2x).

`stage6_satin._short_stitch_guard` retracts alternate penetrations where a
rail bunches under `SATIN_SHORT_STITCH_AT_MM`. That is technique, not defect,
and it is excused by the guard's OWN condition — an inward dip whose
along-boundary step is under that threshold — never by size alone: the same
dip on a rail stepping a full 0.4 mm is a sawtooth and is counted.

    .venv/Scripts/python tools/edge_wobble.py [fixture ...] [--json] [--render DIR]

`--render DIR` writes `<fixture>_worst.png`: the five worst spots as thread
over outline, for the eye this number has not yet been checked against.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
# The measurement itself: `digitizer_core/edge_wobble.py` since 2026-10-03, so
# preflight can report it. Re-exported because this module is how the tests
# and every doc that quotes a reading reach it.
from digitizer_core.edge_wobble import (  # noqa: E402,F401
    OVER_MM, TIER, _row_ends, analyse_plan)


THREAD_MM = 0.35


def render_worst(polygons: dict, plan, row: dict, out_path: str | Path,
                 box_mm: float = 10.0, px_per_mm: int = 60) -> Path:
    """One tile per `row["worst"]` spot: the thread as sewn (at thread width,
    in its own colour), the outline it was given (green), the spot (red ring).

    For Kent's eye, which is the judge this number has not yet met. No
    artwork in it on purpose — that would need registration, and the question
    here is only whether the thread follows the outline.
    """
    import cv2

    side = int(round(box_mm * px_per_mm))
    tiles = []
    for w in row["worst"]:
        x0, y0 = w["at_mm"][0] - box_mm / 2, w["at_mm"][1] - box_mm / 2
        im = np.full((side, side, 3), 255, np.uint8)

        def px(P):
            return np.round((np.asarray(P, float) - (x0, y0)) * px_per_mm).astype(np.int32)

        for block, run in plan.iter_runs():
            if run.kind not in TIER or len(run.points) < 2:
                continue
            P = np.asarray(run.points, float)
            if (P.max(0) < (x0, y0)).any() or (P.min(0) > (x0 + box_mm, y0 + box_mm)).any():
                continue
            r, g, b = block.rgb
            if min(r, g, b) > 225:                       # white thread on a white tile
                r = g = b = 190
            cv2.polylines(im, [px(P)], False, (int(b), int(g), int(r)),
                          max(1, int(round(THREAD_MM * px_per_mm))), cv2.LINE_AA)
        for poly in polygons.values():
            for geom in getattr(poly, "geoms", [poly]):
                for ring in (geom.exterior, *geom.interiors):
                    cv2.polylines(im, [px(ring.coords)], True, (0, 170, 0), 2, cv2.LINE_AA)
        c = (side // 2, side // 2)
        cv2.circle(im, c, int(0.6 * px_per_mm), (0, 0, 235), 2, cv2.LINE_AA)
        label = f"{w['dev_mm']:+.2f} mm  {w['tier']} {w['zone'] or ''}  box {box_mm:g} mm"
        cv2.putText(im, label, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(im, label, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(im)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), np.hstack(tiles) if tiles else np.full((side, side, 3), 255, np.uint8))
    return out_path


def _draw_plan(im, plan, polygons, px, thread_px: int) -> None:
    import cv2
    for block, run in plan.iter_runs():
        if run.kind not in TIER or len(run.points) < 2:
            continue
        r, g, b = block.rgb
        if min(r, g, b) > 225:                           # white thread on a white page
            r = g = b = 190
        cv2.polylines(im, [px(run.points)], False, (int(b), int(g), int(r)),
                      thread_px, cv2.LINE_AA)
    for poly in polygons.values():
        for geom in getattr(poly, "geoms", [poly]):
            for ring in (geom.exterior, *geom.interiors):
                cv2.polylines(im, [px(ring.coords)], True, (0, 170, 0), 1, cv2.LINE_AA)


def render_design(polygons: dict, plan, row: dict, out_path: str | Path,
                  px_per_mm: int = 30, grid_mm: float = 5.0) -> Path:
    """The WHOLE design, every flagged penetration ringed, on a lettered grid.

    Kent on the worst-five tiles, 2026-09-19: *"Yes, those are some. But you
    missed quite a few."* Five tiles are a keyhole. This is the page he can
    answer on: a cell with something ugly and NO ring in it ("C4") is a defect
    this instrument does not see, and that list is the instrument's next job.
    """
    import cv2

    pts = [np.asarray(run.points, float) for _b, run in plan.iter_runs()
           if run.kind in TIER and len(run.points)]
    allp = np.vstack(pts) if pts else np.zeros((1, 2))
    lo = np.floor(allp.min(0) / grid_mm) * grid_mm
    hi = np.ceil(allp.max(0) / grid_mm) * grid_mm
    pad = 24                                             # label gutter, px
    W, H = ((hi - lo) * px_per_mm).astype(int)
    im = np.full((H + pad, W + pad, 3), 255, np.uint8)

    def px(P):
        return (np.round((np.asarray(P, float) - lo) * px_per_mm) + pad).astype(np.int32)

    _draw_plan(im, plan, polygons, px, max(1, int(round(THREAD_MM * px_per_mm))))
    for i, x in enumerate(np.arange(lo[0], hi[0] + 1e-6, grid_mm)):
        X = int((x - lo[0]) * px_per_mm) + pad
        cv2.line(im, (X, pad), (X, H + pad), (225, 200, 160), 1)
        if x < hi[0]:
            cv2.putText(im, chr(65 + i % 26), (X + int(grid_mm * px_per_mm / 2) - 5, 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 70, 0), 1, cv2.LINE_AA)
    for j, y in enumerate(np.arange(lo[1], hi[1] + 1e-6, grid_mm)):
        Y = int((y - lo[1]) * px_per_mm) + pad
        cv2.line(im, (pad, Y), (W + pad, Y), (225, 200, 160), 1)
        if y < hi[1]:
            cv2.putText(im, str(j + 1), (3, Y + int(grid_mm * px_per_mm / 2) + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 70, 0), 1, cv2.LINE_AA)
    for f in row["flagged"]:
        cv2.circle(im, tuple(int(v) for v in px([f["at_mm"]])[0]),
                   max(4, int(0.45 * px_per_mm)), (0, 0, 235), 2, cv2.LINE_AA)
    for s in row["unsewn"]["spans"]:                     # outline with no thread on it
        cv2.polylines(im, [px(s["path_mm"])], False, (220, 0, 220),
                      max(3, int(0.2 * px_per_mm)), cv2.LINE_AA)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), im)
    return out_path


def analyse(image_path: str | Path, cfg: PipelineConfig | None = None,
            render_dir: str | Path | None = None) -> dict:
    image_path = Path(image_path)
    result, plan = digitize(image_path, cfg or PipelineConfig())
    polygons = {r.shape_id: r.polygon for r in result.regions}
    row = analyse_plan(polygons, plan, background={
        r.shape_id for r in result.regions if r.meta.get("enclosed_background")})
    if render_dir is not None:
        row["render"] = str(render_worst(polygons, plan, row,
                                         Path(render_dir) / f"{image_path.stem}_worst.png"))
        row["render_design"] = str(render_design(polygons, plan, row,
                                                 Path(render_dir) / f"{image_path.stem}_all.png"))
    return {"fixture": image_path.name, "route": result.design_class, **row}


def _resolve(names: list[str]) -> list[Path]:
    out = []
    for n in names:
        p = Path(n)
        out.append(p if p.exists() else ROOT / "testdata" / n)
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    render_dir = None
    if "--render" in argv:
        i = argv.index("--render")
        render_dir = argv[i + 1]
        del argv[i:i + 2]
    rows = [analyse(p, render_dir=render_dir)
            for p in _resolve([a for a in argv if not a.startswith("--")])]
    if as_json:
        print(json.dumps(rows, indent=1))
        return 0
    for r in rows:
        print(f"{r['fixture']}  ({r['route']})  {r['points']} edge penetrations, "
              f"{r['short_stitches_excused']} short stitches excused, "
              f"{r['series_ends_unread']} series ends unread")
        for t, s in r["by_tier"].items():
            print(f"  {t:7s} n={s['points']:6d}  std {s['wobble_std_mm']:.3f}  "
                  f"p95 {s['wobble_p95_mm']:.3f}  max {s['wobble_max_mm']:.2f} mm  "
                  f">{OVER_MM} mm {s['share_over']:.1%}  offset {s['offset_mm']:+.2f}")
        for z, s in r["rail_zones"].items():
            print(f"  rails/{z:6s} n={s['points']:6d}  std {s['wobble_std_mm']:.3f}  "
                  f"p95 {s['wobble_p95_mm']:.3f}  >{OVER_MM} mm {s['share_over']:.1%}")
        u = r["unsewn"]
        print(f"  unsewn outline: {u['edge_mm']:.1f} mm in {len(u['spans'])} spans "
              f"({u['share'] or 0:.1%} of sewn shapes' outline), "
              f"{len(u['shapes_without_thread'])} shapes with no thread at all")
        for s in u["spans"][:5]:
            print(f"    bare  {s['length_mm']:5.2f} mm long, {s['gap_mm']:.2f} mm from thread  "
                  f"{s['shape_id']}  at {s['at_mm']}")
        for w in r["worst"]:
            print(f"    worst {w['dev_mm']:+.2f} mm  {w['tier']:6s} {w['zone'] or '-':6s} "
                  f"{w['shape_id']}  at {w['at_mm']}")
        if r.get("render"):
            print(f"  render: {r['render']}\n  render: {r['render_design']}  "
                  f"({len(r['flagged'])} flagged penetrations ringed)")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    raise SystemExit(main())
