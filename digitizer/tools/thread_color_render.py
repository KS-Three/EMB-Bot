#!/usr/bin/env python
"""Draw a design in the THREAD COLOURS it will actually sew, and circle the
shapes whose cone `cfg.revalidate_small_shapes` changes.

`THREAD_MATCH_POOR` reports a dE00 and a shape id. A dE00 does not tell you
whether a mid-grey thread over white artwork is a hairline nobody sees or a
visible smudge in the middle of a logo, and the corpus scorecard cannot answer
it either — the flag this renders fixes the design's worst thread mismatch
without moving a single grade (MASTER_SCOPE 28). So the question goes to the
eye, which is what this is for.

  artwork ....... the re-read source pixels, faded, so the thread can be
                  judged against the colour it is supposed to be
  stitches ...... each run in its own block's cone RGB
  changed ....... a shape whose cone differs between OFF and ON is circled in
                  both panels, labelled `oldcone -> newcone  dE -> dE`

  .venv/bin/python tools/thread_color_render.py photo/screenshot_phone_ui_golke.jpg \\
      --width 80 --out docs/renders/small-shape-resnap-2026-09-06
  .venv/bin/python tools/thread_color_render.py photo/logo_bridge_bar.jpg --zoom

`--zoom` crops to the changed shapes (with margin) instead of drawing the whole
design; on a 153-region screenshot a 0.94 mm2 shard is four pixels at full
extent and the panel proves nothing.

Written 2026-09-06 alongside `tools/revalidate_floor.py`, which finds the
shapes; this one shows them.
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

from digitizer_core import PipelineConfig                          # noqa: E402
from digitizer_core.pipeline import digitize                       # noqa: E402
from digitizer_core.stage1_prep import prep                        # noqa: E402
from digitizer_core.threads import chart_for                       # noqa: E402

TESTDATA = ROOT / "testdata"


def _bgr(rgb) -> tuple[int, int, int]:
    r, g, b = rgb
    return (int(b), int(g), int(r))


def _run(art: Path, width_mm: float, garment: str, small: bool):
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         revalidate_small_shapes=small)
    result, plan = digitize(art, cfg)
    return cfg, result, plan


def _panel(art, cfg, result, plan, bounds, px_per_mm, changed, title):
    x0, y0, x1, y1 = bounds
    W = max(1, int((x1 - x0) * px_per_mm))
    H = max(1, int((y1 - y0) * px_per_mm))
    img = np.full((H, W, 3), 252, np.uint8)

    def to_px(pts):
        return np.asarray([[int((x - x0) * px_per_mm), int((y - y0) * px_per_mm)]
                           for x, y in pts], np.int32)

    # 1. The artwork underneath, faded — the reference the thread is judged
    # against. Same transform preflight uses (mm from the art-bbox centre).
    p = prep(art, cfg)
    ax0, ay0, ax1, ay1 = p.art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    src = cv2.cvtColor(p.rgb, cv2.COLOR_RGB2BGR)
    for yy in range(H):
        my = y0 + yy / px_per_mm
        sy = int(my * p.px_per_mm + cy)
        if not (0 <= sy < src.shape[0]):
            continue
        mxs = x0 + np.arange(W) / px_per_mm
        sxs = (mxs * p.px_per_mm + cx).astype(np.int64)
        ok = (sxs >= 0) & (sxs < src.shape[1])
        img[yy, ok] = (src[sy, sxs[ok]].astype(np.int16) * 0.35
                       + 252 * 0.65).astype(np.uint8)

    # 2. Thread, each run in its own block's cone.
    chart = chart_for(cfg)
    for block, run in plan.iter_runs():
        if run.jump or len(run.points) < 2:
            continue
        cv2.polylines(img, [to_px(run.points)], False,
                      _bgr(chart[block.thread_index].rgb), 1, cv2.LINE_AA)

    # 3. Circle the shapes whose cone moved.
    by_id = {r.shape_id: r for r in result.regions}
    for sid, (old, new) in sorted(changed.items()):
        r = by_id.get(sid)
        if r is None:
            continue
        px = to_px(r.polygon.exterior.coords)
        c = px.mean(axis=0).astype(int)
        rad = max(9, int(np.abs(px - c).max()) + 6)
        cv2.circle(img, tuple(c), rad, (30, 30, 220), 1, cv2.LINE_AA)
        cv2.putText(img, f"{old}->{new}", (c[0] + rad + 3, c[1] + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (30, 30, 220), 1,
                    cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (W - 1, 22), (252, 252, 252), -1)
    cv2.putText(img, title, (6, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (30, 30, 30), 1, cv2.LINE_AA)
    return img


def _tiles(art: Path, changed, off, on, out_dir: Path, width_mm: float,
           px_per_mm: float = 90.0, margin_mm: float = 1.6) -> int:
    """One row per changed shape: OFF | ON, cropped to that shape.

    90 px/mm because these shapes are 0.2-0.9 mm2 — at the 14 px/mm a whole
    design wants, the thing being argued about is four pixels.
    """
    cfg_a, res_a, plan_a = off
    cfg_b, res_b, plan_b = on
    by_a = {r.shape_id: r for r in res_a.regions}
    rows = []
    for sid in sorted(changed, key=lambda s: -by_a[s].area_mm2):
        r = by_a[sid]
        xs, ys = zip(*r.polygon.exterior.coords)
        b = (min(xs) - margin_mm, min(ys) - margin_mm,
             max(xs) + margin_mm, max(ys) + margin_mm)
        old, new = changed[sid]
        pair = [
            _panel(art, cfg_a, res_a, plan_a, b, px_per_mm, {},
                   f"OFF  {sid}  {r.area_mm2:.2f} mm2  cone {old}"),
            _panel(art, cfg_b, res_b, plan_b, b, px_per_mm, {},
                   f"ON   {sid}  {r.area_mm2:.2f} mm2  cone {new}"),
        ]
        h = max(p.shape[0] for p in pair)
        pair = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 6,
                                   cv2.BORDER_CONSTANT, value=(210, 210, 210))
                for p in pair]
        rows.append(np.hstack(pair))
    w = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 8, 0, w - r.shape[1],
                               cv2.BORDER_CONSTANT, value=(210, 210, 210))
            for r in rows]
    img = np.vstack(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{art.stem}_{width_mm:g}mm_tiles.png"
    cv2.imwrite(str(path), img)
    print(f"  {path}")
    for sid, (old, new) in sorted(changed.items()):
        print(f"  {sid:>12} {by_a[sid].area_mm2:8.2f} mm^2   {old} -> {new}")
    return 0


def render(fixture: str, width_mm: float, garment: str, out_dir: Path,
           px_per_mm: float, zoom: bool) -> int:
    art = TESTDATA / fixture
    cfg_a, res_a, plan_a = _run(art, width_mm, garment, False)
    cfg_b, res_b, plan_b = _run(art, width_mm, garment, True)

    a = {r.shape_id: r.thread_number for r in res_a.regions}
    b = {r.shape_id: r.thread_number for r in res_b.regions}
    changed = {k: (a[k], b[k]) for k in a if k in b and a[k] != b[k]}
    if not changed:
        print(f"{fixture}: the flag changes no cone here — nothing to draw")
        return 1

    if zoom:
        # One tile per changed shape, OFF beside ON. A single crop around all
        # of them is useless when they are scattered — on
        # `screenshot_phone_ui_golke` they sit in the status bar AND in the
        # truck 60 mm away, so the "zoom" was the whole design and a 0.94 mm2
        # shard was four pixels of it.
        return _tiles(art, changed, (cfg_a, res_a, plan_a), (cfg_b, res_b, plan_b),
                      out_dir, width_mm)
    else:
        pts = [pt for _b, r in plan_a.iter_runs() for pt in r.points]
        pad = 3.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bounds = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(fixture).stem
    for tag, cfg, res, plan in (("off", cfg_a, res_a, plan_a),
                                ("on", cfg_b, res_b, plan_b)):
        img = _panel(art, cfg, res, plan, bounds, px_per_mm, changed,
                     f"{stem} @ {width_mm:g}mm  revalidate_small_shapes={tag.upper()}"
                     f"   {len(changed)} cone(s) changed")
        path = out_dir / f"{stem}_{width_mm:g}mm_{tag}.png"
        cv2.imwrite(str(path), img)
        print(f"  {path}")
    for sid, (old, new) in sorted(changed.items()):
        r = next(x for x in res_b.regions if x.shape_id == sid)
        print(f"  {sid:>12} {r.area_mm2:8.2f} mm^2   {old} -> {new}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", help="path under digitizer/testdata/")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--out", type=Path, default=Path("/tmp"))
    ap.add_argument("--px-per-mm", type=float, default=14.0)
    ap.add_argument("--zoom", action="store_true",
                    help="crop to the changed shapes instead of the design")
    a = ap.parse_args()
    return render(a.fixture, a.width, a.garment, a.out, a.px_per_mm, a.zoom)


if __name__ == "__main__":
    raise SystemExit(main())
