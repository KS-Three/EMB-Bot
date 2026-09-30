#!/usr/bin/env python
"""Draw a bare patch from the ACTUAL thread path, not from a model of it.

`tools/bare_anatomy.py` finds bare satin artwork by buffering satin crosses in
shapely, and its renders draw that same buffer. So a picture made there can
only ever agree with the number made there — it is the model restated, not
evidence for it. That cost a session on 2026-09-30: a render of the A's apex
was offered as proof the apex was closed, when both halves came out of one
model that counts satin and ignores underlay.

This draws the design through `stitchviz.render_design` instead — the same
renderer the Studio previews with, walking the design's real stitch stream
(underlay, run, travel and fill included) and breaking the thread at jumps and
trims. Nothing here buffers a cross.

Three panels over one crop, centred by default on the worst bare component
`bare_anatomy` reports:

  1. `lit` ......... what the Studio shows the customer;
  2. `bare` ........ the same design on MAGENTA cloth, unlit — cloth shows
                     through exactly where no thread lands;
  3. `outlined` .... panel 2 with the shape's ARTWORK polygon outlined, so a
                     hole can be seen to be inside the artwork.

**Panel 2 is a picture, not a measurement.** `stitchviz.coverage`'s docstring
rejects a sentinel background as a METRIC, because anti-aliased fringe reads as
bare and a tolerance cannot be set that is right in both directions. Quote
`bare_anatomy --all-thread` or `dropped_elements`' `uncovered_*` for numbers.

    .venv/bin/python tools/thread_path_render.py enthusiast --out /tmp/apex
    .venv/bin/python tools/thread_path_render.py becker --half 8 --out /tmp/k
    .venv/bin/python tools/thread_path_render.py enthusiast --at 23.05,-3.16 \
        --shape Scd87e08f --out /tmp/apex
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.pipeline import (build_generation, finish_generation,  # noqa: E402
                                     plan_stitches)
from digitizer_core.stitchviz import _bounds, render_design  # noqa: E402
from tools._console import utf8_console  # noqa: E402
from tools.bare_anatomy import components  # noqa: E402
from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS  # noqa: E402

# Magenta is nowhere in a thread palette and nowhere in `stitchviz`'s fabric
# or shading, so every magenta pixel in panel 2 is cloth. It is a sentinel for
# the EYE only -- see the docstring on why it is not one for a number.
SENTINEL_BGR = (255, 0, 255)


def plan_mm_to_px(design: dict, px_per_mm: float, pad: float = 2.0):
    """-> f(x_mm, y_mm) -> (px, py) in a `render_design` image at `px_per_mm`.

    `render_design` frames the design on its own stitch bounds plus `pad`, and
    `adapter` writes `x_design = x_mm * 10`, `y_design = -y_mm * 10`. Composing
    those two is the whole mapping, and it lives here rather than in each
    caller so a change to either is a change in ONE place — the 2026-09-30
    apex verdict needed it in a tool and in a test, and two copies of a
    coordinate transform is how a picture and a number stop agreeing.
    """
    x0u, _x1u, _y0u, y1u = _bounds(design["stitches"])

    def to_px(x_mm: float, y_mm: float) -> tuple[float, float]:
        return ((x_mm - x0u / 10.0 + pad) * px_per_mm,
                (y1u / 10.0 + y_mm + pad) * px_per_mm)

    return to_px


def px_to_plan_mm(design: dict, px_per_mm: float, pad: float = 2.0):
    """-> f(px, py) -> (x_mm, y_mm); the inverse of `plan_mm_to_px`."""
    x0u, _x1u, _y0u, y1u = _bounds(design["stitches"])

    def to_mm(px: float, py: float) -> tuple[float, float]:
        return (px / px_per_mm - pad + x0u / 10.0,
                py / px_per_mm - pad - y1u / 10.0)

    return to_mm


def draw(name: str, out: Path, half_mm: float = 3.2, px_per_mm: float = 60.0,
         at: tuple[float, float] | None = None, shape: str | None = None,
         **cfg_kw) -> dict:
    """-> {shape, centre, files}. Renders three panels and a joined sheet."""
    rel, width_mm, garment = REAL_ART[name]
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         max_colors=STUDIO_MAX_COLORS, **cfg_kw)
    gen = build_generation(str(ROOT / "testdata" / rel), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    design = plan_to_design(plan)
    polys = {r.shape_id: r.polygon for r in result.regions}

    comps = [c for c in components(polys, plan, all_thread=True)
             if shape is None or c[3] == shape]
    if not comps:
        raise SystemExit(f"no bare component on {name}"
                         + (f" shape {shape}" if shape else ""))
    worst = max(comps)
    sid = worst[3]
    if at is None:
        # the worst component's own centroid, re-derived from its shape
        at = _worst_centroid(polys, plan, sid)

    to_px = plan_mm_to_px(design, px_per_mm)
    cx, cy = to_px(*at)
    box = (int(cx - half_mm * px_per_mm), int(cy - half_mm * px_per_mm),
           int(cx + half_mm * px_per_mm), int(cy + half_mm * px_per_mm))

    def crop(img):
        h, w = img.shape[:2]
        a, b = max(0, box[1]), min(h, box[3])
        c, d = max(0, box[0]), min(w, box[2])
        return img[a:b, c:d].copy()

    lit = crop(render_design(design, px_per_mm=px_per_mm, lit=True))
    bare = crop(render_design(design, px_per_mm=px_per_mm,
                              fabric_bgr=SENTINEL_BGR, lit=False))
    outlined = bare.copy()
    ring = np.array([[int(round(to_px(x, y)[0])) - max(0, box[0]),
                      int(round(to_px(x, y)[1])) - max(0, box[1])]
                     for x, y in polys[sid].exterior.coords], np.int32)
    cv2.polylines(outlined, [ring], True, (0, 0, 0), 2, cv2.LINE_AA)

    out.mkdir(parents=True, exist_ok=True)
    files = []
    tiles = []
    for tag, img in (("lit", lit), ("bare", bare), ("outlined", outlined)):
        tile = _chrome(img, px_per_mm)
        tiles.append(tile)
        p = out / f"{name}_{tag}.png"
        cv2.imwrite(str(p), tile)
        files.append(p)
    h = min(t.shape[0] for t in tiles)
    sheet = out / f"{name}_thread_path.png"
    cv2.imwrite(str(sheet), np.hstack([t[:h] for t in tiles]))
    files.append(sheet)
    return dict(shape=sid, centre=at, worst_mm2=worst[0], files=files)


def _worst_centroid(polys: dict, plan, sid: str) -> tuple[float, float]:
    """The centroid of `sid`'s largest bare-to-all-thread part, in plan mm."""
    from shapely.ops import unary_union

    from digitizer_core import machine
    from digitizer_core.stage6_satin import strip_splits
    from digitizer_core.stitches import strip_ties
    from shapely.geometry import LineString
    import math

    t = machine.COVERAGE_THREAD_W_MM
    segs, cross = [], []
    for _b, r in plan.iter_runs():
        pts = strip_splits(strip_ties(list(r.points)))
        step = 2 if (r.kind == "satin" and r.shape_id == sid) else 1
        made = [LineString([pts[i], pts[i + 1]])
                for i in range(0, len(pts) - 1, step)
                if math.dist(pts[i], pts[i + 1]) > 1e-6]
        (cross if step == 2 else segs).extend(made)
    sewn = unary_union([c.buffer(t / 2.0, cap_style=2) for c in cross + segs])
    bare = polys[sid].difference(sewn)
    part = max(getattr(bare, "geoms", [bare]), key=lambda p: p.area)
    return part.centroid.x, part.centroid.y


def _chrome(img: np.ndarray, px_per_mm: float) -> np.ndarray:
    """A hairline border and a 1 mm scale bar, so a crop carries its own scale."""
    t = img.copy()
    cv2.rectangle(t, (0, 0), (t.shape[1] - 1, t.shape[0] - 1), (60, 60, 60), 1)
    by = t.shape[0] - 14
    cv2.line(t, (14, by), (14 + int(px_per_mm), by), (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(t, "1 mm", (14, by - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 0, 0), 1, cv2.LINE_AA)
    return t


def main(argv: list[str] | None = None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fixture", help="a tools.thin_strokes.REAL_ART name")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--half", type=float, default=3.2, help="crop half-width, mm")
    ap.add_argument("--px-per-mm", type=float, default=60.0)
    ap.add_argument("--shape", default=None)
    ap.add_argument("--at", default=None, help="centre as x,y in plan mm")
    a = ap.parse_args(argv)
    at = tuple(float(v) for v in a.at.split(",")) if a.at else None
    info = draw(a.fixture, a.out, half_mm=a.half, px_per_mm=a.px_per_mm,
                at=at, shape=a.shape)
    print(f"shape {info['shape']}  centre ({info['centre'][0]:.2f}, "
          f"{info['centre'][1]:.2f}) mm  worst {info['worst_mm2']:.2f} mm2")
    for p in info["files"]:
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
